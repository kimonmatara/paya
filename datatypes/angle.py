import pymel.util as _pu
from paya.util import short
import paya.runtime as r


class Angle:

    def unwindPositive(self):
        """
        :return: The unwound positive form of the angle.
        :rtype: :class:`Angle`
        """
        unit = self.unit
        wind = 360.0 if unit == 'degrees' else _pu.radians(360.0)

        out = self % wind
        return type(self)(out, unit=unit)

    def unwindNegative(self):
        """
        :return: The unwound negative form of the angle.
        :rtype: :class:`Angle`
        """
        unit = self.unit
        wind = -360.0 if unit == 'degrees' else _pu.radians(-360.0)

        out = self % wind
        return type(self)(out, unit=unit)

    def unwind(self):
        """
        :return: This angle, unwound, and with the sign preserved.
        :class:`Angle`
        """
        if self < 0.0:
            return self.unwindNegative()

        return self.unwindPositive()

    def unwindShortest(self):
        """
        :return: This angle, unwound and, if less than -180 or greater than
            180, flipped.
        :rtype: :class:`Angle`
        """
        unit = self.unit
        wind = 360.0 if unit == 'degrees' else _pu.radians(360.0)
        halfWind = wind * 0.5
        unwound = self.unwind()

        if unwound < 0.0:
            if unwound < -halfWind:
                unwound += wind

        else:
            if unwound > halfWind:
                unwound -= wind

        return type(self)(unwound, unit=unit)

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
        Unwinds this angle using a mode picked using an integer value.

        :param switchSource: an integer value to pick an implementation
        :type switchSource: int
        :param int shortestIndex/si: the integer value that should pick
            :meth:`unwindShortest`; defaults to 0
        :param int positiveIndex/pi: the integer value that should pick
            :meth:`unwindPositive`; defaults to 1
        :param int negativeIndex/ni: the integer value that should pick
            :meth:`unwindNegative`; defaults to 2
        :return: The switched output.
        :rtype: :class:`Angle`
        """
        pairs = [
            (shortestIndex, self.unwindShortest),
            (positiveIndex, self.unwindPositive),
            (negativeIndex, self.unwindNegative)
            ]

        pairs = list(sorted(pairs, key=lambda x: x[0]))
        method = pairs[switchSource][1]

        return method()