import pymel.core.datatypes as _dt
from paya.util import short, LazyModule
import paya.lib.mathops as _mo

r = LazyModule('paya.runtime')


class Vector:

    #-----------------------------------------------------------|    Addition

    def __add__(self, other):
        """
        Implements **addition** (``+``).

        Overloads :meth:`pymel.core.datatypes.Vector.__add__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.createNode()

                node.attr('input3D')[0].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[1]:
                        child.put(other, p=isplug)

                else:
                    node.attr('input3D')[1].put(other, p=isplug)

                return node.attr('output3D')

            else:
                return NotImplemented

        return _dt.Vector.__add__(self, other)

    def __radd__(self, other):
        """
        Implements **reflected addition** (``+``).

        Overloads :meth:`pymel.core.datatypes.Vector.__radd__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.createNode()

                node.attr('input3D')[1].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[0]:
                        child.put(other, p=isplug)

                else:
                    node.attr('input3D')[0].put(other, p=isplug)

                return node.attr('output3D')

            else:
                return NotImplemented

        return _dt.Vector.__radd__(self, other)
    
    #-----------------------------------------------------------|    Subtraction
    
    def __sub__(self, other):
        """
        Implements **subtraction** (``-``).

        Overloads :meth:`pymel.core.datatypes.Vector.__sub__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.createNode()
                node.attr('operation').set(2)

                node.attr('input3D')[0].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[1]:
                        child.put(other, p=isplug)

                else:
                    node.attr('input3D')[1].put(other, p=isplug)

                return node.attr('output3D')

            else:
                return NotImplemented

        return _dt.Vector.__sub__(self, other)

    def __rsub__(self, other):
        """
        Implements **reflected subtraction** (``-``).

        Overloads :meth:`pymel.core.datatypes.Vector.__rsub__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.createNode()
                node.attr('operation').set(2)

                node.attr('input3D')[1].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[0]:
                        child.put(other, p=isplug)

                else:
                    node.attr('input3D')[0].put(other, p=isplug)

                return node.attr('output3D')

            else:
                return NotImplemented

        return _dt.Vector.__rsub__(self, other)

    #-----------------------------------------------------------|    Multiplication

    def __mul__(self, other):
        """
        Implements **multiplication** (``*``).

        Overloads :meth:`pymel.core.datatypes.Vector.__mul__` to add
        support for 1D, 3D and 16D (matrix) plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('input1').set(self)

                if dim is 1:
                    for child in node.attr('input2'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input2').put(other, p=isplug)

                return node.attr('output')

            elif dim is 16:
                node = r.nodes.PointMatrixMult.createNode()
                node.attr('vectorMultiply').set(True)
                node.attr('inPoint').set(self)
                node.attr('inMatrix').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.Vector.__mul__(self, other)

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``).

        Overloads :meth:`pymel.core.datatypes.Vector.__rmul__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('input2').set(self)

                if dim is 1:
                    for child in node.attr('input1'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input1').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.Vector.__rmul__(self, other)

    #-----------------------------------------------------------|    Division
    
    def __truediv__(self, other):
        """
        Implements **division** (``/``).

        Overloads :meth:`pymel.core.datatypes.Vector.__truediv__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('operation').set(2)
                node.attr('input1').set(self)

                if dim is 1:
                    for child in node.attr('input2'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input2').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.Vector.__truediv__(self, other)

    def __rtruediv__(self, other):
        """
        Implements **reflected division** (``/``).

        Overloads :meth:`pymel.core.datatypes.Vector.__rtruediv__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('operation').set(2)
                node.attr('input2').set(self)

                if dim is 1:
                    for child in node.attr('input1'):
                        child.put(other, p=isplug)
                else:
                    node.attr('input1').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.Vector.__rtruediv__(self, other)

    #-----------------------------------------------------------|    Point-matrix multiplication

    def __xor__(self, other):
        """
        Uses the exclusive-or operator (``^``) to implement
        **point-matrix multiplication**.

        :param other: a matrix plug or value
        :type other: list, :class:`~paya.datatypes.matrix.Matrix`, :class:`~paya.plugtypes.matrix.Matrix`
        """
        other, dim, isplug = _mo.info(other)

        if dim is 16:
            if isplug:
                node = r.nodes.PointMatrixMult.createNode()
                node.attr('inPoint').set(self)
                node.attr('inMatrix').put(other, p=isplug)
                return node.attr('output')

            else:
                return _dt.Point.__mul__(r.data.Point(self), other)

        return NotImplemented

    #-----------------------------------------------------------|    Power

    def __pow__(self, other):
        """
        Implements **power** (``**``).

        Overloads :meth:`pymel.core.datatypes.Vector.__pow__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('operation').set(3)
                node.attr('input1').set(self)

                if dim is 1:
                    for child in node.attr('input2'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input2').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.Vector.__pow__(self, other)

    def __rpow__(self, other):
        """
        Implements **reflected power** (``**``).

        Overloads :meth:`pymel.core.datatypes.Vector.__rpow__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('operation').set(3)
                node.attr('input2').set(self)

                if dim is 1:
                    for child in node.attr('input1'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input1').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.Vector.__rpow__(self, other)
    
    #--------------------------------------------------------------------|    Blending

    @short(weight='w')
    def blend(self, other, weight=0.5, swap=False):
        """
        Blends this output towards ``other``.

        :param other: the scalar value or plug towards which to blend
        :type other: 3D value or plug
        :param weight/w: the blend weight, where *other* takes over fully
            at 1.0; defaults to 0.5
        :type weight/w: :class:`~paya.plugtypes.attributeMath1D.AttributeMath1D`, :class:`Vector`, list, str
        :param bool swap: swap the operands
        :return: The blended output.
        :rtype: :class:`~paya.plugtypes.attributeMath3D.AttributeMath3D`
        """
        other, dim, isplug = _mo.info(other)
        weight, weightd, weightisplug = _mo.info(weight)

        if isplug or weightisplug:
            node = r.nodes.BlendColors.createNode()
            node.attr('color{}'.format(1 if swap else 2)).set(self)
            node.attr('color{}'.format(2 if swap else 1)).put(other, p=isplug)
            node.attr('blender').put(weight, p=weightisplug)

            return node.attr('output')

        if swap:
            return other.blend(self, weight=weight)

        return _dt.Vector.blend(self, other, weight=weight)
        
    #--------------------------------------------------------------------|    Vector operations

    @short(normalize='nr')
    def dot(self, other, normalize=False):
        """
        Returns the dot product of this vector and 'other'.

        Extends the base PyMEL method in these ways:

        -   Adds the 'normalize' keyword argument
        -   Works with plugs as well as values (if 'other' is a plug,
            the output will also be a plug)

        :param other: the other vector
        :type other: :class:`~paya.plugtypes.attributeMath3D.AttributeMath3D`, :class:`Vector`,
            :class:`Point`, list, str
        :param bool normalize/nr: normalize the output; defaults to False
        :return: The dot product.
        :rtype: :class:`Vector` or :class:`~paya.plugtypes.attributeMath1D.AttributeMath1D`
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            node = r.nodes.VectorProduct.createNode()
            node.attr('input1').set(self)
            node.attr('input2').put(other, p=isplug)

            if normalize:
                node.attr('normalizeOutput').set(True)

            return node.attr('outputX')

        out = _dt.Vector.dot(self, other)

        if normalize:
            out = out.normal()

        return out

    @short(normalize='nr')
    def cross(self, other, normalize=False):
        """
        Returns the cross product of this vector and 'other'.

        Extends the base PyMEL method in these ways:

        -   Adds the 'normalize' keyword argument
        -   Works with plugs as well as values (if 'other' is a plug,
            the output will also be a plug)

        :param other: the other vector
        :type other: :class:`~paya.plugtypes.attributeMath3D.AttributeMath3D`, :class:`Vector`,
            :class:`Point`, list, str
        :param bool normalize/nr: normalize the output; defaults to False
        :return: The cross product.
        :rtype: :class:`Vector` or :class:`~paya.plugtypes.attributeMath3D.AttributeMath3D`
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            node = r.nodes.VectorProduct.createNode()
            node.attr('operation').set(2)
            node.attr('input1').set(self)
            node.attr('input2').put(other, p=isplug)

            if normalize:
                node.attr('normalizeOutput').set(True)

            return node.attr('output')

        out = _dt.Vector.cross(self, other)

        if normalize:
            out = out.normal()

        return out

    def angle(self, other):
        """
        Returns the unsigned, 180-degree-range angle between this vector and
        ``other``.

        Extends the base PyMEL method in these ways:

        -   Works with plugs as well as values (if 'other' is a plug,
            the output will also be a plug)

        :param other: the other vector
        :type other: :class:`~paya.plugtypes.attributeMath3D.AttributeMath3D`, :class:`Vector`,
            :class:`Point`, list, str
        :return: The angle.
        :rtype: :class:`~paya.plugtypes.attributeMath1D.AttributeMath1D` or float
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            node = r.nodes.AngleBetween.createNode()
            node.attr('vector1').set(self)
            node.attr('vector2').put(other, p=isplug)

            return node.attr('angle')

        return _dt.Vector.angle(self, other)

    #--------------------------------------------------------------------|    Conversions

    def asScaleMatrix(self):
        """
        Uses this vectors's three components as the magnitudes of an identity
        matrix's base vectors.

        :return: The scale matrix.
        :rtype: :class:`~paya.datatypes.matrix.Matrix`
        """
        matrix = r.data.Matrix()
        matrix.x = r.data.Vector([1, 0, 0]) * self[0]
        matrix.y = r.data.Vector([0, 1, 0]) * self[1]
        matrix.z = r.data.Vector([0, 0, 1]) * self[2]

        return matrix