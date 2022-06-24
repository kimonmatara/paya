import pymel.core as p
import paya.lib.attrs as _atr
from paya.util import short
import paya.runtime as r


class Enum:

    __math_dimension__ = 1

    #-----------------------------------------------------------|    Mixed setting

    @short(plug='p')
    def put(self, other, plug=None):
        """
        Overloads :meth:`paya.plugtypes.Attribute.put` to account for enum
        keys.
        """
        if plug is None:
            if isinstance(other, str):
                plug = other not in self.getEnums().keys()

            else:
                plug = isinstance(other, p.Attribute)

        return r.plugs.Attribute.put(self, other, p=plug)

    __rrshift__ = put

    #-----------------------------------------------------------------|    Section attributes

    def isSectionAttr(self):
        """
        :return: True if this attribute is a 'section' enum.
        :rtype: bool
        """
        labels = plug.getEnums().keys()

        if len(labels) is 1:
            return labels[0] == _atr.__section_enum__

        return False