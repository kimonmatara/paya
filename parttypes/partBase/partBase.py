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

    @short(plug='p')
    def getPartScaleMatrix(self, plug=False):
        """
        :param bool plug/p: return a live output, not just a value
        :return: A scale matrix derived from the part group node.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        node = self.node()

        if plug:
            if not node.hasAttr('partScaleMatrix'):
                node.addAttr('partScaleMatrix', at='matrix')

            plug = node.attr('partScaleMatrix')

            if not plug.inputs():
                plug.unlock()
                node.attr('worldMatrix').pick(scale=True) >> plug
                plug.lock()

            return plug
        else:
            return node.getMatrix(worldSpace=True).pick(scale=True)

    #-----------------------------------------------------|    Attr delegation

    def __getattr__(self, attrName):
        return getattr(self.node(), attrName)

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
        out = self.getByTag('patchbay')

        if out:
            return out[0]

        if create:
            with r.Name(
                    self.node().basename(sns=True, sts=True),
                    'patchbay',
                    inherit=False
            ):
                patchbay = r.networks.createNode()

            self.tag('patchbay', patchbay)
            return patchbay

    patchbay = property(fget=getPatchbay)

    #-----------------------------------------------------|    Destructor

    def remove(self):
        """
        Removes this part and all DG and DAG nodes that were created when it
        was first built.
        """
        for node in self.getByTag('dependencies'):
            if r.objExists(node):
                try:
                    r.delete(node)
                except:
                    continue

        r.delete(self)

    #-----------------------------------------------------|    Repr

    def __str__(self):
        return str(self._node)

    def __repr__(self):
        return "{}('{}')".format(self.__class__.__name__, str(self._node))