import inspect

import pymel.core.nodetypes as _nt
import pymel.core.datatypes as _dt
import pymel.core.general as _gen
import paya.pools as _pl

import maya.cmds as m

#------------------------------------------------------------|    Gather information

classesToPatch = [_gen.PyNode]

for clsname, cls in inspect.getmembers(_dt,inspect.isclass):
    if issubclass(cls, _dt.Array) and '__new__' in cls.__dict__:
        classesToPatch.append(cls)

#------------------------------------------------------------|    Main calls

pyMELIsPatched = False


def patchPyMEL(quiet=False):
    """
    Patches PyMEL so that it will return custom paya classes instead of its own.
    """
    global pyMELIsPatched

    if pyMELIsPatched:
         if not quiet:
             m.warning("PyMEL is already patched.")

    else:
        # Patch instantiators

        def __new__(cls,*args,**kwargs):
            instance = cls.__old_new__(cls,*args,**kwargs)
            pmcls = type(instance)
            pool = _pl.getPoolFromPmBase(pmcls)

            try:
                customCls = pool.getFromPyMELInstance(instance)

            except _pl.UnsupportedLookupError:
                return instance

            instance.__class__ = customCls

            return instance

        for cls in classesToPatch:
            if '__old_new__' in cls.__dict__:
                continue

            cls.__old_new__ = staticmethod(cls.__new__)
            cls.__new__ = staticmethod(__new__)

        pyMELIsPatched = True

        if not quiet:
            print("PyMEL patched successfully.")


def unpatchPyMEL(quiet=False):
    """
    Returns PyMEL to its factory load state.
    """
    global pyMELIsPatched

    if pyMELIsPatched:
        for cls in classesToPatch:
            if '__old_new__' in cls.__dict__:
                cls.__new__ = staticmethod(cls.__old_new__)
                del(cls.__old_new__)

        pyMELIsPatched = False

        if not quiet:
            print("PyMEL unpatched successfully.")

    else:
        if not quiet:
            m.warning("PyMEL is not patched.")

class PatchCtx(object):
    def __init__(self, *state):
        if state:
            self.requested_state = state[0]

        else:
            self.requested_state = True

    def __enter__(self):
        self.last_state = pyMELIsPatched

        if pyMELIsPatched and not self.requested_state:
            unpatchPyMEL()

        elif self.requested_state and not pyMELIsPatched:
            patchPyMEL()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if pyMELIsPatched and not self.last_state:
            unpatchPyMEL()

        elif self.last_state and not pyMELIsPatched:
            patchPyMEL()

        return False