import pymel.util as _pu
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #-----------------------------------------------|    Shape Edits

    @short(select='sel')
    def detach(self, *parameters, select=None):
        """
        Detaches this curve at the specified parameter(s).

        :param \*parameters: the parameter(s) at which to 'cut' the curve
        :type \*parameters: float, :class:`~paya.runtime.plugs.Math1D`
        :param select/sel: a subset of output indices to include in the
            return; ``keep`` attributes will configured accordingly
        :return: [:class:`~paya.runtime.plugs.NurbsCurve`]
        """
        parameters = _pu.expandArgs(*parameters)

        if not parameters:
            raise RuntimeError("No parameter(s) specified.")

        node = r.nodes.DetachCurve.createNode()

        self >> node.attr('inputCurve')

        for i, parameter in enumerate(parameters):
            parameter >> node.attr('parameter')[i]

        node.attr('outputCurve').evaluate()
        outputIndices = range(len(parameters)-1)

        if select is None:
            selectedIndices = outputIndices

        else:
            selectedIndices = _pu.expandArgs(select)

            for outputIndex in outputIndices:
                node.attr('keep')[
                    outputIndex].set(outputIndex in selectedIndices)

        return [node.attr('outputCurve'
            )[selectedIndex] for selectedIndex in selectedIndices]