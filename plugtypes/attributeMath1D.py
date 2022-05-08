from paya.util import short
import paya.lib.mathops as _mo
import paya.runtime as r

if not r.pluginInfo('quatNodes', q=True, loaded=True):
    r.loadPlugin('quatNodes')


class AttributeMath1D:

    __math_dimension__ = 1

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).

        :param other: a value or plug of dimension 1, 2, 3 or 4
        """

        other, dim, isplug = _mo.info(other)

        if dim is 1:
            node = r.nodes.AddDoubleLinear.createNode()

            self >> node.attr('input{}'.format(2 if swap else 1))
            other >> node.attr('input{}'.format(1 if swap else 2))

            return node.attr('output')

        if dim is 2:
            node = r.nodes.PlusMinusAverage.createNode()

            for child in node.attr('input2D')[1 if swap else 0]:
                self >> child

            other >> node.attr('input2D')[0 if swap else 1]

            return node.attr('output2D')

        if dim is 3:
            node = r.nodes.PlusMinusAverage.createNode()

            for child in node.attr('input3D')[1 if swap else 0]:
                self >> child

            other >> node.attr('input3D')[0 if swap else 1]

            return node.attr('output3D')

        if dim is 4:
            node = r.nodes.QuatAdd.createNode()

            for child in node.attr('input{}Quat'.format(2 if swap else 1)):
                self >> child

            for source, dest in zip(
                    other,
                    node.attr('input{}Quat'.format(1 if swap else 2))
            ):
                source >> dest

            return node.attr('outputQuat')

        return NotImplemented

    def __radd__(self, other):
        """
        Implements **reflected addition** (``+``). See :meth:`__add__`.
        """
        return self.__add__(other, swap=True)

    #-----------------------------------------------------------|    Subtraction

    def __sub__(self, other, swap=False):
        """
        Implements **subtraction** (``-``).

        :param other: a value or plug of dimension 1, 2, 3
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 2, 3):
            node = r.nodes.PlusMinusAverage.createNode()
            node.attr('operation').set(2)

            if dim is 1:
                self >> node.attr('input1D')[1 if swap else 0]
                other >> node.attr('input1D')[0 if swap else 1]

                return node.attr('output1D')

            else:
                for child in node.attr('input{}D'.format(dim))[1 if swap else 0]:
                    self >> child

                for src, dest in zip(
                        other,
                        node.attr('input{}D'.format(dim))[0 if swap else 1]
                ):
                    src >> dest

                return node.attr('output{}D'.format(dim))

        return NotImplemented

    def __rsub__(self, other):
        """
        Implements **reflected subtraction** (``-``). See :meth:`__sub__`.
        """
        return self.__sub__(other, swap=True)

    #-----------------------------------------------------------|    Multiply

    def __mul__(self, other, swap=False):
        """
        Implements **multiplication** (``-``).

        :param other: a value or plug of dimension 1 or 3
        """
        other, dim, isplug = _mo.info(other)

        if dim is 1:
            node = r.nodes.MultDoubleLinear.createNode()

            self >> node.attr('input{}'.format(2 if swap else 1))
            other >> node.attr('input{}'.format(1 if swap else 2))

            return node.attr('output')

        if dim is 3:
            node = r.nodes.MultiplyDivide.createNode()

            for dest in node.attr('input{}'.format(2 if swap else 1)):
                self >> dest

            for src, dest in zip(other, node.attr(
                    'input{}'.format(1 if swap else 2))):
                src >> dest

            return node.attr('output')

        return NotImplemented

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``-``). See :meth:`__mul__`.
        """
        return self.__mul__(other, swap=True)

    #-----------------------------------------------------------|    Divide

    def __truediv__(self, other, swap=False):
        """
        Implements **division** (``/``).

        :param other: a value or plug of dimension 1 or 3
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(2)

            if dim is 1:
                self >> node.attr('input{}X'.format(2 if swap else 1))
                other >> node.attr('input{}X'.format(1 if swap else 2))

                return node.attr('outputX')

            else:
                for dest in node.attr('input{}'.format(2 if swap else 1)):
                    self >> dest

                for source, dest in zip(
                        other,
                        node.attr('input{}'.format(1 if swap else 2))
                ):
                    source >> dest

                return node.attr('output')

        return NotImplemented

    def __rtruediv__(self, other):
        """
        Implements **reflected division** (``/``). See :meth:`__truediv__`.
        """
        return self.__truediv__(other, swap=True)

    #-----------------------------------------------------------|    Power

    def __pow__(self, other, modulo=None, swap=False):
        """
        Implements **power** (``**``). The *modulo* keyword argument is
        ignored.

        :param other: a value or plug of dimension 1 or 3
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(3)

            if dim is 1:
                self >> node.attr('input{}X'.format(2 if swap else 1))
                other >> node.attr('input{}X'.format(1 if swap else 2))

                return node.attr('outputX')

            else:
                for dest in node.attr('input{}'.format(2 if swap else 1)):
                    self >> dest

                for source, dest in zip(
                        other,
                        node.attr('input{}'.format(1 if swap else 2))
                ):
                    source >> dest

                return node.attr('output')

        return NotImplemented

    def __rpow__(self, other):
        """
        Implements **reflected power** (``**``). See :meth:`__pow__`.
        """
        return self.__pow__(other, swap=True)

    #-----------------------------------------------------------|    Unary

    def __neg__(self):
        """
        Implements unary negation (``-``).
        :return: ``self * -1.0``
        """
        mdl = r.nodes.MultDoubleLinear.createNode()
        self >> mdl.attr('input1')
        mdl.attr('input2').set(-1.0)
        return mdl.attr('output')