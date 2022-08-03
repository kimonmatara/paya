from paya.util import short
import paya.runtime as r
import paya.lib.mathops as _mo
import paya.lib.plugops as _po


class CurveParallelTransportUpGenerator(r.networks.CurveUpGenerator):

    @classmethod
    @short(interpolation='i', resolution='res', fromEnd='fe')
    def create(cls, curve, normal, resolution=None,
               unwindSwitch=0, interpolation=1, fromEnd=False):
        """
        :param curve: the main curve
        :type curve: str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param normal: the normal / up vector to start solving from
        :type normal: list, tuple, str, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param int resolution/res: the number of parallel-transport solution
            points along the curve; more solutions yield more accuracy at the
            cost of interaction speed; if omitted, defaults to 9
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
        :param bool fromEnd/fe: solve as if *normal* is defined at the end,
            not the start, of the curve; defaults to False
        :return: The network node.
        :rtype: :class:`~paya.runtime.networks.CurveParallelTransportUpGenerator`
        """

        curve = _po.asGeoPlug(curve)

        with r.Name(curve.node().basename(sts=True), 'ptUpGen'):

            #--------------------------------------------|    Basics

            node = cls.createNode()
            node._addSamplesAttr()
            curve >> node.addAttr('curve', at='message')
            rv = r.nodes.RemapValue.createNode()
            rv.attr('message') >> node.addAttr('remapValue', at='message')

            #--------------------------------------------|    Solve

            if resolution is None:
                resolution = 9

            fractions = _mo.floatRange(0, 1, resolution)
            params = [curve.paramAtFraction(f) for f in fractions]
            tangents = [curve.tangentAtParam(param) for param in params]

            if fromEnd:
                normals = _mo.parallelTransport(normal, tangents[::-1])[::-1]

            else:
                normals = _mo.parallelTransport(normal, tangents)

            #--------------------------------------------|    Confg remap value

            rv.setColors(zip(params, normals), i=interpolation)

        return node

    def remapValue(self):
        """
        :return: The associated remap value node.
        :rtype: :class:`~paya.runtime.nodes.RemapValue`
        """
        return self.attr('remapValue').inputs()[0]

    def _sampleAt(self, parameter):
        return self.remapValue().sampleColor(parameter)

