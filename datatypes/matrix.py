from functools import reduce

import pymel.core.datatypes as _dt
import paya.lib.mathops as _mo
import paya.runtime as r
from paya.util import short, resolve_flags


class Matrix:

    #-----------------------------------------------------------|    Addition

    def __add__(self, other):
        """
        Implements **addition** (``+``).

        Overloads :meth:`pymel.core.datatypes.Matrix.__add__` to add
        support for 16D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim is 16:
                node = r.nodes.AddMatrix.make()

                node.attr('matrixIn')[0].set(self)
                other >> node.attr('matrixIn')[1]

                return node.attr('matrixSum')

            raise NotImplemented

        return _dt.Matrix.__add__(self, other)

    def __radd__(self, other):
        """
        Implements **reflected addition** (``+``).

        Overloads :meth:`pymel.core.datatypes.Matrix.__add__` to add
        support for 16D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:

            if dim is 16:
                node = r.nodes.AddMatrix.make()

                node.attr('matrixIn')[1].set(self)
                other >> node.attr('matrixIn')[0]

                return node.attr('matrixSum')

            raise NotImplemented

        return _dt.Matrix.__radd__(self, other)

    #-----------------------------------------------------------|    Multiplication

    def __mul__(self, other):
        """
        Implements **multiplication** (``*``).

        Overloads :meth:`pymel.core.datatypes.Matrix.__mul__` to add
        support for 16D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim is 16:
                node = r.nodes.MultMatrix.make()

                node.attr('matrixIn')[0].set(self)
                other >> node.attr('matrixIn')[1]

                return node.attr('matrixSum')

            raise NotImplemented

        return _dt.Matrix.__mul__(self, other)

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``).

        Overloads :meth:`pymel.core.datatypes.Matrix.__mul__` to add
        support for 3D and 16D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim is 3:
                node = r.nodes.PointMatrixMult.make()
                node.attr('vectorMultiply').set(True)
                other >> node.attr('inPoint')
                node.attr('inMatrix').set(self)

                return node.attr('output')

            if dim is 16:
                node = r.nodes.MultMatrix.make()

                node.attr('matrixIn')[1].set(self)
                other >> node.attr('matrixIn')[0]

                return node.attr('matrixSum')

            raise NotImplemented

        return _dt.Matrix.__rmul__(self, other)

    #-----------------------------------------------------------|    Point-matrix multiplication

    def __rxor__(self, other):
        """
        Uses the exclusive-or operator (``^``) to implement
        **point-matrix multiplication** for 3D values and plugs.
        """
        other, dim, isplug = _mo.info(other)

        if dim is 3:
            if isplug:
                node = r.nodes.PointMatrixMult.make()
                other >> node.attr('inPoint')
                node.attr('inMatrix').set(self)

                return node.attr('output')

            else:
                return r.data.Point(other) * self

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

        if all([translate, rotate, scale, shear]):
            return self.copy()

        if not any([translate, rotate, scale, shear]):
            return type(self)()

        elems = []
        _self = r.data.TransformationMatrix(self)

        if scale:
            matrix = r.data.TransformationMatrix()
            matrix.setScale(_self.getScale('transform'),'transform')
            elems.append(matrix)

        if shear:
            matrix = r.data.TransformationMatrix()
            matrix.setShear(_self.getShear('transform'),'transform')
            elems.append(matrix)

        if rotate:
            matrix = r.data.TransformationMatrix()
            matrix.setRotation(_self.getRotation())
            elems.append(matrix)

        if translate:
            matrix = r.data.TransformationMatrix()
            matrix.setTranslation(
                _self.getTranslation('transform'),'transform')
            elems.append(matrix)

        if elems:
            elems = map(r.data.Matrix, elems)
            return reduce(lambda x, y: x*y, elems)

        return r.data.Matrix()

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
        Filters this matrix, similar to Maya's pickMatrix. If 'default' is
        used, and it's a plug, the output will also be a plug.

        Flags are defined by omission, Maya-style.

        :shorthand: pk

        :param bool translate/t: use translate
        :param bool rotate/r: use rotate
        :param bool scale/s: use scale
        :param shear/sh: use shear
        :param default: take omitted fields from this matrix; can be a value
            or plug; defaults to None
        :type default: list, :class:`Matrix`, str, :class:`AttributeMath16D`
        :return: The filtered matrix.
        :rtype: :class:`Matrix` or :class:`AttributeMath16D`
        """
        translate, rotate, scale, shear = resolve_flags(
            translate, rotate, scale, shear
        )

        if all([translate, rotate, scale, shear]):
            return self.hold()

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

    #-----------------------------------------------------------|    Conveniences

    @classmethod
    def asOffset(cls):
        """
        Implemented for parity with :meth:`paya.plugtypes.attributeMath16D.AttributeMath16D.asOffset`.
        Returns an identity matrix.
        """
        return cls()