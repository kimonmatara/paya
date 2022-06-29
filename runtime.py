class Runtime:
    """
    Top-level **paya** interface. This object serves the entire
    :py:mod:`paya.cmds` namespace which, in turn, imports the full contents
    of :py:mod:`pymel.core`. Hence, it can be used as a drop-in replacement
    for :py:mod:`pymel.core`:

    .. code-block:: python

        >>> import paya.runtime as r
        >>> cube = r.PyNode('pCube1')

    Custom **paya** classes should always be retrieved via this object's
    ``nodes``, ``plugs``, ``comps`` and ``data`` attributes, whether to access
    a custom constructor method or for superclass calls inside template
    classes.

    If ``patchOnLoad`` is set to ``True`` inside :py:mod:`paya.config`, PyMEL
    will be patched to return **paya** types when this module is first
    imported.
    """

    def __init__(self):

        from paya import patch
        self._pt = patch

        import paya.config as config

        if config['patchOnLoad']:
            self.start()

        self.config = config

        import paya.cmds
        self.cmds = paya.cmds

        from paya.pools import pools

        for pool in pools:
            setattr(self, pool.shortName, pool)

        self._pools = pools

    def rehash(self):
        """
        Reloads :py:mod:`paya.cmds` and clears the custom class caches,
        so that subsequent retrievals will trigger reloads.
        """
        from importlib import reload
        reload(self.cmds)

        for pool in self._pools:
            pool.purge()

    def start(self):
        """
        Patches PyMEL to return custom paya types.
        """
        self._pt.patchPyMEL()

    def stop(self):
        """
        Restores PyMEL to its 'factory' state.
        """
        self._pt.unpatchPyMEL()

    @property
    def createControl(self):
        return self.nodes.Transform.createControl

    def __getattr__(self, item):
        return getattr(self.cmds, item)

    def __repr__(self):
        return "<paya runtime: {}>".format(
            'active' if self._pt.pyMELIsPatched else 'inactive')

inst = Runtime()

import sys
sys.modules['paya.runtime'] = inst