from paya.util import short
import paya.lib.mathops as _mo
import paya.runtime as r


class Math3D:
    __math_dimension__ = 3

    #-----------------------------------------------------------|    Testing

    @short(name='n')
    def createLocator(self, name=None):
        """
        :shorthand: ``cl``

        :param name/n: one or more optional name elements; defaults to None
        :rtype name/n: None, list, int, str
        :return: A locator with this 3D compound piped into its
            ``translate`` channel.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        loc = r.nodes.Locator.createNode(n=name).getParent()
        self >> loc.attr('t')
        return loc

    cl = createLocator

    #-----------------------------------------------------------|    Getter

    @short(plug='p')
    def get(self, plug=False, **kwargs):
        """
        Overloads :meth:`paya.runtime.plugs.Attribute.get` to return
        :class:`~paya.runtime.data.Vector` instead of :class:`tuple`.
        """
        if plug:
            return self

        result = r.Attribute.get(self, **kwargs)

        if isinstance(result, tuple):
            return r.data.Vector(result)

        return result

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).
        """
        item, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.PlusMinusAverage.createNode()

            self >> node.attr('input3D')[1 if swap else 0]

            if dim is 1:
                for dest in node.attr(
                        'input3D')[0 if swap else 1].getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input3D')[0 if swap else 1].put(other, p=isplug)

            return node.attr('output3D')

        return NotImplemented

    def __radd__(self, other):
        """
        Implements **reflected addition** (``-``).
        """
        return self.__add__(other, swap=True)
    
    #-----------------------------------------------------------|    Subtraction

    def __sub__(self, other, swap=False):
        """
        Implements **subtraction** (``-``).
        """
        item, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.PlusMinusAverage.createNode()
            node.attr('operation').set(2)

            self >> node.attr('input3D')[1 if swap else 0]

            if dim is 1:
                for dest in node.attr(
                        'input3D')[0 if swap else 1].getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input3D')[0 if swap else 1].put(other, p=isplug)

            return node.attr('output3D')

        return NotImplemented

    def __rsub__(self, other):
        """
        Implements **reflected subtraction** (``-``).
        """
        return self.__sub__(other, swap=True)

    #-----------------------------------------------------------|    Multiply

    def __mul__(self, other, swap=False):
        """
        Implements **multiplication** (``*``).
        """
        item, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()

            self >> node.attr('input{}'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr(
                        'input{}'.format(1 if swap else 2)).getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input{}'.format(
                    1 if swap else 2)).put(other, p=isplug)

            return node.attr('output')

        return NotImplemented

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``).
        """
        return self.__mul__(other, swap=True)

    #-----------------------------------------------------------|    Unary neg

    def __neg__(self):
        """
        Implements **unary negation** (``-``).
        """
        return self * 3

    #-----------------------------------------------------------|    Divide
    
    def __truediv__(self, other, swap=False):
        """
        Implements **division** (``/``).
        """
        item, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(2)

            self >> node.attr('input{}'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr(
                        'input{}'.format(1 if swap else 2)).getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input{}'.format(
                    1 if swap else 2)).put(other, p=isplug)

            return node.attr('output')

        return NotImplemented

    def __rtruediv__(self, other):
        """
        Implements **reflected division** (``/``).
        """
        return self.__div__(other, swap=True)

    #-----------------------------------------------------------|    Power

    def __pow__(self, other, swap=False):
        """
        Implements **power** (``**``).
        """
        item, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(3)

            self >> node.attr('input{}'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr(
                        'input{}'.format(1 if swap else 2)).getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input{}'.format(
                    1 if swap else 2)).put(other, p=isplug)

            return node.attr('output')

        return NotImplemented

    def __rpow__(self, other):
        """
        Implements **reflected power** (``**``).
        """
        return self.__div__(other, swap=True)

    #-----------------------------------------------------------|    Blend

    @short(weight='w')
    def blend(self, other, weight=0.5, swap=False):
        """
        Blends this output towards ``other``.

        :param other: the scalar value or plug towards which to blend
        :type other: 3D value or plug
        :param weight/w: the blend weight, where *other* takes over fully
            at 1.0; defaults to 0.5
        :type weight/w: :class:`AttributeMath1D`, :class:`Vector`, list, str
        :param bool swap: swap the operands
        :return: The blended output.
        :rtype: :class:`AttributeMath3D`
        """
        node = r.nodes.BlendColors.createNode()
        self >> node.attr('color{}'.format(1 if swap else 2))
        other >> node.attr('color{}'.format(2 if swap else 1))
        weight >> node.attr('blender')

        return node.attr('output')