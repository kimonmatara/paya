import maya.cmds as m
import paya.config as config
from paya.nativeunits import NativeUnits
from paya.patch import patchPyMEL, unpatchPyMEL
from paya.pools import pools

global running
running = False

def start(quiet=False):
    """
    Patches PyMEL to return Paya classes.
    """
    global running

    if running and not quiet:
        m.warning('PyMEL is already patched.')

    else:
        patchPyMEL(quiet=True)
        running = True
        print("PyMEL has been patched.")

def stop(quiet=False):
    """
    Reverts PyMEl to its 'factory' state.
    """
    global running

    if running:
        unpatchPyMEL(quiet=True)

        for pool in pools:
            pool.purge(quiet=True)

        running = False
        print("PyMEL has been unpatched.")

    elif not quiet:
        m.warning("Paya is already unpatched.")