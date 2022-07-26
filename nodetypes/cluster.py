import pymel.util as _pu
import paya.lib.names as _nm
from paya.util import short
import paya.runtime as r


class Cluster:

    #------------------------------------------------|    Constructor

    @classmethod
    @short(
        geometry='g',
        maintainOffset='mo',
        conformShapeName='csn',
        resetVisualOrigin='rvo',
        intermediateShape='i',
        bindState='bs',
        weightedNode='wn',
        worldMatrix='wm',
        name='n',
        freeze='fr',
        handle='hnd'
    )
    def create(
            cls,
            *geos,
            geometry=None,
            handle=None,
            maintainOffset=None,
            conformShapeName=False,
            resetVisualOrigin=True,
            intermediateShape=None,
            worldMatrix=None,
            freeze=True,
            name=None,
            **mayaKwargs
    ):
        """
        Cluster constructor.

        :param name/n: one or more name elements; defaults to None
        :type name/n: None, tuple, list, str, int
        :param \*geos: one or more geometries to bind
        :type \*geos: None, str, tuple, list,
            :class:`~paya.runtime.nodes.DeformableShape`,
            :class:`~paya.runtime.nodes.Transform`
        :param geometry/g: alternative geometry aggregator; defaults to None
        :type geometry/g: None, str, tuple, list,
            :class:`~paya.runtime.nodes.DeformableShape`,
            :class:`~paya.runtime.nodes.Transform`
        :param handle/hnd: a custom user handle (weighted node) for the
            cluster; if provided, will override the *weightedNode* / *wn*
            argument for :func:`~pymel.core.animation.cluster`; defaults to
            None
        :param bool maintainOffset/mo: prevent deformation jumps when
            assigning a custom handle that has transform values; if provided,
            will override the *bindState* / *bs* argument for
            :func:`~pymel.core.animation.cluster`; defaults to None
        :param bool conformShapeName/csn: when using a custom handle, rename
            the :class:`~paya.runtime.nodes.ClusterHandle` node accordingly;
            defaults to True
        :param bool resetVisualOrigin/rvo: when using a custom handle, modify
            ``origin`` on the :class:`~paya.runtime.nodes.ClusterHandle` node
            accordingly; defaults to True
        :param bool intermediateShape/i: sets the 'intermediate' state of the
            :class:`~paya.runtime.nodes.ClusterHandle` node; where a custom
            weighted node is specified, this defaults to True if the
            destination parent has hero shapes, otherwise False; if no custom
            handle is specified, defaults to False
        :param worldMatrix/wm: ignored if a custom handle is specified;
            modifes the initial matrix of the default cluster handle; defaults
            to None
        :param bool freeze/fr: ignored if *worldMatrix* was omitted, or if
            a custom handle was specified; after applying custom
            transformations to the default handle, freeze transform and scale
            but preserve rotation; defaults to True
        :type worldMatrix/wm: None, list, tuple,
            :class:`~paya.runtime.data.Matrix`
        :param \*\*mayaKwargs: passed along to
            :func:`~pymel.core.animation.cluster`, except where overriden by
            other options
        :return: The cluster node. To get the handle transform, use
            :meth:`getHandle`.
        """

        # Aggregate geometries
        allGeos = []

        if geos:
            allGeos += list(_pu.expandArgs(geos))

        if geometry:
            allGeos += list(_pu.expandArgs(geometry))

        # Hijack handle swapping args so that we can swap separately
        # via setHandle()
        if handle:
            newWeightedNode = handle

        else:
            newWeightedNode = \
                mayaKwargs.get('weightedNode', [None, None])[0]

        if maintainOffset is None:
            maintainOffset = mayaKwargs.get('bindState', False)

        try:
            del(mayaKwargs['bindState'])

        except KeyError:
            pass

        # Run
        result = r.cluster(*allGeos, **mayaKwargs)
        newNode = r.PyNode(result[0])
        newNode.renameSystem(name)

        if newWeightedNode:
            customMatrix = False

        else:
            customMatrix = worldMatrix is not None

        if customMatrix:
            origName = newNode.getHandle().basename()

            newWeightedNode = r.group(empty=True)
            newWeightedNode.setMatrix(worldMatrix)

            if freeze:
                newWeightedNode.makeIdentity(
                    apply=True, t=True, scale=True, rotate=False)

            conformShapeName = False
            resetVisualOrigin = True
            maintainOffset = True
            intermediateShape = False

        # Swap handle
        if newWeightedNode:
            newNode.setHandle(
                newWeightedNode,
                csn=conformShapeName,
                rvo=resetVisualOrigin,
                dph=True,
                mo=maintainOffset,
                i=intermediateShape
            )

            if customMatrix:
                newWeightedNode.rename(origName)

        elif intermediateShape is not None:
            newNode.getHandleShape(
                ).attr('intermediateObject').set(intermediateShape)

        return newNode

    #------------------------------------------------|    Handle management

    def getHandle(self):
        """
        Paya's flavour of :meth:`~paya.runtime.nodes.getWeightedNode`. Getter
        for ``handle`` property.

        :return: The cluster handle transform (weighted node).
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        result = self.attr('matrix').inputs()

        if result:
            return result[0]

    @short(
        maintainOffset='mo',
        intermediateShape='i',
        resetVisualOrigin='rvo',
        deletePreviousHandle='dph',
        conformShapeName='csn'
    )
    def setHandle(
            self,
            transform,
            maintainOffset=False,
            intermediateShape=None,
            resetVisualOrigin=True,
            deletePreviousHandle=False,
            conformShapeName=True
    ):
        """
        Swaps-in a custom handle transform (weighted node). Setter for
        ``handle`` property.

        :param transform: the node to swap-in
        :type transform: str, :class:`~paya.runtime.nodes.Transform`
        :param bool maintainOffset/mo: prevent changes in deformation;
            defaults to False
        :param bool intermediateShape/i: after reparenting the
            :class:`~paya.runtime.nodes.ClusterHandle` node, set it to
            intermediate; defaults to True if the destination parent has
            hero shapes, otherwise False
        :param bool resetVisualOrigin/rvo: edit the ``origin`` attribute
            on the :class:`~paya.runtime.nodes.ClusterHandle` so that it
            matches the new handle; defauls to True
        :param bool deletePreviousHandle/dph: delete the current weighted node
            after completing the swap
        :param bool copyName/cn: copy the name of the current weighted node
        :param bool conformShapeName/csn: after reparenting the
            :class:`~paya.runtime.nodes.ClusterHandle` node, rename it to
            match the destination transform; defaults to True
        :return: ``self``
        :rtype: :class:`Cluster`
        """
        xf = r.PyNode(transform)

        if intermediateShape is None:
            intermediateShape = bool(xf.getHeroShapes())

        previous = self.getHandle()

        r.cluster(self, e=True, wn=[xf, xf], bs=maintainOffset)

        if deletePreviousHandle:
            r.delete(previous)

        handleShape = self.getHandleShape()

        if conformShapeName:
            handleShape.conformName()

        handleShape.resetVisualOrigin()
        handleShape.attr('intermediateObject').set(intermediateShape)

        return self

    handle = property(fget=getHandle, fset=setHandle)

    #------------------------------------------------|    Name management

    @short(managedNames='mn')
    def renameSystem(self, *elems, managedNames=True):
        """
        Renames the entire cluster system, including the weighted node,
        cluster handle shape and the cluster node itself.

        :param \*elems: one or more name elements
        :type \*elems: None, tuple, list, int, str
        :param bool managedNames/mn: inherit from
            :class:`~paya.lib.names.Name` blocks and apply type suffixes;
            defaults to True
        :return: ``self``
        :rtype: `Cluster`
        """
        cluster = self
        clusterHandleShape = self.getHandleShape()
        clusterHandle = self.getHandle()

        # Rename the cluster handle
        kw = {}

        if managedNames:
            kw['inh'] = True

            if clusterHandle.isControl():
                kw['control'] = True

            else:
                kw['node'] = clusterHandle

        clusterHandleName = _nm.make(*elems, **kw)
        clusterHandle.rename(clusterHandleName)

        # Rename the cluster handle shape
        clusterHandleShape.conformName()

        # Rename the cluster node itself
        kw = {}

        if managedNames:
            kw['inh'] = True
            kw['node'] = self

        name = _nm.make(*elems, **kw)
        self.rename(name)

        return self

    #------------------------------------------------|    Handle shape management

    def getHandleShape(self):
        """
        Getter for ``handleShape`` property.

        :return: The connected class:`~paya.runtime.nodes.ClusterHandle` node,
            if any.
        :rtype: class:`~paya.runtime.nodes.ClusterHandle`
        """
        inputs = self.attr('clusterXforms').inputs(plugs=True)

        if inputs:
            return inputs[0].node()

    handleShape = property(fget=getHandleShape)

    #------------------------------------------------|    Matrix management

    def normalize(self):
        """
        Compensates transformations on the cluster to un-deform the geometry.

        :return: ``self``
        :rtype: :class:`Cluster`
        """
        self.attr('bindPreMatrix').set(self.attr('matrix').get().inverse())
        return self