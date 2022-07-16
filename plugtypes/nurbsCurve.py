import pymel.util as _pu
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #---------------------------------------------------|    Sampling

    @short(reuse='re')
    def info(self, reuse=True):
        """
        :param bool reuse/re: Reuse any previously-connected ``curveInfo``
            node; defaults to True
        :return: A ``curveInfo`` node connected to this curve output.
        :rtype: :class:`~paya.runtime.nodes.CurveInfo`
        """
        if reuse:
            existing = self.outputs(type='curveInfo')

            if existing:
                return existing[0]

        node = r.nodes.CurveInfo.createNode()
        self >> node.attr('inputCurve')
        return node

    def length(self):
        """
        :return: The arc length of this curve output.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.info().attr('arcLength')

    def controlPoints(self):
        """
        :return: The ``.controlPoints`` multi-attribute of a connected
            ``curveInfo`` node.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.info().attr('controlPoints')

    #---------------------------------------------------|    Edits

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