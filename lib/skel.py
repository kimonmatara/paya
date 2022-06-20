from collections import UserList

from paya.config import defaultDownAxis, defaultUpAxis
import paya.lib.mathops as _mo
from paya.util import short, LazyModule
import pymel.util as _pu

r = LazyModule('paya.runtime')


class Chain(UserList):
    __solver__ = 'ikRPsolver'

    #------------------------------------------------------------|    Instantiation

    def __new__(cls, *joints):
        if cls is Chain:
            joints = _pu.expandArgs(*joints)
            num = len(joints)

            if num is 2:
                cls = Bone

            elif num is 3:
                cls = Triad

        return object.__new__(cls)

    def __init__(self, *joints):
        """
        :param \*joints: the joint content for the
            :class:`~paya.lib.skel.Chain` instance
        """
        joints = _pu.expandArgs(*joints)
        joints = map(r.PyNode, joints)
        super(Chain, self).__init__(joints)

    #------------------------------------------------------------|    Constructors

    @classmethod
    def getFromStartEnd(cls, startJoint, endJoint):
        """
        :param startJoint: the root joint for the chain
        :type startJoint: str, :class:`~paya.nodetypes.joint.Joint`
        :param endJoint: the end (tip) joint for the chain
        :type endJoint: str, :class:`~paya.nodetypes.joint.Joint`
        :return: A chain from the start joint to the end joint, inclusively.
        :rtype: :class:`Chain`
        """
        startJoint = r.PyNode(startJoint)
        endJoint = r.PyNode(endJoint)

        stack = list(reversed(endJoint.getParent(None)))

        try:
            startIndex = stack.index(startJoint)

        except ValueError:
            raise RuntimeError(
                "Could not determine a path from the start joint to "+
                "the end joint."
            )

        return cls(stack[startIndex:]+[endJoint])

    @classmethod
    def getFromRoot(cls, rootJoint):
        """
        :param startJoint: the root joint for the chain
        :type startJoint: str, :class:`~paya.nodetypes.joint.Joint`
        :return: A chain from the specified root joint. The chain will
            terminate before the first branch.
        :rtype: :class:`Chain`
        """
        out = [r.PyNode(rootJoint)]

        while True:
            children = out[-1].getChildren(type='joint')

            if len(children) is 1:
                out += children

            else:
                break

        return cls(out)

    @classmethod
    @short(under='u')
    def createFromMatrices(cls, matrices, under=None):
        """
        Creates a chain from matrices. The joints will match the matrices
        exactly; no attempt is made to orient the chain.

        :param matrices: the matrices to use
        :param under/u: an optional parent for the chain; defaults to None
        :return: :class:`Chain`
        """
        joints = []

        for i, matrix in enumerate(matrices):
            joint = r.nodes.Joint.create(
                wm=matrix,
                n=i+1,
                under=joints[-1] if joints else under
            )

            joints.append(joint)

        return cls(joints)

    @classmethod
    @short(
        downAxis='da',
        upAxis='ua',
        under='u',
        tolerance='tol'
    )
    def createFromPoints(
            cls,
            points,
            upVector,
            downAxis=defaultDownAxis,
            upAxis=defaultUpAxis,
            under=None,
            tolerance=1e-7
    ):
        """
        Builds a chain from points. The side ('up') axis will be calculated
        using cross products, but those will be biased towards the reference
        up vector.

        :param points: a world position for each joint
        :param upVector: the reference up vector
        :param str downAxis/da: the 'bone' axis; defaults to
            ``paya.config.defaultDownAxis``
        :param str upAxis/ua: the axis to map to the up vector; defaults to
            ``paya.config.defaultUpAxis``
        :param under/u: an optional parent for the chain; defaults to None
        :param float tolerance/tol: see
            :func:`paya.lib.mathops.getAimingMatricesFromPoints`
        :return: The constructed chain.
        :rtype: :class:`Chain`
        """
        matrices = _mo.getAimingMatricesFromPoints(
            points,
            upVector,
            da=downAxis,
            ua=upAxis,
            tol=tolerance
        )

        return cls.createFromMatrices(matrices, u=under)

    @classmethod
    @short(
        upCurve='upc',
        upVector='upv',
        downAxis='da',
        upAxis='ua',
        tolerance='tol'
    )
    def createFromCurve(
            cls,
            curve,
            numberOrFractions,
            upCurve=None,
            upVector=None,
            downAxis=defaultDownAxis,
            upAxis=defaultUpAxis,
            tolerance=1e-7
    ):
        """
        Draws a chain (once) along a curve. Either 'upCurve' or 'upVector'
        must be provided.

        :param curve: the curve along which to distribute joints
        :type curve: str or :class:`~pymel.core.general.PyNode`
        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :param upCurve/upc: a curve to aim towards; defaults to None
        :type upCurve/upc: str or :class:`~pymel.core.general.PyNode`
        :param upVector/upv: a reference up vector
        :type upVector/upv: list, tuple or
            :class:`~paya.datatypes.vector.Vector`
        :param str downAxis/da: the 'bone' axis; defaults to
            ``paya.config.defaultDownAxis``
        :param str upAxis/ua: the axis to map to the up vector(s); defaults to
            ``paya.config.defaultUpAxis``
        :param float tolerance/tol: see
            :func:`paya.lib.mathops.getAimingMatricesFromPoints`
        :return: The constructed chain.
        :rtype: :class:`Chain`
        """
        if upCurve:
            upCurve = r.PyNode(upCurve)

        elif upVector:
            upVector = r.data.Vector(upVector)

        else:
            raise RuntimeError(
                "Please provide either 'upCurve' or 'upVector'."
            )

        curve = r.PyNode(curve)
        points = curve.distributePoints(numberOrFractions)

        if upCurve:
            aimVectors = _mo.getAimVectorsFromPoints(points)
            aimVectors.append(aimVectors[-1])

            upVectors = []

            for point in points:
                upPoint = upCurve.takeClosestPoint(point)
                upVector = upPoint-point
                upVectors.append(upVector)

        else:
            aimVectors, upVectors = _mo.getAimAndUpVectorsFromPoints(
                points, upVector, tol=tolerance
            )

        matrices = []

        for point, aimVector, upVector in zip(
            points, aimVectors, upVectors
        ):
            matrix = r.createMatrix(
                downAxis, aimVector,
                upAxis, upVector,
                t=point
            ).pk(t=True, r=True)

            matrices.append(matrix)

        return cls.createFromMatrices(matrices)

    #------------------------------------------------------------|    Orient

    @short(
        tolerance='tol',
        downAxis='da',
        upAxis='ua'
    )
    def orient(
            self,
            upVector,
            downAxis=defaultDownAxis,
            upAxis=defaultUpAxis,
            tolerance=1e-7
    ):
        """
        Orients this chain.

        :param upVector: a reference up vector
        :type upVector: list, :class:`~paya.datatypes.vector.Vector`
        :param str downAxis/da: the aiming (bone) axis; defaults to
            :attr:`paya.config.defaultDownAxis`
        :param str upAxis: the axis to map to the up vector; defaults to
            :attr:`paya.config.defaultUpAxis`
        :param float tolerance/tol: see
            :func:`paya.lib.mathops.getAimingMatricesFromPoints`
        :return: ``self``
        :rtype: :class:`Chain`
        """
        points = self.points()

        matrices = _mo.getAimingMatricesFromPoints(
            points,
            upVector,
            da=downAxis,
            ua=upAxis,
            tol=tolerance
        )

        self.explode()

        for joint, point, matrix in zip(self, points, matrices):
            matrix.t = point
            joint.setMatrix(matrix, worldSpace=True)
            r.makeIdentity(joint, apply=True, r=True, jo=False)

        return self.compose()

    #------------------------------------------------------------|    Inspections

    def bones(self):
        """
        :return: A :class:`~paya.lib.skel.Bone` instance for every joint pair
            in the chain.
        :rtype: :class:`~paya.lib.skel.Bone`
        """
        pairs = zip(self, self[1:])
        bones = map(Bone, pairs)
        return list(bones)

    @short(plug='p')
    def vectors(self, plug=False):
        """
        :param bool plug/p: return attributes instead of values; defaults to
            False
        :return: A vector for each bone in this chain.
        :rtype: :class:`list` of :class:`~paya.plugtypes.vector.Vector`
            or :class:`~paya.datatypes.vector.Vector`
        """
        points = self.points(p=plug)
        out = []

        for i, thisPoint in enumerate(points[1:], start=1):
            prevPoint = points[i-1]
            out.append(thisPoint-prevPoint)

        return out

    @short(plug='p')
    def points(self, plug=False):
        """
        :param bool plug/p: return attributes instead of values; defaults to
            False
        :return: A world position for each joint in this chain.
        :rtype: :class:`list` of :class:`~paya.datatypes.point.Point`
        """
        return [joint.gwp(p=plug) for joint in self]

    def contiguous(self):
        """
        :return: True if every member of this chain is a child of its
            predecessor, otherwise False.
        :rtype: bool
        """
        for i, joint in enumerate(self[1:], start=1):
            parent = joint.getParent()

            if parent is None or parent != self[i-1]:
                return False

        return True

    def roots(self):
        """
        :return: The first joint, and any member which is not a child of its
            predecessor.
        :rtype: list
        """
        out = []

        if self:
            out.append(self[0])

            for i, joint in enumerate(self[1:], start=1):
                parent = joint.getParent()

                if parent is None or parent != self[i-1]:
                    out.append(joint)

        return out

    @short(plug='p')
    def length(self, plug=False):
        """
        :param bool plug/p: return an attribute instead of a value; defaults
            to False
        :return: The length of this chain.
        :rtype: :class:`float` or :class:`~paya.plugtypes.math1D.Math1D`
        """
        lengths = [vector.length() for vector in self.vectors(p=plug)]

        if plug:
            pma = r.createNode('plusMinusAverage')

            for i, length in enumerate(lengths):
                length >> pma.attr('input1D')[i]

            return pma.attr('output1D')

        return sum(lengths)

    @short(
        skipNumberingIfSingle='sns',
        startNumber='sn',
        name='n',
        inheritNames='inn',
        suffix='suf'
    )
    def insertJointsAtRatios(
            self,
            ratios,
            skipNumberingIfSingle=True,
            startNumber=1,
            name=None,
            inheritNames=True,
            suffix=None
    ):
        """
        Inserts joints at the specified ratios, 'subdividing' the chain.
        This is an in-place operation, and this Chain instance's membership
        will be modified.

        :param list ratios: the ratios at which to insert joints
        :param bool skipNumberingIfSingle/sns: if only one ratio is specified,
            don't add numbering; defaults to True
        :param int startNumber/sn: for joint names, the starting number;
            defaults to 1
        :param name/n: one or more name elements; defaults to None
        :type name/n: None, str, int, list or tuple
        :param bool inheritNames/inn: inherit names from
            :class:`~paya.lib.names.Name` blocks; defaults to True
        :param suffix/suf: if string, append to name; if ``True``, look up a
            type suffix; if ``False``, omit suffixes; defaults to
            :attr:`paya.config.autoSuffix`
        :raises AssertionError: not all ratios are in the 0.0 -> 1.0 range
        :return: The new joints.
        :rtype: :class:`list`
        """
        assert all([ratio >= 0.0 and ratio <= 1.0 for ratio in ratios]), \
            "Ratios must be in the 0.0 -> 1.0 range."

        numRatios = len(ratios)

        points = self.points()
        vectors = []
        cumulativeLengths = [0.0]

        for i, thisPoint in enumerate(points[1:], start=1):
            prevPoint = points[i-1]
            vector = thisPoint-prevPoint
            vectors.append(vector)
            cumulativeLengths.append(
                cumulativeLengths[-1] + vector.length())

        fullLength = cumulativeLengths[-1]
        jointRatios = [0.0] + [cumulativeLength / fullLength for \
                          cumulativeLength in cumulativeLengths[1:]]

        insertions = {}

        for i, ratio in enumerate(ratios):

            for ii, thisJoint in enumerate(self[:-1]):
                thisRatio = jointRatios[ii]
                nextRatio = jointRatios[ii+1]

                if ratio >= thisRatio and ratio <= nextRatio:
                    startPoint = points[ii]
                    vector = vectors[ii]

                    localRatio = (ratio-thisRatio) / (nextRatio-thisRatio)
                    point = startPoint + vector * localRatio

                    nameElems = [name]

                    if not(skipNumberingIfSingle and numRatios is 1):
                        nameElems.append(i+startNumber)

                    thisName = r.nodes.Joint.makeName(
                        nameElems, suf=suffix, inn=inheritNames)

                    joint = thisJoint.duplicate(po=True, n=thisName)[0]
                    joint.releaseSRT()

                    matrix = thisJoint.getMatrix(worldSpace=True)
                    matrix.t = point

                    joint.setMatrix(matrix, worldSpace=True)
                    pool = insertions.setdefault(thisJoint, [])
                    pool += [joint]

                    break

        newMembership = []

        for i, joint in enumerate(self):
            newMembership.append(joint)

            try:
                newMembership += insertions[joint]

            except KeyError:
                continue

        self.data[:] = newMembership
        self._updateClass()
        self.compose()

        return [insertion[1] for insertion in insertions]

    def skinClusters(self):
        """
        :return: Any skinClusters associated with any joint in this chain, in
            no particular order.
        :rtype: list
        """
        out = []

        for joint in self:
            out += joint.skinClusters()

        return list(set(out))

    def ikHandles(self):
        """
        :return: IK handles affecting this chain.
        :rtype: :class:`list` of :class:`~paya.nodetypes.ikHandle.IkHandle`
        """
        out = []

        for joint in self:
            out += joint.ikHandles()

        return list(set(out))

    def downAxis(self):
        """
        :return: The 'bone' axis of this chain (e.g. 'x')
        :rtype: str
        """
        axes = []

        for i, thisJoint in enumerate(self[:-1]):
            thisPoint = thisJoint.getWorldPosition()
            nextJoint = self[i+1]
            nextPoint = nextJoint.getWorldPosition()

            vector = nextPoint-thisPoint
            matrix = thisJoint.getMatrix(worldSpace=True)

            axes.append(matrix.closestAxisToVector(vector))

        axes.sort(key=lambda x: axes.count(x))
        return axes[-1]

    #------------------------------------------------------------|    DAG editing

    @short(name='n', inheritName='inn', suffix='suf', start='s')
    def duplicate(self, name=None, inheritName=True, suffix=None, start=1):
        """
        Duplicates this chain, with smart reparenting if it's not contiguous.

        :param name/n: one or more name elements
        :type name/n: list, str, int
        :param bool inheritName/inn: inherit from
            :class:`~paya.lib.names.Name` blocks; defaults to True
        :param bool suffix/suf: if string, append; if True, apply the joint
            suffix; if False; omit suffix; defaults to
            :attr:`paya.config.autoSuffix`
        :param int start/s: the number to start from; defaults to 1
        :return: The chain duplicate.
        :rtype: :class:`~paya.lib.skel.Chain`
        """
        parents = []

        for i, joint in enumerate(self):
            parent = joint.getParent()

            if i > 0 and parent is not None:
                try:
                    parent = self.index(parent)

                except ValueError:
                    pass

            parents.append(parent)

        copies = []

        for i, joint in enumerate(self):
            _name = r.nodes.Joint.makeName(
                name, i+start, suf=suffix, inn=inheritName)

            copy = joint.duplicate(n=_name, po=True)[0].releaseSRT()
            copies.append(copy)

        for copy, parent in zip(copies, parents):
            if isinstance(parent, int):
                parent = copies[parent]

            copy.setParent(parent)

        return Chain(copies)

    @short(inheritName='inn',suffix='suf', start='s')
    def rename(self, *elems, inheritName=True, suffix=None, start=1):
        """
        Renames this chain. Numbers will be added before the suffix.

        :param \*elems: one or more name elements
        :type \*elems: list, str, int
        :param bool inheritName/inn: inherit from
            :class:`~paya.lib.names.Name` blocks; defaults to True
        :param bool suffix/suf: if string, append; if True, apply the joint
            suffix; if False; omit suffix; defaults to
            :attr:`paya.config.autoSuffix`
        :param int start/s: the number to start from; defaults to 1
        :return: ``self``
        """
        for i, joint in enumerate(self):
            with r.Name(i+start):
                name = r.nodes.Joint.makeName(
                    *elems, inn=inheritName, suf=suffix)
                joint.rename(name)

        return self

    def compose(self):
        """
        Ensures that every member of this chain is a child of its predecessor.
        """
        for i, joint in enumerate(self[1:], start=1):
            joint.setParent(self[i-1])

        return self

    def explode(self):
        """
        Reparents every joint under the parent of the first joint.
        """
        if self:
            rootParent = self[0].getParent()

            for joint in self[1:]:
                joint.setParent(rootParent)

        return self

    @short(replaceTip='rt')
    def appendChain(self, otherChain, replaceTip=True):
        """
        This is an in-place operation. Splices ``otherChain`` to the bottom of
        this chain and updates the membership.

        :param otherChain: the chain to append to this one
        :type otherChain: list or :class:`Chain`
        :param bool replaceTip/rt: replace this chain's tip joint; defaults
            to True
        :return: ``self``
        :rtype: :class:`Chain`
        """
        if replaceTip:
            tip = self.pop(-1)
            r.delete(tip)

        r.parent(otherChain[0], self[-1])
        self += otherChain
        self._updateClass()
        return self

    #------------------------------------------------------------|    Pole vector management

    @short(distance='d')
    def getDefaultPolePoint(self, distance=1.0):
        """
        This method creates a temporary IK handle and samples its default
        ``poleVector`` value. For this reason it will be affected by any
        ``preferredAngle`` values.

        :param distance/d: the pole point's distance from the chain's chord
            vector axis; defaults to 1.0
        :type distance/d: float or int
        :return: An inert world-position point target for a pole vector
            constraint or
            :meth:`~paya.nodetypes.ikhandle.IkHandle.setPolePoint`.
        :rtype: :class:`~paya.datatypes.point.Point`
        """
        dup = self.duplicate().compose()
        ikh = dup.createIkHandle(solver='ikRPsolver')
        poleVec = ikh.attr('poleVector').get() * ikh.attr('pm')[0].get()
        r.delete(ikh, dup)

        chordStart = self[0].getWorldPosition()
        chordEnd = self[-1].getWorldPosition()
        chordVec = chordEnd-chordStart

        anchorPt = chordStart + (chordVec * 0.5)

        x1 = chordVec.cross(poleVec)
        poleVec = x1.cross(chordVec).normal()

        return anchorPt + (poleVec * distance)

    @short(upVector='upv', flip='fl')
    def autoPreferredAngle(self, upAxis, upVector=None):
        """
        Automatically configures ``preferredAngle`` on the internal joints to
        prevent lockout when creating an IK handle on an in-line chain.

        :param upAxis: the dominant chain 'bend' axis, e.g. '-x'
        :param upVector/upv: an optional 'up' vector; used to override wind
            direction
        :type upVector/upv: list, tuple or
            :class:`~paya.datatypes.vector.Vector`
        :raises AssertionError: the chain is not contiguous
        :return: ``self``
        :rtype: :class:`Chain`
        """
        assert self.isContiguous(), "The chain is not contiguous."

        val = _pu.radians(22.5)

        if '-' in upAxis:
            val *= -1.0

        upAxis = upAxis.strip('-')
        axisIndex = 'xyz'.index(upAxis)

        if upVector:
            upVector = r.data.Vector(upVector).normal()

        for joint in self[1:-1]:
            thisVal = val

            if upVector:
                upAxisVector = joint.getMatrix(
                    worldSpace=True).getAxis(upAxis).normal()

                negUpAxisVector = -upAxisVector

                dot = upAxisVector.dot(upVector)
                negDot = negUpAxisVector.dot(upVector)

                if negDot > dot:
                    thisVal *= -1.0

            euler = [0.0, 0.0, 0.0]
            euler[axisIndex] = thisVal
            euler = r.data.EulerRotation(euler, unit='radians')

            joint.attr('preferredAngle').set(euler)

        return self

    #------------------------------------------------------------|    Pose management

    def reset(self):
        """
        Sets rotations on every joint of this chain to [0.0, 0.0, 0.0].

        :return: ``self``
        """
        for joint in self:
            for ax in 'xyz':
                attr = joint.attr('r'+ax)
                try:
                    attr.set(0.0)

                except:
                    r.warning("Couldn't set attribute: {}".format(attr))

        return self

    #------------------------------------------------------------|    IK

    @short(
        solver='sol',
        startJoint='sj',
        endEffector='ee'
    )
    def createIkHandle(self, solver=None, **createOptions):
        """
        Creates an IK handle for this chain.

        :param str solver/sol: the solver to use; defaults to 'ikRPsolver' if
            this chain has more than two joints, otherwise 'ikSCsolver'
        :param \*\*createOptions: all overflow arguments are forwarded to
            :meth:`~paya.nodetypes.ikHandle.IkHandle.create`
        :return: The IK handle.
        :rtype: :class:`~paya.nodetypes.ikHandle.IkHandle`
        """
        ln = len(self)

        if ln < 2:
            raise RuntimeError("Need two or more joints.")

        if solver is None:
            solver = self.__solver__

        createOptions['solver'] = solver
        createOptions['startJoint'] = self[0]
        createOptions['endEffector'] = self[-1]

        return r.nodes.IkHandle.create(**createOptions)

    def createIkHandles(self):
        """
        Creates One IK handle per bone in this chain. The IK handles will
        all use a single-chain solver.

        :return: The IK handles
        :rtype: :class:`list` of :class:`~paya.nodetypes.ikHandle.IkHandle`
        """
        out = []

        for i, bone in enumerate(self.bones()):
            with r.Name(i+1):
                out.append(bone.createIkHandle())

        return out

    #------------------------------------------------------------|    Type management

    def _updateClass(self):
        self.__class__ =  {2: Bone, 3: Triad}.get(len(self), Chain)

    #------------------------------------------------------------|    Repr

    def __repr__(self):
        ln = len(self)

        if ln > 2:
            content = '[{}...{}]'.format(repr(self[0]), repr(self[-1]))

        else:
            content = repr(self.data)

        return "{}({})".format(self.__class__.__name__, content)


