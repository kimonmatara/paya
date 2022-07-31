import paya.lib.plugops as _po
import paya.runtime as r
from paya.util import short



class CurveLinearUpGenerator(r.networks.CurveUpGenerator):

    @classmethod
    @short(interpolation='i')
    def create(cls, curve, paramUpVectorKeys, interpolation=None):
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