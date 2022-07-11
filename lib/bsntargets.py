"""
This module is not for direct import / use. It defines the ``.targets``
interface on :class:`~paya.runtime.nodes.BlendShape`.
"""
import maya.mel as mel
from paya.util import short
import paya.runtime as r

#---------------------------------------------------------------------------|    Helpers

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

#---------------------------------------------------------------------------|    Subtarget

class Subtarget:

    #--------------------------------------------------------|    Init

    def __init__(
            self,
            index, # logical (in-use / sparse), 5000 -> 6000
            owner
    ):
        self._index = index
        self._owner = owner

    #--------------------------------------------------------|    Basic inspections

    @property
    def index(self): # logical (in-use / sparse), 5000 -> 6000
        return self._index

    @property
    def owner(self):
        return self._owner

    @property
    def node(self):
        return self.owner.node

    @property
    def value(self):
        return subtargetIndexToValue(self.index)

    @property
    def inputTargetItem(self):
        return self.owner.inputTargetItem[self.index]

    iti = inputTargetItem

    @property
    def geoInput(self):
        return self.inputTargetItem.attr('inputGeomTarget')

    #--------------------------------------------------------|    Geometry management

    def getShape(self):
        """
        :return: The shape connected into this target. This may be None if
            this is a 'post' mode target, or if targets were disconnected or
            deleted by the rigger.
        :rtype: :class:`~paya.runtime.nodes.GeometryShape`
        """
        inputs = self.geoInput.inputs(plugs=True)

        if inputs:
            return inputs[0].node()

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
        return '{}[{}]'.format(self.owner, self.value)

#---------------------------------------------------------------------------|    Target

class Target:

    #--------------------------------------------------------|    Init

    def __init__(
            self,
            index, # logical (sparse / in-use)
            owner
    ):
        self._index = index
        self._owner = owner

    #--------------------------------------------------------|    Basic inspections

    @property
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
        return self.node().attr('weight')[self.index]

    @property
    def inputTargetGroup(self):
        return self.node().attr('inputTarget'
            )[0].attr('inputTargetGroup')[self.index]

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

    #--------------------------------------------------------|    Member retrieval

    def indices(self):
        """
        :return: The 5000 -> 6000 logical (sparse) indices of 'tweens'
            (subtargets) for this target.
        :rtype: [int]
        """
        return self.inputTargetItem.getArrayIndices()

    def values(self):
        """
        :return: The values (ratios) of the 'tweens' (subtargets) for this
            target.
        :rtype: [float]
        """
        return [subtargetIndexToValue(index) for index in self.indices()]

    def __iter__(self):
        for index in self.indices():
            yield Subtarget(index, self)

    def __len__(self):
        return self.inputTargetItem.numElements()

    def __getitem__(self, item):
        """
        :param item: the subtarget to retrieve, specified either as a
            5000 -> 6000 logical (sparse / in-use) index *or* a float value
            (weight)
        :type item: float, int
        :return: The subtarget.
        :rtype: :class:`Subtarget`
        """
        if isinstance(item, int):
            index = item
            weight = None

        elif isinstance(item, float):
            weight = item
            index = subtargetValueToIndex(item)

        else:
            raise TypeError(
                "Not a weight (float) or logical index (int): {}".format(item)
            )

        if index in self.indices():
            return Subtarget(index, self)

        if weight is None:
            raise IndexError("Couldn't find logical index {}.".format(index))

        raise ValueError("Subtarget weight {} doesn't exist.".format(weight))

    #--------------------------------------------------------|    Repr

    def __int__(self):
        return self.index

    def __repr__(self):
        alias = self.alias

        if alias:
            content = repr(alias)

        else:
            content = self.index

        return '{}[{}]'.format(self.owner, content)


#---------------------------------------------------------------------------|    Targets

