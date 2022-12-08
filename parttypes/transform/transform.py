from paya.util import short
import paya.runtime as r


class Transform(r.parts.Part):
    """
    Simple single-transform rig part with a joint and control(s).
    """

    @r.partCreator
    @short(worldMatrix='wm',
           keyable='k',
           channelBox='cb',
           rotateOrder='ro',
           numControls='nc',
           createJoint='cj')
    def create(self,
               worldMatrix=None,
               keyable=None,
               channelBox=None,
               rotateOrder='xyz',
               numControls=2,
               createJoint=True):
        """
        :param worldMatrix/wm: the initial world matrix; defaults to the
            identity matrix
        :type worldMatrix/wm: :class:`~paya.runtime.data.Matrix`,
            :class:`list`, :class:`tuple`
        :param keyable/k: list of keyable attributes for the control;
            defaults to ``None``
        :type keyable/k: :class:`list` [ :class:`str`]
        :param channelBox/cb: list of settable attributes for the control;
            defaults to ``None``
        :type channelBox/cb: :class:`list` [ :class:`str`]
        :param rotateOrder/ro: the control's rotate order on creation;
            defaults to ``'xyz'``
        :type rotateOrder/ro: :class:`int`, :class:`str`
        :param int numControls/nc: the number of (stacked, including insets)
            controls to generate; defaults to 2
        :param bool createJoint/cj: create and drive a joint; defaults to
            ``True``
        """
        #----------------------------------------------|    Create controls

        if numControls > 0:
            controls = r.createControls(
                worldMatrix=worldMatrix,
                numControls=numControls,
                keyable=keyable,
                channelBox=channelBox,
                rotateOrder=rotateOrder,
                parent=self.tree['controls'].node()
            )
        else:
            controls = []

        #----------------------------------------------|    Create joint

        if createJoint:
            joint = r.nodes.Joint.create(
                worldMatrix=worldMatrix,
                parent=self.tree['joints'].node(
                    inheritsTransform=not controls)
            )

            if controls:
                controls[-1].attr('worldMatrix').drive(joint)