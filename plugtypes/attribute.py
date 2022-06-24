import re
import maya.cmds as m
import pymel.core as p

from paya.plugtree import getPath
from paya.util import short
import paya.runtime as r

uncap = lambda x: x[0].lower()+x[1:]


class Attribute:

    __math_dimension__ = None

    #-----------------------------------------------------------------|    Type management

    def isAnimatableDynamic(self):
        """
        :return: True if this is a dynamic attribute that can be exposed for
            keying.
        """
        if self.isDynamic():
            typ = r.addAttr(self, q=True, at=True)

            if typ == 'typed':
                return False

            if re.match(
                r"^(float|double|long|short)(2|3)$",
                typ
            ):
                return True

            return typ in ['bool', 'long', 'short', 'enum', 'time',
                 'float', 'double', 'doubleAngle', 'doubleLinear']

        return False

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
    def lock(self, recursive=False, **kwargs):
        """
        Overloads :class:`~pymel.core.general.Attribute` to implement the
        *recursive* option and return ``self``.

        :param bool recursive/r: if this is a compound, lock its children too;
            defaults to False
        :param \*\*kwargs: forwarded to
            :meth:`~pymel.core.general.Attribute.lock`
        :return: ``self``
        :rtype: :class:`~paya.plugtypes.attribute.Attribute`
        """
        p.Attribute.lock(self, **kwargs)
        return self

    @short(recursive='r')
    def hide(self, recursive=False):
        """
        Turns off *keyable* and *channelBox* for this attribute.

        :param bool recursive/r: if this is a compound, edit the children too;
            defaults to False
        :return: ``self``
        :rtype: :class:`~paya.plugtypes.attribute.Attribute`
        """
        if self.get(k=True):
            self.set(k=False)

        elif self.get(cb=True):
            self.set(cb=False)

        return self

    @short(recursive='r', force='f')
    def unlock(self, recursive=False, force=False, **kwargs):
        """
        Overloads :class:`~pymel.core.general.Attribute` to implement the
        *recursive* and *force* options and return ``self``.

        :param bool recursive/r: if this is a compound, unlock the children
            too; defaults to False
        :param bool force/f: if this is the child of a compound, unlock the
            compound parent too; defaults to False
        :param \*\*kwargs: forwarded to
            :meth:`~pymel.core.general.Attribute.unlock`
        :return: ``self``
        :rtype: :class:`~paya.plugtypes.attribute.Attribute`
        """
        p.Attribute.unlock(self, **kwargs)

        if force:
            if self.isChild():
                parent = self.getParent()
                parent.unlock()

        return self

    @short(
        recursive='r',
        keyable='k',
        channelBox='cb'
    )
    def show(self, recursive=False, **kwargs):
        keyable = channelBox = None

        keyable = kwargs.get('keyable')

        if keyable is not None:
            channelBox = not keyable

        if channelBox is None:
            channelBox = kwargs.get('channelBox')

        if channelBox is not None:
            keyable = not channelBox

        if keyable is None and channelBox is None:
            keyable = True
            channelBox = False

        if keyable:
            self.set(k=True)

        else:
            self.set(cb=True)

        return self

    @short(recursive='r', force='f')
    def release(self, recursive=False, force=False):
        """
        Unlocks this attribute and disconnects any inputs.

        :param bool force/f: if this is the child of a compound, unlock
            the parent too; defaults to False
        :param bool recursive/r: if this is a compound, release child attributes
            too; defaults to False
        :return:
        """
        self.unlock(f=force)
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

    #-----------------------------------------------------------------|    Section attributes

    def isSectionAttr(self):
        """
        :return: True if this attribute is a 'section' enum.
        :rtype: bool
        """
        return False

    #-----------------------------------------------------------------|    Reordering

    def _sendAboveOrBelow(self, attrName, below=False):
        thisName = self.attrName()

        if below:
            order = [attrName, thisName]

        else:
            order = [thisName, attrName]

        node = self.node()
        node.reorderAttrs(order)

        return node.attr(thisName)

    def sendAbove(self, attrName):
        """
        Sends this attribute above another attribute in the channel box.

        :param str attrName: the name of the 'anchor' attribute
        :return: This attribute, rebuilt.
        :rtype: :class:`~paya.plugtypes.attribute.Attribute`
        """
        return self._sendAboveOrBelow(attrName, below=False)

    def sendBelow(self, attrName):
        """
        Sends this attribute below another attribute in the channel box.

        :param str attrName: the name of the 'anchor' attribute
        :return: This attribute, rebuilt.
        :rtype: :class:`~paya.plugtypes.attribute.Attribute`
        """
        return self._sendAboveOrBelow(attrName, below=True)