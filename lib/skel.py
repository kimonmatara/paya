from collections import UserList
from paya.config import undefined, takeUndefinedFromConfig
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


class Chain:

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

    def copy(self):
        """
        :return: A copy of this instance (no actual joints will be copied).
        :rtype: :class:`Chain`
        """
        return type(self)(list(self))

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
    @short(parent='p')
    def createFromMatrices(cls, matrices, parent=None):
        """
        Creates a chain from matrices. The joints will match the matrices
        exactly; no attempt is made to orient the chain.

        :param matrices: the matrices to use
        :param parent/p: an optional parent for the chain; defaults to None
        :return: :class:`Chain`
        """
        joints = []

        for i, matrix in enumerate(matrices):
            with r.Name(i+1):
                joint = r.nodes.Joint.create(
                    worldMatrix=matrix,
                    p=joints[-1] if joints else parent
                )

            joints.append(joint)

        return cls(joints)

    @classmethod
    @short(parent='p',
           tolerance='tol',
           downAxis='da',
           upAxis='ua',
           tipMatrix='tm')
    @takeUndefinedFromConfig
    def createFromPoints(
            cls,
            points,
            upVector,
            downAxis=undefined,
            upAxis=undefined,
            parent=None,
            tolerance=1e-7,
            tipMatrix=None
    ):
        """
        Builds a chain from points. The side ('up') axis will be calculated
        using cross products, but those will be biased towards the reference
        up vector.

        :param points: a world position for each joint
        :type points: :class:`list` [:class:`list` [:class:`float`] |
            :class:`~paya.runtime.data.Point` |
            :class:`~paya.runtime.data.Vector`]
        :param str downAxis: the 'bone' axis; defaults to
            ``paya.config.downAxis``
        :param str upAxis: the axis to map to the up vector; defaults to
            ``paya.config.upAxis``
        :param upVector: one up vector hint, or one vector per point
        :type upVector: tuple, list, :class:`~paya.runtime.data.Vector`,
            [tuple, list, :class:`~paya.runtime.data.Vector`]
        :param parent/p: an optional parent for the chain; defaults to None
        :param float tolerance/tol: see
            :func:`paya.lib.mathops.getChainedAimMatrices`
        :param tipMatrix/tm: an optional rotation matrix override for the tip
            (end) joint; if provided, only orientation information will be
            used; defaults to ``None``
        :type tipMatrix/tm: ``None``, :class:`list` [:class:`float`],
            :class:`~paya.runtime.data.Matrix`
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

        if tipMatrix:
            tipMatrix = r.data.Matrix(tipMatrix)
            baseMatrix = matrices[-1]
            tipMatrix = baseMatrix.pick(scale=True, shear=True) \
                * tipMatrix.pick(rotate=True) \
                * baseMatrix.pick(translate=True)

            matrices[-1] = tipMatrix

        return cls.createFromMatrices(matrices, p=parent)

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
            aimVectors = _mo.getAimVectors(points)
            aimVectors.append(aimVectors[-1])

            upVectors = []

            for point in points:
                upPoint = aimCurve.nearestPoint(point, worldSpace=True)
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

    def isContiguous(self):
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

    def isInline(self):
        """
        :return: ``True`` if this chain is in-line (in any direction),
            otherwise ``False``.
        :rtype: :class:`bool`
        """
        states = []
        vectors = self.vectors()

        if len(vectors) < 2:
            raise RuntimeError("Need more than one bone.")

        largestAcceptableDot = 1.0-1e-7

        for i, vector in enumerate(vectors[1:], start=1):
            prev = vectors[i-1]
            dot = prev.dot(vector, normalize=True)
            rejected = dot >= largestAcceptableDot
            states.append(rejected)

        if len(states) is 1:
            return states[0]

        return all([states])

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
                    with r.Name('insertion', count+1):
                        joint = r.nodes.Joint.create(p=self[i])

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

    @short(startNumber='sn')
    def duplicate(self, startNumber=1):
        """
        Duplicates this chain. Joints will be renamed with contextual. Use
        :class:`~paya.lib.names.Name` blocks to modify.

        :param int startNumber/sn: the starting number for the joint renumbering;
            defaults to ``1``
        :return: The duplicated chain.
        :rtype: :class:`Chain`
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
            with r.Name(i+startNumber):
                copy = joint.duplicate(po=True)[0].releaseSRT()

            copies.append(copy)

        for copy, parent in zip(copies, parents):
            if isinstance(parent, int):
                parent = copies[parent]

            copy.setParent(parent)

        return Chain(copies)

    @short(startNumber='sn')
    def rename(self, startNumber=1):
        """
        Renames this chain contextually. Use :class:`~paya.lib.names.Name`
        blocks to modify.

        :param int startNumber/sn: the start number for the chain renumbering;
            defaults to ``1``
        :return: ``self``
        :rtype: :class:`Chain`
        """
        for i, joint in enumerate(self):
            with r.Name(i+startNumber):
                joint.rename()

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
        endEffector='ee',
        jitter='j',
        upAxis='ua',
        upVector='up'
    )
    def createIkHandle(self,
                       jitter=False,
                       upVector=None,
                       **kwargs):
        """
        Creates an IK handle for this chain.

        :param bool jitter: if this chain is in-line, auto-configures
            preferred angles to prevent lockout; *upAxis* will be required
            for this; defaults to ``False``
        :param upVector: used by *jitter*; a reference up vector to indicate
            the wind direction of the jitter; defaults to ``None``
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
        if jitter:
            if upVector is None:
                raise ValueError("An up vector is required for IK jitter.")

            self.jitterForIkHandle(upVector)

        settings = {
            'solver': 'ikRPsolver' if len(self) > 2 else 'ikSCsolver'
        }

        settings.update(kwargs)
        settings['startJoint'] = self[0]
        settings['endEffector'] = self[-1]

        return r.nodes.IkHandle.create(**settings)

    def jitterForIkHandle(self, upVector):
        """
        If this chain is in-line, auto-configures a slight value in the
        preferred angle of the bending ('up') axis of the internal joints
        in anticipation of an IK handle.

        :param upVector: a reference up vector to indicate the wind direction
            of the jitter
        :type upVector: :class:`list` [:class:`float`],
            :class:`~paya.runtime.data.Vector`
        :return: ``self``
        :rtype: Chain
        """
        if len(self) < 3:
            raise RuntimeError(
                "At least three joints required for jitter."
            )

        upVector = r.data.Vector(upVector)

        if self.isInline():
            jitter = _pu.radians(10)

            for joint in self[:-1]:
                bestAxis = joint.closestAxisToVector(upVector)

                bestAxisIsNeg = '-' in bestAxis
                bestAxis = bestAxis.strip('-')

                joint.attr('preferredAngle{}'.format(bestAxis.upper())).set(
                    (jitter * -1) if bestAxisIsNeg else jitter
                )

        return self

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
        assert self.isContiguous(), "The chain is not contiguous."

        #val = _pu.radians(22.5)
        val = r.degToUI(22.5)

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

    def getTwistMap(self, twistChain):
        """
        Returns a list of sublists, where each sublist comprises:

            bone on this chain, subdivided bone (chain) on twist chain

        :param twistChain: a twist chain, derived from this one using
            :meth:`insertJoints` or `subdivide
        :type twistChain: :class:`list`, :class:`Chain`
        :return: A list of sublists, where each sublist comprises
            *bone on this chain, subdivided bone (chain) on twist chain*
        :type: :class:`list` [:class:`Chain`, :class:`Chain`]
        """
        twistChain = Chain(twistChain)
        slaveAnchors = [joint.closestOf(twistChain) for joint in self]
        slaveIndices = [twistChain.index(joint) for joint in slaveAnchors]

        out = []

        for i in range(len(self)-1):
            masterBone = self[i:i+2]
            slaveChain = twistChain[slaveIndices[i]:slaveIndices[i+1]+1]
            out.append([masterBone, slaveChain])

        return out

    @short(
        skipEnd='ske',
        downAxis='da',
        startUpMatrix='sum',
        endUpMatrix='eum',
        useOffsetParentMatrix='uop',
        squashStretch='ss'
    )
    @takeUndefinedFromConfig
    def driveTwistChain(
            self,
            twistChain,
            upAxis,
            globalScale=1.0,
            downAxis=None,
            startUpMatrix=None,
            endUpMatrix=None,
            useOffsetParentMatrix=undefined,
            skipEnd=False,
            squashStretch=False
    ):
        """
        Drives a chain derived by duplicating this one and calling
        :meth:`insertJoints` or :meth:`subdivide` on the copy.

        :param twistChain: the derived chain to drive
        :type twistChain: :class:`list` | :class:`Chain`
        :param str upAxis: this chain's 'up' axis, e.g. ``x``
        :param globalScale/gs: if this is a plug, it will be normalized;
            if it's *not* a plug, it will be overriden to ``1.0``; defaults
            to ``1.0``
        :type globalScale/gs: :class:`float`, :class:`str`,
            :class:`~paya.runtime.plugs.Attribute`
        :param str downAxis/da: if you know this chain's 'down' axis, specify
            if here to prevent extraneous checks; defaults to ``None``
        :param startUpMatrix/sum: an optional matrix to override the
            transformation of the vector at the very start of this chain;
            useful for things like shoulders etc.; defaults to ``None``
        :type startUpMatrix/sum: :class:`str`,
            :class:`~paya.runtime.plugs.Matrix`
        :param endUpMatrix/eum: an optional matrix to override the
            transformation of the vector at the very end of this chain;
            defaults to ``None``
        :type endUpMatrix/eum: :class:`str`,
            :class:`~paya.runtime.plugs.Matrix`
        :param bool useOffsetParentMatrix/uop: use offset parent matrix to
            drive the slave joints; defaults to the namesake configuration
            flag
        :param bool skipEnd/ske: don't drive the final joint; defaults to
            ``False``
        :param bool squashStretch/ss: apply bone scale; defaults to ``False``
        """
        #--------------------------------------|    Prep

        twistChain = Chain(twistChain)
        twistsMap = self.getTwistMap(twistChain)

        if startUpMatrix is not None:
            startUpMatrix = r.conform(startUpMatrix).asOffset()

        if endUpMatrix is not None:
            endUpMatrix = r.conform(endUpMatrix).asOffset()

        globalScale = r.conform(globalScale)
        globalScaleIsPlug = isinstance(globalScale, r.Attribute)

        #--------------------------------------|    Scale management

        if globalScaleIsPlug:
            globalScale = globalScale / globalScale.get()
        else:
            globalScale = 1.0

        if downAxis is None:
            downAxis = self.downAxis().strip('-')

        if squashStretch:
            downAxisIndex = 'xyz'.index(downAxis)

        #--------------------------------------|    Iterate

        i = 0

        for masterChain, slaveChain in twistsMap:
            with r.Name('bone', i):
                # Resolve start / end up vecs
                initStartUpVec = masterChain[0
                    ].getWorldMatrix().getAxis(upAxis)
                initEndUpVec = r.data.Vector(initStartUpVec)

                if i is 0 and startUpMatrix is not None:
                    startXform = startUpMatrix

                else:
                    startXform = masterChain[0
                        ].getWorldMatrix(plug=True, asOffset=True)

                if i is len(masterChain)-1 and endUpMatrix is not None:
                    endXform = endUpMatrix

                else:
                    endXform = masterChain[-1
                        ].getWorldMatrix(plug=True, asOffset=True)

                startUpVec = initStartUpVec * startXform
                endUpVec = initEndUpVec * endXform

                # Get chord vector
                endPoint = masterChain[-1].getWorldPosition(plug=True)
                startPoint = masterChain[0].getWorldPosition(plug=True)
                downVec =  endPoint - startPoint
                downVecN = downVec.normal()
                downVecLn = downVec.length()

                # Get angle
                angle = startUpVec.angleTo(endUpVec, clockNormal=downVec)
                angle = angle.unwindSwitch(0)

                # Resolve stretch information
                if squashStretch:
                    nativeLen = downVecLn.get() * globalScale
                    stretchRatio = downVecLn / nativeLen

                # Iterate
                for ii, slaveRatio, slave in zip(
                    range(len(slaveChain)),
                    slaveChain.ratios(),
                    slaveChain
                ):
                    if i is 0 and ii is len(slaveChain)-1 and skipEnd:
                        continue

                    with r.Name(ii+1):
                        # Get position
                        position = startPoint + \
                                   (downVecN * (downVecLn * slaveRatio))

                        # Resolve up vector
                        upVec = startUpVec.rotateByAxisAngle(
                            downVec,
                            angle * slaveRatio
                        )

                        # Resolve scale matrix
                        factors = [globalScale] * 3

                        if squashStretch:
                            factors[downAxisIndex] = stretchRatio

                        smtx = r.createScaleMatrix(*factors)

                        # Create full driver matrix
                        transRotMtx = r.createMatrix(
                            downAxis, downVec,
                            upAxis, upVec,
                            translate=position
                        ).pick(t=True, r=True)

                        matrix = smtx * transRotMtx

                        # Apply
                        matrix.drive(slave,
                                     worldSpace=True,
                                     maintainOffset=True,
                                     useOffsetParentMatrix=useOffsetParentMatrix)

            i += 1

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



def getClassFromNumJoints(numJoints):
    return {2: Bone}.get(numJoints, Chain)