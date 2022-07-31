import paya.lib.nurbsutil as _nu
import paya.lib.mathops as _mo
import paya.lib.plugops as _po
import paya.runtime as r



class CurveUpGenerator:
    """
    Abstract base class for a curve up-vector generator system.
    """
    @classmethod
    def create(cls, curve):
        """
        :raises NotImplementedError: Not implemented on the base class. Call
            on a concrete subclass, such as
            :class:`~paya.runtime.networks.CurveAimUpGenerator`.
        """
        raise NotImplementedError

    @classmethod
    def _create(cls, curvePlug):
        node = cls.createNode()
        curvePlug >> node.addAttr('curve', at='message')

        node.addAttr('samples', at='compound', multi=True, nc=2)
        node.addAttr('parameter', at='double', k=True, dv=0.0, parent='samples')
        node.addAttr('upVector', at='double3', k=True, parent='samples', nc=3)
        node.addAttr('upVectorX', at='doubleLinear', k=True, parent='upVector')
        node.addAttr('upVectorY', at='doubleLinear', k=True, parent='upVector')
        node.addAttr('upVectorZ', at='doubleLinear', k=True, parent='upVector')

        return node

    def curvePlug(self):
        """
        :return: The output of the main curve associated with this system.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        out = self.attr('curve').inputs(plugs=True)

        if out:
            return out[0]

    def sampleAt(self, parameter):
        """
        Previous samples with the same parameter argument (whether a value
        or plug) will be retrieved and reused.

        :param parameter: the parameter at which to generate an up vector
        :type parameter: float, str, :class:`~paya.runtime.plugs.Math1D`
        :return: The sampled up vector.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        # Look for an existing sample
        param, pdim, pisplug = _mo.info(parameter)

        if not pisplug:
            param = float(param)

        arr = self.attr('samples')
        indices = arr.getArrayIndices()

        for index in indices:
            compound = arr[index]

            pplug = compound.attr('parameter')
            inputs = pplug.inputs(plugs=True)

            if (inputs and pisplug and inputs[0] == param) \
                    or (((not inputs) and not pisplug) \
                    and param == pplug.get()):
                return compound.attr('upVector')

        index = arr.getNextArrayIndex()
        compound = arr[index]
        compound.attr('parameter').put(param, p=pisplug)
        self._sampleAt(parameter) >> compound.attr('upVector')

        return compound.attr('upVector')

    def __getitem__(self, parameter):
        """
        Indexed version of :meth:`sampleAt`.
        """
        return self.sampleAt(parameter)