from paya.util import short
import paya.runtime as r



class CurveUpVectorSamplerRemap(r.networks.CurveUpVectorSampler):
    """
    Abstract base class for curve samplers that use a
    :class:`remapValue <paya.runtime.nodes.RemapValue>` node.
    """

    #----------------------------------------------------------|
    #----------------------------------------------------------|    CONSTRUCTOR
    #----------------------------------------------------------|

    @classmethod
    @short(interpolation='i')
    def create(cls, curve, paramVectorKeys, interpolation='Linear'):
        node = r.networks.CurveUpVectorSampler.create(curve)
        node.attr('payaSubtype').set(cls.__name__)
        node.__class__ = cls

        cls._initRemapValue(node, paramVectorKeys,
                            interpolation=interpolation)
        return node

    @classmethod
    def _initRemapValue(cls, network,
                        paramVectorKeys,
                        interpolation='Linear'):
        rv = r.nodes.RemapValue.createNode()
        rv.attr('message') >> network.addAttr('remapValue', at='message')
        rv.setColors(paramVectorKeys, interpolation=interpolation)
        return rv

    #----------------------------------------------------------|
    #----------------------------------------------------------|    BASIC INSPECTIONS
    #----------------------------------------------------------|

    def remapValue(self):
        """
        :return: The :class:`remapValue <paya.runtime.nodes.RemapValue>`
            node connected to this network.
        :rtype: :class:`~paya.runtime.nodes.RemapValue`
        """
        msg = self.attr('remapValue')
        inps = msg.inputs(type='remapValue')

        if inps:
            return inps[0]

    #----------------------------------------------------------|
    #----------------------------------------------------------|    SAMPLES
    #----------------------------------------------------------|

    def _sampleAtParam(self, parameter, plug=True):
        # No need to 'reuse' since that's tracked at the network
        # level
        return self.remapValue(
            ).sampleColor(parameter, reuse=False, plug=plug)