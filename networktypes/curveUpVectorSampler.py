import paya.lib.mathops as _mo
import paya.lib.plugops as _po
import paya.runtime as r
from paya.util import short


class CurveUpVectorSampler:

    #----------------------------------------------------------|
    #----------------------------------------------------------|    CONSTRUCTOR
    #----------------------------------------------------------|

    @classmethod
    def create(cls, curve):
        curve = _po.asGeoPlug(curve, worldSpace=True)

        # Node
        name = r.nodes.Network.makeName(
            curve.node().basename(),
            curve.attrName(),
            'upVecSampler'
        )

        node = r.createNode('network', n=name)
        node.addAttr('payaSubtype', dt='string')
        node.attr('payaSubtype').set(cls.__name__)

        # Tag curve
        curve >> node.addAttr('curve', at='message')

        # Samples attr
        node.addAttr('samples', at='compound', nc=2, multi=True)
        node.addAttr('parameter', at='double', parent='samples')
        node.addAttr('vector', at='double3', nc=3, parent='samples')

        for ax in 'XYZ':
            node.addAttr('vector'+ax, parent='vector')

        return node.expandClass()

    #----------------------------------------------------------|
    #----------------------------------------------------------|    BASIC INSPECTIONS
    #----------------------------------------------------------|

    def curve(self):
        """
        :return: The curve input for this sampler system.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        msg = self.attr('curve')
        inputs = msg.inputs(plugs=True)

        if inputs:
            return inputs[0]

    #----------------------------------------------------------|
    #----------------------------------------------------------|    SAMPLES
    #----------------------------------------------------------|

    @short(plug='p')
    def sampleAtParam(self, parameter, plug=True):
        """
        :param parameter: the parameter to sample
        :type parameter: :class:`float`, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: return a plug, not just a value; defaults to True
        :return: A sample output at the specified parameter.
        """
        if plug:
            arr = self.attr('samples')
            indices = arr.getArrayIndices()

            parameter, pdim, pisplug = _mo.info(parameter)

            for index in indices:
                compound = arr[index]
                thisparameter = compound.attr('parameter')
                thisParameterInputs = thisparameter.inputs(plugs=True)

                if thisParameterInputs and pisplug:
                    if thisParameterInputs[0] == parameter:
                        return compound.attr('vector')

                elif (not thisParameterInputs) and (not pisplug):
                    if thisparameter.get() == parameter:
                        return compound.attr('vector')

            index = arr.getNextArrayIndex()
            compound = arr[index]
            compound.attr('parameter').put(parameter, p=pisplug)

            self._sampleAtParam(
                compound.attr('parameter')) >> compound.attr('vector')

            return compound.attr('vector')

        return self._sampleAtParam(parameter, plug=False)

    def _sampleAtParam(self, parameter, plug=False):
        """
        This should be overriden to return a vector plug or
        value.
        """
        raise NotImplementedError