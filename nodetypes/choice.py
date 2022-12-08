from paya.util import short
import paya.runtime as r


class Choice:

    @classmethod
    @short(name='n', selector='s')
    def create(cls, *inputs, name=None,
               unitInputsToDouble=False, selector=None):
        """
        :param \*inputs: input plugs
        :type \*inputs: :class:`paya.runtime.plugs.Attribute` |
            [:class:`paya.runtime.plugs.Attribute`]
        :param str name/n: an optional name for the node; defaults to contextual
            naming
        :param bool unitInputsToDouble/utd: if any of the inputs are of
            type ``doubleLinear`` or ``doubleAngle``, convert them according
            to Maya rules to ``double`` instead; defaults to ``False``
        :param selector/s: an optional value or driver for the ``selector``
            attribute; defaults to ``None``
        :type selector/s: :class:`str`, :class:`int`,
            :class:`~paya.runtime.plugs.Math1D`
        :return: The configured ``choice`` node.
        :rtype: :class:`Choice`
        """
        node = cls.createNode(n=name)

        if selector is not None:
            selector >> node.attr('selector')

        if inputs:
            inputs = [r.Attribute(input) for input \
                      in r.util.expandArgs(inputs)]

            if unitInputsToDouble:
                _inputs = []

                for i, input in enumerate(inputs):
                    if input.type() in ('doubleLinear', 'doubleAngle'):
                        proxyName = 'doubleInput{}'.format(i)
                        node.addAttr(proxyName, at='double', k=True)
                        input >> node.attr(proxyName)
                        _inputs.append(node.attr(proxyName))

                    else:
                        _inputs.append(input)

                inputs = _inputs

            for i, input in enumerate(inputs):
                input >> node.attr('input')[i]

        return node