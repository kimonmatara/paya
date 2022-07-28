import maya.OpenMaya as om
import pymel.util as _pu
import pymel.core.datatypes as _dt
from paya.util import short
import paya.runtime as r


class Angle:

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

    def toUnwoundPositive(self):
        out = self % _pu.radians(360.0)
        out.__class__ = type(self)
        return out

    def toUnwoundNegative(self):
        out = self % _pu.radians(-360.0)
        out.__class__ = type(self)
        return out