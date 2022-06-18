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
        name='n',
        inherit='i',
        suffix='s'
    )
    def create(
            cls,
            displayLocalAxis=True,
            worldMatrix=None,
            under=None,
            name=None,
            inherit=True,
            suffix=True
    ):
        """
        Creates a joint.

        :param bool displayLocalAxis/dla: display local axis; defaults to True
        :param worldMatrix/wm: an optional world matrix for the joint;
            defaults to None
        :type worldMatrix/wm: None, list,
            :class:`~paya.datatypes.matrix.Matrix`
        :param under/u: an optional parent for the joint; defaults to None
        :type under/u: None, str, :class:`~pymel.core.general.PyNode`
        :param name/n: one or more name elements for the joint; defaults to
            None
        :type name/n: None, str, list or tuple
        :param bool inherit/i: inherit names from :class:`~paya.lib.names.Name`
            blocks; defaults to True
        :param suffix/s: if True, look up and apply a type suffix; if string,
            apply as suffix; if False, omit suffix; defaults to True
        :return: The joint.
        :rtype: :class:`~paya.nodetypes.joint.Joint`
        """
        joint = cls.createNode(n=name, i=inherit, s=suffix)

        if under:
            joint.setParent(under)

        if worldMatrix:
            joint.setMatrix(worldMatrix, worldSpace=True)
            r.makeIdentity(joint, apply=True, r=True, jo=False)

        if displayLocalAxis:
            joint.attr('dla').set(True)

        return joint

    #------------------------------------------------------------|    Inspections

    def skinClusters(self):
        """
        :return: All the skinClusters this joint participates in, in no
            particular order.
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
        :return: IK handles this joint participates in.
        :rtype: :class:`list` of :class:`~paya.nodetypes.ikHandle.IkHandle`
        """
        out = []

        for ikHandle in r.ls(type='ikHandle'):
            if self in ikHandle.getJointList(it=includeAsTip):
                out.append(ikHandle)

        return list(set(out))

    #------------------------------------------------------------|    Chain

    def chainFromHere(self, to=None):
        """
        :param to: an optional to joint
        :type to: str or :class:`~paya.nodetypes.joint.Joint`
        :return: A chain from this joint up to and including 'to'
            (if provided), or terminating before the first branch.
        :rtype: :class:`~paya.lib.skel.Chain`
        """
        if to:
            return r.Chain.getFromStartEnd(self, to)

        return r.Chain.getFromRoot(self)

    #------------------------------------------------------------|    Sampling

    @short(plug='p')
    def getJointOrientMatrix(self, plug=False):
        """
        Returns joint orientation as a rotation matrix.

        :param bool plug/p: return an attribute instead of a value; this will
            be cooked only once, and afterwards retrieved via a
            'jointOrientMatrix' attribute on the node; defaults to False
        :return: The joint orient matrix.
        :rtype: :class:`paya.datatypes.matrix.Matrix` or
            :class:`paya.plugtypes.matrix.Matrix`
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