class Targets:

    """
    Interface for editing blend shape targets; available on
    :class:`~paya.runtime.nodes.BlendShape` as ``targets`` or ``t``.
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

    def getIndexFromAlias(self, alias):
        """
        Given an alias, returns the associated logical (sparse / in-use)
        target index.

        :param str alias: the target alias
        :return: The logical (sparse / in-use) target index.
        :rtype: int
        """
        return dict(self.node().listAliases())[alias].index()

    def getAliasFromIndex(self, index):
        """
        Given a logical (sparse / in-use) target index, returns the alias.

        :param int index: the logical (sparse / in-use) target index
        :return: The target alias.
        :rtype: str or None
        """
        return self.node().attr('weight')[index].getAlias()

    #--------------------------------------------------------|    Member retrieval

    def indices(self):
        """
        :return: The **logical** (in-use / sparse) target indices.
        :rtype: [int]
        """
        return self.owner.attr('weight').getArrayIndices()

    def aliases(self):
        """
        :return: The target aliases.
        :rtype: [str] or [None]
        """
        plug = self.owner.attr('weight')
        indices = plug.getArrayIndices()

        return [plug[i].getAlias() for i in indices]

    def __getitem__(self, item):
        """
        :param item: this can be an **alias** or a **logical** (sparse) index; to
            access targets by **physical** index, list this object first.
        :type item: str, int
        :raises KeyError: the passed alias couldn't be found
        :raises IndexError: the passed logical index doesn't exist
        :raises TypeError: *item* is neither a string nor an integer
        :return: An instance of :class:`Target`
        """
        if isinstance(item, int):
            index = item

            if index not in self.indices():
                raise IndexError(
                    "Couldn't find logical index {}".format(index))

        elif isinstance(item, str):
            index = self.getIndexFromAlias(item)

        else:
            raise TypeError("Not an index or alias: {}".format(item))

        return Target(index, self)

    def __len__(self):
        return self.owner.attr('weight').numElements()

    def __iter__(self):
        for index in self.indices():
            yield Target(index, self)

    #--------------------------------------------------------|    Member editing

    @short(
        alias='a',
        topologyCheck='tc',
        transform='tr',
        tangentSpace='ts',
        initWeight='iw'
    )
    def add(
            self,
            targetGeo,
            alias=None,
            topologyCheck=False,
            transform=None,
            tangentSpace=False,
            initWeight=0.0,
            index=None
    ):
        """
        Adds a target.

        :param targetGeo: the target geometry
        :type targetGeo: str, :class:`~paya.runtime.nodes.DagNode`
        :param str alias/a: the target alias; if omitted, the geo basename is
            used
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
        #---------------------------------------------|    Prep / early erroring

        bsn = self.node()

        if index is None:
            index = bsn.attr('weight').getNextArrayIndex()

        elif index in bsn.attr('weight').getArrayIndices():
            raise RuntimeError(
                "Logical index already in use: {}".format(index)
            )

        postMode = bsn.inPostMode()

        kwargs = {}

        if postMode:
            if not (transform or tangentSpace):
                tangentSpace = True

            if tangentSpace:
                kwargs['tangentSpace'] = True

                if transform:
                    raise RuntimeError(
                        "Tangent-space was requested, but a transform "+
                        "was passed."
                    )

            else:
                kwargs['transform'] = transform

        shape = r.PyNode(targetGeo).toShape()
        xf = shape.getParent()

        if alias is None:
            alias = xf.basename()

        if alias in self.aliases():
            raise ValueError(
                "Alias already in use: '{}'.".format(alias)
            )

        r.blendShape(
            bsn,
            e=True,
            t=[bsn.getBaseObjects()[0], index, shape, 1.0],
            w=[index, initWeight],
            **kwargs
        )

        target = self[index]

        if postMode:
            target[1.0].geoInput.disconnect(inputs=True)

        target.setAlias(alias)

        return target

    def remove(self, target):
        """
        Removes a target.

        :param target: the target to remove; this can be specified as a
            **logical** (sparse / in-use) index (int), alias (str) or
            :class:`Target` instance
        :type target: int, str, :class:`Target`
        :return: ``self``
        :rtype: :class:`Targets`
        """
        # Wrangle arg

        if isinstance(target, str):
            index = self.getIndexFromAlias(target)

        elif isinstance(target, int):
            index = target

        elif isinstance(target, Target):
            index = int(target)

        else:
            raise TypeError(
                "Not an index, alias or Target: {}".format(target)
            )

        self._remove(index)

        return self

    def _remove(self, index):

        # Transcription of blendShapeDeleteTargetGroup.mel, but doesn't
        # account for 'edit mode' sculpt shapes

        bsn = self.node()
        weightAttr = bsn.attr('weight')[index]

        if weightAttr.isLocked():
            raise RuntimeError("The weight attribute is locked.")

        # Remove combination shape

        try:
            r.delete(weightAttr.inputs(type='combinationShape'))

        except:
            # May have locked them ourselves
            pass

        # Remember the next target of this target
        # This must be done before removing the weight, since it will
        # cause itself removed from the midLayer

        pdAttr = bsn.attr('parentDirectory')[index]
        parentDirectory = pdAttr.get()

        if parentDirectory > 0:
            ciAttr = pdAttr.attr('childIndices')
            childIndices = ciAttr.get()
            location = childIndices.index(index)

            if location != -1 and location + 1 < len(childIndices):
                ntAttr = bsn.attr('nextTarget')[index]
                ntAttr.set(childIndices[location+1])

        # Remove array elements

        for attr in [
            weightAttr,
            pdAttr,
            bsn.attr('nextTarget')[index],
            bsn.attr('targetVisibility')[index],
            bsn.attr('targetParentVisibility')[index],
        ]:
            r.removeMultiInstance(attr, b=True)

        # Remove alias if there is one

        alias = weightAttr.getAlias()

        if alias:
            r.aliasAttr(weightAttr, rm=True)

    def __setitem__(self, item, geo):
        """
        Implements quick target editing via direct geometry assignments. Note
        that, if a matching item is found, any existing inbetween shapes will
        be removed. To preserve them, perform the same operation on a specific
        :class:`Subtarget` instance.

        :param item: a alias or logical index
        :type item: str, int
        :param geo: the geometry to assign
        :type geo: str, :class:`~paya.runtime.nodes.DagNode`
        """
        try:
            self[item].setGeometry(geo)

        except (KeyError, IndexError):
            kwargs = {}

            if isinstance(item, str):
                kwargs['alias'] = item

            elif isinstance(item, int):
                kwargs['index'] = item

            else:
                raise TypeError("Not an index or alias: {}".format(item))

            self.add(geo, **kwargs)

    def __delitem__(self, item):
        """
        :param item: an alias or logical index
        :type item: str, int
        """
        self.remove(item)

    def clear(self):
        """
        Removes all targets.

        :return: self
        :rtype: :class:`Targets`
        """
        for index in self.indices():
            del(self[index])

        return self

    #--------------------------------------------------------|    Repr

    def __repr__(self):
        return "{}.targets".format(repr(self.owner))