import pymel.core as p
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