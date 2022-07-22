import paya.lib.mathops as _mo
from paya.util import short
import maya.cmds as m
import paya.runtime as r


class Joint:

    #------------------------------------------------------------|    Constructor

    @classmethod
    @short(
        displayLocalAxis='dla',
        worldMatrix='wm',
        under='u',
        name='n'
    )
    def create(
            cls,
            displayLocalAxis=True,
            worldMatrix=None,
            under=None,
            name=None
    ):
        """
        Creates a joint.

        :param bool displayLocalAxis/dla: display local axis; defaults to True
        :param worldMatrix/wm: an optional world matrix for the joint;
            defaults to None
        :type worldMatrix/wm: None, list,
            :class:`~paya.runtime.data.Matrix`
        :param under/u: an optional parent for the joint; defaults to None
        :type under/u: None, str, :class:`~pymel.core.general.PyNode`
        :param name/n: one or more name elements for the joint; defaults to
            None
        :type name/n: None, str, list or tuple
        :return: The joint.
        :rtype: :class:`~paya.runtime.nodes.Joint`
        """
        joint = cls.createNode(n=name)

        if under:
            joint.setParent(under)

        if worldMatrix:
            joint.setMatrix(worldMatrix, worldSpace=True)
            r.makeIdentity(joint, apply=True, r=True, jo=False, s=True)

        if displayLocalAxis:
            joint.attr('dla').set(True)

        return joint

    #------------------------------------------------------------|    Visual testing

    def insertCube(self, size=1.0):
        """
        Inserts a poly cube under (including transform) under the joint
        to help test transformations visually.

        :param float size/siz: a single scalar for the cube's width, height
            and depth; defaults to 1.0
        :return: The cube transform.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        cube = r.polyCube(
            ch=False,
            w=size, h=size, d=size,
            n=r.nodes.Mesh.makeName('{}_test_cube'.format(self.basename())),
            sd=2,
            sh=2,
            sw=2
        )[0]

        r.parent(cube, self)
        cube.setMatrix(r.data.Matrix())
        return cube

    #------------------------------------------------------------|    Inspections

    def skinClusters(self):
        """
        :return: Associated skinClusters, in no particular order.
        :rtype: list
        """
        outputs = self.attr('worldMatrix'
                            )[0].outputs(plugs=True, type='skinCluster')

        out = []

        for output in outputs:
            if output.attrName() == 'ma':
                out.append(output.node())

        return list(set(out))

    @short(includeAsTip='iat')
    def ikHandles(self, includeAsTip=True):
        """
        :param bool includeAsTip/iat: Include IK systems for which this joint
            is the tip; defaults to True
        :return: Associated IK handles, in no particular order.
        :rtype: :class:`list` of :class:`~paya.runtime.nodes.IkHandle`
        """
        out = []

        for ikHandle in r.ls(type='ikHandle'):
            if self in ikHandle.getJointList(it=includeAsTip):
                out.append(ikHandle)

        return list(set(out))

    #------------------------------------------------------------|    Chain

    def chainFromHere(self, to=None):
        """
        :param to: an optional terminator joint; defaults to None
        :type to: str or :class:`~paya.runtime.nodes.Joint`
        :return: A chain from this joint up to and including 'to'
            (if provided), or terminating before the first branch.
        :rtype: :class:`~paya.lib.skel.Chain`
        """
        if to:
            return r.Chain.getFromStartEnd(self, to)

        return r.Chain.getFromRoot(self)

    #------------------------------------------------------------|    Matrices

    def setMatrix(self, matrix, worldSpace=False):
        """
        Overloads :meth:`pymel.core.nodetypes.Transform.setMatrix` to include
        shear, which is observed on joints in Maya >= 2022.

        :param matrix: the matrix to apply
        :type matrix: list, tuple, :class:`~paya.runtime.data.Matrix`
        :param bool worldSpace: apply in world space
        """
        matrix = r.data.Matrix(matrix)

        if worldSpace:
            matrix *= self.attr('pim')[0].get()

        r.nodetypes.Joint.setMatrix(self, matrix)
        matrix = r.data.TransformationMatrix(matrix)
        shear = matrix.getShear('transform')
        self.attr('shear').set(shear)

    @short(plug='p')
    def getJointOrientMatrix(self, plug=False):
        """
        Returns joint orientation as a rotation matrix.

        :param bool plug/p: return an attribute instead of a value; this will
            be cooked only once, and afterwards retrieved via a
            'jointOrientMatrix' attribute on the node; defaults to False
        :return: The joint orient matrix.
        :rtype: :class:`paya.runtime.data.Matrix` or
            :class:`paya.runtime.plugs.Matrix`
        """
        if plug:
            attrName = 'jointOrientMatrix'

            if not self.hasAttr(attrName):
                self.addAttr(attrName, at='matrix')

            attr = self.attr(attrName)

            if not attr.inputs():
                self.attr('jointOrient').asRotateMatrix() >> attr

            return attr

        return self.attr('jointOrient').get().asRotateMatrix()