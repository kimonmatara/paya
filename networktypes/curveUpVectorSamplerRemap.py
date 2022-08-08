import paya.runtime as r


class CurveUpVectorSamplerRemap(r.networks.CurveUpVectorSampler):

    #----------------------------------------------------------|
    #----------------------------------------------------------|    CONSTRUCTOR
    #----------------------------------------------------------|

    @classmethod
    def create(cls, curve, paramVectorKeys):
        node = super(cls, cls).create(curve)
        node._initRemapValue(node, paramVectorKeys)
        return node

    @classmethod
    def _initRemapValue(cls, network, paramVectorKeys):
        rv = r.nodes.RemapValue.createNode()
        rv.attr('message') >> network.addAttr('remapValue', at='message')
        rv.setColors(paramVectorKeys)
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