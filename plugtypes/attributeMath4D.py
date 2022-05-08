from paya.util import short
import paya.lib.mathops as _mo
import paya.runtime as r

if not r.pluginInfo('quatNodes', q=True, loaded=True):
    r.loadPlugin('quatNodes')


class AttributeMath4D:

    __math_dimension__ = 4

    #-----------------------------------------------------------|    Getting

    @short(plug='p')
    def get(self, plug=False, **kwargs):
        """
        Overloads :meth:`paya.plugtypes.Attribute.get` to return
        :class:`~paya.datatypes.quaternion.Quaternion` instances.
        """
        result = r.plugs.Attribute.get(self, p=plug)

        if plug:
            return result

        return r.data.Quaternion(result)

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).

        :param other: a value or plug of dimension 1 or 4
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 4):
            node = r.nodes.QuatAdd.createNode()

            self >> node.attr('input{}Quat'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr('input{}Quat'.format(1 if swap else 2)):
                    other >> dest

            else:
                for src, dest in zip(other,node.attr('input{}Quat'.format(1 if swap else 2))):
                    src >> dest

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

        :param other: a value or plug of dimension 1 or 4
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 4):
            node = r.nodes.QuatSub.createNode()

            self >> node.attr('input{}Quat'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr('input{}Quat'.format(1 if swap else 2)):
                    other >> dest

            else:
                for src, dest in zip(
                        other,
                        node.attr('input{}Quat'.format(1 if swap else 2))
                ):
                    src >> dest

            return node.attr('outputQuat')

        return NotImplemented

    def __rsub__(self, other):
        """
        Implements **reflected subtraction** (``-``). See :meth:`__sub__`.
        """
        return self.__sub__(other, swap=True)

    #-----------------------------------------------------------|    Multiplication
    
    def __mul__(self, other, swap=False):
        """
        Implements **multiplication** (``*``).

        :param other: a value or plug of dimension 1 or 4
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 4):
            node = r.nodes.QuatProd.createNode()

            self >> node.attr('input{}Quat'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr('input{}Quat'.format(1 if swap else 2)):
                    other >> dest

            else:
                for src, dest in zip(
                        other,
                        node.attr('input{}Quat'.format(1 if swap else 2))
                ):
                    src >> dest

            return node.attr('outputQuat')

        return NotImplemented

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``). See :meth:`__mul__`.
        """
        return self.__mul__(other, swap=True)

    #-----------------------------------------------------------|    Unary

    def __neg__(self):
        """
        Implements unary negation (``-``) via ``quatNegate``.
        """
        qn = r.nodes.QuatNegate.createNode()
        self >> node.attr('inputQuat')
        return node.attr('outputQuat')