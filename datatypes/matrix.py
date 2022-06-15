from functools import reduce

import pymel.core.datatypes as _dt
import paya.lib.mathops as _mo
import paya.runtime as r
from paya.util import short, resolve_flags

fieldsmap = {
    'x': ['a00','a01','a02'],
    'y': ['a10','a11','a12'],
    'z': ['a20','a21','a22'],
    't': ['a30','a31','a32'],
    'translate': ['a30','a31','a32'],
}


class Matrix:

    #-----------------------------------------------------------|    Testing

    def createLocator(self, scale=1.0):
        """
        Creates a locator and drives its SRT channels using this matrix.

        :shorthand: ``cl``

        :param float scale: the locator display scale; defaults to 1.0
        :return: The locator.
        :rtype: :class:`~paya.nodetypes.transform.Transform`
        """
        loc = r.nodes.Locator.createNode().getParent()
        loc.attr('displayLocalAxis').set(True)
        loc.attr('localScale').set([scale] * 3)

        loc.setMatrix(self)

        return loc

    cl = createLocator

    #-----------------------------------------------------------|    Decomposition

    @short(rotateOrder='ro')
    def decompose(self, rotateOrder='xyz'):
        """
        Decomposes this matrix.

        :param rotateOrder/ro: the rotate order to apply; defaults to 'xyz'
        :type rotateOrder/ro: str, int
        :return: dictionary of {channelName: :class:`~paya.datatypes.point.Point`,
            :class:`~paya.datatypes.vector.Vector`
            or :class:`~paya.datatypes.eulerRotation.EulerRotation`}
        :rtype: dict
        """
        this = _dt.TransformationMatrix(self)

        return {
            'translate': _dt.Point(this.getTranslation('transform')),
            'rotate': this.getRotation().reorder(rotateOrder.upper()),
            'scale': _dt.Vector(this.getScale('transform')),
            'shear': _dt.Vector(this.getShear('transform'))
        }

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
                node = r.nodes.AddMatrix.createNode()

                node.attr('matrixIn')[0].set(self)
                node.attr('matrixIn')[1].put(other, p=isplug)

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
                node = r.nodes.AddMatrix.createNode()

                node.attr('matrixIn')[1].set(self)
                node.attr('matrixIn')[0].put(other, p=isplug)

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
                node = r.nodes.MultMatrix.createNode()

                node.attr('matrixIn')[0].set(self)
                node.attr('matrixIn')[1].put(other, p=isplug)

                return node.attr('matrixSum')

            raise NotImplemented

        return _dt.Matrix.__mul__(self, other)

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``).

        Overloads :meth:`pymel.core.datatypes.Matrix.__rmul__` to add
        support for 3D and 16D plugs as well as simple types.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim is 3:
                node = r.nodes.PointMatrixMult.createNode()
                node.attr('vectorMultiply').set(True)
                node.attr('inPoint').put(other, p=isplug)
                node.attr('inMatrix').set(self)

                return node.attr('output')

            if dim is 16:
                node = r.nodes.MultMatrix.createNode()

                node.attr('matrixIn')[1].set(self)
                node.attr('matrixIn')[0].put(other, p=isplug)

                return node.attr('matrixSum')

            raise NotImplemented

        else:
            if dim is 3:
                return r.data.Vector(other) * self

            elif dim is 16:
                return r.data.Matrix(other) * self

        return _dt.Matrix.__rmul__(self, other) # Let it error

    #-----------------------------------------------------------|    Point-matrix multiplication

    def __rxor__(self, other):
        """
        Uses the exclusive-or operator (``^``) to implement
        **point-matrix multiplication** for 3D values and plugs.
        """
        other, dim, isplug = _mo.info(other)

        if dim is 3:
            if isplug:
                node = r.nodes.PointMatrixMult.createNode()
                node.attr('inPoint').put(other, p=isplug)
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
        :type default: list, :class:`~paya.datatypes.matrix.Matrix`, str, :class:`~paya.plugtypes.matrix.Matrix`
        :return: The filtered matrix.
        :rtype: :class:`~paya.datatypes.matrix.Matrix` or :class:`~paya.plugtypes.matrix.Matrix`
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
        Implemented for parity with :meth:`paya.plugtypes.matrix.Matrix.asOffset`.
        Returns an identity matrix.
        """
        return cls()

    #-----------------------------------------------------------|    Axis getting

    @short(normalize='nr')
    def getAxis(self, axis, normalize=False):
        """
        Extracts the specified axis from this matrix as a vector or point
        value. Used to implement the following properties: **x**, **y**,
        **z** and **translate**/**t**. The property versions will always
        return non-normalized values.

        :param str axis: the axis to extract, one of 'x', 'y', 'z', '-x',
            '-y', '-z' or 'translate' / 't'
        :param bool normalize: normalize the extracted vector; defaults
            to False
        :return: :class:`~paya.datatypes.vector.Vector`, :class:`~paya.datatypes.point.Point`
        """
        absAxis = axis.strip('-')
        fields = fieldsmap[absAxis]

        vals = [getattr(self, field) for field in fields]

        cls = {'t': r.data.Point,
               'translate': r.data.Point}.get(absAxis, r.data.Vector)
        inst = cls(vals)

        if '-' in axis:
            inst *= -1.0

        return inst

    #-----------------------------------------------------------|    Axis setting

    def setAxis(self, axis, vals):
        """
        Sets the values for the specified axis row. Used to implement the
        following properties: **x**, **y**, **z** and **translate**/**t**.

        :param str axis: the axis to extract, one of 'x', 'y', 'z', '-x',
            '-y', '-z' or 'translate' / 't'.
        :param vals: the values to assign to the row
        :type vals: :class:`~paya.datatypes.vector.Vector`,
            :class:`~paya.datatypes.point.Point`, list
        """
        fields = fieldsmap[axis]

        for src, dest in zip(vals, fields):
            setattr(self, dest, src)

    #-----------------------------------------------------------|    Properties

    @short(normalize='nr')
    def getX(self, normalize=False):
        """
        Equivalent to ``getAxis('x')``.
        Getter for the **x** property.
        """
        return self.getAxis('x', nr=normalize)

    def setX(self, vals):
        """
        Equivalent to ``setAxis('x')``.
        Setter for the **x** property.
        """
        self.setAxis('x', vals)

    x = property(fget=getX, fset=setX)

    @short(normalize='nr')
    def getY(self, normalize=False):
        """
        Equivalent to ``getAxis('y')``.
        Getter for the **y** property.
        """
        return self.getAxis('y', nr=normalize)

    def setY(self, vals):
        """
        Equivalent to ``setAxis('y')``.
        Setter for the **y** property.
        """
        self.setAxis('y', vals)

    y = property(fget=getY, fset=setY)

    @short(normalize='nr')
    def getZ(self, normalize=False):
        """
        Equivalent to ``getAxis('z')``.
        Getter for the **z** property.
        """
        return self.getAxis('z', nr=normalize)

    def setZ(self, vals):
        """
        Equivalent to ``setAxis('z')``.
        Setter for the **z** property.
        """
        self.setAxis('z', vals)

    z = property(fget=getZ, fset=setZ)

    @short(normalize='nr')
    def getTranslate(self, normalize=False):
        """
        Equivalent to ``getAxis('translate')``.
        Getter for the **translate**/**t** property.
        """
        return self.getAxis('translate', nr=normalize)

    def setTranslate(self, vals):
        """
        Equivalent to ``setAxis('translate')``.
        Setter for the **translate**/**t** property.
        """
        self.setAxis('translate', vals)

    translate = t = property(fget=getTranslate, fset=setTranslate)

    #--------------------------------------------------------------------|    Plug interop

    @property
    def hold(self):
        return self.copy