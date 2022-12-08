import maya.OpenMaya as om
import pymel.util as _pu
import pymel.core.datatypes as _dt
from paya.util import short
import paya.runtime as r

class Angle:

    #-----------------------------------------------------------|    Constructor

    @classmethod
    @short(attributeType='at')
    def create(cls, node, attrName, **kwargs):
        """
        Creates a ``doubleAngle`` attribute.

        :param node: the node on which to create the attribute
        :type node: :class:`str`, :class:`~paya.runtime.nodes.DependNode`
        :param str attrName: the name of the attribute
        :param \*\*kwargs: forwarded to
            :meth:`paya.runtime.nodes.DependNode.addAttr`
        :return: The generated attribute.
        :rtype: :class:`Angle`
        """
        kwargs['attributeType'] = 'doubleAngle'
        node = r.PyNode(node)
        return node.addAttr(attrName, **kwargs)

    #-----------------------------------------------------------|    Get / set

    @short(plug='p')
    def get(self, plug=False, default=None, **kwargs):
        """
        Overloads :py:meth:`paya.runtime.plugs.Attribute.get` to return an
        :class:`~paya.runtime.data.Angle` instance instead of a
        :class:`float`. The instance will have embedded unit information
        (access via ``.unit``).
        """
        if plug:
            return self

        result = r.plugs.Attribute.get(
            self, plug=False, default=default, **kwargs)

        if isinstance(result, float):
            return r.data.Angle(result)

        return result

    def set(self, *args, **kwargs):
        """
        Overloads :meth:`~paya.runtime.plugs.Attribute.set` for improved unit
        management. If the argument is a :class:`float`, then it will be set
        directly. If the argument is an :class:`~paya.runtime.data.Angle`
        instance with units that are different from the UI, it will be
        converted accordingly.

        To set values with a :class:`float` in degrees regardless of UI
        setting, use :func:`~paya.lib.mathops.degToUI`, available on
        :mod:`paya.runtime`.
        """
        if args:
            value = args[0]

            if isinstance(value, _dt.Angle):
                currentUnit = om.MAngle.uiUnit()

                if currentUnit == om.MAngle.kRadians:
                    if value.unit != 'radians':
                        value = _pu.radians(value)

                elif value.unit != 'degrees':
                    value = _pu.degrees(value)

                args = [value]

        r.plugs.Attribute.set(self, *args, **kwargs)

    #-----------------------------------------------------------------|    Ranges

    def unwind360(self):
        """
        :return: This angle, rolled so that it always remains in the -360 ->
        360 range.
        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        return (self % r.degToUI(360.0)).setClass(type(self))

    def unwindShortest(self):
        """
        :return: This angle, unwound and, if over 180, converted to negative
            form.
        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        unwound = self % _pu.radians(360.0)
        over = unwound.gt(_pu.radians(180.0))

        out = over.ifElse(
            unwound - _pu.radians(360.0),
            unwound
        ).setClass(type(self))

        return out

    def unwindPositive(self):
        """
        :return: The unwound positive form of the angle.
        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        # Sign management is necessary because, unlike Python modulo,
        # Maya expr modulo preserves sign
        unwound = self % _pu.radians(360.0)

        isNeg = unwound.lt(0.0)

        out = isNeg.ifElse(
            unwound + _pu.radians(360.0),
            unwound
        ).setClass(type(self))

        return out

    def unwindNegative(self):
        """
        :return: The unwound negative form of the angle.
        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        # Sign management is necessary because, unlike Python modulo,
        # Maya expr modulo preserves sign
        unwound = self % _pu.radians(360.0)
        isNeg = unwound.lt(0.0)

        out = isNeg.ifElse(
            unwound,
            unwound - _pu.radians(360.0)
        ).setClass(type(self))

        return out

    @short(
        shortestIndex='si',
        positiveIndex='pi',
        negativeIndex='ni'
    )
    def unwindSwitch(
            self,
            switchAttr,
            shortestIndex=0,
            positiveIndex=1,
            negativeIndex=2
    ):
        """
        Unwinds this angle, with the 'shortest' / 'positive' / 'negative'
        modes chosen from a user attribute (typically an enum). Useful for
        twist setups.

        This method is more efficient than switching between the outputs of
        :meth:`unwindShortest`, :meth:`unwindPositive` and
        :meth:`unwindNegative`.

        :param switchAttr: the switch attribute; should be of type ``enum``
            or ``long``
        :type switchAttr: str, :class:`~paya.runtime.plugs.Math1D`
        :param int shortestIndex: the attribute index for 'shortest'; defaults
            to 0
        :param int positiveIndex: the attribute index for 'positive'; defaults
            to 1
        :param int negativeIndex: the attribute index for 'negative'; defaults
            to 2
        :return: The unwound angle.
        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        if isinstance(switchAttr, int):
            if switchAttr is 0:
                return self.unwindShortest()

            elif switchAttr is 1:
                return self.unwindPositive()

            elif switchAttr is 2:
                return self.unwindNegative()

            else:
                raise RuntimeError(
                    "Invalid switch mode: {}".format(switchAttr)
                )

        unwound = self % _pu.radians(360.0)
        isNeg = unwound.lt(0.0)

        positiveOutput = isNeg.ifElse(
            unwound + _pu.radians(360.0),
            unwound
        )

        negativeOutput = isNeg.ifElse(
            unwound,
            unwound - _pu.radians(360.0)
        )

        over = unwound.gt(_pu.radians(180.0))

        shortestOutput = over.ifElse(
            unwound - _pu.radians(360.0),
            unwound
        )

        selector = r.Attribute(switchAttr)

        pairs = zip(
            [shortestIndex, positiveIndex, negativeIndex],
            [shortestOutput, positiveOutput, negativeOutput]
        )

        pairs = sorted(pairs, key=lambda x: x[0])
        items = [pair[1] for pair in pairs]

        out = selector.choose(items).setClass(type(self))

        return out