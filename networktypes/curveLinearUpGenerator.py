import paya.lib.plugops as _po
import paya.runtime as r
from paya.util import short


class CurveLinearUpGenerator(r.networks.CurveUpGenerator):
    """
    Curve up vector generator with linearly interpolated vector keys. Behaves
    similarly to an IK spline handle.
    """

    @classmethod
    @short(interpolation='i')
    def create(cls, curve, paramVectorKeys, interpolation=1):
        """
        :param curve: the main curve
        :type curve: str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param paramVectorKeys:
            zipped *parameter, vector* pairs defining known up vectors between
            which to blend; this should include entries for the minimum and
            maximum parameters in the curve U domain, otherwise you may get
            unexpected results; defaults to None
        :param interpolation/i: an integer plug or value defining which type
            of interpolation should be applied to any subsequently sampled
            values; this tallies with the color interpolation enums on a
            :class:`remapValue <paya.runtime.nodes.RemapValue>` node, which
            are:

            - 0 ('None', you wouldn't usually want this)
            - 1 ('Linear') (the default)
            - 2 ('Smooth')
            - 3 ('Spline')

        :type interpolation/i: int, :class:`~paya.runtime.plugs.Math1D`
        :return: The network node.
        :rtype: :class:`~paya.runtime.networks.CurveLinearUpGenerator`
        """
        curve = _po.asGeoPlug(curve)

        with r.Name(curve.node().basename(sts=True), 'linear_up_gen'):
            node = cls.createNode()
            curve >> node.addAttr('curve', at='message')

            rv = r.nodes.RemapValue.createNode()
            rv.attr('message') >> node.addAttr('remapValue', at='message')
            rv.setColors(paramVectorKeys, i=interpolation)

            node._addSamplesAttr()

        return node

    def remapValue(self):
        """
        :return: The associated remap value node.
        :rtype: :class:`~paya.runtime.nodes.RemapValue`
        """
        return self.attr('remapValue').inputs()[0]

    def _sampleAt(self, parameter):
        return self.remapValue().sampleColor(parameter)