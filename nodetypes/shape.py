from paya.util import short
import paya.runtime as r


class Shape:

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
        shape = r.createNode(cls.__melnode__)
        xf = shape.getParent()
        xf.rename(cls.makeName(name))

        return shape