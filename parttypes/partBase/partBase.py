import re

from pymel.util import expandArgs
from paya.trunk import Trunk
from paya.util import short, resolveFlags, uncap
from paya.lib.grouptree import GroupTree
import paya.runtime as r


class PartBase(Trunk):
    """
    Abstract base class for :class:`~paya.runtime.parts.Part` and
    :class:`~paya.runtime.parts.PartGuide`.
    """
    __suffix__ = 'PART'
    __type_attr_name__ = 'partType'

    #-----------------------------------------------------|    Instantiation

    def __new__(cls, groupNode):
        if cls is r.parts.Part:
            groupNode = r.PyNode(groupNode)

            if groupNode.hasAttr(cls.__type_attr_name__):
                attr = groupNode.attr(cls.__type_attr_name__)
                clsname = attr.get()

                if clsname:
                    try:
                        cls = getattr(r.parts, clsname)
                    except:
                        r.warning(
                            ("Couldn't source custom class '{}', defaulting"+
                             " to Part.").format(clsname)
                        )
                else:
                    r.warning(("Empty '{}' tag on {}, defaulting to Part."
                               ).format(cls.__type_attr_name__, groupNode))
            else:
                r.warning(("No part type information on"+
                           " {}, defaulting to Part.").format(groupNode))

        return object.__new__(cls)

    def __init__(self, groupNode):
        self._node = r.PyNode(groupNode)

    #-----------------------------------------------------|    Construction

    @r.partCreator
    def create(self):
        """
        Stub constructor.

        :return: A fully configured empty part.
        :rtype: :class:`Part`
        """
        pass

    @classmethod
    def createNode(cls):
        """
        Creates the basic transform (group) node for the part.

        :return: The initialised group node.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        with r.Name(suffix=cls.__suffix__):
            node = r.nodes.Transform.createNode()

        node.addAttr(cls.__type_attr_name__, dt='string')
        node.attr(cls.__type_attr_name__).set(cls.__name__)

        return node

    @classmethod
    def _getCreateNameContext(cls):
        """
        Called before a build wrapped by
        :func:`~paya.part.partcreator.partCreator` to establish the naming
        environment.

        :return: A configured context manager.
        :rtype: :class:`~paya.lib.names.Name`
        """
        raise NotImplementedError

    def _postCreate(self):
        """
        Called at the end of a build wrapped by
        :func:`~paya.part.partcreator.partCreator`.

        The base implementation does the following:

        -   Automatically configures visibility attributes for
            ``joints`` and ``controls`` first-level subgroups
        """
        node = self.node()

        for basename, val in zip(
            ['controls', 'joints'],
            [True, False]
        ):
            gp = self.tree[basename].node(create=False)

            if gp is None:
                continue

            src = node.addAttr('{}Vis'.format(basename),
                               at='bool', cb=True, dv=val)
            src >> gp.attr('v')

    def getCreateArgsKwargs(self):
        """
        :raises NotImplementedError: Not implemented on this class.
        :return: The positional and keyword arguments required to recreate
            this part / guide with the same configuration.
        :rtype: (:class:`tuple`, :class:`dict`)
        """
        raise NotImplementedError

    # Stub: finish this
    # @classmethod
    # @short(namespace='ns')
    # def reference(cls, namespace=None):
    #     """
    #     References-in the ``<uncapitalized class name>.ma`` dependency from
    #     the :class:`trunk <paya.trunkTrunk>` directories.
    #
    #     :param str namespace/ns: a namespace for the reference; if omitted, one
    #         will be auto-derived
    #     :return: A :class:`~paya.runtime.parts.Part` instance for the first
    #         detected part in the referenced scene.
    #     :rtype: :class:`~paya.runtime.parts.Part`
    #     """
    #     found = cls.findFile('{}.ma'.format(uncap(cls.__name__)))
    #
    #     if found:
    #         path = found.as_posix()
    #
    #         if namespace is None:
    #             namespace =
    #
    #     raise NotImplementedError

    #-----------------------------------------------------|    Basic inspections

    def node(self):
        """
        :return: The wrapped transform (group) node.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        return self._node

    def basename(self):
        """
        :return: The short name of the group node, without the type suffix.
        :rtype: :class:`str`
        """
        return self._node.basename(sns=True, sts=True)

    def getControls(self):
        """
        :return: All transform nodes under the part group for which
            :meth:`~paya.runtime.nodes.DependNode.isControl` returns ``True``.
        :rtype: [:class:`~paya.runtime.nodes.Transform`]
        """
        return [node for node in self._node.listRelatives(
            allDescendents=True, type='transform') if node.isControl()]

    @property
    def tree(self):
        """
        :return: A :class:`group tree <paya.lib.grouptree.GroupTree>`
            instantiated around this part's group node.
        :rtype: :class:`paya.lib.grouptree.GroupTree`
        """
        return GroupTree(self)

    @short(plug='p')
    def getPartScale(self, plug=False):
        """
        :param bool plug/p: return a live output, not just a value
        :return: A scaling factor derived from the Y axis of the part
            group node's world matrix.
        :rtype: :class:`~paya.runtime.plugs.Double`
        """
        node = self.node()

        if plug:
            if not node.hasAttr('partScale'):
                node.addAttr('partScale', k=False, cb=True, dv=1.0)

            plug = node.attr('partScale')

            if not plug.inputs():
                plug.unlock()
                node.attr('worldMatrix').y.length() >> plug
                plug.lock()

            return plug

        return node.getMatrix(worldSpace=True).y.length()

    #-----------------------------------------------------|    Meta-node scaffolding

    def _getConnectedNode(self, basename, owner, create=True):
        if owner is None:
            if create:
                raise RuntimeError(
                    "Can't create '{}' network because "+
                    "the owner is undefined.".format(basename)
                )

        owner = r.PyNode(owner)
        attrName = '{}Node'.format(basename)

        if not owner.hasAttr(attrName):
            if create:
                owner.addAttr(attrName, at='message')
            else:
                return

        attr = owner.attr(attrName)
        inputs = attr.inputs()

        if inputs:
            return inputs[0]

        if create:
            with r.Name(self.basename(), basename, i=False):
                nw = r.nodes.Network.createNode()

            nw.attr('message') >> attr
            return nw

    #-----------------------------------------------------|    Patchbay

    def getPatchbay(self, create=True):
        """
        Returns a general-utility ``network`` node connected to this part's
        group node.

        :param bool create: create the ``network`` node if it doesn't already
            exist; defaults to ``True``
        :return: The ``network`` node.
        :rtype: :class:`~paya.runtime.nodes.Network`
        """
        return self._getConnectedNode('patchbay', self.node(), create=create)

    patchbay = property(fget=getPatchbay)

    #-----------------------------------------------------|    Node tagging

    def _getTagsNode(self, create=True):
        pb = self.getPatchbay(create=create)
        return self._getConnectedNode('tags', pb, create=create)

    def _getTagAttr(self, basename, create=True):
        tagsNode = self._getTagsNode(create=create)

        if tagsNode is None:
            return

        attrName = '{}Tag'.format(basename)

        if not tagsNode.hasAttr(attrName):
            if create:
                tagsNode.addAttr(attrName, at='message', multi=True)
            else:
                return

        return tagsNode.attr(attrName)

    def _getTagAttrContents(self, tagAttr, nodes=True, attrs=True):
        nodes, attrs = resolveFlags(nodes, attrs)

        if not (nodes or attrs):
            return []

        contents = []
        _nodes = []
        _attrs = []

        for i in tagAttr.getArrayIndices():
            inputs = tagAttr[i].inputs(plugs=True)

            if inputs:
                input = inputs[0]

                if input.type() == 'message':
                    item = input.node()
                    _nodes.append(item)
                else:
                    item = input
                    _attrs.append(item)

                contents.append(item)

        if nodes:
            if attrs:
                return contents
            return _nodes

        return _attrs

    def getByTag(self, tag, nodes=True, attrs=True):
        """
        :param str tag: the tag
        :param bool nodes: include nodes in the returned list; defaults to
            ``True``
        :param bool attrs: include attributes in the returned list; defaults
            to ``True``
        :return: A list of nodes and / or attributes with the specified tag.
        :rtype: [:class:`~paya.runtime.nodes.DependNode`,
            :class:`~paya.runtime.plugs.Attribute`]
        """
        tagAttr = self._getTagAttr(tag, create=False)

        if tagAttr is None:
            return []

        return self._getTagAttrContents(tagAttr, nodes=nodes, attrs=attrs)

    def getNodesByTag(self, tag):
        """
        Equivalent to ``getByTag(tag, nodes=True)``.
        """
        return self.getByTag(nodes=True)

    def getAttrsByTag(self, tag):
        """
        Equivalent to ``getByTag(tag, attrs=True)``.
        """
        return self.getByTag(attrs=True)

    def clearTag(self, tag):
        """
        :param str tag: the tag to remove
        """
        attr = self._getTagAttr(tag, create=False)

        if attr is not False:
            attr.node().deleteAttr(attr.attrName())

    def clearTags(self, *tags):
        """
        :param \*tags: the tag(s) to remove; if omitted, all tags will
            be removed
        :type \*tags: :class:`str`, [:class:`str`]
        """
        if tags:
            tags = list(set(expandArgs(*tags)))
        else:
            tags = self.getTags()

        for tag in tags:
            self.clearTag(tag)

    def getTags(self):
        """
        :return: A list of tags used by this part.
        :rtype: [:class:`str`]
        """
        tagsNode = self._getTagsNode(create=False)

        if tagsNode is None:
            return []

        names = [attr.attrName() for attr in \
               tagsNode.listAttr(ud=True) if attr.type() == 'message']

        matches = [re.match(r"^(.*?)Tag$", name) for name in names]
        matches = [match for match in matches if match]
        return [match.groups()[0] for match in matches]

    def tag(self, tag, *nodesOrAttrs):
        """
        Tags nodes and attributes for later retrieval by :meth:`getByTag`,
        :meth:`getNodesByTag` or :meth:`getAttrsByTag`.

        :param str tag: the name of the tag to apply
        :param \*nodesOrAttrs: nodes or attributes to apply the tag to
        :type \*nodesOrAttrs: :class:`str`,
            :class:`~paya.runtime.nodes.DependNode`,
            :class:`~paya.runtime.plugs.Attribute`,
            [:class:`str`, :class:`~paya.runtime.nodes.DependNode`,
            :class:`~paya.runtime.plugs.Attribute`]
        """
        tagAttr = self._getTagAttr(tag, create=True)
        contents = self._getTagAttrContents(tagAttr)

        nodesOrAttrs = [item if isinstance(item, r.PyNode) \
                        else r.PyNode(item) for item \
                        in expandArgs(*nodesOrAttrs)]

        nodesOrAttrs = [item for item in nodesOrAttrs if item not in contents]
        nextIndex = tagAttr.getNextArrayIndex()

        for i, item in enumerate(nodesOrAttrs, start=nextIndex):
            if isinstance(item, r.Attribute):
                src = item
            else:
                src = item.attr('message')

            src >> tagAttr[i]

    #-----------------------------------------------------|    Repr

    def __str__(self):
        return str(self._node)

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, str(self._node))