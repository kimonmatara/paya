import paya.runtime as r
from paya.lib.bsnboltons import Targets
from paya.util import short, resolveFlags


class BlendShape:
    """
    Use the :class:`.targets <paya.lib.bsnboltons.Targets>` / ``.t`` interface
    to edit targets. See :class:`~paya.lib.bsnboltons.Targets`.

    Instead of passing complete Maya arguments to :meth:`create`, it may be
    easier to reserve the constructor for base initialisation and use
    :class:`.targets <paya.lib.bsnboltons.Targets>` for everything else:

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
        after='af',
        afterReference='ar'
    )
    def create(
            cls,
            *args,
            name=None,
            post=False,
            pre=False,
            after=False,
            automatic=False,
            parallel=False,
            before=False,
            split=False,
            frontOfChain=False,
            afterReference=False,
            **kwargs
    ):
        """
        Wrapper for :func:`~pymel.core.animation.blendShape`. Two new flags,
        ``pre`` and ``post``, can be used for easier / clearer configuration of
        the two mos common configurations (pre-deformation and post-
        deformation). When provided, they will override all the standard Maya
        deformation options.

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
            *   - 'After Reference'
                - afterReference
                - For ref-friendly boundary
        """
        deformOrderFlags = cls._resolveDeformOrderFlags(
            post=post, pre=pre, automatic=automatic,
            frontOfChain=frontOfChain, before=before,
            split=split, parallel=parallel,
            afterReference=afterReference
        )

        kwargs.update(deformOrderFlags)
        name = cls.makeName(name)
        kwargs['name'] = name

        return r.blendShape(*args, **kwargs)[0]

    @staticmethod
    def _resolveDeformOrderFlags(
            post=False,
            pre=False,
            automatic=False,
            frontOfChain=False,
            before=False,
            after=False,
            split=False,
            parallel=False,
            afterReference=False
    ):
        out = {}

        if post:
            out['before'] = True

        elif pre:
            out['frontOfChain'] = True

        else:
            if not any([automatic, frontOfChain, before,
                        after, split, parallel, afterReference]):
                out['automatic'] = True

            else:
                for name, value in zip(
                    ['automatic', 'frontOfChain', 'before',
                        'after', 'split', 'parallel', 'afterReference'],
                    [automatic, frontOfChain, before, after,
                            split, parallel, afterReference]
                ):
                    if value:
                        out[name] = value

        return out

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