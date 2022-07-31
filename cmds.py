"""
The contents of this module can be directly accessed via the
:py:mod:`paya.runtime` interface. This includes:

    * The entire :mod:`pymel.core` namespace
    * :class:`~paya.lib.names.Name`
    * :func:`~paya.lib.mathops.createMatrix` / ``cm``
    * :class:`~paya.lib.skel.Chain`
    * ``controlShapes``, an instance of :class:`~paya.lib.controlshapes.ControlShapesLibrary`

Any module-level variables or functions added here will also become available
via :py:mod:`paya.runtime`.

.. warning::

    When customising this module, take care not to **shadow** factory commands from
    :mod:`pymel.core`. Doing so may break code that accesses such commands via
    :mod:`paya.runtime`.
"""

import re

import maya.mel as mel
from pymel.core import *

from paya.util import toOs
from paya.lib.names import Name
from paya.lib.mathops import createMatrix, \
    createScaleMatrix, cm, csm, NativeUnits, \
    onRad, onCm, onNative

from paya.lib.skel import Chain
from paya.lib.controlshapes import controlShapes

def saveScriptEditor():
    """
    Convenience wrapper for MEL's ``syncExecuterBackupFiles()``.
    """
    mel.eval('syncExecuterBackupFiles')

def findMelProc(procName):
    """
    Convenience wrapper for MEL's `whatIs`. Returns just a path to
    a MEL file. If on Windows, the path will be back-slashed for
    easy copy-paste into an editor.

    :param procName: the MEL proc to locate
    :raises RuntimeError: not a MEL procedure
    :return: the path to the MEL file, in OS format
    :rtype: str
    """
    cmd = 'whatIs {}'.format(procName)
    result = mel.eval(cmd)
    pat = r"^Mel procedure found in: (.*)$"

    mt = re.match(pat, result)

    if mt:
        path = toOs(mt.groups()[0])
        print(path)
        return path

    raise RuntimeError("Not a MEL procedure.")

pn = PyNode