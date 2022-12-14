import re

import maya.cmds as m
from pymel.util import expandArgs

import paya.runtime as r
from paya.util import short



class Tagger(r.networks.System):

    #-------------------------------------------------|
    #-------------------------------------------------|    Constructor(s)
    #-------------------------------------------------|

    @classmethod
    def create(cls, node):
        """
        Adds a tagger node to the specified *node*.

        :param node: the node to which to add a tagger system
        :type node: :class:`str`, :class:`~paya.runtime.nodes.DependNode`
        :return: The tagger node.
        :rtype: :class:`~paya.runtime.networks.Tagger`
        """
        existing = cls.getFromTaggingNode(node)

        if existing:
            raise RuntimeError(
                "Node already has a tagger: {}".format(node)
            )

        node = r.PyNode(node)

        with r.Name(
                node.basename(sns=True, sts=True),
                'tags', inherit=False):
            nw = cls.createNode()

        node.attr('message') >> nw.addAttr('taggingNode', at='message')

        return nw

    #-------------------------------------------------|
    #-------------------------------------------------|    Accessor(s)
    #-------------------------------------------------|

    @classmethod
    def getFromTaggingNode(cls, taggingNode, create=False):
        """
        :param taggingNode: The tagging node.
        :type taggingNode: :class:`str`,
            :class:`~paya.runtime.nodes.DependNode`
        :param bool create: create a tagger if one was not found;
            defaults to ``False``
        :return: The tagger utility node, if present.
        :rtype: :class:`Tagger`, ``None``
        """
        taggingNode = str(taggingNode)

        networks = m.listConnections(taggingNode+'.message',
                                     d=True, t='network')

        if networks:
            matches = [network for network in networks \
                       if cls.matchesType(network, cnt=False)]

            if matches:
                return r.PyNode(matches[0]).asSubtype()

        if create:
            return cls.create(taggingNode)

    #-------------------------------------------------|
    #-------------------------------------------------|    Editing
    #-------------------------------------------------|

    def tag(self, tagName, *attrsOrNodes):
        """
        Tags attributes or nodes for later retrieval via :meth:`getByTag`.

        :param str tagName: the tag to use
        :param \*attrsOrNodes: the attributes or nodes to tags
        :type \*attrNodes: :class:`str`,
            :class:`~paya.runtime.plugs.Attribute`,
            :class:`~paya.runtime.plugs.DependNode`
        :return:
        """
        attrsOrNodes = [x if isinstance(x, r.PyNode) \
            else r.PyNode(x) for x in expandArgs(*attrsOrNodes)]

        if attrsOrNodes:
            attrName = '{}_tag'.format(tagName)

            if self.hasAttr(attrName):
                attr = self.attr(attrName)
                index = attr.getNextArrayIndex()
            else:
                attr = self.addAttr(attrName, at='message', multi=True)
                index = 0

            for i, item in enumerate(attrsOrNodes, start=index):
                if isinstance(item, r.Attribute):
                    if item.type() == 'message':
                        item = item.node()
                else:
                    item = item.attr('message')

                item >> attr[i]
        else:
            raise ValueError("No nodes or attributes were specified.")

        return self

    def getByTag(self, tagName):
        """
        :param str tagName: the tag to inspect
        :return: Nodes and attributes tagged with the specified *tagName*.
        :rtype: :class:`list` [:class:
        """
        attrName = '{}_tag'.format(tagName)
        out = []

        if self.hasAttr(attrName):
            attr = self.attr(attrName)
            indices = attr.getArrayIndices()

            for index in indices:
                inputs = attr[index].inputs(plugs=True)

                for input in inputs:
                    if input.type() == 'message':
                        input = input.node()

                    out.append(input)

        return out

    def getTags(self):
        """
        :return: Tags in use.
        :rtype: :class:`list` [:class:`str`]
        """
        attrs = [attr for attr \
                 in self.listAttr(ud=True) if attr.type() == 'message']

        out = []

        for attr in attrs:
            mt = re.match(r"^(.+?)_tag$", attr.attrName(longName=True))

            if mt:
                out.append(mt.groups()[0])

        return out

    @short(removeTaggerIfEmpty='rem')
    def clearTags(self, *tagNames, removeTaggerIfEmpty=False):
        """
        :param \*tagNames: the tags to remove; if none are specified, all
            tags will be removed
        :type bool removeTaggerIfEmpty/rem: if all tags were removed, delete
            this node as well; defaults to ``False``
        :return: ``None`` if all tags were removed and *removeTaggerIfEmpty*
            is ``True``, otherwise ``self``
        :rtype: :class:`Tagger`, ``None``
        """
        tagNames = expandArgs(*tagNames)

        if tagNames:
            removeAll = False
        else:
            tagNames = self.getTags()
            removeAll = True

        for tagName in tagNames:
            attrName = '{}_tag'.format(tagName)

            if self.hasAttr(attrName):
                attr = self.attr(attrName)

                for index in attr.getArrayIndices():
                    r.removeMultiInstance(attr[index], b=True)

                self.deleteAttr(attrName)

        if removeAll:
            r.delete(self)
        else:
            return self