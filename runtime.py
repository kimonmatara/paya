from functools import wraps
import maya.cmds as m
import maya.OpenMaya as om


class Runtime:

    #--------------------------------------------------|    Instantiation

    __instance__ = None
    __depth__ = 0

    def __new__(cls, *args, **kwargs):
        if cls.__instance__ is None:
            cls.__instance__ = object.__new__(cls)

        return cls.__instance__

    def __init__(self):
        import paya.startstop as startstop
        from paya.pools import pools
        import paya.cmds as cmds
        import pymel.core

        self._pmcore = self._fallback = pymel.core
        self._ss = startstop
        self._cmds = cmds
        self._pools = pools
        self._running = False

    #--------------------------------------------------|    Interfaces

    @property
    def pn(self):
        return self._pmcore.PyNode

    def __createControl(self):
        return self.nodes.Transform.createControl

    def __getattr__(self, item):
        return getattr(self._fallback, item)

    @property
    def running(self):
        return Runtime.__depth__ > 0

    #--------------------------------------------------|    Start / stop

    def _start(self):
        if Runtime.__depth__ is 0:
            # Patch PyMEL
            self._ss.start(quiet=True)

            # Attach attributes
            Runtime.createControl = property(fget=Runtime.__createControl)
            self._fallback = self._cmds

            for pool in self._pools:
                setattr(self, pool.shortName(), pool.browse())

            Runtime.__depth__ = 1
            print("Paya has started successfully.")

        else:
            m.warning("Paya can't be started because it's already running.")

    def _stop(self):
        if Runtime.__depth__ > 0:
            # Unpatch PyMEL
            self._ss.stop(quiet=True)

            # Remove attributes
            self._fallback = self._pmcore
            del(Runtime.createControl)

            for pool in self._pools:
                delattr(self, pool.shortName())

            Runtime.__depth__ = 0

            print("Paya has stopped successfully.")

        else:
            m.warning("Paya can't stop because it's not running.")

    def __enter__(self):
        if Runtime.__depth__ is 0:
            self._start()

        else:
            Runtime.__depth__ += 1

        return self

    def __exit__(self, *args):
        if Runtime.__depth__ is 1:
            self._stop()

        else:
            Runtime.__depth__ -= 1

        return False

    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            with self:
                result = f(*args, **kwargs)
            return result

        return wrapper

    #--------------------------------------------------|    Reloading

    def rehash(self):
        """
        Reloads :py:mod:`paya.cmds` and clears the custom class caches,
        so that subsequent retrievals will trigger reloads.
        """
        from importlib import reload
        reload(self._cmds)
        print('Reloaded paya.cmds.')

        for pool in self._pools:
            pool.purge()

        print('Purged class pools.')

    #--------------------------------------------------|    Repr

    def __repr__(self):
        state = 'running' if self.running else 'stopped'
        return "<paya runtime: {}>".format(state)

inst = Runtime()

import sys
sys.modules['paya.runtime'] = inst