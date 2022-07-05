from collections import UserList
import paya.lib.mathops as _mo
from paya.util import short, LazyModule
import pymel.util as _pu

r = LazyModule('paya.runtime')


class Chain(UserList):

    #------------------------------------------------------------|    Instantiation

    def __init__(self, *joints):
        joints = map(r.PyNode, _pu.expandArgs(*joints))
        super(Chain, self).__init__(joints)

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
                wm=matrix.pick(t=True, r=True),
                n=i+1,
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
        :param upVector: the reference up vector
        :param under/u: an optional parent for the chain; defaults to None
        :param float tolerance/tol: see
            :func:`paya.lib.mathops.getAimingMatricesFromPoints`
        :return: The constructed chain.
        :rtype: :class:`Chain`
        """
        matrices = _mo.getAimingMatricesFromPoints(
            points,
            downAxis,
            upAxis,
            upVector,
            tol=tolerance
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
        Draws a chain (once) along a curve. Either 'upCurve' or 'upVector'
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
            :func:`paya.lib.mathops.getAimingMatricesFromPoints`
        :return: The constructed chain.
        :rtype: :class:`Chain`
        """
        curve = r.PyNode(curve)
        points = curve.distributePoints(numberOrFractions)

        if isinstance(upVectorOrCurve, (str, r.PyNode)):
            upCurve = r.PyNode(upVectorOrCurve)
            aimVectors = _mo.getAimVectorsFromPoints(points)
            aimVectors.append(aimVectors[-1])

            upVectors = []

            for point in points:
                upPoint = upCurve.takeClosestPoint(point)
                upVector = upPoint-point
                upVectors.append(upVector)

        else:
            aimVectors, upVectors = _mo.getAimAndUpVectorsFromPoints(
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
            :func:`paya.lib.mathops.getAimingMatricesFromPoints`
        :return: ``self``
        :rtype: :class:`Chain`
        """
        points = self.points()

        matrices = _mo.getAimingMatricesFromPoints(
            points,
            downAxis,
            upAxis,
            upVector,
            tol=tolerance
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

    #------------------------------------------------------------|    Inspections

    def bones(self):
        """
        :return: One :class:`Chain` instance per overlapping pair of joints.
        :rtype: :class:`list` of :class:`Chain`
        """
        pairs = zip(self, self[1:])
        bones = map(Chain, pairs)
        return list(bones)

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

    @short(plug='p')
    def points(self, plug=False):
        """
        :param bool plug/p: return attributes instead of values; defaults to
            False
        :return: A world position for each joint in this chain.
        :rtype: :class:`list` of :class:`~paya.runtime.data.Point`
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
                userRatios = numberOrRatios

        else:
            raise RuntimeError("No ratios or number specified.")

        # Gather info

        points = self.points()
        vectors = []
        cumulativeLengths = [0.0]

        for i, thisPoint in enumerate(points[:-1]):
            nextPoint = points[i+1]
            vector = nextPoint-thisPoint
            vectors.append(vector)
            cumulativeLength = vector.length() + cumulativeLengths[-1]
            cumulativeLengths.append(cumulativeLength)

        fullLength = cumulativeLengths[-1]

        jointRatios = [0.0] + [cumulativeLength / fullLength \
                for cumulativeLength in cumulativeLengths[1:]]

        if perBone:
            _userRatios = []

            for i, thisJointRatio in enumerate(jointRatios[:-1]):
                nextJointRatio = jointRatios[i+1]
                newRatios = [_pu.blend(
                    thisJointRatio,
                    nextJointRatio,
                    weight=userRatio
                    ) for userRatio in userRatios
                ]

                _userRatios += newRatios

            _userRatios.append(jointRatios[-1])
            userRatios = _userRatios

        # Perform the insertions

        ln = len(self)
        insertions = {}
        newJoints = []

        for i, userRatio in enumerate(userRatios):
            for x in range(ln-1):
                thisRatio = jointRatios[x]
                nextRatio = jointRatios[x+1]

                if userRatio >= thisRatio and userRatio <= nextRatio:
                    thisJoint = self[x]
                    nextJoint = self[x+1]

                    localRatio = (userRatio-thisRatio)/(nextRatio-thisRatio)

                    startPoint = points[x]
                    vector = vectors[x]

                    position = startPoint + vector * localRatio
                    matrix = thisJoint.getMatrix(worldSpace=True)
                    matrix.t = position

                    dup = thisJoint.duplicate(
                        name=r.nodes.Joint.makeName(i+1), po=True)[0]

                    dup.setMatrix(matrix, worldSpace=True)
                    pool = insertions.setdefault(thisJoint, [])
                    pool.append(dup)
                    break

        membership = []

        for joint in self:
            membership.append(joint)

            try:
                theseInsertions = insertions[joint]
                membership += theseInsertions
                newJoints += theseInsertions

            except KeyError:
                continue

        self.data[:] = membership
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

    def _getSubdivisionMapping(self, subdividedChain):
        """
        Returns a list where each member is:
        [jointOnThisChain, [closestJointOnSubidividedChain,
            childJoint1, childJoint2... terminating before next matched joint]
        """
        sourcePoints = self.points()
        destPoints = subdividedChain.points()
        destAnchorIndices = []

        for sourcePoint in sourcePoints:
            bestDistance = None
            bestPointIndex = None

            for i, destPoint in enumerate(destPoints):
                vec = destPoint-sourcePoint
                ln = vec.length()

                if bestDistance is None or (ln < bestDistance):
                    bestDistance = ln
                    bestPointIndex = i

            destAnchorIndices.append(bestPointIndex)

        out = []
        destLen = len(subdividedChain)

        for i, srcJoint, destAnchorIndex in zip(
            range(len(self)),
            self,
            destAnchorIndices
        ):
            destAnchorJoint = subdividedChain[destAnchorIndex]
            entry = [srcJoint, [destAnchorJoint]]

            for x, destJoint in enumerate(
                    subdividedChain[destAnchorIndex+1:], start=destAnchorIndex+1):
                if x is destAnchorIndices[i+1]:
                    break

                entry[1].append(destJoint)

            out.append(entry)

        return out

    # WIP
    # @short(
    #     downAxis='da',
    #     upVectorOverrides='uvo'
    # )
    # def driveSubdivided(
    #         self,
    #         destChain,
    #         upAxis,
    #         downAxis=None,
    #         upVectorOverrides=None,
    #         stretch=True,
    #         stretchByTranslate=False
    # ):
    #     driverMapping = self._getSubdivisionMapping(destChain)
    #
    #     if stretch:
    #         points = self.points(p=True)
    #
    #     for i, thisJoint, targets in zip(
    #             range(len(self)-1), driverMapping[:-1]):
    #
    #         nextJoint = self[i+1]
    #
    #
    #
    #
