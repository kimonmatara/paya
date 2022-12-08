from paya.util import short
import paya.runtime as r


class TransformGuide(r.parts.PartGuide):

    @r.partCreator
    @short(worldMatrix='wm')
    def create(self, worldMatrix=None):
        """
        Guide for a :class:`~paya.runtime.parts.Transform` part.

        .. note::

            Control matrix vectors will be normalized when this guide is used
            to create the rig part.

        :param worldMatrix/wm: the initial control matrix; defaults to the
            identity matrix
        :type worldMatrix/wm: :class:`tuple`, :class:`list`,
            :class:`~paya.runtime.data.Matrix`
        """

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
        """
        :return: Positional and keyword arguments that can be passed along
            to the ``create()`` method on the associated
            :class:`~paya.runtime.parts.Part` subclass.
        :rtype: (:class:`tuple`, :class:`dict`)
        """
        control = self.getByTag('control')[0]
        node = self.node()

        kwargs = self.getBuildSettings()

        kwargs['worldMatrix'] = control.getMatrix(worldSpace=True).normal()
        kwargs['keyable'] = ['t', 'r', 'rotateOrder']
        kwargs['rotateOrder'] = control.attr('rotateOrder').get(asString=True)

        return (), kwargs