"""
This module is not for direct import / use. It defines the ``.targets``
interface on :class:`~paya.runtime.nodes.BlendShape`.
"""
import maya.mel as mel
mel.eval('source doBlendShapeAddTarget')
from paya.util import short
import paya.runtime as r

#---------------------------------------------------------------------------|    Helpers

def subtargetIndexToValue(index):
    return round((index-5000) / 1000, 3)

def subtargetValueToIndex(weight):
    weight = round(weight, 3)
    weight *= 1000
    weight = int(weight)
    return 5000 + weight

#---------------------------------------------------------------------------|    Subtarget

class Subtarget:

    #--------------------------------------------------------|    Init

    def __init__(self, index, owner):
        self._index = index
        self._owner = owner

    #--------------------------------------------------------|    Basic inspections

    @property
    def index(self):
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

    #--------------------------------------------------------|    Repr

    def __repr__(self):
        return '{}[{}]'.format(self.owner, self.value)

#---------------------------------------------------------------------------|    Target

class Target:

    #--------------------------------------------------------|    Init

    def __init__(self, index, owner):
        self._index = index
        self._owner = owner

    #--------------------------------------------------------|    Basic inspections

    @property
    def index(self):
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

    #--------------------------------------------------------|    Misc

    def resetDelta(self):
        bsn = self.node()
        r.blendShape(bsn, e=True, rtd=[0, self.index])

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
        Sets the alias for this blend shape target. Setter for ``alias``
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
        Equivalent to ``setAlias(None)``. Deleter for ``alias`` property.

        :return: ``self``
        :rtype: :class:`Target`
        """
        self.setAlias(None)

    alias = property(fget=getAlias, fset=setAlias, fdel=clearAlias)

    #--------------------------------------------------------|    Member access

    def indices(self):
        """
        :return: The 5000 -> 6000 indices of 'tweens' (subtargets) for this
            target.
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

    def __getitem__(self, value):
        index  = subtargetValueToIndex(value)

        if index in self.indices():
            return Subtarget(index, self)

        raise IndexError(
            "No subtarget found at value {}.".format(value)
        )

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

    #--------------------------------------------------------|    Member access

    def indices(self):
        """
        :return: The target indices.
        :rtype: [int]
        """
        return self.owner.attr('weight').getArrayIndices()

    def nextIndex(self):
        """
        :return: The next available target index.
        :rtype: int
        """
        indices = self.owner.attr('weight').getArrayIndices()

        if indices:
            return indices[-1] + 1

        return 0

    def aliases(self):
        """
        :return: The target aliases.
        :rtype: [str] or [None]
        """
        plug = self.owner.attr('weight')
        indices = plug.getArrayIndices()

        return [plug[i].getAlias() for i in indices]

    def __getitem__(self, aliasOrIndex):
        if isinstance(aliasOrIndex, int):
            index = aliasOrIndex

            if index in self.indices():
                return Target(index, self)

            else:
                raise IndexError("Index {} doesn't exist.".format(index))

        elif isinstance(aliasOrIndex, str):
            index = self.aliases().index(aliasOrIndex)

        return Target(index, self)

    def __len__(self):
        return self.owner.attr('weight').numElements()

    def __iter__(self):
        for index in self.indices():
            yield Target(index, self)

    #--------------------------------------------------------|    Member additions

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
            initWeight=0.0
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
        :raises RuntimeError:

            -   both *transform* and *tangent* were specified, or
            -   either *transform* or *tangent* were specified and the blend
                shape node is not in 'post-deformation' mode
        :return: The target instance.
        :rtype: :class:`Target`
        """
        bsn = self.node()
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
                "Alias '{}' is already in use.".format(alias)
            )

        index = self.nextIndex()

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

    #--------------------------------------------------------|    Repr

    def __repr__(self):
        return "{}.targets".format(repr(self.owner))


