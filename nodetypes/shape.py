import paya.runtime as r


class Shape:

    @classmethod
    def createNode(cls, **nameOptions):
        """
        Object-oriented version of :func:`pymel.core.general.createNode` with
        managed naming.

        :param \*\*nameOptions: passed-through to :meth:`~DependNode.makeName`
        :return: The constructed node.
        :rtype: :class:`DependNode`
        """
        shape = r.createNode(cls.__melnode__)
        xf = shape.getParent()
        xf.rename(cls.makeName(**nameOptions))

        return shape