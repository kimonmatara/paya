from paya.util import short
import paya.runtime as r


class Shape:

    #-----------------------------------------------------------|    Abstract I/O

    @property
    def geoInput(self):
        raise NotImplementedError

    @property
    def worldGeoOutput(self):
        raise NotImplementedError

    @property
    def localGeoOutput(self):
        raise NotImplementedError

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

    #--------------------------------------------------------|    Shape / transform management

    def toShape(self):
        """
        :return: If this node is a transform, its first shape child;
            otherwise, the node itself.
        :rtype: :class:`~paya.runtime.nodes.Shape` or
            :class:`~paya.runtime.nodes.Transform`
        """
        return self

    def toTransform(self):
        """
        :return: If this node is a shape, its parent; otherwise, the node
            itself.
        :rtype: :class:`~paya.runtime.nodes.Shape` or
            :class:`~paya.runtime.nodes.Transform`
        """
        return self.getParent()