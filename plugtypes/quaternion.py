import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r


class Quaternion:

    #-----------------------------------------------------------|    Value getting

    @short(plug='p')
    def get(self, plug=False, default=None, **kwargs):
        """
        Overloads :py:meth:`paya.runtime.plugs.Attribute.get` to return
        :class:`~paya.runtime.data.Quaternion` instances instead of
        tuples.
        """
        if plug:
            return self

        result = r.plugs.Attribute.get(
            self, plug=False, default=default, **kwargs)

        if isinstance(result, tuple):
            return r.data.Quaternion(result)

        return result

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).

        :param other: a value or plug of dimension 1 or 4
        """
        other, dim, ut, isplug = _mo.info(other).values()

        if dim in (1, 4):
            node = r.nodes.QuatAdd.createNode()

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
        other, dim, ut, isplug = _mo.info(other).values()

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
        other, dim, ut, isplug = _mo.info(other).values()

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

    #-----------------------------------------------------------|    Inversion

    def inverse(self):
        """
        :return: The inverse of this quaternion.
        :rtype: :class:`Quaternion`
        """
        node = r.nodes.QuatInvert.createNode()
        self >> node.attr('inputQuat')
        return node.attr('outputQuat')

    #--------------------------------------------------------------------|    Misc

    def normal(self):
        """
        :return: The normalized quaternion.
        :rtype: :class:`Quaternion`
        """
        node = r.nodes.QuatNormalize.createNode()
        self >> node.attr('inputQuat')
        return node.attr('outputQuat')

    def conjugate(self):
        """
        :return: The conjugated quaternion.
        :rtype: :class:`Quaternion`
        """
        node = r.nodes.QuatConjugate.createNode()
        self >> node.attr('inputQuat')
        return node.attr('outputQuat')

    #--------------------------------------------------------------------|    Blend

    @short(
        weight='w',
        angleInterpolation='ai'
    )
    def blend(
            self,
            other,
            weight=0.5,
            swap=False,
            angleInterpolation='Shortest'
    ):
        """
        Blends this quaternion towards ``other``.

        :param other: the quaternion value or plug towards which to blend
        :type other: list, :class:`Quaternion`, :class:`Quaternion`
        :param weight/w: 'other' will be fully active at 1.0; defaults to 0.5
        :type weight/w: int, float, :class:`Math1D`
        :param bool swap: reverse operands, defaults to False
        :param angleInterpolation: the type of slerp interpolation to use,
            defaults to 'Shortest'
        :type angleInterpolation: str (an enum name from
            ``QuatSlerp.angleInterpolation``, int, or :class:`Math1D`
        :return: The blended output.
        :rtype: :class:`Quaternion`
        """
        node = r.nodes.QuatSlerp.createNode(n='blend')
        self >> node.attr('input{}Quat'.format(2 if swap else 1))
        node.attr('input{}Quat'.format(1 if swap else 2)).put(other)

        weight >> node.attr('inputT')
        angleInterpolation >> node.attr('angleInterpolation')

        return node.attr('outputQuat')

    #-----------------------------------------------------------|    Conversions

    @short(rotateOrder='ro')
    def asEulerRotation(self, rotateOrder='xyz'):
        """
        Returns this quaternion as an euler compound.

        :param rotateOrder/ro: the rotate order, defaults to 'xyz'
        :type rotateOrder/ro: int, str, :class:`Math1D`
        :return: The euler rotation.
        :rtype: :class:`Math3D`
        """
        node = r.nodes.QuatToEuler.createNode()
        self >> node.attr('inputQuat')
        node.attr('inputRotateOrder').put(rotateOrder)
        return node.attr('outputRotate')

    def asAxisAngle(self):
        """
        Returns this quaternion as a tuple of axis, angle outputs.

        :return: The axis (vector) and angle outputs.
        :rtype: :class:`tuple`
        """
        node = r.nodes.QuatToAxisAngle.createNode()
        self >> node.attr('inputQuat')
        return node.attr('outputAxis'), node.attr('outputAngle')

    def asRotateMatrix(self):
        """
        Returns this quaternion as a rotation matrix.

        :return: The rotation matrix.
        :rtype: :class:`~paya.attributeMath16D.AttributeMath16D`
        """
        node = r.nodes.ComposeMatrix.createNode()
        self >> node.attr('inputQuat')
        node.attr('useEulerRotation').set(False)

        return node.attr('outputMatrix')