import maya.cmds as m
import pymel.core as p
from paya.util import short
import paya.runtime as r


class Attribute:

    __math_dimension__ = None

    #-----------------------------------------------------------------|    Type management

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

    def setDimension(self, dimension):
        """
        Sources the generic class for the requested dimension and defers to
        :meth:`setClass`.

        :param int dimension: the dimension to apply, for example 4
            for :class:`~paya.plugtypes.attributeMath4D.AttributeMath4D`
        :return: This instance, with a reassigned class.
        :rtype: :class:`Attribute`
        """
        className = 'Attribute{}D'.format(dimension)
        cls = getattr(r.plugs, className)

        return self.setClass(cls)

    #-----------------------------------------------------------------|    Get() overload

    @short(plug='p')
    def get(self, plug=False, **kwargs):
        """
        Extends :py:meth:`pymel.core.general.Attribute.get` with the ``plug``
        keyword argument, which is sometimes useful in mixed value / plug
        workflows.

        :param bool plug/p: if True, return ``self``; defaults to False
        :param **kwargs: forwarded to the base method
        :return: :class:`Attribute` or a value type
        """
        if plug:
            return self

        return p.general.Attribute.get(self, **kwargs)

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
            if isinstance(source, p.Attribute):
                plug = True

            elif isinstance(source, str):
                plug = '.' in source and m.objExists(source)

            else:
                plug = False

        if plug:
            r.connectAttr(source, self, f=True)

        else:
            self.set(source)

        return self

    __rrshift__ = put

    #-----------------------------------------------------------------|    Multis and compounds

    def __iter__(self):
        """
        Overloads :py:meth:`pymel.core.general.Attribute.__iter__` to support
        compounds.
        """
        if self.isMulti():
            return p.Attribute.__iter__(self)

        else:
            if self.isCompound():
                return iter(self.getChildren())

        return p.Attribute.__iter__(self)