import pymel.util as _pu
from paya.util import short
import paya.runtime as r


class Cluster:

    #--------------------------------------------------------|    Constructor

    @classmethod
    @short(
        weightedNode='wn',
        bindState='bs',
        geometry='g'
    )
    def create(
            cls,
            *geos,
            geometry=None,
            weightedNode=None,
            bindState=False,
            name=None,
            **kwargs
    ):
        """
        Cluster constructor.

        :param \*geos: one or more geometries to include in the deformation
        :type \*geos: str, list, tuple,
            :class:`~paya.runtime.nodes.DeformableShape`,
            :class:`~paya.runtime.nodes.Transform`
        :param geometry/g: an alternative geometry aggregator
        :type geometry/g: str, list, tuple,
            :class:`~paya.runtime.nodes.DeformableShape`,
            :class:`~paya.runtime.nodes.Transform`
        :param weightedNode/wn: use this to swap in a custom user handle;
            unlike on the standard :func:`~pymel.core.animation.cluster`
            command, here this will also accept a single argument; defaults to
            None
        :type weightedNode/wn: None, tuple, list, str,
            :class:`~paya.runtime.nodes.Transform`
        :param bool bindState/bs: similar to *maintainOffset* on constraints;
            prevents jumping when the custom weighted node has transformations;
            defaults to False
        :param name/n: one or more name elements; these will be applied both
            to the cluster node and its adjuncts; defaults to None
        :type name/n: None, tuple, list, str, int
        :param \*\*kwargs: forwarded to :func:`~pymel.core.animation.cluster`;
            see :func:`~pymel.core.animation.cluster` for details
        :return: The cluster node. To get the weighted node (transform), use
            :meth:`getWeightedNode` or the ``weightedNode`` / ``wn`` property.
        :rtype: :class:`~paya.runtime.nodes.Cluster`
        """

        # Wrangle args, prep

        allgeo = []

        if geos:
            allgeo += list(_pu.expandArgs(*geos))

        if geometry:
            allgeo += list(_pu.expandArgs(geometry))

        mayaKwargs = {}

        if bindState:
            mayaKwargs['bindState'] = True

        if weightedNode:
            mayaKwargs['weightedNode'] = \
                cls._conformWeightedNodeArg(weightedNode)
            customWn = True

        else:
            customWn = False

        r.select(cl=True)

        if allgeo:
            r.select(allgeo)

        # Execute

        kwargs.update(mayaKwargs)
        node, wn = [r.PyNode(item) for item in r.cluster(**kwargs)]

        # Post config
        node.rename(name, mn=True)

        if not customWn:
            wn.rename(name, mn=True)

        return node

    #--------------------------------------------------------|    Weighted node management

    @staticmethod
    def _conformWeightedNodeArg(*args):
        args = list(_pu.expandArgs(*args))

        ln = len(args)

        if ln is 0 or ln > 2:
            raise ValueError("Need one or two values for weightedNode.")

        if ln is 1:
            out = args * 2

        else:
            out = args[0]

        return out

    def getWeightedNode(self):
        """
        Overload of :meth:`pymel.core.nodetypes.Cluster.getWeightedNode`
        for return type.

        Getter for ``weightedNode`` / ``wn`` property.

        :return: The weighted node.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        result = r.nodetypes.Cluster.getWeightedNode(self)

        if result:
            return r.PyNode(result)

    @short(bindState='bs')
    def setWeightedNode(self, *args, bindState=False):
        """
        Overloads :meth:`pymel.core.nodetypes.Cluster.setWeightedNode` to
        accept a single argument for the weighted node. This will merely
        be duplicated and passed along.

        Setter for ``weightedNode`` / ``wn`` property.

        :param \*args: the weighted node arg(s)
        :type \*args: str, :class:`~paya.runtime.nodes.Transform`
        :param bool bindState/bs: maintain offset when switching weighted
            nodes; defaults to False
        :return: ``self``
        :rtype: :class:`Cluster`
        """
        args = _pu.expandArgs(*args)

        ln = len(args)

        if ln:
            if ln is 1:
                args = [args] * 2

            elif ln > 2:
                raise ValueError(
                    "Need one or two arguments, packed or unpacked."
                )
        else:
            raise ValueError(
                "Need one or two arguments, packed or unpacked."
            )

    weightedNode = wn = property(fget=getWeightedNode, fset=setWeightedNode)