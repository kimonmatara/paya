from paya.util import short
import paya.runtime as r


class Cluster:

    #--------------------------------------------------------|    Constructor

    @classmethod
    @short(
        handle='hnd',
        name='n'
    )
    def create(
            cls,
            *geometry,
            handle=None,
            name=None,
            **mayaFlags
    ):
        """
        See :func:`~pymel.core.animation.cluster` for documentation on *mayaFlags*.

        :param \*geometry: optional geometry to bind
        :type \*geometry: tuple, list, str, :class:`~paya.runtime.nodes.DagNode`,
            :class:`~paya.runtime.comps.Component`,
        :param handle/hnd: an optional alternative handle for the cluster; if
            this is provided, it will override the *weightedNode/wn* argument;
            defaults to None
        :type handle/hnd: None, str, :class:`~paya.runtime.nodes.Transform`
        :param name/n: one or more name elements; defaults to None
        :param \*\*mayaFlags: forwarded to
            :func:`~pymel.core.animation.cluster`
        :return: The cluster node. The handle can be accessed through the
            ``.handle`` property.
        :rtype: :class:`~paya.runtime.nodes.Cluster`
        """
        #--------------------------------------|    Edit kwargs

        # Define our overrides

        ourKwargs = {}

        if handle:
            customHandle = True
            ourKwargs['weightedNode'] = (handle, handle)
            ourKwargs['bindState'] = True

        else:
            customHandle = False

        # Update Maya kwargs

        mayaFlags.update(ourKwargs)

        #--------------------------------------|    Execute

        node, handle = r.cluster(*geometry, **mayaFlags)

        #--------------------------------------|    Post-config

        handleName = r.nodes.ClusterHandle.makeName(name)

        if customHandle:
            node._getClusterHandleShape().rename(handleName+'Shape')
        else:
            handle.rename(handleName)

        nodeName = cls.makeName(name)
        node.rename(nodeName)

        return node

    #--------------------------------------------------------|    Weighted-node management

    def getHandle(self):
        """
        Getter for ``.handle`` property. Returns the weighted node.

        :return: The handle *transform*.
        :rtype :class:`~paya.runtime.nodes.Transform`
        """
        return r.PyNode(self.getWeightedNode())

    def _getClusterHandleShape(self):
        # Returns the 'clusterHandle' node connected to this cluster.
        inputs = self.attr('clusterXforms'
                ).inputs(plugs=True, type='clusterHandle')

        if inputs:
            return inputs[0].node()

    def setHandle(self, handle):
        """
        Setter for ``.handle`` property. Swaps-out the weighted node.
        :param handle: the new handle
        :type handle: str, :class:`~paya.runtime.nodes.Transform`
        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.Cluster`
        """
        r.cluster(self, e=True, wn=(handle, handle), bs=True)

        cHandleShape = self._getClusterHandleShape()

        if inputs:
            # Clean up the clusterHandle shape
            cHandleShape = inputs[0].node()
            cHandleShape.attr('origin').set([0, 0, 0])
            cHandleShape.attr('intermediateObject').set(True)

        return self