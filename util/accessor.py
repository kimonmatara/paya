import pymel.core as p


class Accessor:
    """
    Utility class for nested interfaces.
    """

    #-------------------------------------------------------|    Instantiation

    def __init__(self, owner, name):
        self.owner = owner
        self.name = name

    #-------------------------------------------------------|    Repr

    def __repr__(self):
        return '{}.{}'.format(repr(self.owner), self.name)


class AccessorOnNode(Accessor):
    """
    Subclass of :class:`Accessor` with a few extra facilitiations for node-
    level interfaces.
    """

    def __init__(self, owner, attrName):
        self.owner = p.PyNode(owner)
        self.name = attrName

    def node(self):
        """
        :return: The owner node.
        :rtype: :class:`~paya.runtime.nodes.DependNode`
        """
        return self.owner