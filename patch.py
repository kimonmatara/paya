"""
Internal. Defines methods used by :py:mod:`paya.runtime` to manage PyMEL
patching.
"""

import inspect

import pymel.core.nodetypes as _nt
import pymel.core.datatypes as _dt
import pymel.core.general as _gen
import paya.pools as _pl

import maya.cmds as m
import maya.OpenMaya as om

#------------------------------------------------------------|    Gather information

classesToPatch = [_gen.PyNode]

for clsname, cls in inspect.getmembers(_dt,inspect.isclass):
    if (issubclass(cls, _dt.Array) or \
            issubclass(cls, _dt.Unit)) and '__new__' in cls.__dict__:
        classesToPatch.append(cls)

#------------------------------------------------------------|    Main calls

pyMELIsPatched = False

# Pools whose base PyMEL types will be cross-tagged with the
# associated pool
poolsToPatch = [_pl.nodes, _pl.plugs, _pl.comps, _pl.data]

def patchPyMEL(quiet=False):
    """
    Patches PyMEL so that it will return custom paya classes instead of
    its own. Called by :py:meth:`~paya.runtime.Runtime.start`.

    .. warning::

        Should not be called directly. Use :mod:`paya.runtime` as a context
        manager instead.

    :param bool quiet: don't print status messages; defaults to False
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
            pool = pmcls.__paya_pool__

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

        # Patch pool root classes
        for pool in poolsToPatch:
            for root in pool.__roots__:
                root.__paya_pool__ = pool

        pyMELIsPatched = True

        if not quiet:
            print("PyMEL patched successfully.")

def unpatchPyMEL(quiet=False):
    """
    Reverts PyMEL to its 'factory' state. Called by
    :py:meth:`~paya.runtime.Runtime.stop`.

    .. warning::

        Should not be called directly. Use :mod:`paya.runtime` as a context
        manager instead.

    :param bool quiet: don't print status messages; defaults to False
    """
    global pyMELIsPatched

    if pyMELIsPatched:
        # Unpatch pool root classes
        for pool in poolsToPatch:
            for root in pool.__roots__:
                del(root.__paya_pool__)

        # Unpatch instantiators
        for cls in classesToPatch:
            if '__old_new__' in cls.__dict__:
                cls.__new__ = staticmethod(cls.__old_new__)
                del(cls.__old_new__)

        pyMELIsPatched = False

        if not quiet:
            print("PyMEL unpatched successfully.")

    elif not quiet:
        m.warning("PyMEL is not patched.")