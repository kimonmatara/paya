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

    #------------------------------------------------------------|    Hierarchy editing

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


class Triad(Chain):
    """
    A specialised subclass of :class:`~paya.lib.skel.Chain` for three-joint
    chains.
    """