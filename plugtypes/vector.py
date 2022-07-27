import pymel.util as _pu
import pymel.core.nodetypes as _nt
import pymel.core.datatypes as _dt
from paya.util import short
import paya.lib.mathops as _mo
import paya.runtime as r


class Vector:

    #-----------------------------------------------------------|    Getter

    def isTranslateChannel(self):
        """
        :return: True if this is the ``translate`` channel of a transform
            node, otherwise False.
        :rtype: bool
        """
        return self.attrName(longName=True
            ) == 'translate' and isinstance(self.node(), _nt.Transform)

    @short(plug='p')
    def get(self, plug=False, **kwargs):
        """
        Overrides :meth:`~paya.runtime.plugs.Attribute.get` to return
        :class:`~paya.runtime.data.Point` values if this is the translate
        channel of a transform node.
        """
        if plug:
            return self

        result = r.plugs.Attribute.get(self, **kwargs)

        if isinstance(result, _dt.Vector):
            if self.isTranslateChannel():
                return r.data.Point(result)

        return result

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

        elif dim is 16 and not swap:
            node = r.nodes.PointMatrixMult.createNode()
            node.attr('vectorMultiply').set(True)
            self >> node.attr('inPoint')
            other >> node.attr('inMatrix')
            return node.attr('output')

        return NotImplemented

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``).
        """
        return self.__mul__(other, swap=True)

    #-----------------------------------------------------------|    Point-Matrix Multiply

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

    #-----------------------------------------------------------|    Vector operations

    @short(
        weight='w',
        blendLength='blg'
    )
    def _blendByVectorAngle(
            self,
            other,
            weight=0.5,
            swap=False,
            blendLength=False
    ):
        other, dim, isplug = _mo.info(other)

        if swap:
            first, second = other, self

        else:
            first, second = self, other

        cross = first.cross(second)
        angle = first.angle(second)
        targetAngle = angle * weight

        out = self.rotateByAxisAngle(cross, targetAngle)

        if blendLength:
            mag = first.length().blend(other.length(), weight=weight)
            out = out.normal() * mag

        return out

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
        :rtype: :class:`paya.runtime.plugs.Vector`
        """
        other, otherDim, otherIsPlug = _mo.info(other)

        if swap:
            first, second = other, self
            firstIsPlug = otherIsPlug
            secondIsPlug = True

        else:
            first, second = self, other
            firstIsPlug = True
            secondIsPlug = otherIsPlug

        if byVectorAngle:
            cross = first.cross(second)
            baseAngle = first.angle(second)
            targetAngle = baseAngle * weight
            outVector = first.rotateByAxisAngle(cross, targetAngle)

            if includeLength:
                targetLength = first.length().blend(second.length(), w=weight)
                outVector = outVector.normal() * targetLength

        else:
            node = r.nodes.BlendColors.createNode()
            node.attr('color2').put(first, p=firstIsPlug)
            node.attr('color1').put(second, p=secondIsPlug)
            weight >> node.attr('blender')

            outVector = node.attr('output')

        return outVector

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
        axisAngle = r.nodes.AxisAngleToQuat.createNode()
        axisVector >> axisAngle.attr('inputAxis')
        angle >> axisAngle.attr('inputAngle')
        quat = axisAngle.attr('outputQuat')
        matrix = quat.asRotateMatrix()

        return self * matrix

    @short(normalize='nr')
    def dot(self, other, normalize=False):
        """
        Returns the dot product of ``self`` and ``other``.

        :param other: the other vector
        :type other: :class:`list`, :class:`tuple`, :class:`~paya.runtime.plugs.Math3D`
        :param bool normalize/nr: normalize the output; defaults to False
        :return: :class:`paya.runtime.plugs.Math1D`
        """
        node = r.nodes.VectorProduct.createNode()
        self >> node.attr('input1')
        other >> node.attr('input2')
        node.attr('normalizeOutput').set(normalize)

        return node.attr('outputX')

    def length(self):
        """
        Returns the length of this vector.

        :return: The length of this vector.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        node = r.nodes.DistanceBetween.createNode(n='mag')
        self >> node.attr('point2')
        return node.attr('distance')

    def normal(self):
        """
        :return: This vector, normalized.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        with r.Name('normal'):
            return self / self.length()

    @short(normalize='nr')
    def cross(self, other, normalize=False):
        """
        Returns the cross product of ``self`` and ``other``.

        :param other: the other vector
        :type other: :class:`list`, :class:`tuple`, :class:`~paya.runtime.plugs.Math3D`
        :param bool normalize/nr: normalize the output; defaults to False
        :return: :class:`paya.runtime.plugs.Vector`
        """
        node = r.nodes.VectorProduct.createNode()
        node.attr('operation').set(2)
        self >> node.attr('input1')
        other >> node.attr('input2')

        if normalize:
            node.attr('normalizeOutput').set(True)

        return node.attr('output')

    def angle(self, other, euler=False, axisAngle=False):
        """
        Returns the unsigned, 180-degree-range angle between this vector and
        ``other``.

        :param other: the other vector
        :type other: :class:`~paya.runtime.plugs.Math3D`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`, list, str
        :param bool euler: return an euler angle
            triple compound, defaults to False
        :param bool axisAngle: return an axis, angle tuple;
            defaults to False
        :return: A single angle output, a triple euler compound,
            or a tuple of *(axis vector, angle)*, depending on flags
        :rtype: :class:`~paya.runtime.plugs.Vector` or :class:`tuple`
        """
        node = r.nodes.AngleBetween.createNode()
        self >> node.attr('vector1')
        node.attr('vector2').put(other)

        if euler:
            return node.attr('euler')

        if axisAngle:
            return node.attr('axis'), node.attr('angle')

        return node.attr('angle')

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
        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        if clockNormal is None:
            complete = False

        else:
            complete = True
            clockNormal, cnDim, cnIsPlug = _mo.info(clockNormal)
            cross = self.cross(clockNormal)

        ab = r.createNode('angleBetween')
        self >> ab.attr('vector1')
        other >> ab.attr('vector2')

        angle = ab.attr('angle')

        if complete:
            dot = cross.dot(other, normalize=True)
            angle = dot.gt(0.0).ifElse(_pu.radians(360.0)-angle, angle)

        return angle

    def projectOnto(self, other):
        """
        See https://en.wikipedia.org/wiki/Vector_projection.

        :param other: the vector onto which to project this one
        :type other: list, tuple, str, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The project of this vector onto *other*.
        :rtype: :class:`~paya.runtime.plugs.Vector`
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
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        other = _mo.info(other)[0]
        cosTheta = self.dot(other, nr=True)
        rejection = self - (self.length() * cosTheta) * other.normal()
        return rejection

    #-----------------------------------------------------------|    Conversions

    def asTranslateMatrix(self):
        """
        Inserts this into the translate row of an identity matrix, and
        returns the matrix.

        :return: The translate matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        ffm = r.nodes.FourByFourMatrix.createNode()
        fields = ['in30', 'in31', 'in32']
        children = self.getChildren()

        for src, field in zip(self.getChildren(), fields):
            src >> ffm.attr(field)

        return ffm.attr('output')

    def asScaleMatrix(self):
        """
        Uses this output's three components as the magnitudes of
        an identity matrix's base vectors.

        :return: The scale matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        ffm = r.nodes.FourByFourMatrix.createNode()

        for src, field in zip(
            self.getChildren(),
            ['in00','in11','in22']
        ):
            src >> ffm.attr(field)

        return ffm.attr('output')

    def asShearMatrix(self):
        """
        Composes this output's three components into a shear matrix.

        :return: The shear matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        cm = r.nodes.ComposeMatrix.createNode()
        self >> cm.attr('inputShear')
        return cm.attr('outputMatrix')

    def asEulerRotation(self):
        """
        Returns XYZ euler rotations for this vector.

        :return: A compound of three euler channels.
        :rtype: :class:`~paya.runtime.plugs.EulerRotation`
        """
        node = r.nodes.AngleBetween.createNode()
        self >> node.attr('vector2')

        return node.attr('euler')