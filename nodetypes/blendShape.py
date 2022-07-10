import paya.runtime as r
from paya.lib.bsntargets import Targets
from paya.util import short, resolveFlags

#---------------------------------------------------------------------------|    Class

class BlendShape:
    """
    Use the :class:`.targets <paya.lib.bsntargets.Targets>` / ``.t`` attribute
    to edit targets.

    Instead of passing complete Maya arguments to :meth:`create`, it may be
    easier to reserve the constructor for base initialisation and use
    :class:`.targets <paya.lib.bsntargets.Targets>` for everything else:

    .. code-block:: python

        bsn = r.nodes.BlendShape.create(baseGeo, pre=True)
        bsn.targets.add(sadGeo)
        bsn.targets.add(happyGeo)
        # etc.
    """

    @property
    def targets(self):
        return Targets(self)

    t = targets

    #-----------------------------------------------------------------------|    Constructor

    @classmethod
    @short(
        name='n',
        frontOfChain='foc',
        parallel='par',
        split='sp',
        before='bf',
        after='af'
    )
    def create(cls, *args, name=None, post=None, pre=None, **kwargs):
        """
        Wrapper for :func:`~pymel.core.animation.blendShape`. Adds managed
        naming and simpler deformation order management via 'post' and 'pre'.

        :param \*args: forwarded to :func:`~pymel.core.animation.blendShape`
        :param name/n: one or more name elements; defaults to None
        :type name/n: int, str, None, list, tuple
        :param bool post: if True, set all deformation flags for post-
            deformation; defaults to False
        :param bool pre: if True, set all deformation flags for pre-
            deformation; defaults to False
        :param \*\*kwargs: forwarded to
            :func:`~pymel.core.animation.blendShape`
        :return: The blend shape node.
        :rtype: :class:`~BlendShape`

        If you'd rather skip 'post' / 'pre' and use the standard Maya flags,
        here's a reference:

        .. list-table::
            :header-rows: 1

            *   - UI Option
                - Command Flag
                - Description
            *   - 'Automatic'
                - -automatic
                - Maya makes a guess.
            *   - 'Pre-deformation'
                - -frontOfChain
                - Pre-skin (typical use)
            *   - 'Post-deformation'
                - -before
                - Post-skin, same end shape
            *   - 'After'
                - -after
                - Post-skin, new end shape
            *   - 'Split'
                - -split
                - Deforms origShape into new end shape
            *   - 'Parallel'
                - -parallel
                - Deforms origShape, adds-in with second blend
        """
        post, pre = resolveFlags(post, pre)

        if post and pre:
            post = pre = None

        def clearOrder():
            for key in [
                'automatic',
                'frontOfChain',
                'after',
                'split',
                'parallel',
                'before'
            ]:
                try:
                    del(kwargs[key])

                except KeyError:
                    pass

        if post:
            clearOrder()
            kwargs['before'] = True

        elif pre:
            clearOrder()
            kwargs['frontOfChain'] = True

        name = cls.makeName(name)
        kwargs['name'] = name
        return r.blendShape(*args, **kwargs)[0]

    #-----------------------------------------------------------------------|    Misc

    def getIndexFromAlias(self, alias):
        """
        :param str alias: the target alias
        :return: The matching index.
        :rtype: int
        """
        weights = self.attr('weight')

        for index in weights.getArrayIndices():
            if weights[index].getAlias() == alias:
                return index

        raise ValueError(
            "Couldn't find a matching index for '{}'.".format(alias)
        )

    def inPostMode(self):
        """
        :return: True if the blend shape node is configured for
            'post-deformation', otherwise False.
        :rtype: bool
        """
        return self.attr('deformationOrder').get() is 1