import maya.OpenMaya as om
import pymel.util as _pu
import pymel.core.datatypes as _dt
from paya.util import short
import paya.runtime as r

class Angle:

    #-----------------------------------------------------------|    Get / set

    @short(plug='p')
    def get(self, plug=False, default=None, **kwargs):
        """
        Overloads :py:meth:`paya.runtime.plugs.Attribute.get` to return
        :class:`~paya.runtime.data.Angle` instances instead of
        :class:`float`.
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
        Overloads :meth:`~paya.runtime.plugs.Attribute.get` to ensure
        that instances of :class:`~paya.runtime.data.Angle`
        with units that don't match the UI setting are set correctly.
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

    def unwind(self):
        """
        :return: This angle, unwound and with the sign preserved.
        :rtype: :class:`Angle`
        """
        out = self % r.degToUI(360.0)
        return out.setClass(type(self))

    def unwindPositive(self):
        """
        :return: The unwound positive form of the angle.
        :rtype: :class:`Angle`
        """
        out = self.unwind()
        wind = r.degToUI(360.0)
        isNeg = out.lt(0.0)

        corrected = wind + out

        out = isNeg.ifElse(corrected, out)
        return out.setClass(type(self))

    def unwindNegative(self):
        """
        :return: The unwound negative form of the angle.
        :rtype: :class:`Angle`
        """
        out = self.unwind()
        wind = r.degToUI(360.0)
        isNeg = out.lt(0.0)

        corrected = out - wind

        out = isNeg.ifElse(out, corrected)
        return out.setClass(type(self))

    def unwindShortest(self):
        """
        :return: This angle, unwound and, if less than -180 or greater than
            180, flipped.
        :rtype: :class:`Angle`
        """
        unwound = self.unwind()

        over180 = unwound.gt(r.degToUI(180))
        under180 = unwound.lt(r.degToUI(-180))

        over180Correction = unwound-r.degToUI(360.0)
        under180Correction = r.degToUI(360.0)+unwound

        out = over180.ifElse(
            over180Correction,
            under180.ifElse(
                under180Correction,
                unwound
            ))

        return out.setClass(type(self))

    @short(
        shortestIndex='si',
        positiveIndex='pi',
        negativeIndex='ni'
    )
    def unwindSwitch(
            self,
            switchSource,
            shortestIndex=0,
            positiveIndex=1,
            negativeIndex=2
    ):
        """
        Unwinds this angle using a mode picked using an integer value or plug
        (typically an animator switcher attribute).

        :param switchSource: either an integer value to pick an
            implementation, or an attribute of type ``enum`` or ``int`` to
            switch between all implementations
        :type switchSource: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param int shortestIndex/si: the attribute output value that should
            activate 'shortest' mode; defaults to 0
        :param int positiveIndex/pi: the attribute output value that should
            activate 'positive' mode; defaults to 1
        :param int negativeIndex/ni: the attribute output value that should
            activate 'negative' mode; defaults to 2
        :return: The switched output.
        :rtype: :class:`Angle`
        """
        if isinstance(switchSource, r.Attribute):
            switchIsPlug = True

        elif isinstance(switchSource, str):
            switchSource = r.Attribute(switchSource)
            switchIsPlug = True

        elif isinstance(switchSource, int):
            switchIsPlug = False

        else:
            raise TypeError("Switch source not an integer or integer plug.")

        if switchIsPlug:
            unwound = self.unwind()
            wind = r.degToUI(360.0)

            #------------------------|    Positive

            isNeg = unwound.lt(0.0)

            correctedToPositive = isNeg.ifElse(
                wind + unwound,
                unwound
            )

            #------------------------|    Negative

            correctedToNegative = isNeg.ifElse(
                unwound,
                unwound-wind
            )

            #------------------------|    Shortest

            over180 = unwound.gt(r.degToUI(180))
            under180 = unwound.lt(r.degToUI(-180))

            over180Correction = unwound-r.degToUI.radians(360.0)
            under180Correction = r.degToUI(360.0)+unwound

            shortestCorrection = over180.ifElse(
                over180Correction,
                under180.ifElse(
                    under180Correction,
                    unwound
                ))

            #------------------------|    Switch

            pairs = zip(
                [shortestIndex, positiveIndex, negativeIndex],
                [shortestCorrection, correctedToPositive, correctedToNegative]
            )

            pairs = list(sorted(pairs, key=lambda x: x[0]))
            outputs = [pair[1] for pair in pairs]

            return switchSource.choose(outputs).setClass(type(self))

        else:
            pairs = zip(
                [shortestIndex, positiveIndex, negativeIndex],
                [self.unwindShortest, self.unwindPositive,
                                    self.unwindNegative]
            )

            pairs = list(sorted(pairs, key=lambda x: x[0]))
            method = pairs[switchSource][1]

            return method()

    #--------------------------------------------------------------------|    Trigonometry

    # See plugtypes.Math1D for the inverse functions

    def cos(self):
        """
        Returns the trigonometric cosine.

        :rtype: :class:`Math1D`
        """
        return self.asRadians().unaryExpr('cos')

    def sin(self):
        """
        Returns the trigonometric sine.

        :rtype: :class:`Math1D`
        """
        return self.asRadians().unaryExpr('sin')

    def tan(self):
        """
        Returns the trigonometric tangent.

        :rtype: :class:`Math1D`
        """
        return self.asRadians().unaryExpr('tan')