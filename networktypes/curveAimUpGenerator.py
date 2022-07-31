import paya.lib.plugops as _po
import paya.runtime as r
from paya.util import short



class CurveAimUpGenerator(r.networks.CurveUpGenerator):
    """
    Curve up vector generator that pulls interest points from an 'aim'
    curve, similar to the option on
    :class:`curveWarp <paya.runtime.nodes.CurveWarp>` deformers.
    """

    @classmethod
    @short(closestPoint='cp')
    def create(cls, curve, aimCurve, closestPoint=True):
        """
        :param curve: the main curve
        :type curve: str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param aimCurve: the aim curve
        :type aimCurve: str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from the aim curve
            based on proximity, not matched parameter; defaults to
            True
        :return: The network node for the up vector sample system.
        :rtype: :class:`~paya.runtime.nodes.Network`
        """
        # Wrangle args
        curve = _po.asGeoPlug(curve, ws=True)
        aimCurve = _po.asGeoPlug(aimCurve, ws=True)

        with r.Name(curve.node().basename(sts=True), 'aim_up_gen'):
            # Prep node
            node = cls.createNode()
            curve >> node.addAttr('curve', at='message')
            aimCurve >> node.addAttr('aimCurve', at='message')
            node.addAttr('closestPoint',
                at='bool', k=True, dv=closestPoint).lock()
            node._addSamplesAttr()

        return node

    def aimCurve(self):
        """
        :return: The associated aim curve's geo output.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        return self.attr('aimCurve').inputs(plugs=True)[0]

    def _sampleAt(self, parameter):
        curve = self.curve()
        aimCurve = self.aimCurve()
        refPoint = curve.pointAtParam(parameter)
        closestPoint = self.attr('closestPoint').get()

        if closestPoint:
            interest = aimCurve.closestPoint(refPoint)

        else:
            interest = aimCurve.pointAtParam(parameter)

        return interest-refPoint



