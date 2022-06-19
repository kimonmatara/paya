import maya.cmds as m
import pymel.core as p

from paya.plugtree import getPath
from paya.util import short
import paya.runtime as r

uncap = lambda x: x[0].lower()+x[1:]


class Attribute:

    __math_dimension__ = None

    #-----------------------------------------------------------------|    Type management

    @short(inherited='i')
    def plugType(self, inherited=False):
        """
        Returns abstract type information for this plug.

        :param bool inherited/i: return the full hierarchy stack instead
            of just a single type; defaults to False
        :return: The type information.
        :rtype: str or list
        """
        out = getPath(self.__class__.__name__)

        if inherited:
            return list(map(uncap, out))

        return uncap(out[-1])

    def setClass(self, cls):
        """
        Convenience method to enable chained dot notation when reassigning the
        plug class (sometimes necessary for ambiguous output types, e.g. on
        'choice' nodes). Returns ``self``.

        Equivalent to:

        .. code-block:: python

            self.__class__ = cls

        :param type cls: the class to assign
        :return: This instance, with a reassigned class.
        :rtype: :class:`Attribute`
        """
        self.__class__ = cls

        return self

    #-----------------------------------------------------------------|    Get() overload

    @short(plug='p')
    def get(self, plug=False, **kwargs):
        """
        Extends :py:meth:`pymel.core.general.Attribute.get` with the ``plug``
        keyword argument, which is useful when the decision whether to work
        statically or dynamically rests with the end-user.

        :param bool plug/p: if True, return ``self``; defaults to False
        :param \*\*kwargs: forwarded to the base method
        :return: :class:`Attribute` or a value type
        """
        if plug:
            return self

        return p.general.Attribute.get(self, **kwargs)

    #-----------------------------------------------------------------|    State management

    @short(recursive='r')
    def release(self, recursive=False):
        """
        Unlocks this attribute and disconnects any inputs.

        :param bool recursive/r: if this is a compound, release child attributes
            too; defaults to False
        :return:
        """
        self.unlock()
        self.disconnect(inputs=True)
        return self

    #-----------------------------------------------------------------|    Connections

    @short(plug='p')
    def put(self, source, plug=None):
        """
        Helper for mixed plug / value workflows. If 'source' is an attribute,
        it will be connected into this plug. Otherwise, this plug will be set
        to 'source'.

        :param source: the source value or plug
        :param plug/p: if you know whether 'source' is a plug or not, specify
            if here; defaults to None
        :type plug/p: bool or None
        :return: self
        """
        if plug is None:
            plug = isinstance(source, (str, p.Attribute))

        if plug:
            r.connectAttr(source, self, f=True)

        else:
            self.set(source)

        return self

    __rrshift__ = put