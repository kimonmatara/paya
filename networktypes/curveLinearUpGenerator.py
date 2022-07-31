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
    def create(cls, curve, paramUpVectorKeys, interpolation='Linear'):
        """
        :param curve: the main curve
        :type curve: str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param paramUpVectorKeys: zipped param: upVector pairs, defining
            'known' up vectors at specific parameters between which to
            interpolate
        :param interpolation/i: this can be either one enum key or index
            for the value interpolation, or a list of them
            (one per key: value pair) The enums are:

            -   0: 'None'
            -   1: 'Linear' (the default)
            -   2: 'Smooth'
            -   3: 'Spline'
        :return:
        """
        curve = _po.asGeoPlug(curve, ws=True)

        with r.Name(curve.node().basename(sts=True), 'linear_up_gen'):
            node = cls.createNode()
            curve >> node.addAttr('curve', at='message')

            rv = r.nodes.RemapValue.createNode()
            rv.attr('message') >> node.addAttr('remapValue', at='message')
            rv.setColors(paramUpVectorKeys, i=interpolation)

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