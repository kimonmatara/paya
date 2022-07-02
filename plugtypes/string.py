import pymel.core as p
from paya.util import short
import paya.runtime as r


class String:

    #-----------------------------------------------------------|    Mixed setting

    @short(plug='p')
    def put(self, other, plug=None):
        """
        Overloads :meth:`paya.runtime.plugs.Attribute.put` to prevent any type of
        incoming connection.
        """
        self.set(other)

    __rrshift__ = put