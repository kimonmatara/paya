import paya.lib.mathops as _mo
import paya.lib.plugops as _po
from paya.util import short
import paya.runtime as r


class CurveUpVectorAimCurveSampler(r.networks.CurveUpVectorSampler):
    """
    Works similarly to the 'aim curve' mode of a
    :class:`curveWarp <paya.runtime.nodes.CurveWarp>` deformer.

    .. note::

        Returned vectors won't be perpendicular to curve tangents, with the
        expectation that they will be perpendicularized during subsequent
        matrix construction.
    """

    #-------------------------------------------------------|    Constructor

    @classmethod
    @short(closestPoint='cp')
    def create(cls, curve, aimCurve, closestPoint=True):
        """
        :param curve: the curve on which to create the sampler
        :type curve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param aimCurve: the curve from which to pull per-point aiming
            interests
        :type aimCurve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity
            rather than matched parameter; defaults to ``True``
        :return: The network system.
        :rtype: :class:`CurveUpVectorAimCurveSampler`
        """
        with r.NodeTracker() as track:
            node = cls._create(curve, aimCurve, closestPoint=closestPoint)

        node._tagDependencies(track.getNodes())

        return node

    @classmethod
    def _create(cls, curve, aimCurve, closestPoint=True):
        """
        :param curve: the curve on which to create the sampler
        :type curve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param aimCurve: the curve from which to pull per-point aiming
            interests
        :type aimCurve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity
            rather than matched parameter; defaults to ``True``
        :return: The network system.
        :rtype: :class:`CurveUpVectorAimCurveSampler`
        """
        nw = super(r.networks.CurveUpVectorAimCurveSampler, cls)._create(curve)

        aimCurve = _po.asGeoPlug(aimCurve, worldSpace=True)
        aimCurve >> nw.addAttr('aimCurve', at='message')

        if closestPoint:
            nw.addAttr('closestPoint', at='bool', dv=True).lock()

        return nw

    #-------------------------------------------------------|    Basic inspections

    def byClosestPoint(self):
        """
        :return: ``True`` if this sampler was configured to use closest-point
            calculations, otherwise ``False``.
        :rtype: bool
        """
        return self.hasAttr('closestPoint')

    def aimCurve(self):
        """
        :return: The aim curve output connected to this system.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        out = self.attr('aimCurve').inputs(plugs=True)

        if out:
            return out[0]

    #-------------------------------------------------------|    Sampling

    def _sampleAtParam(self, param, plug=True):
        curve = self.curve()
        aimCurve = self.aimCurve()

        refPoint = curve.pointAtParam(param, p=plug)

        if self.byClosestPoint():
            interest = curve.closestPoint(refPoint, p=plug)

        else:
            interest = curve.pointAtParam(param, p=plug)

        return interest-refPoint