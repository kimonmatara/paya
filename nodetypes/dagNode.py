import paya.runtime as r
from paya.util import short
import paya.lib.names as _nm


class DagNode:

    #-----------------------------------------------------------|    Sampling

    @property
    def getWorldMatrix(self):
        return self.attr('wm').get

    gwm = getWorldMatrix

    @short(plug='p')
    def getWorldPosition(self, plug=False):
        """
        Returns the world translation of this DAG node.

        :shorthand: ``gwp``
        :param bool plug/p: return an attribute instead of a value; defaults
            to False
        :return: The position attribute or value.
        :rtype: :class:`~paya.runtime.data.Point` or
           :class:`~paya.runtime.plugs.Vector`
        """
        return self.getWorldMatrix(p=plug).t

    gwp = getWorldPosition

    #-----------------------------------------------------------|    Name management

    @short(
        stripNamespace='sns',
        stripTypeSuffix='sts',
        stripDagPath='sdp'
    )
    def basename(
            self,
            stripNamespace=False,
            stripTypeSuffix=False,
            stripDagPath=True
    ):
        """
        Returns shorter versions of this node's name.

        :param bool stripNamespace/sns: remove namespace information; defaults to
            False
        :param bool stripDagPath/sdp: remove DAG path information; defaults to
            True
        :param bool stripTypeSuffix/sts: removes anything that looks like a type
            suffix; defaults to False
        :return: the modified name
        :rtype: str
        """
        return _nm.shorten(
            str(self),
            sns=stripNamespace,
            sts=stripTypeSuffix,
            sdp=stripDagPath
        )

    bn = basename

    #-----------------------------------------------------------|    Controller management

    def isControl(self, *state):
        """
        :param bool \*state: if ``True``, make this node a controller; if
            ``False``, remove any controller tags; if omitted, return whether
            this node is a controller
        :return: bool or None
        """
        tags = r.controller(self, q=True)

        if state:
            state = state[0]

            if state and not tags:
                r.controller(self)

            elif tags and not state:
                r.delete(tags)

        else:
            return bool(tags)

    def setPickWalkParent(self, parent):
        """
        Sets the pick walk parent for this node. If there's no controller tag,
        one will be added automatically.

        :param parent: the node to set as the pick walk parent; pass None
            to unparent this node (any existing controller tag will be
            preserved)
        :type parent: str, :class:`~pymel.core.general.PyNode`, None
        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.DagNode`
        """
        if parent is None:
            if self.isControl():
                r.controller(self, e=True, unparent=True)

        else:
            parent = r.PyNode(parent)
            parent.isControl(True)
            self.isControl(True)

            r.controller(self, parent, e=True, parent=True)

        return self

    def getPickWalkParent(self):
        """
        :return: The pick walk parent for this node, if any.
        :rtype: None, :class:`~paya.runtime.nodes.DependNode`
        """
        result = r.controller(self, q=True, parent=True)

        if result:
            return r.PyNode(result)

        return None