from paya.util import short
import paya.runtime as r


class Transform(r.parts.Part):

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