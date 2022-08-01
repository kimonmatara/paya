import maya.cmds as m
import paya.config as config
from paya.nativeunits import NativeUnits
from paya.patch import patchPyMEL, unpatchPyMEL
from paya.pools import pools

global running
running = False

def start():
    """
    Starts a Paya session. PyMEL is patched to return Paya classes and,
    unless *ignoreUnits* is ``True`` in :mod:`~paya.config`, creates a
    few callbacks to monitor unit settings.
    """
    global running

    if running:
        m.warning('Paya is already running.')

    else:
        if not config['ignoreUnits']:
            NativeUnits().addCallbacks()

        patchPyMEL(quiet=True)
        running = True

        print("Welcome to Paya.")

def stop():
    """
    Stops the Paya session. PyMEL is reverted to its 'factory' state and any
    callbacks are removed.
    """
    global running

    if running:
        if not config['ignoreUnits']:
            NativeUnits().removeCallbacks()

        unpatchPyMEL(quiet=True)

        for pool in pools:
            pool.purge(quiet=True)

        running = False

        print("Paya has been stopped.")

    else:
        m.warning("Paya is already stopped.")