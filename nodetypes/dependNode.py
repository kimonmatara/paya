import pymel.util as _pu
from paya.util import short, resolveFlags
import paya.lib.names as _nm
import paya.runtime as r


class MakeName(object):

    def __get__(self, inst, instype):

        @short(name='n')
        def makeName(*elems, name=None):
            """
            Generates a context-appropriate Maya name. Results will vary
            depending on whether this method is called on a class or on a
            node instance.

            Construction is determined by the following keys inside :mod:`paya.config`:
            ``inheritNames``, ``padding``, ``suffixNodes``.

            Settings can be overriden using :class:`~paya.override.Override`.

            :param \*elems: one or more name elements
            :param name/n: elements contributed via ``name`` keyword
                arguments; these will always be prepended; defaults to None
            :type name/n: None, str, int, or list
            :return: The node name.
            :rtype: str
            """
            kwargs = {}

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

    #-----------------------------------------------------------|    Attr management

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
        :rtype: :class:`~paya.nodetypes.dependNode.DependNode`
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
            attr.show()
            attr.unlock(f=True)

        for name in channelBox:
            attr = self.attr(name)
            attr.show(cb=True)
            attr.unlock(f=True)

        return self