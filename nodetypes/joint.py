import paya.lib.mathops as _mo
from paya.util import short
import maya.cmds as m
import paya.runtime as r


class Joint:

    #------------------------------------------------------------|    Constructor

    @classmethod
    @short(displayLocalAxis='dla',
           worldMatrix='wm',
           parent='p',
           name='n',
           freeze='fr',
           decompose='dec',
           rotateOrder='ro',
           radius='rad')
    def create(cls,
               displayLocalAxis=True,
               worldMatrix=None,
               parent=None,
               name=None,
               freeze=True,
               decompose=True,
               rotateOrder='xyz',
               radius=1.0):
        """
        :param bool displayLocalAxis/dla: display the local matrix
            axes; defaults to ``True``
        :param worldMatrix/wm: defines the joint's default pose; defaults
            to ``None``
        :type worldMatrix/wm: None, tuple, list, str,
            :class:`~paya.runtime.data.Matrix`,
            :class:`~paya.runtime.plugs.Matrix`
        :param parent/p: an optional destination parent for the joint
        :type parent/p: None, str, :class:`~paya.runtime.nodes.Transform`
        :param str name/n: a name for the joint; defaults to ``None``
        :param bool freeze/fr: zero-out transformations (except translate)
            at the initial pose; defaults to ``True``
        :param bool decompose/dec: if ``False``, connect to
            ``offsetParentMatrix`` instead of driving the joint's SRT
            channels; note that, if *freeze* is requested, the initial matrix
             will *always* be applied via decomposition and then frozen;
             defaults to ``True``
        :param rotateOrder/ro: the rotate order for the joint; defaults
            to ``'xyz'``
        :type rotateOrder/ro: ``None``, :class:`str`, :class:`int`,
            :class:`~paya.runtime.plugs.Math1D`
        :param float radius/rad: the joint display radius; defaults to 1.0
        :return: The joint.
        :rtype: :class:`~paya.runtime.nodes.Joint`
        """
        # Draw the joint, perform basic configurations
        kw = {}

        if name is not None:
            kw['name'] = name

        joint = cls.createNode(**kw)
        joint.attr('displayLocalAxis').set(displayLocalAxis)
        joint.attr('radius').set(radius)
        rotateOrder >> joint.attr('rotateOrder')

        if parent is not None:
            joint.setParent(parent, relative=worldMatrix is None)

        # Manage matrix
        if worldMatrix is not None:
            worldMatrix, wmDim, wmUt, wmIsPlug = \
                _mo.info(worldMatrix).values()

            if freeze:
                if wmIsPlug:
                    _worldMatrix = worldMatrix.get()

                else:
                    _worldMatrix = worldMatrix

                _worldMatrix = _worldMatrix.pick(t=True, r=True)
                joint.setMatrix(_worldMatrix, worldSpace=True)

                r.makeIdentity(joint, apply=True, r=True, s=True, jo=False)

            if decompose:
                worldMatrix.decomposeAndApply(joint, worldSpace=True)

            else:
                worldMatrix.applyViaOpm(joint, worldSpace=True)

        return joint

    #------------------------------------------------------------|    Visual testing

    @short(name='n')
    def insertCube(self, size=1.0, name=None):
        """
        Inserts a poly cube under (including transform) under the joint
        to help test transformations visually.

        :param str name/n: a name for the cube; defaults to ``None``
        :param float size/siz: a single scalar for the cube's width, height
            and depth; defaults to 1.0
        :return: The cube transform.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        kw = {}

        if name is not None:
            kw['name'] = name

        cube = r.polyCube(ch=False, w=size,
                          h=size, d=size,
                          sd=2, sh=2, sw=2,
                          **kw)[0]

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