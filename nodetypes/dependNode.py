import pymel.util as _pu
import paya.lib.names as _nm
import paya.lib.attrs as _atr
from paya.util import short, resolveFlags
import paya.lib.names as _nm
import paya.runtime as r


class MakeName(object):

    def __get__(self, inst, instype):
        @short(name='n', control='ct')
        def makeName(*elems, name=None, control=False):
            """
            Generates a context-appropriate Maya name. Results will vary
            depending on whether this method is called on a class or on a
            node instance.

            Construction is determined by the following keys inside
            :mod:`paya.config`: ``inheritNames``, ``padding``,
            ``suffixNodes``. Use the context manager functionality of
            :mod:`paya.config` to override for specific blocks.

            :param \*elems: one or more name elements
            :param name/n: elements contributed via ``name`` keyword
                arguments; these will always be prepended; defaults to None
            :type name/n: None, str, int, or list
            :param bool control/ct: use the Paya suffix for controls;
                defaults to False
            :return: The node name.
            :rtype: str
            """
            kwargs = {}

            if control:
                kwargs['control'] = True

            else:
                if inst:
                    kwargs['node'] = inst

                else:
                    kwargs['nodeType'] = instype.__melnode__

            return _nm.make(name, *elems, **kwargs)

        return makeName


class DependNode:

    #-----------------------------------------------------------|    Name management

    makeName = MakeName()

    @short(stripNamespace='sns', stripTypeSuffix='sts')
    def basename(self, stripNamespace=False, stripTypeSuffix=False):
        """
        Returns shorter versions of this node's name.

        :param bool stripNamespace/sns: remove namespace information; defaults to
            False
        :param bool stripTypeSuffix/sts: removes anything that looks like a type
            suffix; defaults to False
        :return: the modified name
        :rtype: str
        """
        return _nm.shorten(str(self), sns=stripNamespace, sts=stripTypeSuffix)

    bn = basename

    #-----------------------------------------------------------|    Constructors

    @classmethod
    @short(name='n')
    def createNode(cls, name=None):
        """
        Object-oriented version of :func:`pymel.core.general.createNode` with
        managed naming.

        :param name/n: one or more name elements; defaults to None
        :type name/n: None, str, int, or list
        :return: The constructed node.
        :rtype: :class:`~pymel.core.general.PyNode`
        """
        name = cls.makeName(name)
        return r.createNode(cls.__melnode__, n=name)

    @classmethod
    def createFromMacro(cls, macro, **overrides):
        """
        Basic :class:`DependNode` implementation; uses :meth:`createNode`.

        :param dict macro: the macro to use
        :param \*\*overrides: one or more overrides to the macro dict,
            passed-in as keyword arguments
        :return: The constructed node.
        :rtype: :class:`DependNode`
        """
        nodeType = macro['nodeType']

        if nodeType != cls.__melnode__:
            cls = getattr(r.nodes, nodeType[0].upper()+nodeType[1:])
            return cls.createFromMacro(macro, **overrides)

        macro = macro.copy()
        macro.update(overrides)
        nodeType = macro['nodeType']
        name = macro['name']
        return r.createNode(nodeType, n=name)

    def macro(self):
        """
        Basic :class:`DependNode` implementation; includes merely the node
        name and node type.

        :return: This node's name and type in a dictionary.
        :rtype: dict
        """
        return {'name': str(self), 'nodeType': self.__melnode__}

    #-----------------------------------------------------------|    Attr management

    @property
    def attrSections(self):
        return _atr.Sections(self, 'attrSections')

    @short(edit='e', query='q', channelBox='cb')
    def addAttr(self, attrName, channelBox=None, **kwargs):
        """
        Overloads :meth:`~pymel.core.nodetypes.DependNode.addAttr` to add the
        ``channelBox/cb`` option and to return ``self``. ``None`` will be
        returned if compound children are not yet completely specified.

        :param str attrName: the attribute name
        :param bool channelBox/cb: when in create mode, create the attribute
            as settable instead of keyable; defaults to None
        :param \*\*kwargs: forwarded to
            :meth:`~pymel.core.nodetypes.DependNode.addAttr`
        :return: Where possible, the newly-created attribute.
        :rtype: None, :class:`~paya.runtime.plugs.Attribute`
        """
        result = r.nodetypes.DependNode.addAttr(self, attrName, **kwargs)

        if 'query' in kwargs or 'edit' in kwargs:
            return result

        try:
            plug =  self.attr(attrName)

            if channelBox:
                plug.set(k=False)
                plug.set(cb=True)

                if plug.isCompound():
                    for child in plug.getChildren():
                        child.set(k=False)
                        child.set(cb=True)

            return plug

        except r.MayaAttributeError:
            return None

    @short(keyable='k', channelBox='cb')
    def maskAnimAttrs(self, *args, keyable=None, channelBox=None):
        """
        Selectively enables attributes of interest to animators. Useful for
        control configuration.

        :param \*args: names of attributes to set to keyable
        :param keyable/k: names of attributes to set to keyable; defaults to
            None
        :type: keyable/k: None, tuple, list, str
        :param channelBox/cb: names of attributes to set to settable; defaults
            to None
        :type channelBox/cb: None, tuple, list, str
        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.DependNode`
        """
        if keyable:
            keyable = list(_pu.expandArgs(keyable))

        else:
            keyable = []

        if args:
            args = list(_pu.expandArgs(*args))
            keyable = args + keyable

        if channelBox:
            channelBox = list(_pu.expandArgs(channelBox))

        else:
            channelBox = []

        # Disable attributes

        if isinstance(self, r.nodetypes.DagNode):
            v = self.attr('v')
            v.hide()
            v.lock()

            if isinstance(self, r.nodetypes.Transform):
                for name in ['t','r','s','ro']:
                    attr = self.attr(name)
                    attr.hide(r=True)
                    attr.lock(r=True)

        for attr in filter(
            lambda x: x.isAnimatableDynamic(),
            self.listAttr(ud=True)
        ):
            attr.hide(r=True)

        # Selectively enable requested attributes

        for name in keyable:
            attr = self.attr(name)
            attr.show(r=True, f=True)
            attr.unlock(r=True, f=True)

        for name in channelBox:
            attr = self.attr(name)
            attr.show(r=True, f=True, k=False)
            attr.unlock(r=True, f=True)

        return self

    def reorderAttrs(self, *attrNames, above=None, below=None):
        """
        Reorders attributes on this node. The attributes must be dynamic
        (not 'factory' Maya attributes like translateX), animatable (i.e. not
        matrix, string etc) and not compounds or multis. Lock states are
        dodged and connections are preserved.

        :param attrNames: attribute names in the preferred order
        :type attrNames: list of str
        :param above/ab: the name of an attribute above which to insert
            the attributes; defaults to None
        :type above/ab: None, str
        :param below/bl: the name of an attribute below which to insert
            the attributes; defaults to None
        :return: list of :class:`~paya.runtime.plugs.Attribute`
        """
        attrNames = list(_pu.expandArgs(*attrNames))

        if above or below:
            allAttrNames = self.getReorderableAttrNames()

            for attrName in attrNames:
                allAttrNames.remove(attrName)

            anchorIndex = allAttrNames.index(above if above else below)

            if above:
                head = allAttrNames[:anchorIndex]
                tail = allAttrNames[anchorIndex:]

            else:
                head = allAttrNames[:anchorIndex+1]
                tail = allAttrNames[anchorIndex+1:]

            attrNames = head + attrNames + tail

        return _atr.reorder(self, attrNames)

    def getReorderableAttrs(self):
        """
        :return: Attributes on this node that can be reordered.
        :rtype: list of str
        """
        return filter(
            lambda x: x.isAnimatableDynamic() and \
                    x.get(k=True) or x.get(cb=True),
            self.listAttr(ud=True)
        )

    def getReorderableAttrNames(self):
        """
        :return: The names of attributes on this node that can be reordered
            using :meth:`reorderAttrs` and related methods.
        :rtype: list of str
        """
        return [attr.attrName(
            longName=True) for attr in self.getReorderableAttrs()]

    def addSectionAttr(self, sectionName):
        """
        Adds a 'section' enum attribute.

        :param str sectionName: the name of the section
        :return: The 'section' enum attribute.
        :rtype: :class:`~paya.runtime.plugs.Enum`
        """
        attrName = _nm.legalise(sectionName).upper()

        self.addAttr(
            attrName,
            at='enum',
            k=False,
            enumName=_atr.__section_enum__
        )

        plug = self.attr(attrName)
        plug.set(cb=True)
        plug.lock()

        return plug

    def getSectionAttrs(self):
        """
        :return: A list of 'section' attributes on this node.
        :rtype: list of :class:`~paya.runtime.plugs.Enum`
        """
        return list(filter(
            lambda x: x.isSectionAttr(), self.listAttr(ud=True)))

    def getAttrSectionMembership(self):
        """
        :return: A zipped mapping of *section name: member attributes*.
        :rtype: list of tuple
        """
        out = []

        for attr in self.getReorderableAttrs():
            if attr.isSectionAttr():
                out.append((attr.attrName(), []))

            elif out:
                out[-1][-1].append(attr)

        return out