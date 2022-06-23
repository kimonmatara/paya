from paya.util import short
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