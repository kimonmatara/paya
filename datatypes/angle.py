import pymel.util as _pu
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