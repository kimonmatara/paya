import paya.lib.mathops as _mo
import paya.runtime as r
from paya.util import short


class CurveUpVectorPtSampler(r.networks.CurveUpVectorRemapSampler):
    """
    Solves for parallel-transport from a single starter vector.
    """

    #-------------------------------------------------------|    Constructor

    @classmethod
    @short(interpolation='i', resolution='res')
    def create(cls, curve, upVector, resolution=9, interpolation='Linear'):
        """
        :param curve: the curve on which to create the sampler
        :type curve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param upVector: the starter vector for the parallel-transport
            solution
        :type upVector: tuple, list, str, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param int resolution/res: the number of parallel-transport solutions to
            generate along the curve; higher numbers improve accuracy at the
            expense of performance; defaults to 9
        :param interpolation/i: a string label or integer value or plug
            specifying how to interpolate between the keyed pairs, namely:

            -   ``0`` (``'None'``) (you wouldn't normally want this)
            -   ``1`` (``'Linear'``) (the default)
            -   ``2`` (``'Smooth'``)
            -   ``3`` (``'Spline'``)

        :type interpolation/i: int, str, :class:`~paya.runtime.plugs.Math1D`
        :return: The network system.
        :rtype: :class:`CurveUpVectorPtSampler`
        """
        with r.NodeTracker() as track:
            node = cls._create(curve, upVector,
                               resolution=resolution,
                               interpolation=interpolation)

        node._tagDependencies(track.getNodes())

        return node

    @classmethod
    def _create(cls, curve, upVector, resolution=9, interpolation='Linear'):
        # Solve parallel transport
        curve = _tm.asGeoPlug(curve, worldSpace=True)
        fractions = _mo.floatRange(0, 1, resolution)
        params = [curve.paramAtFraction(f, p=False) for f in fractions]
        tangents = [curve.tangentAtParam(param, p=True) for param in params]

        # Build up keymap, pass along to CurveUpVectorRemapSampler
        upVectors = _mo.parallelTransport(upVector, tangents)
        keymap = list(zip(params, upVectors))

        return super(r.networks.CurveUpVectorPtSampler, cls)._create(
                         curve, keymap, interpolation=interpolation)