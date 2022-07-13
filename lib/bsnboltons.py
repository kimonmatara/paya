"""
This module is not for direct import / use. It defines the ``.targets``
interface on :class:`~paya.runtime.nodes.BlendShape`.
"""
import maya.mel as mel
mel.eval('source blendShapeDeleteInBetweenTarget')
mel.eval('source blendShapeDeleteTargetGroup')

from paya.util import short
import paya.runtime as r

#-------------------------------------------------------------------------------|
#-------------------------------------------------------------------------------|    TARGETS
#-------------------------------------------------------------------------------|

#---------------------------------------------------------------------|    Exceptions

class NonTransformSpaceTargetError(RuntimeError):
    """
    The target being manipulated is not transform-space.
    """

class TargetMatrixNotATransformError(RuntimeError):
    """
    A transform-space target has a matrix input from a non-transform node
    (e.g. a maths utility node).
    """

#----------------------------------------------------------------|    Helpers

def subtargetIndexToValue(index):
    """
    Given a logical subtarget (tween) index in the 5000 -> 6000 range, returns
    a float weight.

    :param index: the logical subtarget index
    :return: The weight.
    :rtype: float
    """
    return round((index-5000) / 1000, 3)

def subtargetValueToIndex(value):
    """
    Given a subtarget (tween) value, returns a logical index in the
    5000 -> 6000 range.

    :param value: the subtarget value
    :return: The index.
    :rtype: int
    """
    value = round(value, 3)
    value *= 1000
    value = int(value)
    return 5000 + value

#----------------------------------------------------------------|    Classes

class Subtarget:
    """
    Interface for editing subtargets (tweens).

    .. rubric:: Updating geometry

    .. code-block:: python

        target = bsn.targets['L_smile']
        subtarget = target[1.0]
        subtarget.shape = 'new_geo'
    """

    #--------------------------------------------------------|    Init

    def __init__(
            self,
            index, # logical (in-use / sparse), 5000 -> 6000
            owner
    ):
        self._index = index
        self._owner = owner

    #--------------------------------------------------------|    Basic inspections

    def index(self): # logical (in-use / sparse), 5000 -> 6000
        return self._index

    @property
    def owner(self):
        return self._owner

    @property
    def node(self):
        return self.owner.node

    def value(self):
        return subtargetIndexToValue(self.index())

    @property
    def inputTargetItem(self):
        return self.owner.inputTargetItem[self.index()]

    iti = inputTargetItem

    @property
    def geoInput(self):
        return self.inputTargetItem.attr('inputGeomTarget')

    #--------------------------------------------------------|    Geometry management

    @short(create='c', connect='con')
    def getShape(self, create=False, connect=None):
        """
        :param bool create/cr: recreate the target where possible; defaults to
            False
        :param bool connect/con: after recreating the target, connect it back
            to the target; defaults to False if this is a 'post' target,
            otherwise False
        :return: The shape connected into this target. This may be None if
            this is a 'post' mode target, or if targets were disconnected or
            deleted by the rigger.
        :rtype: :class:`~paya.runtime.nodes.GeometryShape`
        """
        inputs = self.geoInput.inputs(plugs=True)

        if inputs:
            return inputs[0].node()

        if create:
            bsn = self.node()
            post = bsn.inPostMode()

            if connect is None:
                connect = False if post else True

            elif connect and post:
                raise RuntimeError(
                    "Can't reconnect a regenerated shape when the blend "+
                    "shape node is in 'post-deformation' mode."
                )

            xf = r.PyNode(r.sculptTarget(
                bsn,
                e=True,
                t=self.owner.index(),
                ibw=self.value(),
                r=True
            )[0])

            xf.conformShapeNames()
            shape = xf.getShape()

            if not connect:
                self.geoInput.disconnect(inputs=True)

            return shape

    @short(connect='con')
    def setShape(self, shape, connect=None):
        """
        :param shape: the geometry shape to use to drive this subtarget
        :type shape: str, :class:`~paya.runtime.nodes.DagNode`
        :param bool connect/con: keep a live connection to the shape;
            this defaults to False if this is a post-mode target, otherwise
            True; passing True on a post-mode target will throw an error
        :return: ``self``
        :rtype: :class:`Subtarget`
        """
        inPost = self.owner.inPostMode()

        if connect is None:
            connect = not inPost

        elif connect and inPost:
            raise RuntimeError("Post-mode shapes can't be connected.")

        shape = r.PyNode(shape).toShape()
        shape.worldGeoOutput >> self.geoInput

        if not connect:
            self.geoInput.disconnect(inputs=True)

        return self

    shape = property(fget=getShape, fset=setShape)

    #--------------------------------------------------------|    Repr

    def __repr__(self):
        return '{}[{}]'.format(self.owner, self.value())

    #--------------------------------------------------------|    Conversions

    def __int__(self):
        """
        :return: The logical (sparse) 5000 - > 6000 index for this subtarget
            (``self.index``)
        :rtype: int
        """
        return self.index()

    def __float__(self):
        """
        :return: The 0.0 -> 1.0 weight (value) for this subtarget
            (``self.value``)
        :rtype: float
        """
        return self.value()

