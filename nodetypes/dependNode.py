from paya.util import short
import paya.lib.names as _nm
import paya.runtime as r


class MakeName(object):

    def __get__(self, inst, instype):

        @short(
            name='n',
            inheritName='inn',
            suffix='suf'
        )
        def makeName(
                *elems,
                name=None,
                inheritName=True,
                suffix=None
        ):
            """
            Generates a context-appropriate Maya name. Results will vary
            depending on whether this method is called on a class or on a
            node instance.

            :param \*elems: one or more name elements
            :param name/n: elements contributed via ``name`` keyword
                arguments; these will always be prepended; defaults to None
            :type name/n: None, str, int, or list
            :param suffix/suf: if string, append; if ``True``, look up a type
                suffix and apply it; if ``False``, omit; defaults to
                :attr:`~paya.config.autoSuffix`
            :type suffix/suf: None, bool, str
            :param bool inheritName/inn: inherit names from
                :class:`~paya.lib.names.Name` blocks; defaults to True
            :return: The node name.
            :rtype: str
            """
            kwargs = {'inheritName': True, 'name': name, 'suffix': suffix}

            if inst:
                kwargs['node'] = inst

            else:
                kwargs['nodeType'] = instype.__melnode__

            return _nm.make(*elems, **kwargs)


class DependNode:

    makeName = MakeName()

    #-----------------------------------------------------------|    Constructors

    @classmethod
    @short(name='n', suffix='suf', inheritName='inn')
    def createNode(cls, name=None, suffix=None, inheritName=True):
        """
        Object-oriented version of :func:`pymel.core.general.createNode` with
        managed naming.

        :param name/n: one or more name elements; defaults to None
        :type name/n: None, str, int, or list
        :param suffix/suf: if string, append; if ``True``, look up a type
            suffix and apply it; if ``False``, omit; defaults to
            :attr:`~paya.config.autoSuffix`
        :type suffix/suf: None, bool, str
        :param bool inheritName/inn: inherit names from
            :class:`~paya.lib.names.Name` blocks; defaults to True
        :return: The constructed node.
        :rtype: :class:`~pymel.core.general.PyNode`
        """
        return r.createNode(
            cls.__melnode__,
            n=cls.makeName(n=name, suf=suffix, inn=inheritName)
        )