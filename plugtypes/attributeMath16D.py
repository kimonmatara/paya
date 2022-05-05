import paya.runtime as r
import paya.lib.mathops as _mo
from paya.util import resolve_flags, short, cap


class AttributeMath16D:

    __math_dimension__ = 16

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).

        :param other: a 16D value or plug
        """
        other, dim, isplug = _mo.info(other)

        if dim is 16:
            node = r.nodes.AddMatrix.createNode()

            self >> node.attr('matrixIn')[1 if swap else 0]
            other >> node.attr('matrixIn')[0 if swap else 1]

            return node.attr('matrixSum')

        return NotImplemented

    def __radd__(self, other):
        """
        Implements **reflected addition** (``+``). See :meth:`__add__`.
        """
        return self.__add__(other, swap=True)

    #-----------------------------------------------------------|    Multiplication

    def __mul__(self, other, swap=False):
        """
        Implements **multiplication** (``*``).

        :param other: a value or plug of dimension 3 (left only) or 16.
        """
        other, dim, isplug = _mo.info(other)

        if dim is 3 and swap:
            node = r.nodes.PointMatrixMult.createNode()
            node.attr('vectorMultiply').set(True)
            self >> node.attr('inMatrix')
            other >> node.attr('inPoint')

            return node.attr('output')

        if dim is 16:
            node = r.nodes.MultMatrix.createNode()

            self >> node.attr('matrixIn')[1 if swap else 0]
            other >> node.attr('matrixIn')[0 if swap else 1]

            return node.attr('matrixSum')

        return NotImplemented

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``). See :meth:`__mul__`.
        """
        return self.__mul__(other, swap=True)

    #-----------------------------------------------------------|    Point-matrix mult

    def __rxor__(self, other):
        """
        Uses the exclusive-or operator (``^``) to implement
        **point-matrix multiplication** (reflected only).

        :param other: a 3D value or plug
        """
        other, dim, isplug = _mo.info(other)

        if dim is 3:
            node = r.nodes.PointMatrixMult.createNode()
            self >> node.attr('inMatrix')
            other >> node.attr('inPoint')

            return node.attr('output')

        return NotImplemented

    #-----------------------------------------------------------|    Filtering

    def _pick(
            self,
            translate=None,
            rotate=None,
            scale=None,
            shear=None
    ):
        translate, rotate, scale, shear = resolve_flags(
            translate, rotate, scale, shear
        )

        if not any([translate, rotate, scale, shear]):
            node = r.nodes.HoldMatrix.createNode()
            return node.attr('outMatrix')

        if all([translate, rotate, scale, shear]):
            return self.hold()

        node = r.nodes.PickMatrix.createNode()
        self >> node.attr('inputMatrix')

        for chan, state in zip(
            ['translate','rotate','scale','shear'],
            [translate, rotate, scale, shear]
        ):
            node.attr('use{}'.format(cap(chan))).set(state)

        return node.attr('outputMatrix')

    @short(
        translate='t',
        rotate='r',
        scale='s',
        shear='sh'
    )
    def pick(
            self,
            translate=None,
            rotate=None,
            scale=None,
            shear=None,
            default=None
    ):
        """
        Filters this matrix through one or more pickMatrix nodes, depending on
        combinations with 'default'. Flags are defined by omission, Maya-style.

        :shorthand: pk

        :param bool translate/t: use translate
        :param bool rotate/r: use rotate
        :param bool scale/s: use scale
        :param shear/sh: use shear
        :param default: take omitted fields from this matrix; can be a value
            or plug; defaults to None
        :type default: list, :class:`~paya.datatypes.matrix.Matrix`, str,
            :class:`~paya.plugtypes.attributeMath16D.AttributeMath16D`
        :return: The filtered matrix.
        :rtype: :class:`~paya.plugtypes.attributeMath16D.AttributeMath16D`
        """
        translate, rotate, scale, shear = resolve_flags(
            translate, rotate, scale, shear
        )

        if default:
            default = _mo.info(default)[0]

        if not any([translate, rotate, scale, shear]):
            return (default if default else self).hold()

        chunks = [] # (source, chanList)

        for chan, state in zip(
                ['scale','shear','rotate','translate'],
                [scale,shear,rotate,translate]
        ):
            src = self if state else default

            if src is None:
                continue

            if chunks:
                if chunks[-1][0] is src:
                    chunks[-1][1].append(chan)
                    continue

            chunks.append((src,[chan]))

        reduction = []

        for chunk in chunks:
            source, chanList = chunk
            picked = source._pick(**{chan:True for chan in chanList})
            reduction.append(picked)

        return _mo.multMatrices(*reduction)

    pk = pick

    #--------------------------------------------------------------------|    Signing

    def inverse(self):
        """
        :return: The inverse of this matrix.
        :rtype: :class:`AttributeMath16D`
        """
        node = r.nodes.InverseMatrix.createNode()
        self >> node.attr('inputMatrix')
        return node.attr('outputMatrix')

    #--------------------------------------------------------------------|    Conveniences

    def asOffset(self):
        """
        Inverts this matrix once, to create an offset matrix. Equivalent to:

        .. code-block:: python

            self.get().inverse() * self

        :return: The offset matrix.
        :rtype: :class:`AttributeMath16D`
        """
        return self.get().inverse() * self

