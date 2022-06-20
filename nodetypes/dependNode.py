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

            Construction is determined by the following keys inside
                :mod:`paya.config`: ``inheritNames``, ``padding``,
                ``suffixNodes``

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

            return _nm.make(*elems, **kwargs)

        return makeName


class DependNode:

    makeName = MakeName()

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
        return r.createNode(cls.__melnode__, n=cls.makeName(name))