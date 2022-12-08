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
        import paya.startstop
        from paya.pools import pools
        import paya.cmds
        import paya.nativeunits
        import pymel.core

        self._pmcore = self._fallback = pymel.core
        self._ss = paya.startstop
        self._cmds = paya.cmds
        self._pools = pools
        self._running = False

        self.NativeUnits = paya.nativeunits.NativeUnits
        self._NativeUnitsInstance = None

        for pool in self._pools:
            setattr(self, pool.shortName(), pool.browse())

    #--------------------------------------------------|    Interfaces

    @property
    def pn(self):
        return self._pmcore.PyNode

    def __getattr__(self, item):
        return getattr(self._fallback, item)

    @property
    def running(self):
        return Runtime.__depth__ > 0

    #--------------------------------------------------|    Start / stop

    def __enter__(self):
        Runtime.__depth__ += 1

        if Runtime.__depth__ is 1:
            # Patch PyMEL
            self._ss.start(quiet=True)

            # Attach attributes
            self._fallback = self._cmds

            # Here for reference. Can't be added / removed dynamically
            # as used for subclassing in part classes
            # for pool in self._pools:
            #     setattr(self, pool.shortName(), pool.browse())

            # Enter a NativeUnits context manager
            self._NativeUnitsInstance = self.NativeUnits()
            self._NativeUnitsInstance.__enter__()

            print("Paya has started successfully.")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Runtime.__depth__ -= 1

        if Runtime.__depth__ is 0:
            # Exit the NativeUnits context manager
            self._NativeUnitsInstance.__exit__(exc_type, exc_val, exc_tb)

            # Remove attributes
            self._fallback = self._pmcore

            # Here for reference. Can't be added / removed dynamically
            # as used for subclassing in part classes
            # for pool in self._pools:
            #     delattr(self, pool.shortName())

            print("Paya has stopped successfully.")

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