class Target:
    """
    .. rubric:: Retrieving Subtargets (Tweens)

    .. code-block:: python

        # Start
        target = bsn.targets['L_smile']

        # Iterate subtargets
        for subtarget in target:
            # do something

        # List subtargets
        list(target)

        # By logical (sparse, 5000 -> 6000) index
        subtarget = target.getByLogicalIndex(logicalIndex)

        # By physical (contiguous) index
        subtarget = target.getByPhysicalIndex(physicalIndex)
        # or
        subtarget = list(taret)[physicalIndex]

        # By value (ratio)
        subtarget = target.getByValue(value)
        # or
        subtarget = target[value]

    .. rubric:: Adding Subtargets (Tweens)

    .. code-block:: python

        subtarget = target.add(0.5, tweenShape)
        # or
        target[0.5] = tweenShape # by value
        # or
        target[5500] = tweenShape # by logical index

    See :meth:`add` for more options.

    .. rubric:: Removing Subtargets (Tweens)

    .. code-block:: python

        target.removeByPhysicalIndex(physicalIndex)
        target.removeByLogicalIndex(logicalIndex)
        target.removeByValue(value)

        # or
        del(target[physicalIndex])
        del(target[value])

        # Clear all inbetweens (but not at 1.0)
        target.clearInbetweens()

    See :class:`Subtarget` for more.
    """

    #--------------------------------------------------------|    Init

    def __init__(
            self,
            index, # logical (sparse / in-use)
            owner
    ):
        self._index = index
        self._owner = owner

    #--------------------------------------------------------|    Basic inspections

    def index(self): # logical (sparse / in-use)
        return self._index

    @property
    def owner(self):
        return self._owner

    @property
    def node(self):
        return self.owner.node

    @property
    def weight(self):
        return self.node().attr('weight')[self.index()]

    @property
    def inputTargetGroup(self):
        return self.node().attr('inputTarget'
            )[0].attr('inputTargetGroup')[self.index()]

    itg = inputTargetGroup

    @property
    def inputTargetItem(self):
        return self.inputTargetGroup.attr('inputTargetItem')

    iti = inputTargetItem

    #--------------------------------------------------------|    Space management

    def isTransformSpace(self):
        """
        :return: True if this is a transform-space target, else False.
        :rtype: bool
        """
        plug = self.inputTargetGroup.attr('postDeformersMode')
        return plug.get() is 2

    def isTangentSpace(self):
        """
        :return: True if this is a tangent-space target, else False.
        :rtype: bool
        """
        plug = self.inputTargetGroup.attr('postDeformersMode')
        return plug.get() is 1

    def inPostMode(self):
        """
        :return: True if this is a tangent- or transform-space target,
            otherwise False.
        :rtype: bool
        """
        plug = self.inputTargetGroup.attr('postDeformersMode')
        return plug.get() in (1, 2)

    #--------------------------------------------------------|    Transform management

    @property
    def targetMatrix(self):
        return self.inputTargetGroup.attr('targetMatrix')

    def getTransform(self):
        """
        Setter for the ``transform`` / ``xf`` property.

        :raises NonTransformSpaceTargetError: this is not a transform-space
            target
        :raises TargetMatrixNotATransformError: there's an input into
            .targetMatrix, but it's from a utility node
        :return: if this is a transform-space target, the transform
            connected to it
        :rtype: None, :class:`~paya.runtime.nodes.Transform`
        """
        if self.isTransformSpace():
            inputs = self.targetMatrix.inputs(plugs=True)

            if inputs:
                input = inputs[0]
                node = input.node()

                if isinstance(node, r.nodes.Transform):
                    return node

                else:
                    raise TargetMatrixNotATransformError(
                        "The input to .targetMatrix is not a transform."
                    )

        else:
            raise NonTransformSpaceTargetError(
                "Target is not in transform space."
            )

    def setTransform(self, transform):
        """
        If this is a transform-space target, connects the ``.worldMatrix``
        of the specified transform into its ``.targetMatrix`` attribute.

        Setter for the ``transform`` / ``xf`` property.

        :param transform: the transform to connect
        :type transform: str, :class:`~paya.runtime.nodes.Transform`
        :raises NonTransformSpaceTargetError: this is not a transform-space
            target
        :return: ``self``
        :rtype: :class:`Target`
        """
        if self.isTransformSpace():
            r.PyNode(transform).attr('worldMatrix') >> self.targetMatrix
            return self

        raise NonTransformSpaceTargetError(
                "Target is not in transform space."
            )

    def clearTransform(self):
        """"
        If this is a transform-space target, clears any inputs on its
        ``.targetMatrix`` attribute.

        Deleter for the ``transform`` / ``xf`` property.

        :raises NonTransformSpaceTargetError: this is not a transform-space
            target
        :return: ``self``
        :rtype: :class:`Target`
        """
        if self.isTransformSpace():
            self.targetMatrix.disconnect(inputs=True)
            return self

        raise NonTransformSpaceTargetError(
                "Target is not in transform space."
            )

    transform = xf = property(
        fget=getTransform, fset=setTransform, fdel=clearTransform)

    #--------------------------------------------------------|    Normalization group

    def getNormalizationId(self):
        """
        Getter for the ``normalizationId`` / ``nid`` property.

        :return: The normalization ID of this target. An ID of 0 means
            that the target doesn't belong to any normalization groups.
        :rtype: int or None
        """
        return self.node().attr('inputTarget')[0].attr(
            'inputTargetGroup')[self.index()].attr('nid').get()

    def setNormalizationId(self, nid):
        """
        Sets the normalization ID of this target. An ID of 0 means
        that the target doesn't belong to any normalization groups.

        Setter for the ``normalizationId`` / ``nid`` property.

        :param int nid: the normalization ID
        :return: ``self``
        :rtype: :class:`Target`
        """
        self.node().attr('inputTarget')[0].attr(
            'inputTargetGroup')[self.index()].attr('nid').set(nid)

        return self

    def clearNormalizationId(self):
        """
        Deleter for the ``normalizationId`` / ``nid`` property. Equivalent
        to ``setNormalizationId(0)``.

        :return: ``self``
        :rtype: :class:`Target`
        """
        return self.setNormalizationId(0)

    normalizationId = nid = property(
        fget=getNormalizationId, fset=setNormalizationId,
        fdel=clearNormalizationId)

    #--------------------------------------------------------|    Alias

    def getAlias(self):
        """
        Returns the alias for this blend shape target. Getter for the
        ``alias`` property.

        :return: The alias for this target, if any.
        :rtype: str or None
        """
        return self.weight.getAlias()

    def setAlias(self, alias):
        """
        Sets the alias for this blend shape target. Setter for the ``alias``
        property.

        :param str alias: the alias to set
        :return: ``self``
        :rtype: :class:`Target`
        """
        origAlias = self.getAlias()

        if origAlias is None and alias is None:
            return

        if origAlias is not None and alias is not None:
            if origAlias == alias:
                return

        if alias is None:
            import maya.cmds as m
            r.aliasAttr(self.weight, rm=True)

        else:
            self.weight.setAlias(alias)

        return self

    def clearAlias(self):
        """
        Removes the alias for this blend shape target (not usually advisable).
        Equivalent to ``setAlias(None)``. Deleter for the ``alias`` property.

        :return: ``self``
        :rtype: :class:`Target`
        """
        self.setAlias(None)

    alias = property(fget=getAlias, fset=setAlias, fdel=clearAlias)

    #--------------------------------------------------------|    Member retrievals

    def getLogicalFromPhysicalIndex(self, physicalIndex):
        """
        :param int physicalIndex: the physical (contiguous) subtarget index
        :return: The logical (sparse, 5000 -> 6000) index.
        :rtype: int
        """
        return self.indices()[physicalIndex]

    def getPhysicalFromLogicalIndex(self, logicalIndex):
        """
        :param int logicalIndex: the logical (sparse, 5000 -> 6000) subtarget
            index
        :return: The physical (contiguous) index.
        :rtype: int
        """
        return self.indices().index(logicalIndex)

    def getLogicalIndexFromValue(self, value):
        """
        :param float value: the 0.0 -> 1.0 subtarget value (ratio)
        :return: The matching logical (sparse, 5000 -> 6000) index.
        :rtype: int
        """
        value = round(value, 3)
        value *= 1000
        value = int(value)
        logicalIndex = 5000 + value

        if logicalIndex in self.indices():
            return logicalIndex

        raise ValueError("No matching logical index found.")

    def getValueFromLogicalIndex(self, logicalIndex):
        """
        :param int logicalIndex: the sparse, 5000 -> 6000 subtarget index
        :return: The matching tween value (ratio).
        :rtype: float
        """
        if logicalIndex in self.indices():
            return round((logicalIndex-5000) / 1000, 3)

        raise IndexError(
            "Couldn't find logical index {}.".format(logicalIndex))

    def values(self):
        """
        :return: The subtarget (tween) values (ratios).
        :rtype: [float]
        """
        return [subtargetIndexToValue(index) for index in self.indices()]

    def indices(self):
        """
        :return: The logical (sparse, 5000 -> 6000) target indices.
        :rtype: [int]
        """
        return self.inputTargetItem.getArrayIndices()

    def getByLogicalIndex(self, logicalIndex):
        """
        Retrieves a subtarget (tween) by logical (sparse, 5000 -> 6000) index.

        :param int logicalIndex: the logical subtarget index
        :return: The subtarget.
        :rtype: :class:`Subtarget`
        """
        return Subtarget(logicalIndex, self)

    def getByPhysicalIndex(self, physicalIndex):
        """
        Retrieves a subtarget (tween) by logical (contiguous) index.

        :param physicalIndex: the physical subtarget index
        :return: The subtarget.
        :rtype: :class:`Subtarget`
        """
        logicalIndex = self.getLogicalFromPhysicalIndex(physicalIndex)
        return Subtarget(logicalIndex, self)

    def getByValue(self, value):
        """
        Retrieves a subtarget (tween) by value (ratio).

        :param float value: the value (ratio)
        :return: The subtarget.
        :rtype: :class:`Subtarget`
        """
        logicalIndex = self.getLogicalIndexFromValue(value)
        return Subtarget(logicalIndex, self)

    def __len__(self):
        """
        :return: The number of subtargets (number of inbetweens + 1)
        :rtype: int
        """
        raise NotImplementedError

    def __iter__(self):
        """
        Yields :class:`Subtarget` instances.
        """
        for logicalIndex in self.indices():
            yield Subtarget(logicalIndex, self)

    def __getitem__(self, logicalIndexOrValue):
        """
        Retrieves subtargets by logical (5000 -> 6000) index or value (ratio).

        :param logicalIndexOrValue: the value or logical index
        :type logicalIndexOrValue: float, int
        :return: The subtarget.
        :rtype: :class:`Subtarget`
        """
        if isinstance(logicalIndexOrValue, float):
            logicalIndex = self.getLogicalIndexFromValue(logicalIndexOrValue)

        elif isinstance(logicalIndexOrValue, int):
            logicalIndex = logicalIndexOrValue

        else:
            raise TypeError(
                "Not an integer or float: {}".format(logicalIndexOrValue)
            )

        if logicalIndex in self.indices():
            return Subtarget(logicalIndex, self)

        raise IndexError(
            "Logical index doesn't exist: {}".format(logicalIndex))

    #--------------------------------------------------------|    Member additions

    @short(relative='rel', topologyCheck='tc')
    def add(self, value, geometry, relative=False, topologyCheck=False):
        """
        Adds a subtarget (tween) at the specified value (ratio).

        :param float value: the value at which to add the subtarget
        :param geometry: the geometry shape to assign
        :param bool topologyCheck/tc: check topology before applying; defaults
            to False
        :param bool relative/rel: create a 'relative' inbetween target;
            defaults to False
        :raises RuntimeError: the requested value (ratio) is already in use
        :return: The new Subtarget instance.
        :rtype: :class:`Subtarget`
        """
        value = round(float(value), 3)

        if value in self.values():
            raise RuntimeError("Value already in use: {}".format(value))

        bsn = self.node()
        base = bsn.getBaseObjects()[0]

        kwargs = {}

        dm = self.inputTargetGroup.attr('postDeformersMode').get()

        if dm is 1:
            kwargs['tangentSpace'] = True

        elif dm is 2:
            kwargs['transform'] = self.getTransform()

        r.blendShape(
            bsn,
            e=True,
            ib=True,
            tc=topologyCheck,
            ibt='relative' if relative else 'absolute',
            t=[base, self.index(), geometry, value],
            **kwargs
        )

        if dm in (1, 2):
            # Disconnect shape
            plug = self.inputTargetItem[
                self.getLogicalIndexFromValue(value)].attr('inputGeomTarget')

            plug.disconnect(inputs=True)

        return self[value]

    #--------------------------------------------------------|    Member setting / updating

    def __setitem__(self, valueOrLogicalIndex, shape):
        if isinstance(valueOrLogicalIndex, int):
            value = subtargetIndexToValue(valueOrLogicalIndex)

        elif isinstance(valueOrLogicalIndex, float):
            value = round(valueOrLogicalIndex, 3)

        else:
            raise TypeError(
                "Not an integer or float: {}".format(valueOrLogicalIndex)
            )

        if value in self.values():
            subtarget = self.getByValue(value)
            subtarget.setShape(shape)

        else:
            self.add(value, shape)

    #--------------------------------------------------------|    Member removals

    def remove(self, subtarget):
        """
        Removes a subtarget.

        :param subtarget: The subtarget to remove.
        :type subtarget: :class:`Subtarget`
        :return: ``self``
        :rtype: :class:`Target`
        """
        return self.removeByLogicalIndex(subtarget.index())

    def removeByLogicalIndex(self, logicalIndex):
        """
        Removes the subtarget (tween) at the specified logical index. The
        main subtarget (at 6000 / 1.0) can't be removed; use remove() on
        :class:`Targets` instead.

        :param int logicalIndex: the logical (sparse / occupied, 5000 -> 6000)
            subtarget index
        :return: ``self``
        :rtype: :class:`Target`
        """
        cmd = 'blendShapeDeleteInBetweenTarget "{}" {} {}'.format(
            self.node(),
            self.index(),
            logicalIndex
        )

        mel.eval(cmd)

        return self

    def removeByPhysicalIndex(self, physicalIndex):
        """
        Removes the subtarget (tween) at the specified physical index. The
        main subtarget can't be removed; use remove() on :class:`Targets`
        instead.

        :param int physicalIndex: the physical (contiguous) subtarget index
        :return: ``self``
        :rtype: :class:`Target`
        """
        logicalIndex = self.getLogicalFromPhysicalIndex(physicalIndex)
        return self.removeByLogicalIndex(logicalIndex)

    def removeByValue(self, value):
        """
        Removes the subtarget (tween) at the specified value (ratio). The
        main subtarget (at 1.0) can't be removed; use remove() on
        :class:`Targets` instead.

        :param float value: the subtarget (tween) value (ratio)
        :return: ``self``
        :rtype: :class:`Target`
        """
        logicalIndex = self.getLogicalIndexFromValue(value)
        return self.removeByLogicalIndex(logicalIndex)

    def clearInbetweens(self):
        """
        Removes all inbetweens.

        :return: ``self``
        :rtype: :class:`Target`
        """
        indices = self.indices()

        if len(indices) > 1:
            for index in indices[:-1]:
                self.removeByLogicalIndex(index)

        return self

    def __delitem__(self, valueOrLogicalIndex):
        """
        Removes a subtarget by logical (sparse / occupied, 5000 -> 6000) index
        or value (ratio).

        :param valueOrLogicalIndex: The value or logical index.
        :type valueOrLogicalIndex: float, int
        """
        if isinstance(valueOrLogicalIndex, int):
            return self.removeByLogicalIndex(valueOrLogicalIndex)

        elif isinstance(valueOrLogicalIndex, float):
            return self.removeByValue(valueOrLogicalIndex)

        else:
            raise TypeError(
                "Not an integer or float: {}".format(valueOrLogicalIndex)
            )

    #--------------------------------------------------------|    Conversions

    def __int__(self):
        """
        :return: The logical (sparse) index for this target group.
        """
        return self.index()

    #--------------------------------------------------------|    Repr

    def __repr__(self):
        alias = self.alias

        if alias:
            content = repr(alias)

        else:
            content = self.index()

        return '{}[{}]'.format(self.owner, content)


