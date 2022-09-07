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
        from paya.nativeunits import NativeUnits

        self._ss = startstop
        self._cmds = cmds
        self._pools = pools
        self._running = False
        self._nu = NativeUnits

    #--------------------------------------------------|    Interfaces

    def __createControl(self):
        return self.nodes.Transform.createControl

    def __getattr(self, attrName):
        return getattr(self._cmds, attrName)

    @property
    def running(self):
        return Runtime.__depth__ > 0

    #--------------------------------------------------|    Start / stop

    def start(self):
        if Runtime.__depth__ is 0:
            # Patch PyMEL
            self._ss.start(quiet=True)

            # Attach attributes
            Runtime.createControl = property(fget=Runtime.__createControl)
            Runtime.__getattr__ = self.__getattr

            for pool in self._pools:
                setattr(self, pool.shortName(), pool.browse())

            # Enforce native units
            self._nu.start()

            Runtime.__depth__ = 1
            print("Paya has started successfully.")

        else:
            m.warning("Paya can't be started because it's already running.")

    def stop(self):
        if Runtime.__depth__ > 0:
            # Unpatch PyMEL
            self._ss.stop(quiet=True)

            # Remove attributes
            del(Runtime.__getattr__)
            del(Runtime.createControl)

            for pool in self._pools:
                delattr(self, pool.shortName())

            self._nu.stop()
            Runtime.__depth__ = 0

            print("Paya has stopped successfully.")

        else:
            m.warning("Paya can't stop because it's not running.")

    def __enter__(self):
        if Runtime.__depth__ is 0:
            self.start()

        else:
            Runtime.__depth__ += 1

        return self

    def __exit__(self, *args):
        if Runtime.__depth__ is 1:
            self.stop()

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