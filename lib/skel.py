from collections import UserList
import paya.lib.mathops as _mo
from paya.util import short, LazyModule
import pymel.util as _pu

r = LazyModule('paya.runtime')

def _getJointSettings(joint):
    return {attrName: joint.attr(attrName
        ).get() for attrName in [
            'rotateOrder', 'rotateAxis', 'jointOrient',
            'radius', 'displayLocalAxis']}

def _applyJointSettings(settings, joint):
    for attrName, value in settings.items():
        joint.attr(attrName).set(value)


class Chain(object):

    #------------------------------------------------------------|    Type management

    def __new__(cls, *joints):
        joints = _pu.expandArgs(*joints)
        cls = getClassFromNumJoints(len(joints))

        return object.__new__(cls)

    def _updateClass(self):
        self.__class__ = getClassFromNumJoints(len(self))

    #------------------------------------------------------------|    Instantiation

    def __init__(self, *joints):
        joints = map(r.PyNode, _pu.expandArgs(*joints))
        self.data = list(joints)

    @classmethod
    def getFromStartEnd(cls, startJoint, endJoint):
        """
        :param startJoint: the root joint for the chain
        :type startJoint: str, :class:`~paya.runtime.nodes.Joint`
        :param endJoint: the end (tip) joint for the chain
        :type endJoint: str, :class:`~paya.runtime.nodes.Joint`
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
        :type startJoint: str, :class:`~paya.runtime.nodes.Joint`
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

    #------------------------------------------------------------|    Construction

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
                wm=matrix, n=i+1,
                under=joints[-1] if joints else under
            )

            joints.append(joint)

        return cls(joints)

    @classmethod
    @short(
        under='u',
        tolerance='tol'
    )
    def createFromPoints(
            cls,
            points,
            downAxis,
            upAxis,
            upVector,
            under=None,
            tolerance=1e-7
    ):
        """
        Builds a chain from points. The side ('up') axis will be calculated
        using cross products, but those will be biased towards the reference
        up vector.

        :param points: a world position for each joint
        :param str downAxis: the 'bone' axis; defaults to
            ``paya.config.downAxis``
        :param str upAxis: the axis to map to the up vector; defaults to
            ``paya.config.upAxis``
        :param upVector: one up vector hint, or one vector per point
        :type upVector: tuple, list, :class:`~paya.runtime.data.Vector`,
            [tuple, list, :class:`~paya.runtime.data.Vector`]
        :param under/u: an optional parent for the chain; defaults to None
        :param float tolerance/tol: see
            :func:`paya.lib.mathops.getChainedAimMatrices`
        :return: The constructed chain.
        :rtype: :class:`Chain`
        """
        matrices = _mo.getChainedAimMatrices(
            points,
            downAxis,
            upAxis,
            upVector,
            tol=tolerance,
            fra=True
        )

        return cls.createFromMatrices(matrices, u=under)

    @classmethod
    @short(tolerance='tol')
    def createFromCurve(
            cls,
            curve,
            numberOrFractions,
            downAxis,
            upAxis,
            upVectorOrCurve,
            tolerance=1e-7
    ):
        """
        Draws a chain (once) along a curve. Either 'aimCurve' or 'upVector'
        must be provided.

        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :param curve: the curve along which to distribute joints
        :type curve: str or :class:`~pymel.core.general.PyNode`
        :param str downAxis: the 'bone' axis
        :param str upAxis: the axis to map to the up vector(s)
        :param upVectorOrCurve: either an up vector, or an up curve
        :type upVectorOrCurve: list, :class:`~paya.runtime.data.Vector`, str,
            :class:`~paya.runtime.nodes.DagNode`
        :param float tolerance/tol: see
            :func:`paya.lib.mathops.getChainedAimMatrices`
        :return: The constructed chain.
        :rtype: :class:`Chain`
        """
        curve = r.PyNode(curve)
        points = curve.distributePoints(numberOrFractions)

        if isinstance(upVectorOrCurve, (str, r.PyNode)):
            aimCurve = r.PyNode(upVectorOrCurve)
            aimVectors = _mo.getAimVectors(points, col=True)
            aimVectors.append(aimVectors[-1])

            upVectors = []

            for point in points:
                upPoint = aimCurve.takeClosestPoint(point)
                upVector = upPoint-point
                upVectors.append(upVector)

        else:
            aimVectors, upVectors = _mo.getFramedAimAndUpVectors(
                points, upVectorOrCurve, tol=tolerance
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

    @short(tolerance='tol')
    def orient(self, downAxis, upAxis, upVector, tolerance=1e-7):
        """
        Orients this chain.

        :param upVector: a reference up vector
        :param str downAxis: the aiming (bone) axis
        :param str upAxis: the axis to map to the up vector
        :type upVector: list, :class:`~paya.runtime.data.Vector`
        :param float tolerance/tol: see
            :func:`paya.lib.mathops.getChainedAimMatrices`
        :return: ``self``
        :rtype: :class:`Chain`
        """
        points = self.points()

        matrices = _mo.getChainedAimMatrices(
            points,
            downAxis,
            upAxis,
            upVector,
            tol=tolerance,
            fra=True
        )

        parents = []

        for joint in self:
            parents.append(joint.getParent())
            joint.setParent(None)

        for joint, point, matrix in zip(self, points, matrices):
            matrix.t = point
            joint.setMatrix(matrix, worldSpace=True)
            r.makeIdentity(joint, apply=True, r=True, jo=False)

        for joint, parent in zip(self, parents):
            joint.setParent(parent)

        return self

    #------------------------------------------------------------|    Standard inspections

    def bones(self):
        """
        :return: One :class:`Bone` instance per overlapping pair of joints.
        :rtype: :class:`list` of :class:`Bone`
        """
        pairs = zip(self, self[1:])
        return [Chain(pair) for pair in pairs]

    @short(plug='p')
    def points(self, plug=False):
        """
        :param bool plug/p: return attributes instead of values; defaults to
            False
        :return: A world position for each joint in this chain.
        :rtype: :class:`list` of :class:`~paya.runtime.data.Point`
        """
        return [joint.getWorldPosition(p=plug) for joint in self]

    @short(plug='p')
    def vectors(self, plug=False):
        """
        :param bool plug/p: return attributes instead of values; defaults to
            False
        :return: A vector for each bone in this chain.
        :rtype: :class:`list` of :class:`~paya.runtime.plugs.Vector`
            or :class:`~paya.runtime.data.Vector`
        """
        points = self.points(p=plug)
        out = []

        for i, thisPoint in enumerate(points[1:], start=1):
            prevPoint = points[i-1]
            out.append(thisPoint-prevPoint)

        return out

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
        :rtype: :class:`float` or :class:`~paya.runtime.plugs.Math1D`
        """
        lengths = [vector.length() for vector in self.vectors(p=plug)]

        if plug:
            pma = r.createNode('plusMinusAverage')

            for i, length in enumerate(lengths):
                length >> pma.attr('input1D')[i]

            return pma.attr('output1D')

        return sum(lengths)

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

    def ratios(self):
        """
        :return: A length ratio for reach joint in this chain.
        :rtype: list of float
        """
        vectors = self.vectors()
        cumulativeLengths = [0.0]

        for vector in vectors:
            cumulativeLength = cumulativeLengths[-1]+vector.length()
            cumulativeLengths.append(cumulativeLength)

        fullLength = cumulativeLengths[-1]

        return [cumulativeLength / fullLength for \
                cumulativeLength in cumulativeLengths]

    #------------------------------------------------------------|    Hierarchy editing

    @staticmethod
    def _resolveRatios(*numberOrRatios):
        numberOrRatios = _pu.expandArgs(*numberOrRatios)
        ln = len(numberOrRatios)

        if ln > 0:
            if len(numberOrRatios) is 1:
                numberOrRatios = numberOrRatios[0]

                if isinstance(numberOrRatios, int):
                    userRatios = _mo.floatRange(0, 1, numberOrRatios+2)[1:-1]

                else:
                    userRatios = [numberOrRatios]

            else:
                userRatios = [min(1, max(0,
                    userRatio)) for userRatio in numberOrRatios]

                userRatios = list(sorted(numberOrRatios))

            return userRatios

        raise RuntimeError("No ratios or number specified.")


    @short(perBone='pb')
    def insertJoints(self, *numberOrRatios, perBone=False):
        """
        Inserts joints into this chain. This is an in-place operation.

        :param \*numberOrRatios: this can be passed either as a single
            integer or one or more floats; if an integer is passed, this
            number of joints will be uniformly distributed along the length
            of this chain; if floats are passed, then joints will be inserted
            at those length ratios
        :type \*numberOrRatios: int, float, list, tuple
        :param bool perBone/pb: perform the operation per bone in the chain;
            defaults to False
        :return: The newly-generated joints.
        :rtype: list of :class:`~paya.runtime.nodes.Joint`
        """
        # Resolve user ratios

        userRatios = self._resolveRatios(*numberOrRatios)
        jointRatios = self.ratios()
        lenSelf = len(self)

        if perBone:
            _userRatios = []

            for i in range(lenSelf-1):
                thisRatio = jointRatios[i]
                nextRatio = jointRatios[i+1]

                _userRatios += [_pu.blend(thisRatio,
                    nextRatio, weight=userRatio) for userRatio in userRatios]

            userRatios = _userRatios

        # Perform insertions

        count = 0
        newMembership = []
        points = self.points()
        newJoints = []

        for i in range(lenSelf-1):
            startRatio = jointRatios[i]
            endRatio = jointRatios[i+1]

            cuts = []

            for userRatio in userRatios:
                if i is lenSelf-2:
                    include = userRatio >= \
                        startRatio and userRatio <= endRatio

                else:
                    include = userRatio >= startRatio and userRatio < endRatio

                if include:
                    localisedRatio = (userRatio
                        -startRatio) / (endRatio-startRatio)

                    cuts.append(localisedRatio)

            theseNewJoints = []

            if cuts:
                startPoint = points[i]
                endPoint = points[i+1]

                settings = _getJointSettings(self[i])
                baseMtx = self[i].getMatrix(worldSpace=True)

                for cut in cuts:
                    joint = r.nodes.Joint.create(
                        under=self[i], n=('insertion', count+1))
                    _applyJointSettings(settings, joint)
                    mtx = baseMtx.copy()
                    mtx.t = _pu.blend(startPoint, endPoint, weight=cut)
                    joint.setMatrix(mtx, worldSpace=True)
                    theseNewJoints.append(joint)
                    count += 1

            newMembership.append(self[i])
            newMembership += theseNewJoints

            if i is lenSelf-2:
                newMembership.append(self[-1])

            newJoints += theseNewJoints

        self[:] = newMembership

        self.compose()
        return newJoints

    def subdivide(self, *iterations):
        """
        Recursively inserts joints to 'subdivide' this chain. This is an in
        place operation. The chain will be edited and its membership updated.

        :param int \*iterations: the number of times to subdivide; defaults to
            1 if omitted
        :return: The newly-generated joints.
        :rtype: list of :class:`~paya.runtime.nodes.Joint`
        """
        if iterations:
            iterations = iterations[0]

        else:
            iterations = 1

        ratios = self.ratios()
        origIndices = range(len(self))

        for x in range(iterations):
            _ratios = []

            for i, thisRatio in enumerate(ratios[:-1]):
                nextRatio = ratios[i+1]
                midRatio = _pu.blend(thisRatio, nextRatio)
                _ratios += [thisRatio, midRatio]

            _ratios.append(ratios[-1])
            ratios = _ratios
            origIndices = [origIndex * 2 for origIndex in origIndices]

        ratios = [ratios[x] for x in range(
            len(ratios)) if x not in origIndices]

        return self.insertJoints(ratios)

    @short(name='n', start='sn')
    def duplicate(self, name=None, startNumber=1):
        """
        Duplicates this chain, with smart reparenting if it's not contiguous.

        :param name/n: one or more name elements
        :type name/n: list, str, int
        :param int startNumber/sn: the number to start from; defaults to 1
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
            _name = r.nodes.Joint.makeName(name, i+startNumber)
            copy = joint.duplicate(n=_name, po=True)[0].releaseSRT()
            copies.append(copy)

        for copy, parent in zip(copies, parents):
            if isinstance(parent, int):
                parent = copies[parent]

            copy.setParent(parent)

        return Chain(copies)

    @short(startNumber='sn')
    def rename(self, *elems, startNumber=1):
        """
        Renames this chain. Numbers will be added before the suffix.

        :param \*elems: one or more name elements
        :type \*elems: list, str, int
        :param int startNumber/sn: the number to start from; defaults to 1
        :return: ``self``
        """
        for i, joint in enumerate(self):
            name = r.nodes.Joint.makeName(*elems, i+startNumber)
            joint.rename(name)

        return self

    def compose(self):
        """
        Ensures that every member of this chain is a child of its predecessor.
        """
        for i, joint in enumerate(self[1:], start=1):
            newParent = self[i-1]

            currentParent = joint.getParent()

            if currentParent is None or currentParent != newParent:
                joint.setParent(newParent)

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

    #------------------------------------------------------------|    IK management

    @short(distance='d')
    def getPolePoint(self, distance=1.0):
        """
        This method creates a temporary IK handle and samples its default
        ``poleVector`` value. For this reason it will be affected by any
        ``preferredAngle`` values.

        :param distance/d: the pole point's distance from the chain's chord
            vector axis; defaults to 1.0
        :type distance/d: float or int
        :return: An inert world-position point target for a pole vector
            constraint or
            :meth:`~paya.runtime.nodes.IkHandle.setPolePoint`.
        :rtype: :class:`~paya.runtime.data.Point`
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
        poleVec *= distance

        return anchorPt + poleVec

    def ikHandles(self):
        """
        :return: IK handles affecting this chain.
        :rtype: :class:`list` of :class:`~paya.runtime.nodes.IkHandle`
        """
        out = []

        for joint in self:
            out += joint.ikHandles()

        return list(set(out))

    @short(
        solver='sol',
        startJoint='sj',
        endEffector='ee'
    )
    def createIkHandle(self, **kwargs):
        """
        Creates an IK handle for this chain.

        :param \**kwargs: forwarded to
            :meth:`paya.runtime.nodes.IkHandle.create` with the following
            modifications:

            -   ``startJoint`` and ``endJoint`` are overriden to the start and
                end joints of this chain, respectively
            -   Unless specified, the solver defaults to ``ikSCsolver`` if
                there are only two joints in this chain, and ``ikRPsolver``
                otherwise

        :return: The IK handle.
        :rtype: :class:`~paya.runtime.nodes.IkHandle`
        """

        settings = {
            'solver': 'ikRPsolver' if len(self) > 2 else 'ikSCsolver'
        }

        settings.update(kwargs)
        settings['startJoint'] = self[0]
        settings['endEffector'] = self[-1]

        return r.nodes.IkHandle.create(**settings)

    def createIkHandles(self):
        """
        Creates one IK handle per bone in this chain. The IK handles will
        all use a single-chain solver. The IK handles will be numbered.
        Prefixes and padding can be specified using a
        :class:`~paya.lib.name.Name` block.

        :return: The IK handles
        :rtype: :class:`list` of :class:`~paya.runtime.nodes.IkHandle`
        """
        out = []

        for i, bone in enumerate(self.bones()):
            with r.Name(i+1):
                out.append(bone.createIkHandle())

        return out

    @short(upVector='upv', flip='fl')
    def autoPreferredAngle(self, upAxis, upVector=None):
        """
        Automatically configures ``preferredAngle`` on the internal joints to
        prevent lockout when creating an IK handle on an in-line chain.

        :param upAxis: the dominant chain 'bend' axis, e.g. '-x'
        :param upVector/upv: an optional 'up' vector; used to override wind
            direction
        :type upVector/upv: list, tuple or
            :class:`~paya.runtime.data.Vector`
        :raises AssertionError: the chain is not contiguous
        :return: ``self``
        :rtype: :class:`Chain`
        """
        assert self.contiguous(), "The chain is not contiguous."

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

    #------------------------------------------------------------|    Higher-level rigging

    def _getTwistMap(self, twistChain):
        # Maps bones on this chain to sub-chains on 'twistChain' by proximity.

        slaveAnchors = [joint.closestOf(twistChain) for joint in self]
        slaveIndices = [twistChain.index(joint) for joint in slaveAnchors]

        out = []

        for i in range(len(self)-1):
            masterBone = self[i:i+2]
            slaveChain = twistChain[slaveIndices[i]:slaveIndices[i+1]+1]
            out.append([masterBone, slaveChain])

        return out

    @short(
        downAxis='da',
        startUpMatrix='sum',
        endUpMatrix='eum',
        maintainOffset='mo',
        decompose='dec',
        skipEnd='ske'
    )
    def driveTwistChain(
            self,
            twistChain,
            upAxis,
            globalScale,
            downAxis=None,
            startUpMatrix=None,
            endUpMatrix=None,
            maintainOffset=False,
            decompose=False,
            skipEnd=False
    ):
        """
        Drives a twist chain that was generated by duplicating this chain
        and calling :meth:`subdivide` or :meth:`insertJoints` on the
        duplicate. This method has no return value.

        :param twistChain: the chain to drive
        :type twistChain: :class:`Chain`
        :param str upAxis: the dominant 'curl' axis on this chain, e.g. 'x'
        :param globalScale: a global scaling factor to normalize stretch
        :type globalScale: int, float, :class:`~paya.runtime.plugs.Math1D`
        :param downAxis/da: if you already know this chain's 'down' axis,
            specify it here; defaults to None
        :type downAxis/da: str, None
        :param startUpMatrix/sum: an optional alternative matrix to govern
            the start up vector (useful for effects like 'fixing' upper
            shoulder twist); defaults to None
        :type startUpMatrix/sum: None, list, tuple,
            :class:`paya.runtime.plugs.Matrix`,
            :class:`paya.runtime.data.Matrix`
        :param endUpMatrix/eum: an optional alternative matrix to govern
            the end up vector; defaults to None
        :type endUpMatrix/eum: None, list, tuple,
            :class:`paya.runtime.plugs.Matrix`,
            :class:`paya.runtime.data.Matrix`
        :param bool maintainOffset/mo: preserve offsets when applying
            matrix connections; defaults to False
        :param bool decompose/dec: drive by connecting into SRT channels
            instead of offsetParentMatrix; defaults to False
        :param bool skipEnd/ske: don't drive the end joint; defaults to False
        """
        twistMap = self._getTwistMap(twistChain)
        num = len(twistMap)

        for i, pair in enumerate(twistMap):
            masterBone, slaveChain = pair

            if i is 0:
                _startUpMatrix = startUpMatrix
                _endUpMatrix = None
                _skipEnd = False

            elif i is num-1:
                _startUpMatrix = None
                _endUpMatrix = endUpMatrix
                _skipEnd = skipEnd

            else:
                _startUpMatrix = _endUpMatrix = None
                _skipEnd = False

            masterBone._driveTwistChain(
                slaveChain,
                upAxis,
                globalScale,
                da=downAxis,
                sum=_startUpMatrix,
                eum=_endUpMatrix,
                mo=maintainOffset,
                dec=decompose,
                ske=_skipEnd
            )

    #------------------------------------------------------------|    List interface

    @property
    def index(self):
        return self.data.index

    @property
    def __len__(self):
        return self.data.__len__

    def __getitem__(self, item):
        result = self.data.__getitem__(item)

        if isinstance(item, slice):
            result = Chain(result)

        return result

    def __add__(self, other):
        result = list(self) + list(other)
        return Chain(result)

    def __iadd__(self, other):
        result = list(self) + list(other)
        self.data = result

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            value = list(value)

        self.data.__setitem__(key, value)
        self._updateClass()

    def __delitem__(self, key):
        self.data.__delitem__(key)
        self._updateClass()

    def __iter__(self):
        return iter(self.data)

    def __repr__(self):
        return repr(self.data)

    @property
    def pop(self):
        return self.data.pop


