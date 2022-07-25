from paya.util import short
import paya.runtime as r


class Shape:

    #-----------------------------------------------------------|    Constructors

    @classmethod
    @short(
        name='n',
        under='u',
        conformShapeNames='csn',
        intermediate='i'
    )
    def createShape(
            cls,
            name=None,
            under=None,
            conformShapeNames=True,
            intermediate=False
    ):
        """
        Basic shape constructor.

        :param name/n: one or more name elements; defaults to None
        :type name/n: None, tuple, list, str, int
        :param under/u: a custom destination parent; defaults to None
        :type under/u: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool conformShapeNames/csn: ignored if *under* was omitted;
            conform destination shape names after reparenting; defaults to
            True
        :param bool intermediate/i: create the shape as an intermediate
            object; defaults to False
        :return: The shape node.
        :rtype: :class:`Shape`
        """
        shape = cls.createNode(n=name)
        parent = shape.getParent()

        if under:
            newParent = r.PyNode(under)
            r.parent(shape, newParent, r=True, shape=True)
            r.delete(parent)

            if conformShapeNames:
                newParent.conformShapeNames()

        if intermediate:
            shape.attr('intermediateObject').set(True)

        return shape

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