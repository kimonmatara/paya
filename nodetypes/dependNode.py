import pymel.util as _pu
import paya.lib.names as _nm
import paya.lib.attrs as _atr
from paya.util import short, resolveFlags, LazyModule, undefined
import paya.pools as _pl
import paya.lib.names as _nm
import maya.cmds as m
import maya.OpenMaya as om

r = LazyModule('paya.runtime')

class MakeName:

    def __get__(self, inst, instype):

        @short(inherit='i',
               padding='pad',
               suffix='suf')
        def makeName(*elems,
                     inherit=undefined,
                     padding=undefined,
                     suffix=undefined):
            """
            Constructs a node name based on :class:`~paya.lib.names.Name`
            contexts. Results will vary depending on whether this method is
            called on:

            -  A class
            -  A transform instance with a controller tag
            -  A transform instance with shapes
            -  A transform instance without shapes
            -  A shape instance
            -  Any other kind of node instance

            :alias: ``mn``
            :return: The constructed node name.
            :rtype: :class:`str`
            """
            kw = {'padding': padding, 'inherit': inherit, 'suffix': suffix}

            if inst is None:
                kw['nodeType'] = instype.__melnode__

            else:
                nts = inst.nodeType(i=True)

                if 'transform' in nts:
                    if inst.isControl():
                        kw['control'] = True

                    else:
                        shapes = inst.getShapes()

                        if shapes:
                            kw['nodeType'] = shapes[0].nodeType()
                            kw['transform'] = True

                        else:
                            kw['nodeType'] = nts[-1]

                else:
                    kw['nodeType'] = nts[-1]

            return _nm.Name.make(*elems, **kw)

        return makeName