class Bone(Chain):

    #------------------------------------------------------------|    Standard inspections

    def bones(self):
        """
        :return: One :class:`Bone` instance per overlapping pair of joints.
        :rtype: :class:`list` of :class:`Bone`
        """
        return [self]

    def ratios(self):
        """
        :return: A length ratio for reach joint in this chain.
        :rtype: list of float
        """
        return [0.0, 1.0]

    @short(plug='p')
    def vector(self, plug=False):
        """
        :param bool plug/p: return an attribute instead of a value;
            defaults to False
        :return: The vector for this bone.
        :rtype: :class:`paya.runtime.data.Vector` or
            :class:`paya.runtime.plugs.Vector`
        """
        points = self.points(p=plug)
        return points[-1]-points[0]

    #------------------------------------------------------------|    Higher-level rigging

    @short(
        skipEnd='ske',
        downAxis='da',
        startUpMatrix='sum',
        endUpMatrix='eum',
        maintainOffset='mo',
        decompose='dec'
    )
    def _driveTwistChain(
            self,
            twistChain,
            upAxis,
            globalScale,
            downAxis=None,
            startUpMatrix=None,
            endUpMatrix=None,
            maintainOffset=False,
            decompose=False,
            skipEnd=False
    ):
        numSlaves = len(twistChain)

        if numSlaves < 2:
            raise RuntimeError("Need two or more joints on the twist chain.")

        globalScale = _mo.info(globalScale)[0]

        if downAxis is None:
            downAxis = self.downAxis()

        if startUpMatrix is None:
            startUpMatrix = self[0].attr('wm')

        points = self.points(p=True)
        downVector = points[1]-points[0]

        if startUpMatrix is None:
            startUpVector = self[0].attr('wm').getAxis(upAxis)

        else:
            startUpMatrix = _mo.info(startUpMatrix)[0]
            startUpVector = self[0].getMatrix(worldSpace=True).getAxis(upAxis)
            startUpVector *= startUpMatrix.asOffset()
            startUpVector.rejectFrom(downVector)

        _downAxis = downAxis.strip('-')
        _upAxis = upAxis.strip('-')
        thirdAxis = [ax for ax in 'xyz' if ax not in (_downAxis, _upAxis)][0]

        liveLen = downVector.length()
        nativeLen = liveLen.get() * globalScale
        boneScale = liveLen / nativeLen

        smtx = r.createScaleMatrix(
            _downAxis, boneScale,
            _upAxis, globalScale,
            thirdAxis, globalScale
        )

        matrices = []

        if numSlaves is 2:
            matrix = smtx * r.createMatrix(
                downAxis, downVector,
                upAxis, startUpVector,
                t=points[0]
            ).pk(t=True, r=True)

            matrices.append(matrix)

            if not skipEnd:
                matrices.append(self[1].attr('wm'))

        else:
            # Resolve end up vector

            if endUpMatrix is None:
                endUpMatrix = self[1].attr('wm')

            else:
                endUpMatrix = _mo.info(endUpMatrix)[0]

            endUpVector = startUpVector.get() * endUpMatrix.asOffset()
            endUpVector = endUpVector.rejectFrom(downVector)

            # Get slave ratios
            slaveRatios = twistChain.ratios()

            # Iterate

            for i, slave in enumerate(twistChain):
                if i is 0:
                    upVector = startUpVector
                    point = points[0]

                elif i is numSlaves-1:
                    if not skipEnd:
                        matrices.append(self[1].attr('wm'))

                    break

                else:
                    upVector = startUpVector.blend(
                        endUpVector,
                        bva=True,
                        w=slaveRatios[i]
                    )

                    point = points[0].blend(points[1], w=slaveRatios[i])

                matrix = smtx * r.createMatrix(
                    downAxis, downVector,
                    upAxis, upVector,
                    t=points[0]
                ).pk(t=True, r=True)

                matrices.append(matrix)

            for i, matrix in enumerate(matrices):
                slaveJoint = twistChain[i]

                if decompose:
                    matrix *= slaveJoint.attr('pim')[0]

                    if maintainOffset:
                        matrix = slaveJoint.getMatrix() * matrix.asOffset()

                    matrix.decomposeAndApply(slaveJoint)

                else:
                    matrix = slaveJoint.getMatrix(
                        worldSpace=True) * matrix.asOffset()

                    matrix = slaveJoint.getMatrix().inverse() * matrix
                    matrix >> slaveJoint.attr('opm')
                    slaveJoint.attr('it').set(False)

def getClassFromNumJoints(numJoints):
    return {2: Bone}.get(numJoints, Chain)
