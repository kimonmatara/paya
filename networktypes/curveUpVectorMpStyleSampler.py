from paya.networktypes.curveUpVectorSampler import NoMatchingSampleError
import paya.lib.mathops as _mo
import paya.runtime as r
from paya.util import short


class CurveUpVectorMpStyleSampler(r.networks.CurveUpVectorSampler):
    """
    Works similarly to the 'follow' options on
    :class:`motionPath <paya.runtime.nodes.MotionPath>` nodes.

    .. note::

        Returned vectors won't be perpendicular to curve tangents, with the
        expectation that they will be perpendicularized during subsequent
        matrix construction.
    """
    #-------------------------------------------------------|    Constructor

    @classmethod
    @short(upObject='uo', upVector='upv')
    def create(cls, curve, upObject=None, upVector=None):
        """
        If neither *upObject* nor *upVector* are specified, the system will
        default to curve normals.

        :param curve: the curve on which to create the sampler
        :type curve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param upObject/uo: if provided on its own, works as an aiming interest
            (similar to 'Object Up' mode on
            :class:`motionPath <paya.runtime.nodes.MotionPath>` nodes);
            if combined with *upVector*, the object's world matrix is used to
            multiply the up vector; defaults to ``None``
        :type upObject/uo: str, :class:`~paya.runtime.nodes.Transform`
        :param upVector/upv: if provided on its own, used as-is; if combined
            with *upObject*, the object's world matrix is used to multiply
            the up vector; defaults to ``None``
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The network system.
        :rtype: :class:`CurveUpVectorMpStyleSampler`
        """
        with r.NodeTracker() as track:
            node = cls._create(curve, upObject=upObject, upVector=upVector)

        node._tagDependencies(track.getNodes())
        return node

    @classmethod
    def _create(cls, curve, upObject=None, upVector=None):
        nw = super(r.networks.CurveUpVectorMpStyleSampler, cls)._create(curve)
        nw._initMpStyleConfig(upObject=upObject, upVector=upVector)
        return nw

    #-------------------------------------------------------|    Partial construction

    def _initMpStyleConfig(self, upObject=None, upVector=None):

        if upObject:
            upObject = r.PyNode(upObject)

        if upVector is not None:
            upVector = _mo.conformVectorArg(upVector)

        if upVector is not None:
            if upObject:
                upVector *= upObject.attr('worldMatrix')

            self.addAttr('upVector', at='double3', nc=3)

            for ax in 'XYZ':
                self.addAttr('upVector'+ax, parent='upVector')

            upVector >> self.attr('upVector')

        elif upObject:
            self.addAttr('interest', at='double3', nc=3)

            for ax in 'XYZ':
                self.addAttr('interest'+ax, parent='interest')

            upObject.getWorldPosition(plug=True) >> self.attr('interest')

        return self

    #-------------------------------------------------------|    Sampling

    def hasInterest(self):
        return self.hasAttr('interest')

    def hasUpVector(self):
        return self.hasAttr('upVector')

    def _findSample(self, param):
        if self.hasUpVector():
            return self.attr('upVector')

        return(super(type(self), self)._findSample(param))

    def _sampleAtParam(self, param, plug=True):
        curve = self.curve()

        if self.hasUpVector():
            return self.attr('upVector').get(p=plug)

        elif self.hasInterest():
            refPoint = curve.pointAtParam(param, p=plug)
            interest = self.attr('interest').get(p=plug)
            return interest-refPoint

        return curve.normalAtParam(param, p=plug)