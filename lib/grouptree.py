from paya.lib.suffixes import suffixes
from paya.util import short
import paya.runtime as r


class GroupTree:
    """
    Group trees are dict-like interfaces for quick generation of hierarchical
    group structures with cascading prefixes.

    :Example:

    .. code-block:: python

        import paya.runtime as r
        from paya.lib.grouptree import GroupTree

        with r:
            group = r.PyNode('L_arm_XFRM')
            tree = GroupTree(group)

            print(tree['controls']['shapers'].node())
            # Result: L_arm_controls_shapers_XFRM
    """

    #---------------------------------------------------|    Instantiation

    def __init__(self, *node, owner=None, key=None):
        if node:
            self._node = r.PyNode(node[0])

        elif not (owner and key):
            raise RuntimeError("Either 'node', or an "+
                "'owner' and 'key', must be provided.")

        else:
            self._node = None

        self._owner = owner
        self._key = key

    #---------------------------------------------------|    Navigation

    def __getitem__(self, key):
        return GroupTree(owner=self, key=key)

    #---------------------------------------------------|    Inspections

    def root(self):
        """
        :return: The root :class:`GroupTree` instance.
        :rtype: :class:`GroupTree`.
        """
        current = self

        while True:
            if current._owner is None:
                return current

            current = current._owner

    def keyPath(self):
        """
        :return: All the keys leading up to this node.
        :rtype: [:class:`str`]
        """
        out = []
        current = self

        while True:
            if current._key is None:
                break

            out.append(current._key)

            if current._owner is None:
                break

            current = current._owner

        return out[::-1]

    #---------------------------------------------------|    Actualisation

    @short(inheritsTransform='it', hide='h', create='c')
    def node(self, inheritsTransform=None, hide=None, create=True):
        """
        :param bool inheritsTransform/it: sets ``inheritsTransform`` on the
            node; defaults to ``None``
        :param bool create/c: create the group node if it doesn't exist;
            defaults to ``True``
        :param bool hide/h: hide the node; defaults to ``None``
        :return: The transform node at the current key.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        if self._node is None:
            rootNode = self.root().node()
            elems = []
            bn = rootNode.basename(sts=True)

            if bn:
                elems.append(bn)

            elems += self.keyPath()
            suffix = suffixes.get('transform')

            if suffix:
                elems.append(suffix)

            name = '_'.join(elems)
            dagPath = rootNode.longName() + '|' + name

            if not create:
                if not r.objExists(dagPath):
                    return

            self._node = r.nodes.Transform.create(dagPath=dagPath)

        if inheritsTransform is not None:
            self._node.attr('inheritsTransform').set(inheritsTransform)

        if hide is not None:
            if hide:
                r.hide(self._node)

            else:
                r.showHidden(self._node)

        return self._node

    #---------------------------------------------------|    Repr

    def __repr__(self):
        return "{}(key={}, owner={})".format(
            self.__class__.__name__,
            repr(self._key),
            repr(self._owner)
        )