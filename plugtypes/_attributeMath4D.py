from paya.util import short
import paya.runtime as r
import paya.lib.mathops as _mo

def conformOutput(x):
    x.__class__ = r.plugtypes.AttributeMath4D
    return x


class AttributeMath4D:

    __math_dimension__ = 4

    #--------------------------------------------------------------------|    Retrieval

    @short(plug='p')
    def get(self, plug=False, **kwargs):
        """
        Casts tuple / list to Quaternion instances.

        :param bool plug/p: return self; defaults to False
        :param \*kwargs: forwarded to :meth:`paya.plugtypes.attribute.Attribute.get`
        :return: bool, :class:`~paya.datatypes.quaternion.Quaternion`
        """
        if plug:
            return self

        result = r.Attribute.get(self, **kwargs)

        if isinstance(result, (list, tuple)):
            result = r.data.Quaternion(result)

        return result

    #--------------------------------------------------------------------|    Add

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).

        :param other: a value or plug of dimension 1 or 4
        """
        other, dim, isplug = _mo.info(other)

        if dim in (1, 4):
            node = r.nodes.QuatAdd.createNode()

            self >> node.attr('input{}Quat'.format(2 if swap else 1))

            if dim is 1:
                for child in node.attr(
                        'input{}Quat'.format(1 if swap else 2)).getChildren():

                    child.put(other, p=isplug)

            else:
                node.attr('input{}Quat'.format(1 if swap else 2)).put(
                    other,
                    p=isplug
                )

            return conformOutput(node.attr('outputQuat'))

        return NotImplemented

    def __radd__(self, other):
        """
        Implements **reflected addition** (``+``). See :meth:`__add__`.
        """
        return self.__add__(other, swap=True)

    #--------------------------------------------------------------------|    Subtract

    def __sub__(self, other, swap=False):
        other, dim, isplug = _mo.info(other)

        if dim in (1, 4):
            node = r.nodes.QuatSub.createNode()

            self >> node.attr('input{}Quat'.format(2 if swap else 1))

            if dim is 1:
                for child in node.attr(
                        'input{}Quat'.format(1 if swap else 2)).getChildren():

                    child.put(other, p=isplug)

            else:
                node.attr('input{}Quat'.format(1 if swap else 2)).put(
                    other,
                    p=isplug
                )

            return conformOutput(node.attr('outputQuat'))

        return NotImplemented

    def __rsub__(self, other):
        return self.__sub__(other, swap=True)

    #--------------------------------------------------------------------|    Multiply

    def __mul__(self, other, swap=False):
        other, dim, isplug = _mo.info(other)

        if dim in (1, 4):
            node = r.nodes.QuatProd.createNode()

            self >> node.attr('input{}Quat'.format(2 if swap else 1))

            if dim is 1:
                for child in node.attr(
                        'input{}Quat'.format(1 if swap else 2)).getChildren():

                    child.put(other, p=isplug)

            else:
                node.attr('input{}Quat'.format(1 if swap else 2)).put(
                    other,
                    p=isplug
                )

            return conformOutput(node.attr('outputQuat'))

        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other, swap=True)

    #--------------------------------------------------------------------|    Signing

    def negate(self):
        """
        Implements unary **negation** (``-``).

        :return: The negation of this quaternion.
        :rtype: :class:`~paya.plugtypes.attributeMath4D.AttributeMath4D`
        """
        node = r.nodes.QuatNegate.createNode()
        self >> node.attr('inputQuat')
        return conformOutput(node.attr('outputQuat'))

    __neg__ = negate

    def inverse(self):
        """
        Implements unary **inversion** (``~``).

        :return: The inverse of this quaternion.
        :rtype: :class:`~paya.plugtypes.attributeMath4D.AttributeMath4D`
        """
        node = r.nodes.QuatInvert.createNode()
        self >> node.attr('inputQuat')
        return conformOutput(node.attr('outputQuat'))

    __invert__ = inverse

    #--------------------------------------------------------------------|    Misc

    def normal(self):
        """
        :return: The normalized quaternion.
        :rtype: :class:`~paya.plugtypes.attributeMath4D.AttributeMath4D`
        """
        node = r.nodes.QuatNormalize.createNode()
        self >> node.attr('inputQuat')
        return conformOutput(node.attr('outputQuat'))

    def conjugate(self):
        """
        :return: The conjugated quaternion.
        :rtype: :class:`~paya.plugtypes.attributeMath4D.AttributeMath4D`
        """
        node = r.nodes.QuatConjugate.createNode()
        self >> node.attr('inputQuat')
        return conformOutput(node.attr('outputQuat'))

    #--------------------------------------------------------------------|    Blend

    @short(weight='w')
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
        :type other: list, :class:`~paya.datatypes.quaternion.Quaternion`, :class:`~paya.plugtypes.attributeMath4D.AttributeMath4D`
        :param weight/w: 'other' will be fully active at 1.0; defaults to 0.5
        :type weight/w: int, float, :class:`~paya.plugtypes.attributeMath1D.AttributeMath1D`
        :param bool swap: reverse operands, defaults to False
        :param angleInterpolation: the type of slerp interpolation to use,
            defaults to 'Shortest'
        :type angleInterpolation: str (an enum name from
            ``QuatSlerp.angleInterpolation``, int, or :class:`~paya.plugtypes.attributeMath1D.AttributeMath1D`
        :return: The blended output.
        :rtype: :class:`~paya.plugtypes.attributeMath4D.AttributeMath4D`
        """
        node = r.nodes.QuatSlerp.createNode(n='blend')
        self >> node.attr('input{}Quat'.format(2 if swap else 1))
        node.attr('input{}Quat'.format(1 if swap else 2)).put(other)

        weight >> node.attr('inputT')
        angleInterpolation >> node.attr('angleInterpolation')

        return conformOutput(node.attr('outputQuat'))

    #--------------------------------------------------------------------|    Conversions

    @short(rotateOrder='ro')
    def asEuler(self,rotateOrder='xyz'):
        """
        Returns this quaternion as an euler compound.

        :param rotateOrder/ro: the rotate order, defaults to 'xyz'
        :type rotateOrder/ro: int, str, :class:`~paya.plugtypes.attributeMath1D.AttributeMath1D`
        :return: The euler rotation.
        :rtype: :class:`AttributeMath3D`
        """
        node = r.nodes.QuatToEuler.createNode()
        self >> node.attr('inputQuat')
        node.attr('inputRotateOrder').put(rotateOrder)
        return node.attr('outputRotate')

    def asAxisAngle(self):
        """
        Returns this quaternion as a tuple of *axis, angle* outputs.

        :return: The axis (vector) and angle outputs.
        :rtype: :class:`tuple`
        """
        node = r.nodes.QuatToAxisAngle.createNode()
        self >> node.attr('inputQuat')
        return node.attr('outputAxis'), node.attr('outputAngle')

    def asMatrix(self):
        """
        Returns this quaternion as a rotation matrix.

        :return: The rotation matrix.
        :rtype: :class:`AttributeMath16D`
        """
        node = r.nodes.ComposeMatrix.createNode()
        self >> node.attr('inputQuat')
        node.attr('useEulerRotation').set(False)

        return node.attr('outputMatrix')