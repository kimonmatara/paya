from collections import UserList

from paya.config import defaultDownAxis, defaultUpAxis
import paya.lib.mathops as _mo
from paya.util import short, LazyModule
import pymel.util as _pu

r = LazyModule('paya.runtime')


class Chain(UserList):

    #------------------------------------------------------------|    Instantiation

    def __init__(self, *joints):
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
        :param downAxis/da: the 'bone' axis; defaults to
            ``paya.config.defaultDownAxis``
        :param upAxis/ua: the axis to map to the up vector; defaults to
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

    def points(self):
        """
        :return: A world position for each joint in this chain.
        :rtype: :class:`list` of :class:`~paya.datatypes.point.Point`
        """
        out = []

        for joint in self:
            pos = r.data.Point(r.xform(joint, q=True, t=True, ws=True))
            out.append(pos)

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

