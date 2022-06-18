from paya.util import short
import paya.runtime as r


class Shape:

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
        shape = r.createNode(cls.__melnode__)
        xf = shape.getParent()
        xf.rename(cls.makeName(n=name, suf=suffix, inn=inheritName))

        return shape