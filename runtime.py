class Runtime:
    """
    Main paya interface object.

    The entire paya.cmds (itself importing the whole of pymel.core) namespace
    can be accessed via this object.

    Class pools can be accessed thus:

    .. code-block:: python

        import paya.runtime as r

        r.nodetypes
        r.plugtypes
        r.comptypes
        r.datatypes
    """

    def __init__(self):

        from paya import patch
        self._pt = patch

        from paya import config

        if config.patchOnLoad:
            self.start()

        import paya.cmds
        self.cmds = paya.cmds

        from paya.pools import pools

        for pool in pools:
            setattr(self, pool.shortName, pool)

        self._pools = pools

    def rehash(self):
        """
        Reloads paya.cmds and the class modules.
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
        Restores PyMEL to its factory state.
        """
        self._pt.unpatchPyMEL()

    def __getattr__(self, item):
        return getattr(self.cmds, item)

    def __repr__(self):
        return "<paya runtime: {}>".format(
            'active' if self._pt.pyMELIsPatched else 'inactive')

inst = Runtime()

import sys
sys.modules['paya.runtime'] = inst