class Bone(Chain):
    """
    A specialised subclass of :class:`~paya.lib.skel.Chain` for two-joint
    chains.
    """
    __solver__ = 'ikSCsolver'

    @short(
        skipNumberingIfSingle='sns',
        startNumber='sn',
        name='n',
        inheritNames='inn',
        suffix='suf'
    )
    def insertJoints(
            self,
            number,
            skipNumberingIfSingle=True,
            startNumber=1,
            name=None,
            inheritNames=True,
            suffix=None
    ):
        """
        Variant of :meth:`~Chain.insertJointsAtRatios`; inserts joints
        uniformly along the bone.

        :param int number: the number of joints to insert
        :param bool skipNumberingIfSingle/sns: if only one ratio is specified,
            don't add numbering; defaults to True
        :param int startNumber/sn: for joint names, the starting number;
            defaults to 1
        :param name/n: one or more name elements; defaults to None
        :type name/n: None, str, int, list or tuple
        :param bool inheritNames/inn: inherit names from
            :class:`~paya.lib.names.Name` blocks; defaults to True
        :param suffix/suf: if string, append to name; if ``True``, look up a
            type suffix; if ``False``, omit suffixes; defaults to
            :attr:`paya.config.autoSuffix`
        :return: The new joints.
        :rtype: :class:`list`
        """
        ratios = _mo.floatRange(0, 1, number+2)[1:-1]

        return self.insertJointsAtRatios(
            ratios,
            sns=skipNumberingIfSingle,
            sn=startNumber,
            n=name,
            inn=inheritNames,
            suf=suffix
        )


class Triad(Chain):
    """
    A specialised subclass of :class:`~paya.lib.skel.Chain` for three-joint
    chains.
    """