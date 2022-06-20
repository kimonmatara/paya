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
        Overrides :meth:`~paya.plugtypes.attribute.Attribute.get` to return
        :class:`~paya.datatypes.point.Point` values if this is the translate
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

    def rotateByAxisAngle(self, axisVector, angle):
        """
        :param axisVector: the vector around which to rotate this vector
        :type axisVector: list, tuple, :class:`~paya.datatypes.vector.Vector`
            or :class:`~paya.plugtypes.vector.Vector`
        :param angle: the angle of rotation
        :type angle: float, :class:`~paya.datatypes.angle.Angle`, str or
            class:`~paya.plugtypes.math3D.Math3D`
        :return: This vector, rotated around ``axisVector`` by the specified
            ``angle``.
        :rtype: :class:`~paya.plugtypes.vector.Vector`
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
        :type other: :class:`list`, :class:`tuple`, :class:`~paya.plugtypes.math3D.Math3D`
        :param bool normalize/nr: normalize the output; defaults to False
        :return: :class:`paya.plugtypes.math1D.Math1D`
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
        :rtype: :class:`~paya.plugtypes.math1D.Math1D`
        """
        node = r.nodes.DistanceBetween.createNode(n='mag')
        self >> node.attr('point2')
        return node.attr('distance')

    def normal(self):
        """
        :return: This vector, normalized.
        :rtype: :class:`~paya.plugtypes.vector.Vector`
        """
        with r.Name('normal'):
            return self / self.length()

    @short(normalize='nr')
    def cross(self, other, normalize=False):
        """
        Returns the cross product of ``self`` and ``other``.

        :param other: the other vector
        :type other: :class:`list`, :class:`tuple`, :class:`~paya.plugtypes.math3D.Math3D`
        :param bool normalize/nr: normalize the output; defaults to False
        :return: :class:`paya.plugtypes.vector.Vector`
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
        :type other: :class:`~paya.plugtypes.math3D.Math3D`,
            :class:`~paya.datatypes.vector.Vector`,
            :class:`~paya.datatypes.point.Point`, list, str
        :param bool euler: return an euler angle
            triple compound, defaults to False
        :param bool axisAngle: return an axis, angle tuple;
            defaults to False
        :return: A single angle output, a triple euler compound,
            or a tuple of *(axis vector, angle)*, depending on flags
        :rtype: :class:`~paya.plugtypes.vector.Vector` or :class:`tuple`
        """
        node = r.nodes.AngleBetween.createNode()
        self >> node.attr('vector1')
        node.attr('vector2').put(other)

        if euler:
            return node.attr('euler')

        if axisAngle:
            return node.attr('axis'), node.attr('angle')

        return node.attr('angle')

    #-----------------------------------------------------------|    Conversions

    def asTranslateMatrix(self):
        """
        Inserts this into the translate row of an identity matrix, and
        returns the matrix.

        :return: The translate matrix.
        :rtype: :class:`~paya.plugtypes.matrix.Matrix`
        """
        ffm = r.nodes.FourByFourMatrix.createNode()

        fields = ['in30','in31','in32']

        for src, field in zip(self.getChildren(), fields):
            src >> ffm.attr(field)

        return ffm.attr('output')

    def asScaleMatrix(self):
        """
        Uses this output's three components as the magnitudes of
        an identity matrix's base vectors.

        :return: The scale matrix.
        :rtype: :class:`~paya.plugtypes.matrix.Matrix`
        """
        ffm = r.nodes.FourByFourMatrix.createNode()

        for src, field in zip(
            self.getChildren(),
            ['in00','in11','in22']
        ):
            src >> ffm.attr(field)

        return ffm.attr('output')

    def asEulerRotation(self):
        """
        Returns XYZ euler rotations for this vector.

        :return: A compound of three euler channels.
        :rtype: :class:`~paya.plugtypes.eulerRotation.EulerRotation`
        """
        node = r.nodes.AngleBetween.createNode()
        self >> node.attr('vector2')

        return node.attr('euler')