import paya.lib.mathops as _mo
import paya.lib.plugops as _po
from paya.util import short
import paya.runtime as r


class CurveParallelTransportUpVectorSampler(r.networks.CurveUpVectorSamplerRemap):

    @classmethod
    @short(interpolation='i', resolution='res')
    def create(cls, curve, normal, resolution=9, interpolation='Linear'):
        """

        :param curve: the curve associated with this system
        :type curve: str, :class:`~paya.runtime.nodes.NurbsCurve` ,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param normal: the starting normal
        :type normal: list, tuple, str, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param int resolution/res: the number of parallel transport solutions to
            generate; higher numbers improve accuracy at the cost of rig
            performance; defaults to 9
        :param interpolation/i: an integer or string for the interpolation
            enumerator on the :class:`remapValue <paya.runtime.nodes.RemapValue>`
            node, namely:

            -   0 / 'None' (you wouldn't normally want this)
            -   1 / 'Linear' (the default)
            -   2 / 'Smooth'
            -   3 / 'Spline'

        :type interpolation/i: str, int
        :return: The network system.
        :rtype: :class:`CurveParallelTransportUpVectorSampler`
        """
        curve = _po.asGeoPlug(curve, worldSpace=True)
        umin, umax = curve.getKnotDomain(p=False)

        params = _mo.floatRange(umin, umax, resolution)
        tangents = [curve.tangentAtParam(param) for param in params]
        normals = _mo.parallelTransport(normal, tangents)
        keymap = list(zip(params, normals))

        node = r.networks.CurveUpVectorSamplerRemap.create(
            curve, keymap, i=interpolation)

        node.attr('payaSubtype').set(cls.__name__)
        node.__class__ = cls

        return node