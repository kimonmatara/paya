import pymel.core.datatypes as _dt
import pymel.core.nodetypes as _nt
from paya.util import short
import paya.lib.mathops as _mo
import paya.runtime as r


class AttributeMath3D:

    __math_dimension__ = 3

    #-----------------------------------------------------------|    Retrieval

    @short(
        plug='p',
        rotateOrder='ro'
    )
    def get(
            self,
            plug=False,
            asPoint=None,
            asAngle=None,
            rotateOrder=None,
            **kwargs
    ):
        """
        :param bool plug/p: return self; defaults to False
        :param asPoint: return a :class:`~paya.datatypes.point.Point`
            instance; defaults to True if this is a translate channel on a
            transform, otherwise False
        :param asAngle: return an
            :class:`~paya.datatypes.eulerRotation.EulerRotation` instance;
            defaults to True if this is a rotate channel on a transform,
            otherwise False
        :param str rotateOrder/ro: used if 'asAngle' resolves to True; if this
            is a rotate channel on a transform node, defaults to the node's
            rotate order, otherwise XYZ
        :param \*\*kwargs: forwarded to the base method
        :return: bool, :class:`~paya.datatypes.vector.Vector`,
            :class:`~paya.datatypes.point.Point`,
            :class:`~paya.datatypes.eulerRotation.EulerRotation`
        """

        # Plug bail

        if plug:
            return self

        # Get basic result

        out = r.Attribute.get(self, **kwargs)

        if not isinstance(out, _dt.Array):
            return out

        # Type management

        if asPoint is None and asAngle is None:
            node = self.node()
            isXform = isinstance(node, _nt.Transform)
            sn = self.attrName()

            if isXform and sn == 't':
                asPoint = True
                asAngle = False

            else:
                children = self.getChildren()

                if all([isinstance(child, r.plugs.AttributeDoubleAngle
                                   ) for child in self.getChildren()]):
                    asPoint = False
                    asAngle = True

                    if rotateOrder is None:
                        if isXform and sn == 'r':
                            rotateOrder = node.attr(
                                'rotateOrder').get(asString=True).upper()

                        else:
                            rotateOrder = 'XYZ'

        if asPoint:
            out = r.data.Point(out)

        elif asAngle:
            out = r.data.EulerRotation(out)

            if rotateOrder is None:
                node = self.node()

                if isinstance(node, _nt.Transform) and self.attrName() == 'r':
                    rotateOrder = node.attr(
                        'rotateOrder').get(asString=True).upper()
                else:
                    rotateOrder = 'XYZ'

            elif isinstance(rotateOrder, str):
                rotateOrder = rotateOrder.upper()

            out.order = rotateOrder

        return out

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).

        :param other: a value or plug of dimension 1 or 3
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.PlusMinusAverage.createNode()

            self >> node.attr('input3D')[1 if swap else 0]

            if dim is 1:
                for dest in node.attr('input3D')[0 if swap else 1]:
                    other >> dest

            else:
                other >> node.attr('input3D')[0 if swap else 1]

            return node.attr('output3D')

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

        :param other: a value or plug of dimension 1 or 3
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.PlusMinusAverage.createNode()
            node.attr('operation').set(2)

            self >> node.attr('input3D')[1 if swap else 0]

            if dim is 1:
                for dest in node.attr('input3D')[0 if swap else 1]:
                    other >> dest

            else:
                other >> node.attr('input3D')[0 if swap else 1]

            return node.attr('output3D')

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

        :param other: a value or plug of dimension 1, 3 or right-only 16.
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()

            self >> node.attr('input{}'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr('input{}'.format(1 if swap else 2)):
                    other >> dest

            else:
                other >> node.attr('input{}'.format(1 if swap else 2))

            return node.attr('output')

        if dim is 16 and not swap:
            node = r.nodes.PointMatrixMult.createNode()
            node.attr('vectorMultiply').set(True)
            self >> node.attr('inPoint')
            other >> node.attr('inMatrix')

            return node.attr('output')

        return NotImplemented

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``). See :meth:`__mul__`.
        """
        return self.__mul__(other, swap=True)

    #-----------------------------------------------------------|    Point-matrix mult

    def __xor__(self, other):
        """
        Uses the exclusive-or operator (``^``) to implement
        **point-matrix multiplication**.

        :param other: a matrix value or plug
        """
        node = r.nodes.PointMatrixMult.createNode()
        self >> node.attr('inPoint')
        other >> node.attr('inMatrix')
        return node.attr('output')

    #-----------------------------------------------------------|    Division

    def __truediv__(self, other, swap=False):
        """
        Implements **division** (``/``).

        :param other: a value or plug of dimension 1 or 3.
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(2)

            self >> node.attr('input{}'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr('input{}'.format(1 if swap else 2)):
                    other >> dest

            else:
                other >> node.attr('input{}'.format(1 if swap else 2))

            return node.attr('output')

        return NotImplemented

    def __rtruediv__(self, other):
        """
        Implements **reflected division** (``/``). See :meth:`__truediv__`.
        """
        return self.__truediv__(other, swap=True)

    #-----------------------------------------------------------|    Power
    
    def __pow__(self, other, swap=False):
        """
        Implements **power** (``**``).

        :param other: a value or plug of dimension 1 or 3.
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(3)

            self >> node.attr('input{}'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr('input{}'.format(1 if swap else 2)):
                    other >> dest

            else:
                other >> node.attr('input{}'.format(1 if swap else 2))

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
        mdv = r.nodes.MultiplyDivide.createNode()
        self >> mdv.attr('input1')

        for child in mdv.attr('input2').getChildren():
            child.set(-1.0)

        return mdv.attr('output')