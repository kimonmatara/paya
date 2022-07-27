import pymel.core.datatypes as _dt
import pymel.util as _pu
from paya.util import short, LazyModule
import paya.lib.mathops as _mo

r = LazyModule('paya.runtime')


class Vector:

    #-----------------------------------------------------------|    Testing

    @short(name='n')
    def createLocator(self, name=None):
        """
        :shorthand: ``cl``

        :param name/n: one or more optional name elements; defaults to None
        :rtype name/n: None, list, int, str
        :return: A locator with this vector / point piped into its
            ``translate`` channel.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        loc = r.nodes.Locator.createNode(n=name).getParent()
        loc.attr('t').set(self)
        return loc

    cl = createLocator

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
        :type other: list, :class:`~paya.runtime.data.Matrix`, :class:`~paya.runtime.plugs.Matrix`
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

    @short(
        weight='w',
        swap='sw',
        includeLength='ilg',
        byVectorAngle='bva'
    )
    def blend(
            self,
            other,
            weight=0.5,
            swap=False,
            includeLength=False,
            byVectorAngle=False
    ):
        """
        If 'other' or 'weight' is a plug, then the return will also be a
        plug.

        :param other: the vector that will be fully active when 'weight'
            is 1.0 (or 0.0, if 'swap' is True)
        :type other: list, tuple, :class:`paya.runtime.data.Vector`,
            :class:`paya.runtime.plugs.Vector`
        :param weight/w: the blending weight; defaults to 0.5
        :type weight/w: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool swap/sw: swap operands around; defaults to False
        :param bool byVectorAngle/bva: blend by rotating one vector towards
            the other, rather than via linear value interpolation; defaults
            to False
        :param bool includeLength/ilg: ignored if 'byVectorAngle' is False;
            blend vector lengths (magnitudes) as well; defaults to False
        :return: The blended vector.
        :rtype: :class:`paya.runtime.data.Vector` or
            :class:`paya.runtime.plugs.Vector`
        """
        other, otherDim, otherIsPlug = _mo.info(other)
        weight, weightDim, weightIsPlug = _mo.info(weight)

        if swap:
            first, second = other, self
            firstIsPlug = otherIsPlug
            secondIsPlug = False

        else:
            first, second = self, other
            firstIsPlug = False
            secondIsPlug = otherIsPlug

        if byVectorAngle:
            cross = first.cross(second)
            baseAngle = first.angle(second)
            targetAngle = baseAngle * weight
            outVector = first.rotateByAxisAngle(cross, targetAngle)

            if includeLength:
                firstLength = first.length()
                secondLength = second.length()

                if firstIsPlug:
                    targetLength = firstLength.blend(secondLength, w=weight)

                elif secondIsPlug:
                    targetLength = secondLength.blend(
                        firstLength, w=weight, swap=True)

                else:
                    targetLength = _pu.blend(
                        firstLength, secondLength, weight=weight
                    )

                outVector = outVector.normal() * targetLength

        else:
            if any([firstIsPlug, secondIsPlug, weightIsPlug]):
                node = r.nodes.BlendColors.createNode()
                node.attr('color2').put(first, p=firstIsPlug)
                node.attr('color1').put(second, p=secondIsPlug)
                node.attr('blender').put(weight, weightIsPlug)

                outVector = node.attr('output')

            else:
                outVector = _pu.blend(first, second, weight=weight)

        return outVector
        
    #--------------------------------------------------------------------|    Vector operations

    def rotateByAxisAngle(self, axisVector, angle):
        """
        :param axisVector: the vector around which to rotate this vector
        :type axisVector: list, tuple, :class:`~paya.runtime.data.Vector`
            or :class:`~paya.runtime.plugs.Vector`
        :param angle: the angle of rotation
        :type angle: float, :class:`~paya.runtime.data.Angle`, str or
            class:`~paya.runtime.plugs.Math3D`
        :return: This vector, rotated around ``axisVector`` by the specified
            ``angle``.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        axisVector, axisVectorDim, axisVectorIsPlug = _mo.info(axisVector)
        angle, angleDim, angleIsPlug = _mo.info(angle)

        hasPlugs = axisVectorIsPlug or angleIsPlug

        if hasPlugs:
            axisAngle = r.nodes.AxisAngleToQuat.createNode()
            axisVector >> axisAngle.attr('inputAxis')
            angle >> axisAngle.attr('inputAngle')
            quat = axisAngle.attr('outputQuat')
            matrix = quat.asRotateMatrix()

            return self * matrix

        else:
            return self.rotateBy(axisVector, angle)

    @short(normalize='nr')
    def dot(self, other, normalize=False):
        """
        Returns the dot product of this vector and 'other'.

        Extends the base PyMEL method in these ways:

        -   Adds the 'normalize' keyword argument
        -   Works with plugs as well as values (if 'other' is a plug,
            the output will also be a plug)

        :param other: the other vector
        :type other: :class:`~paya.runtime.plugs.Math3D`, :class:`Vector`,
            :class:`Point`, list, str
        :param bool normalize/nr: normalize the output; defaults to False
        :return: The dot product.
        :rtype: :class:`Vector` or :class:`~paya.runtime.plugs.Math1D`
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            node = r.nodes.VectorProduct.createNode()
            node.attr('input1').set(self)
            node.attr('input2').put(other, p=isplug)

            if normalize:
                node.attr('normalizeOutput').set(True)

            return node.attr('outputX')

        if normalize:
            out = _dt.Vector.dot(self.normal(), other.normal())

        else:
            out = _dt.Vector.dot(self, other)

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
        :type other: :class:`~paya.runtime.plugs.Math3D`, :class:`Vector`,
            :class:`Point`, list, str
        :param bool normalize/nr: normalize the output; defaults to False
        :return: The cross product.
        :rtype: :class:`Vector` or :class:`~paya.runtime.plugs.Math3D`
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

    @short(clockNormal='cn')
    def angle(self, other, clockNormal=None):
        """
        :param other: the other vector
        :type other: :class:`~paya.runtime.plugs.Math3D`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`, list, str
        :param clockNormal/cn: provide this to get a 360 angle; defaults to
            None
        :type clockNormal/cn: None, list, tuple,
            :class:`~paya.runtime.plugs.Vector`,
            :class:`~paya.runtime.data.Vector`
        :return: The angle from this vector to ``other``.
        :rtype: :class:`~paya.runtime.plugs.Angle` or
            :class:`~paya.runtime.data.Angle`
        """
        other, otherDim, otherIsPlug  = _mo.info(other)

        if clockNormal is None:
            complete = False
            hasPlugs = otherIsPlug

        else:
            complete = True
            clockNormal, cnDim, cnIsPlug = _mo.info(clockNormal)
            hasPlugs = cnIsPlug or otherIsPlug

        if complete:
            cross = self.cross(clockNormal)

        if hasPlugs:
            ab = r.createNode('angleBetween')
            ab.attr('vector1').set(self)
            ab.attr('vector2').put(other, p=otherIsPlug)

            angle = ab.attr('angle')

            if complete:
                dot = cross.dot(other, normalize=True)
                angle = dot.gt(0.0).ifElse(_pu.radians(360.0)-angle, angle)

        else:
            angle = _dt.Vector.angle(self, other)

            if complete:
                dot = self.dot(other, normalize=True)

                if dot > 0.0:
                    angle = _pu.radians(360.0)-angle

        return angle

    def projectOnto(self, other):
        """
        See https://en.wikipedia.org/wiki/Vector_projection.

        :param other: the vector onto which to project this one
        :type other: list, tuple, str, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The project of this vector onto *other*.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        other = _mo.info(other)[0]
        return (self.dot(other) / other.dot(other)) * other

    def rejectFrom(self, other):
        """
        Same as 'make perpendicular to' (although length will change).
        See https://en.wikipedia.org/wiki/Vector_projection.

        :param other: the vector from which to reject this one
        :type other: list, tuple, str, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The rejection of this vector from *other*.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        other = _mo.info(other)[0]
        cosTheta = self.dot(other, nr=True)
        rejection = self - (self.length() * cosTheta) * other.normal()
        return rejection

    #--------------------------------------------------------------------|    Conversions

    def asTranslateMatrix(self):
        """
        :return: An identity matrix with this vector / point as the translate
            component.
        :rtype: :class:`~paya.runtime.data.Matrix`
        """
        out = r.data.Matrix()
        out.t = self
        return out

    def asScaleMatrix(self):
        """
        Uses this vectors's three components as the magnitudes of an identity
        matrix's base vectors.

        :return: The scale matrix.
        :rtype: :class:`~paya.runtime.data.Matrix`
        """
        matrix = r.data.Matrix()
        matrix.x = r.data.Vector([1, 0, 0]) * self[0]
        matrix.y = r.data.Vector([0, 1, 0]) * self[1]
        matrix.z = r.data.Vector([0, 0, 1]) * self[2]

        return matrix

    def asShearMatrix(self):
        """
        Composes this output's three components into a shear matrix.

        :return: The shear matrix.
        :rtype: :class:`~paya.runtime.data.Matrix`
        """
        this = r.data.TransformationMatrix(self)
        out = r.data.TransformationMatrix()
        shear = this.getShear('transform')
        out.setShear(shear, 'transform')
        return r.data.Matrix(out)
