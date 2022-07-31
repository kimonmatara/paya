import paya.lib.mathops as _mo
import paya.runtime as r


class CurveUpGenerator:
    """
    Abstract base class for a curve up vector generator.
    """

    def sampleAt(self, parameter):
        """
        :param parameter: the parameter at which to sample the up
            vector
        :type parameter: float, str, :class:`~paya.runtime.
        :return: An up vector sampled at the specified parameter.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        parameter, pdim, pisplug = _mo.info(parameter)
        array = self.attr('samples')
        indices = array.getArrayIndices()

        for index in indices:
            compound = array[index]
            inputs = compound.attr('parameter').inputs(plugs=True)

            if inputs:
                if pisplug:
                    if inputs[0] == parameter:
                        return compound.attr('upVector')

            else:
                if not pisplug:
                    if parameter == compound.attr('parameter').get():
                        return compound.attr('upVector')

        index = array.getNextArrayIndex()
        compound = array[index]

        compound.attr('parameter').put(parameter, p=pisplug)
        self._sampleAt(parameter) >> compound.attr('upVector')
        return compound.attr('upVector')

    def __getitem__(self, parameter):
        """
        Indexed-access version of :meth:`sampleAt`.
        """
        return self.sampleAt(parameter)

    def _addSamplesAttr(self):
        self.addAttr('samples', at='compound', multi=True, nc=2)
        self.addAttr('parameter', parent='samples')
        self.addAttr('upVector', parent='samples', at='double3', nc=3)

        for axis in 'XYZ':
            self.addAttr('upVector'+axis,
                         parent='upVector', at='doubleLinear')

        return self.attr('samples')

    def curve(self):
        """
        :return: The curve's geo output.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        return self.attr('curve').inputs(plugs=True)[0]