class Targets:
    """
    Interface for editing blend shape targets, available on
    :class:`~paya.runtime.nodes.BlendShape` instances as ``.targets`` /
    ``.t``.

    .. rubric:: Retrieving Targets

    .. code-block:: python

        # Iteration
        for target in bsn.targets:
            # do something

        # Listing
        list(bsn.targets)

        # By logical (sparse / occupied) index:
        target = bsn.targets.getByLogicalIndex(logicalIndex)
        # or:
        target = bsn.targets[logicalIndex]

        # By physical (contiguous) index:
        target = bsn.targets.getByPhysicalIndex(physicalIndex)
        # or:
        target = list(bsn.targets)[physicalIndex]

        # By alias:
        target = bsn.targets.getByAlias(alias)
        # or:
        target = bsn.targets[alias]

    .. rubric:: Adding Targets

    .. code-block:: python

        target = bsn.targets.add(geometry)
        # or
        target[alias] = geometry

    See :meth:`add` for more options.

    .. rubric:: Removing Targets

    Use :meth:`removeByPhysicalIndex`, :meth:`removeByLogicalIndex`,
    :meth:`removeByAlias`, :meth:`__delitem__` or :meth:`clear`:

    .. code-block:: python

        # By logical index:
        bsn.targets.removeByLogicalIndex(logicalIndex)
        # or
        del(bsn.targets[logicalIndex])

        # By physical index
        bsn.targets.removeByPhysicalIndex(physicalIndex)

        # By instance
        target = bsn.targets.add(geometry)
        bsn.targets.remove(target)

        # By alias
        bsn.targets.removeByAlias('L_smile')
        # or
        del(bsn.targets['L_smile'])

        # Clear all targets
        bsn.clear()

    See :class:`Target` for additional methods for subtargets (tweens) etc.
    """

    #--------------------------------------------------------|    Init

    def __init__(self, owner):
        self._owner = owner

    @property
    def owner(self):
        return self._owner

    #--------------------------------------------------------|    Basic inspections

    def node(self):
        """
        :return: The owner blend shape node.
        :rtype: :class:`~paya.runtime.nodes.BlendShape`
        """
        return self.owner

    #-------------------------------------------------------|    Member retrievals

    def getLogicalIndexFromAlias(self, alias):
        """
        Given an alias, returns the associated logical (sparse / in-use)
        target index.

        :param str alias: the target alias
        :return: The logical (sparse / in-use) target index.
        :rtype: int
        """
        return dict(self.node().listAliases())[alias].index()

    def getLogicalFromPhysicalIndex(self, physicalIndex):
        """
        :param physicalIndex: the physical (contiguous) target index
        :return: The logical (sparse / occupied) index.
        :rtype: int
        """
        return self.indices()[physicalIndex]

    def getPhysicalFromLogicalIndex(self, logicalIndex):
        """
        :param logicalIndex: the logical (sparse / occupied) target index
        :return: the physical (contiguous) index
        :rtype: int
        """
        return self.indices().index(logicalIndex)

    def getAliasFromLogicalIndex(self, index):
        """
        Given a logical (sparse / in-use) target index, returns the alias.

        :param int index: the logical (sparse / in-use) target index
        :return: The target alias.
        :rtype: str or None
        """
        return self.node().attr('weight')[index].getAlias()

    def getByAlias(self, alias):
        """
        :param alias: the alias for the target
        :return: The target.
        :rtype: :class:`Target`
        """
        logicalIndex = self.getLogicalIndexFromAlias(alias)
        return Target(logicalIndex, self)

    def getByLogicalIndex(self, logicalIndex):
        """
        :param logicalIndex: the logical (sparse / occupied) index for
            the target
        :raises IndexError: the index doesn't exist
        :return: The target.
        :rtype: :class:`Target`
        """
        if logicalIndex in self.indices():
            return Target(logicalIndex, self)

        raise IndexError(
            "Logical index not found: {}".format(logicalIndex)
        )

    def getByPhysicalIndex(self, physicalIndex):
        """
        :param logicalIndex: the physical (listed) index for the target
        :raises IndexError: the index doesn't exist
        :return: The target.
        :rtype: :class:`Target`
        """
        logicalIndex = self.getLogicalFromPhysicalIndex(physicalIndex)
        return Target(logicalIndex, self)

    def aliases(self):
        """
        :return: All available target aliases. ``None`` aliases are skipped.
        :rtype: [str]
        """
        bsn = self.node()
        weight = bsn.attr('weight')
        out = []

        for index in weight.getArrayIndices():
            plug = weight[index]
            alias = plug.getAlias()

            if alias is None:
                continue

            out.append(alias)

        return out

    def indices(self):
        """
        :return: Logical (sparse) indices for the targets.
        :rtype: [int]
        """
        return self.node().attr('weight').getArrayIndices()

    def __getitem__(self, aliasOrLogicalIndex):
        """
        Retrieves a target by alias or logical (sparse / occupied) index.

        :param aliasOrLogicalIndex: the alias or logical (sparse /
            occupied) index
        :type aliasOrLogicalIndex: str, int
        :return: The target.
        :rtype: :class:`Target`
        """
        if isinstance(aliasOrLogicalIndex, str):
            logicalIndex = self.getLogicalIndexFromAlias(aliasOrLogicalIndex)

        else:
            logicalIndex = aliasOrLogicalIndex

        if logicalIndex in self.indices():
            return Target(logicalIndex, self)

        raise IndexError(
            "Logical index couldn't be found: {}".format(logicalIndex)
        )

    def __len__(self):
        """
        :return: The number of targets.
        :rtype: int
        """
        return self.node().attr('weight').numElements()

    def __iter__(self):
        """
        Yields :class:`Target` instances.
        """
        for index in self.indices():
            yield Target(index, self)

    #-------------------------------------------------------|    Member additions

    @short(
        alias='a',
        topologyCheck='tc',
        transform='tr',
        tangentSpace='ts',
        initWeight='iw',
        index='i'
    )
    def add(
            self,
            targetGeo,
            alias=None,
            topologyCheck=False,
            transform=None,
            tangentSpace=None,
            initWeight=0.0,
            index=None
    ):
        """
        Adds a blend shape target.

        :param targetGeo: the target geometry
        :type targetGeo: str, :class:`~paya.runtime.nodes.GeometryShape`,
            :class:`~paya.runtime.nodes.Transform`
        :param alias: an optional alias for the target; if omitted, defaults
            to the geometry's base name
        :type alias: None, str
        :param bool topologyCheck/tc: check topology when applying; defaults
            to False
        :param transform/tr: if this is provided, and the blend shape node is
            in 'post-deformation' mode, a transform-space target will be
            configured; defaults to None
        :type transform/tr: None, str, :class:`~paya.runtime.nodes.DagNode`
        :param bool tangentSpace/ts: if the blend shape node is in
            'post-deformation' mode, configure a tangent-space target;
            defaults to False
        :param float initWeight/iw: the blend shape weight value on
            creation; defaults to 0.0
        param int index/i: a preferred logical (sparse) index for the target;
            this mustn't already exist; if omitted, defaults to the next non-
            contiguous index.
        :raises RuntimeError:
            -   both *transform* and *tangent* were specified
            -   either *transform* or *tangent* were specified and the blend
                shape node is not in 'post-deformation' mode
            -   the requested or derived alias is already in use
            -   the requested logical index is already in use
        :return: The target instance.
        :rtype: :class:`Target`
        """
        #----------------------------------------|    Prep / early erroring

        bsn = self.node()
        post = bsn.inPostMode()

        # Resolve index
        if index is None:
            index = bsn.attr('weight').getNextArrayIndex()

        elif index in bsn.attr('weight').getArrayIndices():
            raise RuntimeError(
                "Logical index already in use: {}".format(index)
            )

        # Resolve alias
        if alias is None:
            geoShape = r.PyNode(targetGeo).toShape()
            geoXf = geoShape.getParent()
            alias = geoXf.basename(sns=True)

        existingAliases = [pair[0] for pair in bsn.listAliases()]

        if alias in existingAliases:
            raise ValueError(
                "Alias in use: '{}'".format(alias)
            )

        # Resolve space
        kwargs = {}

        if post:
            if transform:
                if tangentSpace:
                    raise ValueError(
                        "Transforms can't be assigned in tangent space."
                    )

                kwargs['transform'] = transform

            else:
                if tangentSpace is not None:
                    if not tangentSpace:
                        raise ValueError(
                            "The blend shape node is in post-deformation "+
                            "mode, and no transform was specified. "+
                            "Therefore tangentSpace must be allowed "+
                            "to default to True."
                        )

                kwargs['tangentSpace'] = True

        elif transform or tangentSpace:
            raise ValueError(
                "The blend shape node is not in post-deformation mode."
            )

        # Run the command
        r.blendShape(
            bsn,
            e=True,
            t=[bsn.getBaseObjects()[0], index, targetGeo, 1.0],
            w=[index, initWeight],
            **kwargs
        )

        # Post-config
        if post:
           bsn.attr('inputTarget')[0].attr('inputTargetGroup'
                )[index].attr('inputTargetItem')[6000].attr(
                'inputGeomTarget').disconnect()

        currentAlias = bsn.attr('weight')[index].getAlias()

        if currentAlias is None or currentAlias != alias:
            bsn.attr('weight')[index].setAlias(alias)

        return Target(index, self)

    #-------------------------------------------------------|    Member setting / replacement

    def __setitem__(self, aliasOrLogicalIndex, shape):
        """
        Performs quick target editing via direct geometry assignments. Note
        that, if a matching item is found, any existing inbetween shapes will
        be removed. To preserve them, perform the same operation on a
        subtarget via :class:`Target` instead.

        :param aliasOrLogicalIndex: the target alias or logical
            (sparse / occupied) index
        :type aliasOrLogicalIndex: str, int
        :param shape: the shape to assign
        :type shape: str, :class:`~paya.runtime.nodes.GeometryShape`,
            :class:`~paya.runtime.nodes.Transform`,
        """
        if isinstance(aliasOrLogicalIndex, int):
            logicalIndex = aliasOrLogicalIndex
            alias = None

        elif isinstance(aliasOrLogicalIndex, str):
            logicalIndex = self.getLogicalIndexFromAlias(aliasOrLogicalIndex)
            alias = aliasOrLogicalIndex

        else:
            raise TypeError(
                "Not a string or integer: {}".format(aliasOrLogicalIndex)
            )

        if logicalIndex in self.indices():
            target = self.getByPhysicalIndex(logicalIndex)
            target.clearInbetweens()
            target[1.0].setShape(shape)

        else:
            self.add(shape, alias=alias, index=logicalIndex)

    #-------------------------------------------------------|    Member removal

    def removeByAlias(self, alias):
        """
        Removes a target by alias.

        :param str alias: the target alias
        :return: ``self``
        :rtype: :class:`Targets`
        """
        logicalIndex = self.getLogicalIndexFromAlias(alias)
        return self.removeByLogicalIndex(logicalIndex)

    def removeByPhysicalIndex(self, physicalIndex):
        """
        Removes a target by physical (contiguous) index.

        :param int logicalIndex: the physical (contiguous) index
        :return: ``self``
        :rtype: :class:`Targets`
        """
        logicalIndex = self.getLogicalFromPhysicalIndex(physicalIndex)
        return self.removeByLogicalIndex(logicalIndex)

    def removeByLogicalIndex(self, logicalIndex):
        """
        Removes a target by logical (sparse / occupied) index.

        :param int logicalIndex: the logical (sparse / occupied) index
        :return: ``self``
        :rtype: :class:`Targets`
        """
        cmd = 'blendShapeDeleteTargetGroup "{}" {}'.format(self.node(), logicalIndex)
        mel.eval(cmd)
        return self

    def remove(self, target):
        """
        Removes a target.

        :param target: the target to remove
        :type target: :class:`Target`
        :return: ``self``
        :rtype: :class:`Targets`
        """
        logicalIndex = target.index()
        return self.removeByLogicalIndex(logicalIndex)

    def __delitem__(self, aliasOrLogicalIndex):
        """
        Removes a target by alias or logical (sparse / occupied) index.

        :param aliasOrLogicalIndex: the alias or logical index
        :type aliasOrLogicalIndex: str, int
        """
        if isinstance(aliasOrLogicalIndex, str):
            logicalIndex = self.getLogicalIndexFromAlias(aliasOrLogicalIndex)

        else:
            logicalIndex = aliasOrLogicalIndex

        self.removeByLogicalIndex(logicalIndex)

    def clear(self):
        """
        Removes all targets.

        :return: ``self``
        :rtype: :class:`Targets`
        """
        for index in self.indices():
            self.removeByLogicalIndex(index)

        return self

    #-------------------------------------------------------|    Repr

    def __repr__(self):
        return "{}.targets".format(repr(self.owner))
