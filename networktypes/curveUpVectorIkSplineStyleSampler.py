from paya.util import short
import paya.runtime as r


class CurveUpVectorIkSplineStyleSampler(r.networks.CurveUpVectorRemapSampler):
    """
    Works similarly to IK spline handle twist, but supports multiple twist
    points.

    .. note::

        Returned vectors won't be perpendicular to curve tangents, with the
        expectation that they will be perpendicularized during subsequent
        matrix construction.
    """

    #-------------------------------------------------------|    Constructor

    @classmethod
    @short(interpolation='i')
    def create(cls, curve, paramVectorKeys, interpolation='Linear'):
        """
        :param curve: the curve on which to create the sampler
        :type curve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param paramVectorKeys: zipped *parameter, vector* pairs, indicating
            known up vectors along the curve; at least two such keys are
            needed
        :type paramVectorKeys:
            [[:class:`float` | :class:`str` | :class:`~paya.runtime.plugs.Math1D`],
            [:class:`tuple` | :class:`list`,
            :class:`paya.runtime.data.Vector`,
            :class:`paya.runtime.plugs.Vector`]]
        :param interpolation/i: a string label or integer value or plug
            specifying how to interpolate between the keyed pairs, namely:

            -   ``0`` (``'None'``) (you wouldn't normally want this)
            -   ``1`` (``'Linear'``) (the default)
            -   ``2`` (``'Smooth'``)
            -   ``3`` (``'Spline'``)

        :type interpolation/i: int, str, :class:`~paya.runtime.plugs.Math1D`
        :return: The network system.
        :rtype: :class:`CurveUpVectorIkSplineStyleSampler`
        """
        with r.NodeTracker() as track:
            node = cls._create(curve, paramVectorKeys,
                               interpolation=interpolation)

        node._tagDependencies(track.getNodes())

        return node

    @classmethod
    def _create(cls, curve, paramVectorKeys, interpolation='Linear'):
        return super(r.networks.CurveUpVectorIkSplineStyleSampler,
                   cls)._create(curve,
                   paramVectorKeys,
                   interpolation=interpolation)