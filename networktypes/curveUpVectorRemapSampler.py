import paya.runtime as r
from paya.util import short


class CurveUpVectorRemapSampler(r.networks.CurveUpVectorSampler):
    """
    Abstract base class for up vector samplers that interpolate using a
    remapValue node.
    """
    #-------------------------------------------------------|    Constructor

    @classmethod
    @short(interpolation='i')
    def create(cls, curve, keymap, interpolation='Linear'):
        """
        Not for direct use; called by the subclasses.

        :param curve: the curve on which to create the sampler
        :type curve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param keymap: zipped *parameter, vector* pairs, indicating
            known up vectors along the curve; at least two such keys are
            needed
        :type keymap:
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
        :rtype: :class:`CurveUpVectorRemapSampler`
        """
        with r.NodeTracker() as track:
            node = cls._create(curve, keymap, interpolation=interpolation)

        node._tagDependencies(track.getNodes())

        return node

    @classmethod
    def _create(cls, curve, keymap, interpolation='Linear'):
        node = super(r.networks.CurveUpVectorRemapSampler, cls)._create(curve)
        node._initRemapValue(keymap, interpolation=interpolation)
        return node

    #-------------------------------------------------------|    Partial construction

    def _initRemapValue(self, keymap, interpolation='Linear'):
        keymap = list(keymap)

        if len(keymap) < 2:
            raise ValueError("Need at least two param: vector keys.")

        rv = r.nodes.RemapValue.createNode()
        rv.setColors(keymap, i=interpolation)
        rv.attr('message') >> self.addAttr('remapValue', at='message')
        return rv

    #-------------------------------------------------------|    Basic inspections

    def remapValue(self):
        out = self.attr('remapValue').inputs(type='remapValue')

        if out:
            return out[0]

    def _sampleAtParam(self, param, plug=True):
        # No need to pass reuse=True, since chasing is managed at the
        # sampler level
        out = self.remapValue().sampleColor(param, p=plug, re=False)

        if not plug:
            out = r.data.Vector(out)

        return out