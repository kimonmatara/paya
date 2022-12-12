from functools import reduce
import math

import maya.OpenMaya as om
import pymel.util as _pu
from paya.util import short
import paya.lib.mathops as _mo
import paya.runtime as r

if not r.pluginInfo('quatNodes', q=True, loaded=True):
    r.loadPlugin('quatNodes')


class Math1D:

    __create_attr_type__ = 'double'

    @classmethod
    @short(attributeType='at')
    def createAttr(cls,
               attrName,
               node=None,
               attributeType=None,
               **kwargs):
        """
        On :class:`Math1D` subclasses, overloads
        :meth:`paya.runtime.plugs.Attribute.create` to preload
        *attributeType* with a type appropriate for the class.

        :param str attrName: the name of the attribute
        :param node: the node on which to create the attribute; if omitted,
            a free-standing ``network`` node will be created to hold the
            attribute; defaults to ``double`` for :class:`Math1D`,
            ``doubleAngle`` for :class:`~paya.runtime.plugs.Angle`,
            ``doubleLinear`` for :class:`~paya.runtime.plugs.Distance` and
            ``time`` for :class:`~paya.runtime.plugs.Time`
        :param str attributeType/at: the type of the attribute to create;
            defaults to something sensible for this 1D class
        :type node: :class:`str`, :class:`~paya.runtime.nodes.DependNode`
        :param \*\*kwargs: forwarded to
            :meth:`~paya.runtime.nodes.DependNode.addAttr`
        :return: The generated attribute.
        :rtype: `Attribute`
        """
        if attributeType is None:
            attributeType = cls.__create_attr_type__

        return super(r.plugs.Math1D, cls).createAttr(attrName,
                                                     node=node,
                                                     at=attributeType,
                                                     **kwargs)

    #-----------------------------------------------------------|    Unit management

    def convertUnit(self, *factor):
        """
        Connects and configures a ``unitConversion`` node and returns its
        output.

        :param \*factor: the conversion factor; if omitted, defaults to 1.0
        :return: The output of the ``unitConversion`` node.
        :rtype: :class:`~paya.runtime.plugs.Attribute`
        """
        node = r.nodes.UnitConversion.createNode()
        self >> node.attr('input')

        if factor:
            factor[0] >> node.attr('conversionFactor')

        return node.attr('output')

    def asAngle(self):
        """
        If this attribute is of type 'doubleAngle', it is returned as-is.
        If it's of any other type, it's converted using Maya UI rules and
        a 'doubleAngle' output for it returned.

        :return: The angle output.
        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        unitType = self.unitType()

        if unitType == 'angle':
            return self

        with r.Name('asAngle'):
            nw = r.nodes.Network.createNode()

        nw.addAttr('output', at='doubleAngle', k=True)
        self >> nw.attr('output')
        return nw.attr('output')

    def asRadians(self):
        """
        :return: A unitless (type 'double') output representing radians.
            Conversions are performed according to Maya rules.
        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        inp = self
        unitType = self.unitType()

        if unitType is None:
            # Make sure it's double and not generic
            if inp.type() != 'double':
                with r.Name('asDouble'):
                    nw = r.nodes.Network.createNode()

                nw.addAttr('output', at='double', k=True)
                inp >> nw.attr('output')
                inp = nw.attr('output')

            if om.MAngle.uiUnit() == om.MAngle.kRadians:
                # No conversions necessary
                return inp

            # Run through a unit conversion just for the multiplication
            # functionality; return a double output

            uc = r.nodes.UnitConversion.createNode()
            inp >> uc.attr('input')
            uc.attr('conversionFactor').set(math.pi / 180.0)
            uc.addAttr('asDouble', k=True, at='double')
            uc.attr('output') >> uc.attr('asDouble')

            return uc.attr('asDouble')

        if unitType == 'angle':
            with r.Name('asRadians'):
                nw = r.nodes.Network.createNode()

            nw.addAttr('output', k=True, at='double')

            with r.NativeUnits():
                inp >> nw.attr('output')

            return nw.attr('output')

        # In all other cases, pipe into an angle attribute to get Maya
        # to perform unit conversions on its own, then connect into
        # a double output with native units to get the radians

        with r.Name('asRadians'):
            nw = r.nodes.Network.createNode()

        nw.addAttr('asAngle', at='doubleAngle', k=True)
        inp >> nw.attr('asAngle')
        nw.addAttr('output', at='double', k=True)

        with r.NativeUnits():
            nw.attr('asAngle') >> nw.attr('output')

        return nw.attr('output')

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).

        :param other: a value or plug of dimension 1, 2, 3 or 4
        """
        other, dim, unitType, isplug = _mo.info(other).values()

        if dim is 1:
            node = r.nodes.PlusMinusAverage.createNode()
            self >> node.attr('input1D')[1 if swap else 0]
            node.attr('input1D')[0 if swap else 1].put(other, p=isplug)
            return node.attr('output1D')

        if dim is 2:
            node = r.nodes.PlusMinusAverage.createNode()

            for child in node.attr('input2D')[1 if swap else 0]:
                self >> child

            node.attr('input2D')[0 if swap else 1].put(other, p=isplug)

            return node.attr('output2D')

        if dim is 3:
            node = r.nodes.PlusMinusAverage.createNode()

            for child in node.attr('input3D')[1 if swap else 0]:
                self >> child

            node.attr('input3D')[0 if swap else 1].put(other, p=isplug)

            return node.attr('output3D')

        if dim is 4:
            node = r.nodes.QuatAdd.createNode()

            for child in node.attr('input{}Quat'.format(2 if swap else 1)):
                self >> child

            for source, dest in zip(
                    other,
                    node.attr('input{}Quat'.format(1 if swap else 2))
            ):
                dest.put(source, p=plug)

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

        :param other: a value or plug of dimension 1, 2, 3
        """
        other, dim, ut, isplug = _mo.info(other).values()

        if dim in (1, 2, 3):
            node = r.nodes.PlusMinusAverage.createNode()
            node.attr('operation').set(2)

            if dim is 1:
                self >> node.attr('input1D')[1 if swap else 0]
                node.attr('input1D')[0 if swap else 1].put(other, p=isplug)

                return node.attr('output1D')

            else:
                for child in node.attr('input{}D'.format(dim))[1 if swap else 0]:
                    self >> child

                for src, dest in zip(
                        other,
                        node.attr('input{}D'.format(dim))[0 if swap else 1]
                ):
                    dest.put(src, p=isplug)

                return node.attr('output{}D'.format(dim))

        return NotImplemented

    def __rsub__(self, other):
        """
        Implements **reflected subtraction** (``-``). See :meth:`__sub__`.
        """
        return self.__sub__(other, swap=True)

    #-----------------------------------------------------------|    Multiply

    def __mul__(self, other, swap=False):
        """
        Implements **multiplication** (``-``).

        :param other: a value or plug of dimension 1 or 3
        """
        other, dim, ut, isplug = _mo.info(other).values()

        if dim is 1:
            node = r.nodes.MultiplyDivide.createNode()
            self >> node.attr('input{}X'.format(2 if swap else 1))
            other >> node.attr('input{}X'.format(1 if swap else 2))

            return node.attr('outputX')

        if dim is 3:
            node = r.nodes.MultiplyDivide.createNode()

            for dest in node.attr('input{}'.format(2 if swap else 1)):
                self >> dest

            for src, dest in zip(other, node.attr(
                    'input{}'.format(1 if swap else 2))):
                dest.put(src, p=isplug)

            return node.attr('output')

        return NotImplemented

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``-``). See :meth:`__mul__`.
        """
        return self.__mul__(other, swap=True)

    #-----------------------------------------------------------|    Divide

    def __truediv__(self, other, swap=False):
        """
        Implements **division** (``/``).

        :param other: a value or plug of dimension 1 or 3
        """
        other, dim, ut, isplug = _mo.info(other).values()

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(2)

            if dim is 1:
                self >> node.attr('input{}X'.format(2 if swap else 1))
                node.attr('input{}X'.format(1 if swap else 2)).put(other, p=isplug)

                return node.attr('outputX')

            else:
                for dest in node.attr('input{}'.format(2 if swap else 1)):
                    self >> dest

                for source, dest in zip(
                        other,
                        node.attr('input{}'.format(1 if swap else 2))
                ):
                    dest.put(source, p=isplug)

                return node.attr('output')

        return NotImplemented

    def __rtruediv__(self, other):
        """
        Implements **reflected division** (``/``). See :meth:`__truediv__`.
        """
        return self.__truediv__(other, swap=True)

    #-----------------------------------------------------------|    Power

    def __pow__(self, other, modulo=None, swap=False):
        """
        Implements **power** (``**``). The *modulo* keyword argument is
        ignored.

        :param other: a value or plug of dimension 1 or 3
        """
        other, dim, ut, isplug = _mo.info(other).values()

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(3)

            if dim is 1:
                self >> node.attr('input{}X'.format(2 if swap else 1))
                node.attr('input{}X'.format(1 if swap else 2)).put(other, p=isplug)

                return node.attr('outputX')

            else:
                for dest in node.attr('input{}'.format(2 if swap else 1)):
                    self >> dest

                for source, dest in zip(
                        other,
                        node.attr('input{}'.format(1 if swap else 2))
                ):
                    dest.put(source, p=isplug)

                return node.attr('output')

        return NotImplemented

    def __rpow__(self, other):
        """
        Implements **reflected power** (``**``). See :meth:`__pow__`.
        """
        return self.__pow__(other, swap=True)

    def sqrt(self):
        """
        :return: The square root of ``self``, equivalent to ``self ** 0.5``.
        :rtype: :class:``Math1D``
        """
        return self ** 0.5

    #-----------------------------------------------------------|    Unary

    def __neg__(self):
        """
        Implements unary negation (``-``).
        :return: ``self * -1.0``
        """
        mdv = r.nodes.MultiplyDivide.createNode()
        self >> mdv.attr('input1X')
        mdv.attr('input2X').set(-1.0)
        return mdv.attr('outputX')

    def normal(self, scalar=True):
        """
        :param bool scalar/s: if this is ``True``, normalization will
            be performed as ``self / self.get()``; if it's ``False``,
            ``self - self.get()`` will be performed instead; defaults
            to True
        :return: A normalized output for this plug. Normalization will be
            skipped, and ``self`` will be returned, if the currrent value
            of this plug is already 1.0 (for *scalar*) or 0.0.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        _self = self.get()

        if scalar:
            if _self == 1.0:
                out = self
            else:
                out = self / _self
        else:
            if _self == 0.0:
                out = self
            else:
                out = self - _self

        return out

    #-----------------------------------------------------------------|    Sign

    def setSign(self, positive):
        """
        :param bool positive: set the sign to positive
        :return: This scalar, with the sign forced to positive if *positive* is
            ``True``, otherwise to negative
        """
        thisAbs = self.abs()

        if positive:
            return thisAbs

        return -thisAbs

    def copySignFrom(self, other):
        """
        Copies the sign from another scalar.

        :param other: the scalar from which to copy the sign
        :type other: float, int, :class:`~paya.runtime.plugs.Math1D`
        :return: This scalar, with sign copied from *other*.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        other, otherDim, otherUnitType, otherIsPlug = \
            _mo.info(other).values()

        thisAbs = self.abs()

        if otherIsPlug:
            out = other.lt(0.0).ifElse(
                -thisAbs,
                thisAbs
            )

            out.__class__ = type(self)

        else:
            if other < 0:
                return thisAbs

            return -thisAbs

    def abs(self):
        """
        :return: ``self``, unsigned.
        :rtype: :class:`Math1D`
        """
        return self.ge(0).ifElse(self,-self).setClass(type(self))

    #-----------------------------------------------------------------|    Loops and ranges

    def trunc(self):
        """
        :return: The truncation of this float.
        :type: :class:`~paya.runtime.plugs.Math1D`
        """
        out = self.unaryExpr('trunc')
        out.__class__ = type(self)
        return out

    @short(method='m')
    def combine(self, *others, method='multiplication'):
        """
        Uses a `combinationShape
        <https://help.autodesk.com/cloudhelp/2023/ENU/Maya-Tech-Docs/Nodes/combinationShape.html>`_
        node to combine this scalar with *\*others*.

        :param \*others: unpacked scalars
        :type \*others: int, float, :class:`~paya.runtime.plugs.Math1D`
        :param method/m: an enum for the 'combinationMethod' attribute of the
            node; can be specified as an index or label; one of:

            -   0: 'multiplication' (the default)
            -   1: 'lowest weighting'
            -   2: 'smooth'
        :return: The combined output.
        :rtype: :class:`~paya.runtime.plugtypes.Math1D`
        """
        node = r.nodes.CombinationShape.createNode()
        node.attr('combinationMethod').set(method)

        elems = [self] + [_mo.info(item
            )['item'] for item in _pu.expandArgs(*others)]

        for i, elem in enumerate(elems):
            elem >> node.attr('inputWeight')[i]

        out = node.attr('outputWeight')
        out.__class__ = type(self)
        return out

    def cycle(self,min,max):
        """
        Cycles this value so that it remains within the specified
        range.

        :param min: the range minimum
        :type min: [1D scalar value or ``Math1D``]
        :param max: the range maximum
        :type max: [1D scalar value or ``Math1D``]
        :return: The looped scalar output.
        :rtype: :class:`Math1D`
        """
        return min+((self-min)%(max-min))

    def __mod__(self, other, swap=False):
        """
        Implements the % operator (modulo).
        """
        if swap:
            op1, op2 = other, self
        else:
            op1, op2 = self, other

        expression = '.O[0] = {} % {}'.format(op1, op2)
        node = r.nodes.Expression.createNode()
        node.attr('expression').set(expression)
        output = node.attr('output')[0]
        return output.setClass(type(self))

    def __rmod__(self, other):
        return self.__mod__(other, swap=True)

    def remap(self, oldMin, oldMax, newMin, newMax, clamp=True):
        """
        Peforms simple linear remapping.

        :param oldMin: the previous range minimum
        :type oldMin: 1D value type or ``Math1D``
        :param oldMax: the previous range maximum
        :type oldMax: 1D value type or ``Math1D``
        :param newMin: the new range minimum
        :type newMin: 1D value type or ``Math1D``
        :param newMax: the new range maximum
        :type newMax: 1D value type or ``Math1D``
        :param bool clamp: clamp to the new range
            instead of extrapolating; defaults to ``True``
        :return: The remapped output.
        :rtype: :class:`Math1D`
        """
        if clamp:
            node = r.nodes.RemapValue.createNode()

            self >> node.attr('inputValue')

            oldMin >> node.attr('inputMin')
            oldMax >> node.attr('inputMax')

            newMin >> node.attr('outputMin')
            newMax >> node.attr('outputMax')

            return node.attr('outValue')

        else:
            ratio = (self-oldMin) / (oldMax-oldMin)

            return newMin+((newMax-newMin)*ratio)

    def clamp(self,min,max):
        """
        Clamps this output

        :param min: the range minimum
        :type min: 1D scalar type or ``Math1D``
        :param max: the range maximum
        :type max: 1D scalar type or ``Math1D``
        :return: The clamped output.
        :rtype: :class:`Math1D`
        """
        node = r.nodes.Clamp.createNode()

        self >> node.attr('inputR')

        min >> node.attr('minR')
        max >> node.attr('maxR')

        return node.attr('outputR')

    def minClamp(self,other):
        """
        Clamps this value to a minimum of 'other'.

        :param other: the new range minimum
        :type other: 1D scalar type or ``Math1D``
        :return: The min-clamped output.
        :rtype: :class:`Math1D`
        """
        return self.max(other)

    def maxClamp(self,other):
        """
        Clamps this value to a maximum of 'other'.

        :param other: the new range maximum
        :type other: 1D scalar type or ``Math1D``
        :return: The max-clamped output.
        :rtype: :class:`Math1D`
        """
        return self.min(other)

    def gatedClamp(self, floorOrCeiling, floorOpen, ceilingOpen):
        """
        Useful for squash-and-stretch control.

        :param floorOrCeiling: acts as a floor or ceiling for this output,
            depending on *floorOpen* and *ceilingOpen*
        :type floorOrCeiling: float, :class:`~paya.runtime.plugs.Math1D`
        :param floorOpen: when this is at 0.0, this output won't dip below
            *floorOrCeiling*
        :type floorOpen: float, :class:`~paya.runtime.plugs.Math1D`
        :param ceilingOpen: when this is at 0.0, this output won't rise above
            *floorOrCeiling*
        :return: The clamped output.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        ceiling = self.maxClamp(floorOrCeiling)
        ceiling = ceiling.blend(self, weight=ceilingOpen)

        floor = ceiling.minClamp(floorOrCeiling)
        floor = floor.blend(ceiling, weight=floorOpen)

        return floor

    #-----------------------------------------------------------------|    Comparisons

    def min(self,*others):
        """
        Returns the minimum amongst ``self`` and ``\*others``.

        :param \*others: unpacked list of scalar values or inputs to compare to
        :type \*others: [scalar value type of ``Math1D``]
        :return: The maximum scalar.
        :rtype: :class:`Math1D`
        """
        allinps = [self] + list(others)

        def pairwise(x,y):
            node = r.nodes.Condition.createNode(n='min')

            x >> node.attr('firstTerm')
            y >> node.attr('secondTerm')

            node.operation.set('Less Than')

            x >> node.attr('colorIfTrueR')
            y >> node.attr('colorIfFalseR')

            return node.attr('outColorR')

        return reduce(pairwise,allinps)

    def max(self,*others):
        """
        Returns the maximum amongst ``self`` and ``\*others``.

        :param \*others: unpacked list of scalar values or inputs to compare to
        :type \*others: [scalar value type of ``Math1D``]
        :return: The maximum scalar.
        :rtype: ``Math1D``
        """
        allinps = [self] + list(others)

        def pairwise(x,y):
            node = r.nodes.Condition.createNode(n='max')

            x >> node.attr('firstTerm')
            y >> node.attr('secondTerm')

            node.operation.set('Greater Than')

            x >> node.attr('colorIfTrueR')
            y >> node.attr('colorIfFalseR')

            return node.attr('outColorR')

        return reduce(pairwise,allinps)

    def _makeCompCondition(self, other, operation):
        """
        Configures a condition node for comparisons.
        """
        node = r.nodes.Condition.createNode()
        node.attr('operation').set(operation)

        self >> node.attr('firstTerm')
        other >> node.attr('secondTerm')

        node.attr('colorIfTrueR').set(1)
        node.attr('colorIfFalseR').set(0)

        return node.attr('outColorR')

    def eq(self,other):
        """
        Returns an output for 'equal'.

        :param other: the value or plug to compare to
        :type other: scalar value type or ``Math1D``
        :return: A ``condition`` node output that can be
            evaluated as a gating ``bool``.
        :rtype: ``Math1D``
        """
        return self._makeCompCondition(other,0)

    def ne(self,other):
        """
        Returns an output for 'not equal'.

        :param other: the value or plug to compare to
        :type other: scalar value type or ``Math1D``
        :return: A ``condition`` node output that can be
            evaluated as a gating ``bool``.
        :rtype: ``Math1D``
        """
        return self._makeCompCondition(other,1)

    def gt(self,other):
        """
        Returns an output for 'greater than'.

        :param other: the value or plug to compare to
        :type other: scalar value type or ``Math1D``
        :return: A ``condition`` node output that can be
            evaluated as a gating ``bool``.
        :rtype: ``Math1D``
        """
        return self._makeCompCondition(other,2)

    def ge(self,other):
        """
        Returns an output for 'greater or equal'.

        :param other: the value or plug to compare to
        :type other: scalar value type or ``Math1D``
        :return: A ``condition`` node output that can be
            evaluated as a gating ``bool``.
        :rtype: ``Math1D``
        """
        return self._makeCompCondition(other,3)

    def lt(self,other):
        """
        Returns an output for 'less than'.

        :param other: the value or plug to compare to
        :type other: scalar value type or ``Math1D``
        :return: A ``condition`` node output that can be
            evaluated as a gating ``bool``.
        :rtype: ``Math1D``
        """
        return self._makeCompCondition(other,4)

    def le(self,other):
        """
        Returns an output for 'less or equal'.

        :param other: the value or plug to compare to
        :type other: scalar value type or ``Math1D``
        :return: A ``condition`` node output that can be
            evaluated as a gating ``bool``.
        :rtype: ``Math1D``
        """
        return self._makeCompCondition(other,5)

    def inRange(self, minValue, maxValue):
        """
        :param minValue: the floor value
        :type minValue: float, int, str, :class:`Math1D`
        :param maxValue: the ceiling value
        :type maxnValue: float, int, str, :class:`Math1D`
        :return: :return: A ``condition`` node output that can be
            evaluated as a gating ``bool``.
        :rtype: ``Math1D``
        """
        return self.ge(minValue) * self.le(maxValue)

    #--------------------------------------------------------------------|    Gates

    def choose(self, inputs):
        node = r.nodes.Choice.createNode()
        self >> node.attr('selector')

        for i, input in enumerate(inputs):
            input >> node.attr('input')[i]

        return node.attr('output')

    def ifElse(
            self,
            outputIfTrue,
            outputIfFalse
    ):
        """
        If-then-else output selector.

        :param Attribute outputIfTrue: plug to return if this plug evaluates as True
        :param Attribute outputIfFalse: plug to return if this plug evaluates as False
        :return: The selected output.
        :rtype: :class:`Attribute`
        """
        return self.choose([outputIfFalse,outputIfTrue])

    #--------------------------------------------------------------------|    Blending

    @short(weight='w', swap='sw')
    def blend(self, other, weight=0.5, swap=False):
        """
        Blends this output towards ``other``.

        :param other: The scalar value or plug towards which to blend
        :type other: 1D value type, or :class:`Math1D`
        :param weight/w: 'other' will be fully active at 1.0; defaults to 0.5
        :type weight/w: 1D value type or :class:`Math1D`
        :param bool swap/sw: swap operands; defaults to False
        :return: The blended output.
        :rtype: :class:`Math1D`
        """
        node = r.nodes.BlendTwoAttr.createNode()
        self >> node.attr('input')[1 if swap else 0]
        other >> node.attr('input')[0 if swap else 1]
        weight >> node.attr('attributesBlender')

        return node.attr('output')

    #--------------------------------------------------------------------|    Expression utils

    def unaryExpr(self, operation, returnsRadians=False):
        """
        Configures an expression node to run a unary expression on this plug,
        and returns its output.

        :param str operation: the expression operation, for example ``'sin'``
        :param bool returnsRadians: interpret the output as a radian return
            (e.g. from a trigonometric function) and pipe into an angle
            output; defaults to ``False``
        :return: the expression output
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        with r.Name(operation):
            node = r.nodes.Expression.createNode()

        expr = '.O[0] = {}({})'.format(operation, self)
        node.attr('expression').set(expr)
        r.expression(node, e=True, alwaysEvaluate=False)

        out = node.attr('output')[0]

        if returnsRadians:
            node.addAttr('angleOutput', at='doubleAngle', k=True)

            with r.NativeUnits():
                out >> node.attr('angleOutput')

            out = node.attr('angleOutput')

        return out

    #--------------------------------------------------------------------|    Trigonometry

    # See plugtypes.Angle for the forward functions

    def acos(self):
        """
        Returns the inverse trigonometric cosine.

        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        return self.clamp(0, 1).unaryExpr('acos', returnsRadians=True)

    def asin(self):
        """
        Returns the inverse trigonometric sine.

        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        return self.unaryExpr('asin', returnsRadians=True)

    def atan(self):
        """
        Returns the inverse trigonometric tangent.

        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        return self.unaryExpr('atan', returnsRadians=True)

    #--------------------------------------------------------------------|    Sampling

    @short(relative='rel')
    def atTime(self, time, relative=False):
        """
        Returns this output either sampled at a particular time, or with
        a live time offset.

        :param time: the time at which to sample this output
        :param bool relative: interpret 'time' as a relative offset;
            defaults to False
        :return: the sampled output
        :rtype: :class:`Math1D`
        """
        time, dim, ut, isplug = _mo.info(time).values()

        node = r.nodes.FrameCache.createNode()
        self >> node.attr('stream')

        if isplug:
            if relative:
                time = r.PyNode('time1').attr('outTime') + time

            time >> node.attr('varyTime')
            out = node.attr('varying')

        else:
            if relative:
                if isinstance(time, (long, int)):
                    if time >= 0:
                        out = node.attr('future')[time]

                    else:
                        out = node.attr('past')[abs(time)]

                else:
                    time = r.PyNode('time1').attr('outTime') + time
                    time >> node.attr('varyTime')
                    out = node.attr('varying')

            else:
                node.attr('varyTime').set(time)
                out = node.attr('varying')

        out.__class__ = type(self)
        return out