class DependNode:

    #-----------------------------------------------------------|    Subtype management

    @classmethod
    def getSubtypePool(cls):
        try:
            return _pl.poolsByLongName[cls.__melnode__+'types']

        except KeyError:
            pass

    def setSubtype(self, clsname):
        """
        Initialises and populates the ``payaSubtype`` attribute.

        .. note::

            This does not modify class assignment. To switch to the specified
            type, follow this up with :meth:`asSubtype`.

        :param str clsname: the subtype class name
        :return: ``self``
        :rtype: :class:`DependNode`
        """
        if not self.hasAttr('payaSubtype'):
            self.addAttr('payaSubtype', dt='string')

        attr = self.attr('payaSubtype')
        attr.set(clsname)

        return self

    def getSubtype(self):
        """
        :return: The contents of the ``payaSubtype`` attribute, if present and
            populated, otherwise ``None``.
        :rtype: :class:`str`, ``None``
        """
        if self.hasAttr('payaSubtype'):
            attr = self.attr('payaSubtype')
            out = attr.get()

            if out:
                return out

    def getSubtypeClass(self, *name):
        """
        If this node has a configured ``payaSubtype`` attribute, and a
        subtypes pool is defined for this node type, attempts to retrieve
        the class.

        If the operation fails, explanatory warnings are issued and ``None``
        is returned.

        :param str \*name: an optional override for the class name; if
            provided, no attempt will be made to access the ``payaSubtype``
            attribute
        :return: The custom class, if one could be retrieved.
        :rtype: :class:`type`, ``None``
        """
        pool = self.getSubtypePool()

        if pool is None:
            m.warning(("Subclassing {}: No subtypes pool for node type '{}'."
                       ).format(self, self.__melnode__))

            return

        if name:
            clsname = name[0]

        else:
            clsname = self.getSubtype()

        if clsname is None:
            m.warning("Subclassing {}: Undefined subtype.".format(self))

        try:
            return pool.getByName(clsname)

        except _pl.MissingTemplateError:
            m.warning(("Subclassing {}: Class '{}' could not be retrieved."
                       ).format(self, clsname))

    def asSubtype(self, *name):
        """
        If this node has a configured ``payaSubtype`` attribute, and a
        subtypes pool is defined for this node type, attempts to retrieve
        the class and assign it to this instance.

        This is an in-place operation, but ``self`` is returned for
        convenience. If the operation fails, explanatory warnings are issued
        and reassignment is skipped.

        :param str \*name: an optional override for the class name; if
            provided, no attempt will be made to access the ``payaSubtype``
            attribute
        :return: ``self``
        :rtype: :class:`DependNode`
        """
        cls = self.getSubtypeClass(*name)

        if cls is not None:
            self.__class__ = cls

        return self

    #-----------------------------------------------------------|    Name management

    makeName = mn = MakeName()

    def rename(self, *name, **kwargs):
        """
        Overloads :meth:`pymel.core.nodetypes.DependNode.rename` to
        turn *name* into an optional argument.

        :param \*name: the name to use; if omitted, defaults to a contextual
            name
        :param \*\*kwargs: forwarded to
            :meth:`pymel.core.nodetypes.DependNode.rename`
        :return: ``self``
        :rtype: :class:`DependNode`
        """
        if name:
            name = name[0]

        if not name:
            name = self.makeName()

        result = super(r.nodes.DependNode, self).rename(name, **kwargs)

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

    #-----------------------------------------------------------|    Duplication

    @short(name='n')
    def duplicate(self, name=None, **kwargs):
        """
        Overloads :meth:`pymel.core.nodetypes.DependNode.duplicate` to add a
            contextual default to *name/n*.

        :param str name/n: a name for the duplicate; defaults to a contextual
            name
        :param \*\*kwargs: forwarded to
            :meth:`pymel.core.nodetypes.DependNode.duplicate`
        :return: The duplicate node.
        :rtype: :class:`DependNode`
        """
        if not name:
            name = self.makeName()

        return super(r.nodes.DependNode, self).duplicate(n=name, **kwargs)

    #-----------------------------------------------------------|    Constructors

    @classmethod
    @short(name='n')
    def createNode(cls, name=None, **kwargs):
        """
        Object-oriented version of :func:`pymel.core.general.createNode`.

        :param str name/n: a name for the new node; defaults to a contextual
            name
        :param \*kwargs: forwarded to :func:`pymel.core.general.createNode`
        :return: The node.
        :rtype: :class:`DependNode`
        """
        node = r.createNode(
            cls.__melnode__,
            name=name if name else cls.makeName(),
            **kwargs)

        if cls.__is_subtype__:
            node.setSubtype(cls.__name__)
            node.asSubtype(cls.__name__)

        return node

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

    #-----------------------------------------------------------|    Control management

    def isControl(self, *state): # Overloaded on DAG node
        """
        :param bool \*state: if ``True``, make this node a controller; if
            ``False``, remove any controller tags; if omitted, return whether
            this node is a controller
        :raises NotImplementedError: The control state can't be edited on non-
            DAG nodes.
        :return: bool or None
        """
        if len(state):
            if state[0]:
                raise NotImplementedError(
                    "The control state of non-DAG nodes can't be edited."
                )

            return

        return False

    #-----------------------------------------------------------|    Attr management

    def _addVectorOrEulerAttr(
            self,
            name,
            suffixes='XYZ',
            angle=False,
            keyable=None,
            channelBox=None,
            defaultValue=None,
            input=None,
            lock=False,
            multi=False
    ):
        if keyable is None and channelBox is None:
            keyable = True
            channelBox = False

        elif keyable is None:
            keyable = not channelBox

        else:
            channelBox = not keyable

        kw = {}

        if keyable:
            kw['k'] = True

        if multi:
            if input is None:
                kw['multi'] = True

            else:
                raise ValueError(
                    "An input can't be provided if "+
                    "the attribute is a multi."
                )

        self.addAttr(name, at='double3', nc=3, **kw)

        kw = {'at': 'doubleAngle' if angle else 'double', 'parent': name}

        if keyable:
            kw['k'] = True

        for i, suffix in enumerate(suffixes):
            if defaultValue is not None:
                kw['defaultValue'] = defaultValue[i]

            self.addAttr(name+suffix, **kw)

        main = self.attr(name)

        if input is not None:
            input >> main

        if not multi:
            if channelBox:
                main.set(cb=True)

                for child in main.getChildren():
                    child.set(cb=True)

            if lock:
                main.lock(recursive=True)

        return main

    @short(
        keyable='k',
        channelBox='cb',
        input='i',
        defaultValue='dv',
        lock='l',
        multi='m'
    )
    def addVectorAttr(
            self,
            name,
            keyable=None,
            channelBox=None,
            input=None,
            defaultValue=None,
            lock=False,
            multi=False
    ):
        """
        :param name: the attribute name
        :param bool keyable/k: make the attribute keyable; defaults to True
        :param bool channelBox/cb: make the attribute settable; defaults to
            False
        :param bool multi/m: create a multi (array) attribute; defaults to
            False
        :param input/i: an optional input for the attribute, if it's not a
            multi
        :type input/i: str, :class:`~paya.runtime.plugs.Vector`
        :param defaultValue/dv: an optional default value for the attribute;
            defaults to [0.0, 0.0, 0.0]
        :type defaultValue/dv: list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`
        :param bool lock/l: lock the attribute; defaults to False
        :return: A vector / point attribute (i.e., a compound of type
            ``double3`` with children of type ``double``).
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self._addVectorOrEulerAttr(
            name, keyable=keyable,
            channelBox=channelBox,
            input=input,
            defaultValue=defaultValue,
            lock=lock,
            multi=multi
        )

    @short(
        keyable='k',
        channelBox='cb',
        input='i',
        defaultValue='dv',
        lock='l',
        multi='m'
    )
    def addEulerAttr(
            self,
            name,
            keyable=None,
            channelBox=None,
            input=None,
            defaultValue=None,
            lock=False,
            multi=False
    ):
        """
        :param name: the attribute name
        :param bool keyable/k: make the attribute keyable; defaults to True
        :param bool channelBox/cb: make the attribute settable; defaults to
            False
        :param bool multi/m: create a multi (array) attribute; defaults to
            False
        :param input/i: an optional input for the attribute
        :type input/i: str, :class:`~paya.runtime.plugs.Vector`
        :param defaultValue/dv: an optional default value for the attribute;
            defaults to [0.0, 0.0, 0.0]
        :type defaultValue/dv: list, tuple,
            :class:`~paya.runtime.data.EulerRotation`
        :param bool lock/l: lock the attribute; defaults to False
        :return: An euler rotation attribute (i.e., a compound of type
            ``double3`` with children of type ``doubleAngle``)
        :rtype: :class:`~paya.runtime.plugs.EulerRotation`
        """
        return self._addVectorOrEulerAttr(
            name, keyable=keyable,
            channelBox=channelBox,
            input=input,
            defaultValue=defaultValue,
            lock=lock,
            angle=True,
            multi=multi
        )

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