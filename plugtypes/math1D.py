from functools import reduce

import pymel.util as _pu
from paya.util import short
import paya.lib.typeman as _tm
import paya.runtime as r

if not r.pluginInfo('quatNodes', q=True, loaded=True):
    r.loadPlugin('quatNodes')


class Math1D:

    __math_dimension__ = 1

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).

        :param other: a value or plug of dimension 1, 2, 3 or 4
        """

        other, dim, isplug = _tm.mathInfo(other)

        if dim is 1:
            node = r.nodes.AddDoubleLinear.createNode()

            self >> node.attr('input{}'.format(2 if swap else 1))
            node.attr('input{}'.format(1 if swap else 2)).put(other, p=isplug)

            return node.attr('output')

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
        other, dim, isplug = _tm.mathInfo(other)

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
        other, dim, isplug = _tm.mathInfo(other)

        if dim is 1:
            node = r.nodes.MultDoubleLinear.createNode()

            self >> node.attr('input{}'.format(2 if swap else 1))
            other >> node.attr('input{}'.format(1 if swap else 2))

            return node.attr('output')

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
        other, dim, isplug = _tm.mathInfo(other)

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
        other, dim, isplug = _tm.mathInfo(other)

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
        mdl = r.nodes.MultDoubleLinear.createNode()
        self >> mdl.attr('input1')
        mdl.attr('input2').set(-1.0)
        return mdl.attr('output')

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
        other, otherDim, otherIsPlug = _tm.mathInfo(other)

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

        elems = [self] + [_tm.mathInfo(item
            )[0] for item in _pu.expandArgs(*others)]

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
            expr = str(other)+'%'+str(self)

        else:
            expr = str(self)+'%'+str(other)

        node = r.nodes.Expression.createNode(n='modulo')
        node.attr('expression').set('.O[0] = {}'.format(expr))

        return node.attr('output')[0]

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

    def choose(self, outputs):
        """
        Uses this attribute as an index selector for any number of other
        outputs or values.

        Named 'choose' rather than 'select' to avoid shadowing the PyMEL
        namesake. If all the outputs are of the same attribute type, the type
        will be assigned to the output as well.

        :param list outputs: list of outputs from which to choose
        :type outputs: [``Attribute``]
        """
        # the inline if-else is necessary otherwise r.Attribute will discard
        # any custom class assignments
        outputs = [r.Attribute(output) if not \
            isinstance(output, r.Attribute) else output for output in outputs]

        node = r.nodes.Choice.createNode()
        self >> node.attr('selector')

        for i, output in enumerate(outputs):
            output >> node.attr('input')[i]

        out = node.attr('output')
        plugTypes = [type(output) for output in outputs]

        if len(set(plugTypes)) is 1:
            out.__class__ = plugTypes[0]

        return out

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

    def unaryExpr(self, operation):
        """
        Constructs an expression that calls the specified operation on 'self'.
        Used to implement all the trig methods.

        :param str operation: The operation to call, for example *cos*
        :return: The output plug of the expression node.
        :rtype: :class:`Attribute`
        """
        expr = '{}({})'.format(operation,str(self))
        node = r.nodes.Expression.createNode(n=operation)
        node.attr('expression').set('.O[0] = {}'.format(expr))
        r.expression(node, e=True, alwaysEvaluate=False)
        return node.attr('output')[0]

    #--------------------------------------------------------------------|    Trigonometry

    def degrees(self):
        """
        Converts radians to degrees.

        :rtype: :class:`Math1D`
        """
        return self * 57.2958

    def radians(self):
        """
        Converts degrees to radians.

        :rtype: :class:`Math1D`
        """
        return self * 0.0174533

    def cos(self):
        """
        Returns the trigonometric cosine.

        :rtype: :class:`Math1D`
        """
        return self.unaryExpr('cos')

    def sin(self):
        """
        Returns the trigonometric sine.

        :rtype: :class:`Math1D`
        """
        return self.unaryExpr('sin')

    def tan(self):
        """
        Returns the trigonometric tangent.

        :rtype: :class:`Math1D`
        """
        return self.unaryExpr('tan')

    def acos(self):
        """
        Returns the inverse trigonometric cosine.

        :rtype: :class:`Math1D`
        """
        input = self.clamp(0, 1)
        return input.unaryExpr('acos')

    def asin(self):
        """
        Returns the inverse trigonometric sine.

        :rtype: :class:`Math1D`
        """
        return self.unaryExpr('asin')

    def atan(self):
        """
        Returns the inverse trigonometric tangent.

        :rtype: :class:`Math1D`
        """
        return self.unaryExpr('atan')

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
        time, dim, isplug = _tm.mathInfo(time)

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