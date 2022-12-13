import re
import maya.OpenMaya as om
import maya.cmds as m
import pymel.core as p

import paya.pluginfo as _pi
from paya.util import short
import paya.lib.attrs as _atr
import paya.runtime as r

cap = lambda x: x[0].upper()+x[1:]
uncap = lambda x: x[0].lower()+x[1:]


class Attribute:

    #-----------------------------------------------------------------|    Constructor

    @classmethod
    def createAttr(cls, attrName, node=None, **kwargs):
        """
        Creates an attribute.

        :param str attrName: the name of the attribute
        :param node: the node on which to create the attribute; if omitted,
            a free-standing ``network`` node will be created to hold the
            attribute; defaults to ``None``
        :type node: :class:`str`, :class:`~paya.runtime.nodes.DependNode`
        :param \*\*kwargs: forwarded to
            :meth:`~paya.runtime.nodes.DependNode.addAttr`
        :return: The generated attribute.
        :rtype: `Attribute`
        """
        if node is None:
            node = cls._createFreeAttrNode()
        return node.addAttr(attrName, **kwargs)

    @classmethod
    def _createFreeAttrNode(cls):
        with r.Name(cls.__name__):
            return r.nodes.Network.createNode()

    #-----------------------------------------------------------------|    Connections

    @short(recursive='r')
    def hasInputs(self, recursive=False):
        """
        :param bool recursive/r: if this is a compound, inspect children as
            well
        :return: ``True`` if this plug has inputs, otherwise ``False``.
        :rtype: :class:`bool`
        """
        if self.inputs():
            return True

        if self.isCompound():
            for child in self.getChildren():
                if child.hasInputs():
                    return True

        return False

    def splitInputs(self):
        """
        Splits any compound-level input into per-child connections. The
        compound-level connection is maintained.

        :return: ``self``
        """
        if self.isCompound():
            inputs = self.inputs(plugs=True)

            if inputs:
                input = inputs[0]

                srcChildren = input.getChildren()
                destChildren = self.getChildren()

                for srcChild, destChild in zip(srcChildren, destChildren):
                    srcChild >> destChild
        else:
            r.warning("Can't split inputs; not a compound.")

        return self

    #-----------------------------------------------------------------|    Proxy attributes

    @short(longName='ln', shortName='sn')
    def createProxy(self, node, longName=None, shortName=None):
        """
        Creates a proxy of this attribute.

        :param node: the node on which to create the proxy
        :type node: :class:`str`, :class:`~paya.runtime.nodes.DependNode`
        :param str longName/ln: a long name for the proxy attribute; defaults
            this attribute's long name
        :param str shortName/sn: a short name for the proxy attribute;
            defaults this attribute's short name
        :return: The proxy attribute.
        :rtype: :class:`~paya.runtime.plugs.Attribute`
        """
        _self = str(self)

        if longName is None:
            longName = self.attrName(longName=True)

        if shortName is None:
            shortName = self.attrName()

        kw = {'proxy': _self}

        if longName:
            kw['longName'] = longName

        if shortName:
            kw['shortName'] = shortName

        m.addAttr(str(node), **kw)
        return node.attr(longName)

    #-----------------------------------------------------------------|    Unit / type management

    # @short(onlyIfUnits='ofu')
    # def asDouble(self, onlyIfUnits=False):
    #     if onlyIfUnits:
    #         doPipe = self.type() in ('doubleLinear', 'doubleAngle')
    #
    #     else:
    #         doPipe = True
    #
    #     if doPipe:
    #         with r.Name('asDouble'):
    #             node = r.nodes.Network.createNode()
    #
    #         node.addAttr('output', at='double')
    #         self >> node.attr('output')
    #
    #         return node.attr('output')
    #
    #     return self

    # def asUnitless(self):
    #     attrType = self.type()
    #
    #     if attrType in ('double', 'float',)
    #
    #

    # def isMath1D(self):
    #     """
    #     :return: ``True`` if this is a 1D scalar or similar.
    #     :rtype: :class:`bool`
    #     """
    #     if self.isArray():
    #         return False
    #
    #     if self.isCompound():
    #         return False
    #
    #     if self.isMulti():
    #         self = self[0]
    #
    #     mplug = self.__apimplug__()
    #     mobj = mplug.attribute()
    #
    #     if mobj.hasFn(om.MFn.kNumericAttribute):
    #         return True
    #
    #     if mobj.hasFn(om.MFn.kUnitAttribute):
    #         return True
    #
    #     return False

    # def _asType(self,
    #             typ,
    #             checkSkip=True,
    #             outputOnThisNode=False,
    #             allowUnitConversions=True):
    #
    #     if checkSkip and self.type() == typ:
    #         return self
    #
    #     if outputOnThisNode:
    #         targetNode = self.node()
    #
    #     else:
    #         with r.Name('as{}'.format(cap(typ))):
    #             targetNode = r.nodes.Network.createNode()
    #
    #     if (not allowUnitConversions) and \
    #             (typ in ('doubleLinear',))

        # if outputOnThisNode:
        #     node = self.node()
        #     attrName = '{}_as{}'.format(self.attrName(), cap(typ))
        #
        # else:
        #     with r.Name('as{}'.format(cap(typ))):
        #         node = r.nodes.Network.createNode()
        #
        #     attrName = 'output'
        #
        # if (not allowUnitConversions) and \
        #         (typ in ('doubleLinear', 'doubleAngle')):
        #     node.addAttr('typedInput', at='typed')
        #     self >> node.attr('typedInput')
        #     self = node.attr('typedInput')
        #
        # node.addAttr('output', at=typ)
        # self >> node.attr('output')
        # return node.attr('output')

    # @short(allowUnitConversions='auc')
    # def asDouble(self, allowUnitConversions=True):
    #     return self._asType('double', allowUnitConversions=allowUnitConversions)
    #
    # @short(allowUnitConversions='auc')
    # def asDoubleLinear(self, allowUnitConversions=True):
    #     return self._asType('doubleLinear',
    #                         allowUnitConversions=allowUnitConversions)
    #
    # @short(allowUnitConversions='auc')
    # def asDoubleAngle(self, allowUnitConversions=True):
    #     return self._asType('doubleAngle',
    #                         allowUnitConversions=allowUnitConversions)
    #
    # @short(allowUnitConversions='auc')
    # def asFloat(self, allowUnitConversions=True):
    #     return self._asType('float',
    #                         allowUnitConversions=allowUnitConversions)
    #
    # @short(allowUnitConversions='auc')
    # def asDoubleOrFloat(self,
    #                     allowUnitConversions=True):
    #     if self.type() in ('float', 'double'):
    #         return self
    #
    #     return self._asType('double', checkSkip=False)
    #
    # def asTyped(self):
    #     return self._asType('typed')

    def hasUnits(self):
        """
        :return: ``True`` if this is a linear, angle or time attribute, or
            a compound with any children for which this is ``True``, otherwise
            ``False``.
        :rtype: :class:`bool`
        """
        if self.isMulti(): # to prevent crashes around API calls
            self = self[0]

        if self.isCompound():
            for child in self.getChildren():
                if child.hasUnits():
                    return True

            return False

        mobj = self.__apimplug__().attribute()

        return mobj.hasFn(om.MFn.kUnitAttribute)

    def unitType(self):
        """
        :return: One of 'angle', 'distance', 'time' or ``None``.
        :rtype: :class:`str` | ``None``
        """
        if self.isMulti():
            self = self[0]

        if self.isCompound():
            types = [child.unitType() for child in self.getChildren()]

            if len(set(types)) is 1:
                return types[0]

        else:
            mobj = self.__apimplug__().attribute()

            if mobj.hasFn(om.MFn.kUnitAttribute):
                mfn = om.MFnUnitAttribute(mobj)
                unitType = mfn.unitType()

                if unitType == om.MFnUnitAttribute.kAngle:
                    return 'angle'

                if unitType == om.MFnUnitAttribute.kDistance:
                    return 'distance'

                if unitType == om.MFnUnitAttribute.kTime:
                    return 'time'

    #-----------------------------------------------------------------|    Type management

    # def hasUnit(self):
    #     """
    #     :return: ``True`` if this is an angle, distance or time attribute.
    #     :rtype: :class:`bool`
    #     """
    #     mobj = self.__apimobject__()
    #     return mobj.hasFn(om.MFn.kUnitAttribute)
    #
    # def isTyped(self):
    #     """
    #     :return: ``True`` if this is a 'typed' data attribute, otherwise
    #         ``False``.
    #     :rtype: :class:`bool`
    #     """
    #     mobj = self.__apimobject__()
    #     return mobj.hasFn(om.MFn.kTypedAttribute)
    #
    # def isGeneric(self):
    #     """
    #     :return: ``True`` if this is a 'generic' data attribute, otherwise
    #         ``False``.
    #     :rtype: :class:`bool`
    #     """
    #     mobj = self.__apimobject__()
    #     return mobj.hasFn(om.MFn.kGenericAttribute)
    #
    # def isAngle(self):
    #     """
    #     :return: ``True`` if this is an angle (``doubleAngle``) attribute,
    #         otherwise ``False``.
    #     :rtype: :class:`bool`
    #     """
    #     mobj = self.__apimobject__()
    #     if mobj.hasFn(om.MFn.kUnitAttribute):
    #         mfn = om.MFnUnitAttribute(mobj)
    #         return mfn.unitType() == om.MFnUnitAttribute.kAngle
    #
    #     return False
    #
    # def isDistance(self):
    #     """
    #     :return: ``True`` if this is a distance (``doubleLinear``) attribute,
    #         otherwise ``False``.
    #     :rtype: :class:`bool`
    #     """
    #     mobj = self.__apimobject__()
    #     if mobj.hasFn(om.MFn.kUnitAttribute):
    #         mfn = om.MFnUnitAttribute(mobj)
    #         return mfn.unitType() == om.MFnUnitAttribute.kDistance
    #
    #     return False
    #
    # def isTime(self):
    #     """
    #     :return: ``True`` if this is a time attribute, otherwise ``False``.
    #     :rtype: :class:`bool`
    #     """
    #     mobj = self.__apimobject__()
    #     if mobj.hasFn(om.MFn.kUnitAttribute):
    #         mfn = om.MFnUnitAttribute(mobj)
    #         return mfn.unitType() == om.MFnUnitAttribute.kTime
    #
    #     return False

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

    def plugInfo(self):
        """
        Calls :func:`paya.pluginfo.getInfoFromAttr` on this attribute and
        returns the result.
        """
        return _pi.getInfoFromAttr(self)

    def mathDimension(self):
        """
        :return: The math dimension of this
            plug (e.g. 16 for a matrix), if any.
        :rtype: :class:`int`, :class:`None`
        """
        return self.plugInfo().get('mathDimension')

    @short(inherited='i')
    def plugType(self, inherited=False):
        """
        Returns abstract type information for this plug.

        :param bool inherited/i: return the full hierarchy stack instead
            of just a single type; defaults to False
        :return: The type information.
        :rtype: str or list
        """
        info = _pi.getInfoFromMPlug(self.__apimplug__())
        out = _pi.getPath(info['key'])

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

    @short(recursive='r', force='f')
    def enable(self, recursive=False, force=False):
        """
        Equivalent to:

        .. code-block:: python

            self.show()
            self.unlock()

        See :meth:`show` and :meth:`unlock` for details.
        """
        self.show(r=recursive, f=force)
        self.unlock(r=recursive, f=force)
        return self

    @short(recursive='r')
    def disable(self, recursive=False):
        """
        Equivalent to:

        .. code-block:: python

            self.lock()
            self.hide()

        See :meth:`lock` and :meth:`hide` for details.
        """
        self.lock(recursive=recursive)
        self.hide(recursive=recursive)
        return self

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
        :rtype: :class:`~paya.runtime.plugs.Attribute`
        """
        p.Attribute.lock(self, **kwargs)

        if recursive and self.isCompound():
            for child in self.getChildren():
                p.Attribute.lock(child, **kwargs)

        return self

    @short(recursive='r')
    def hide(self, recursive=False):
        """
        Turns off *keyable* and *channelBox* for this attribute.

        :param bool recursive/r: if this is a compound, edit the children too;
            defaults to False
        :return: ``self``
        :rtype: :class:`~paya.runtime.plugs.Attribute`
        """
        if self.get(k=True):
            self.set(k=False)

        elif self.get(cb=True):
            self.set(cb=False)

        if recursive and self.isCompound():
            for child in self.getChildren():
                if child.get(k=True):
                    child.set(k=False)

                elif child.get(cb=True):
                    child.set(cb=False)

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
        :rtype: :class:`~paya.runtime.plugs.Attribute`
        """
        p.Attribute.unlock(self, **kwargs)

        if force and self.isChild():
            parent = self.getParent()

            if parent.isLocked():
                parent.unlock()

                for child in parent.getChildren():
                    if child == self:
                        continue

                    else:
                        child.lock()

        elif recursive and self.isCompound():
            for child in self.getChildren():
                p.Attribute.unlock(child)

        return self

    @short(recursive='r', keyable='k', force='f')
    def show(self, recursive=False, force=False, keyable=True):
        """
        Unhides this attribute in the channel box.

        :param bool recursive/r: if this is a compound, edit the children
            as well; defaults to False
        :param bool force/f: if this is the child of a compound, edit the
            parent attribute too; defaults to False
        :param bool keyable/k: reveal by making the attribute keyable; if this
            is False, the attribute will be made settable instead; defaults
            to True
        :return: ``self``
        :rtype: :class:`~paya.runtime.plugs.Attribute`
        """
        if keyable:
            self.set(k=True)

        else:
            self.set(k=False)
            self.set(cb=True)

        if recursive and self.isCompound():
            for child in self.getChildren():
                child.show(k=keyable)

        elif force and self.isChild():
            parent = self.getParent()

            if not(parent.get(k=True) or parent.get(cb=True)):
                parent.show(k=keyable)

                for child in parent.getChildren():
                    if child == self:
                        continue

                    child.hide()

        return self

    @short(recursive='r', force='f')
    def release(self, recursive=False, force=False):
        """
        Unlocks this attribute and disconnects any inputs.

        :param bool force/f: if this is the child of a compound, release
            the parent too; defaults to False
        :param bool recursive/r: if this is a compound, release child
            attributes too; defaults to False
        :return:
        """
        self.unlock(f=force, r=recursive)
        self.disconnect(inputs=True)

        if force and self.isChild():
            parent = self.getParent()

            if parent.inputs():
                parent.release()

        elif recursive and self.isCompound():
            for child in self.getChildren():
                if child == self:
                    continue

                child.disconnect(inputs=True)

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

    def sendAbove(self, attrName):
        """
        Sends this attribute above another attribute in the channel box.

        :param str attrName: the name of the 'anchor' attribute
        :return: This attribute, rebuilt.
        :rtype: :class:`~paya.runtime.plugs.Attribute`
        """
        thisName = self.attrName(longName=True)
        node = self.node()
        allAttrNames = node.getReorderableAttrNames()
        allAttrNames.remove(thisName)
        targetIndex = allAttrNames.index(attrName)
        head = allAttrNames[:targetIndex]
        tail = allAttrNames[targetIndex:]
        fullList = [head] + [thisName] + [tail]
        _atr.reorder(node, fullList)
        return node.attr(thisName)

    def sendBelow(self, attrName):
        """
        Sends this attribute below another attribute in the channel box.

        :param str attrName: the name of the 'anchor' attribute
        :return: This attribute, rebuilt.
        :rtype: :class:`~paya.runtime.plugs.Attribute`
        """
        thisName = self.attrName(longName=True)
        node = self.node()
        allAttrNames = node.getReorderableAttrNames()
        allAttrNames.remove(thisName)
        targetIndex = allAttrNames.index(attrName)

        head = allAttrNames[:targetIndex+1]
        tail = allAttrNames[targetIndex+1:]
        fullList = [head] + [thisName] + [tail]
        _atr.reorder(node, fullList)
        return node.attr(thisName)

    #-----------------------------------------------------------------|    Extended iteration

    def __iter__(self):
        if self.isMulti():
            for i in self._getArrayIndices()[1]:
                yield self[i]
        elif self.isCompound():
            for child in self.getChildren():
                yield child

        else:
            raise TypeError(("{} is not a multi-attribute "+
                            "and cannot be iterated over.").format(self))

    #-----------------------------------------------------------------|    Array (multi) attributes

    @short(fillGaps='fg')
    def getNextArrayIndex(self, fillGaps=False):
        """
        Returns the next available logical array index.

        :param bool fillGaps/fg: return the first available gap in the
            logical array indices; defaults to False
        :return: The index.
        :rtype: int
        """
        indices = self.getArrayIndices()

        if indices:
            if fillGaps:
                for i, index in enumerate(indices):
                    if index > i:
                        return i

            return indices[-1]+1

        return 0