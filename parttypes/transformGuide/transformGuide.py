from paya.util import short
import paya.runtime as r


class TransformGuide(r.parts.PartGuide):

    @r.partCreator
    @short(worldMatrix='wm')
    def create(self, worldMatrix=None):

        #---------------------------------------------------|    Control

        control = r.createControl(worldMatrix=worldMatrix,
                                  parent=self.tree['controls'].node(),
                                  channelBox=['t', 'r', 's', 'ro'])

        self.tag('control', control)

        #---------------------------------------------------|    Settings

        self.addBuildSetting('numControls', 2, min=0)
        self.addBuildSetting('createJoint', True)

    #-------------------------------------------------------|    Create part

    def getPartCreateArgsKwargs(self):
        control = self.getByTag('control')[0]
        node = self.node()

        kwargs = self.getBuildSettings()

        kwargs['worldMatrix'] = control.getMatrix(worldSpace=True).normal()
        kwargs['keyable'] = ['t', 'r', 'rotateOrder']
        kwargs['rotateOrder'] = control.attr('rotateOrder').get(asString=True)

        return (), kwargs