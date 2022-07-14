from paya.util import short
import paya.runtime as r

flags = ['about', 'allowPartial', 'axis', 'preserveSeam',
         'reset', 'seamFalloffCurve', 'seamTolerance',
         'symmetry', 'tolerance', 'topoSymmetry']

class SymmetricModelling:
    """
    Context manager. Applies overrides via
    :func:`~pymel.internal.pmcmds.symmetricModelling` and reverts them on
    block exit. Can also be used to bracket settings around routines that
    might affect them, for example the symmetry-flipping modes of
    :func:`~pymel.core.animation.blendShape`.
    """

    @short(symmetry='s')
    def __init__(self, **overrides):
        """
        :param \*\*overrides: flags for :func:`~pymel.internal.pmcmds.symmetricModelling`,
            in long or shorthand form
        """
        self.overrides = overrides

        symmetry = overrides.pop('symmetry', None)

        if symmetry is None:
            if overrides:
                overrides['symmetry'] = True

        else:
            overrides['symmetry'] = symmetry

    def __enter__(self):
        self.before = {flag: r.symmetricModelling(
            q=True, **{flag: True}) for flag in flags}

        r.symmetricModelling(e=True, **self.overrides)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        topoSymmetry = self.before.pop('topoSymmetry')

        if topoSymmetry:
            self.before['topoSymmetry'] = True

        for k, v in self.before.items():
            r.symmetricModelling(e=True, **{k: v})

        return False