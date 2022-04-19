"""
Defines the template class interfaces served by the ``nodes``,
``plugs``, ``comps`` and ``data`` attributes on :py:mod:`paya.runtime`.

This module is not intended for direct use.
"""

import inspect
import sys
import os

import maya.cmds as m
import pymel.core.nodetypes as _nt
import pymel.core.datatypes as _dt
import pymel.core.general as _gen

import paya
import paya.config as config
import paya.plugtree as _pt
from paya.util import cap, uncap, path_to_dotpath

paya_root = os.path.dirname(paya.__file__)
rootpkg = paya.__name__

#------------------------------------------------------------|
#------------------------------------------------------------|    Exceptions
#------------------------------------------------------------|

class MissingTemplateError(RuntimeError):
    """
    Raised when a module can't be found for a requested template class.
    """
    pass

class UnsupportedLookupError(RuntimeError):
    """
    Raised when MatrixN or Array are requested from the 'data' pool.
    """
    pass

#------------------------------------------------------------|
#------------------------------------------------------------|    Misc
#------------------------------------------------------------|

def ispmcls(cls):
    """
    :param cls: The class to query
    :return: ``True`` if the class is a 'vanilla' PyMEL class,
        otherwise ``False``.
    :rtype: bool
    """
    return cls.__module__.startswith('pymel.')

def iscustomcls(cls):
    """
    :param cls: The class to query
    :return: ``True`` if the class is a **paya** class,
        otherwise ``False``.
    :rtype: bool
    """
    return rootpkg in cls.__module__

#------------------------------------------------------------|
#------------------------------------------------------------|    paya metaclass
#------------------------------------------------------------|

class payaMeta(type):

    def mro(cls):
        clsname = cls.__name__

        defaultmro = super().mro()

        # Build up a 'head' from the main class to the first encountered
        # PyMEL namesake

        outmro = [cls]
        pickupindex = None
        pmbase = None
        pool = None

        for i, mrocls in enumerate(defaultmro[1:],start=1):

            outmro.append(mrocls)

            if ispmcls(mrocls):
                pickupindex = i+1
                pmbase = mrocls
                pool = getPoolFromPmBase(pmbase)
                break

        # If the terminator class wasn't encountered, continue
        # to insert our classes into the inheritance

        if pmbase in pool.__pm_root_classes__:
            outmro += pmbase.__mro__[1:]

        else:
            for i, mrocls in enumerate(
                    defaultmro[pickupindex:],
                    start=pickupindex
            ):
                if ispmcls(mrocls):
                    clsname = mrocls.__name__

                    try:
                        insertcls = pool.getByName(clsname)
                        outmro += [insertcls,mrocls]

                    except UnsupportedLookupError:
                        outmro.append(mrocls)

                    if mrocls in pool.__pm_root_classes__:
                        outmro += defaultmro[i+1:]
                        break

                else:
                    outmro.append(mrocls)

        return outmro

#------------------------------------------------------------|
#------------------------------------------------------------|    Abstract base class
#------------------------------------------------------------|

class ClassPool:
    """
    Abstract. Defines base functionality for all template class pools.
    """

    #-------------------------------------------------|    Config

    __singular__ = None # e.g. 'node'
    __plural__ = None # e.g. 'nodes'

    __pm_mod__ = None # e.g. _nt
    __pm_root_classes__ = None # e.g. [DependNode]

    #-------------------------------------------------|    Instantiation

    def __new__(cls):
        if cls is ClassPool:
            raise RuntimeError("Can't instantiate abstract base class.")

        return object.__new__(cls)

    #-------------------------------------------------|    Init

    def __init__(self):
        self._cache = {}
        self._metacache = {}    # PM meta: paya: meta; never flushed
        self._pmbasecache = {}  # name lookup: PM base; never flushed

        self._longName = '{}types'.format(self.__singular__)
        self._shortName = self.__plural__
        self._dirPath = os.path.join(paya_root, self.longName)
        self._dotPath = '.'.join([rootpkg, self._longName])

    #-------------------------------------------------|    Info

    @property
    def dirPath(self):
        return self._dirPath

    @property
    def dotPath(self):
        return self._dotPath

    @property
    def longName(self):
        return self._longName

    @property
    def shortName(self):
        return self._shortName

    #-------------------------------------------------|    Class construction

    def _getMeta(self, clsname):
        pmbase = self._getPmBase(clsname)
        pmmeta = type(pmbase)

        metaname = pmmeta.__name__+'payaMeta'

        try:
            return self._metacache[metaname]

        except KeyError:
            metacls = type(metaname, (payaMeta, pmmeta), {})
            self._metacache[metaname] = metacls

            return metacls

    def _getPreferredBase(self, clsname):
        return self._getPmBase(clsname)

    def _getPmBase(self, clsname):
        try:
            return self._pmbasecache[clsname]

        except KeyError:
            self._pmbasecache[clsname] = pmbase \
                = getattr(self.__pm_mod__, clsname)

            return pmbase

    def _getTemplateFilePath(self, clsname):
        """
        Caution: For speed, this doesn't check for duplicates; the first
        match is always returned.
        """
        filename = '{}.py'.format(uncap(clsname))

        for root, dirs, files in os.walk(self.dirPath):
            for file in files:
                if file == filename:
                    return os.path.join(root, file)

        raise MissingTemplateError(
            "Couldn't find template file {} under {}".format(
                filename, self.dirPath)
        )

    def _getModuleSignature(self, clsname):
        return '{}.{}'.format(self.dotPath, uncap(clsname))

    def _getConformedBases(self, clsname, bases):
        preferredBase = self._getPreferredBase(clsname)

        bases = [base for base in bases if base is not object]

        if not any([issubclass(base, preferredBase) for base in bases]):
            # If there's a custom user base class, leave it at index 0
            # so that its branch gets evaluated first via multiple inheritance
            bases.append(preferredBase)

        return tuple(bases)

    def _getConformedDict(self, clsname, dct):
        dct = dict(dct)

        dct['__module__'] = self._getModuleSignature(clsname)
        dct['__pm_base__'] = pmbase = self._getPmBase(clsname)

        # Insert an overriden __new__ that will prevent the paya class
        # from ever being instantiated; instead, the PM base will be
        # instantiated and __class__ reassigned on the instance.

        if '__new__' in dct:
            raise RuntimeError(
                'Overriding __new__ on paya classes is not allowed.'
            )

        def __new__(cls, *args, **kwargs):
            inst = pmbase.__new__(pmbase, *args, **kwargs)
            inst.__class__ = cls

            return inst

        dct['__new__'] = __new__

        return dct

    def _getBasesDictFromTemplate(self, clsname):
        # Source the template class from disk

        filepath = self._getTemplateFilePath(clsname)
        dotpath = path_to_dotpath(filepath)

        exec("import {}".format(dotpath)) in locals()
        mod = eval(dotpath)

        cls = getattr(mod, clsname)

        return cls.__bases__, cls.__dict__

    def _getSpec(self, clsname):
        try:
            bases, dct = self._getBasesDictFromTemplate(clsname)

        except MissingTemplateError:
            bases, dct = (), {}

        return self._getConformedBases(clsname, bases), \
               self._getConformedDict(clsname, dct)

    def _buildClass(self, clsname):
        bases, dct = self._getSpec(clsname)
        meta = self._getMeta(clsname)

        return type.__new__(meta, clsname, bases, dct)

    #-------------------------------------------------|    High-level access

    def getFromPyMELInstance(self, inst):
        """
        Given a PyNode or PyMEL data type instance, returns a custom class
        suitable for assignment.

        :param inst: the PyNode or PyMEL data type instance
        :return: The custom class.
        """
        lookup = inst.__class__.__name__
        return self.getByName(lookup)

    def getByName(self, clsname):
        """
        Returns a custom class by name.

        :param str clsname: the name of the class to retrieve
        :return: The custom class.
        """
        try:
            return self._cache[clsname]

        except KeyError:
            newcls = self._buildClass(clsname)
            self._cache[clsname] = newcls

            return newcls

    def __getitem__(self, clsname):
        return self.getByName(clsname)

    def __getattr__(self, item):
        return self[item]

    #-------------------------------------------------|    Clearing / reloading

    def purge(self):
        """
        Clears the cache so that subsequent class lookups will trigger
        reloads.
        """
        self._cache.clear()

        modsToDelete = [name for name in sys.modules \
                        if name.startswith(self.dotPath+'.')]

        for modToDelete in modsToDelete:
            del(sys.modules[modToDelete])

        print("Purged class pool {}.".format(self))

    #-------------------------------------------------|    Dict

    @property
    def keys(self):
        return self._cache.keys

    @property
    def values(self):
        return self._cache.values

    @property
    def items(self):
        return self._cache.items

    @property
    def __len__(self):
        return self._cache.__len__

    @property
    def __contains__(self):
        return self._cache.__contains__

    #-------------------------------------------------|    Repr

    def __repr__(self):
        return 'paya.{}'.format(self.shortName)

#------------------------------------------------------------|
#------------------------------------------------------------|    Pool classes
#------------------------------------------------------------|

class NodeClassPool(ClassPool):
    """
    Serves custom classes for **nodes**.
    """

    __singular__ = 'node'
    __plural__ = 'nodes'
    __pm_mod__ = _nt
    __pm_root_classes__ = [_nt.DependNode]

nodes = NodeClassPool()


class PlugClassPool(ClassPool):
    """
    Serves custom classes for **plugs** (attributes) off of an inheritance tree
    defined inside ``paya/plugtree.json``.
    """

    __singular__ = 'plug'
    __plural__ = 'plugs'
    __pm_mod__ = _gen
    __pm_root_classes__ = [_gen.Attribute]

    #-------------------------------------------------|    Class construction

    def _getPmBase(self, *args):
        # Always return Attribute for plugs, since PyMEL doesn't
        # furnish any other types
        return self.__pm_root_classes__[0]

    def _getPreferredBase(self, clsname):
        if clsname == 'Attribute':
            return self.__pm_root_classes__[0]

        typePath = _pt.getPath(clsname)
        return self.getByName(typePath[-2])

    #-------------------------------------------------|    High-level access

    def getFromPyMELInstance(self, inst):
        """
        Overloads :py:meth:`ClassPool.getFromPyMELInstance` to implement
        ``MPlug`` inspections.

        :param inst: the PyNode or PyMEL data type instance
        :return: The custom class.
        """
        mplug = inst.__apimplug__()
        lookup = _pt.getTypeFromMPlug(mplug)
        return self.getByName(lookup)

plugs = PlugClassPool()


class CompClassPool(ClassPool):
    """
    Serves custom classes for **components**.
    """

    __singular__ = 'comp'
    __plural__ = 'comps'
    __pm_mod__ = _gen
    __pm_root_classes__ = [_gen.Component]

comps = CompClassPool()


def getRootDataClasses():
    classes = [pair[1] for pair in inspect.getmembers(_dt, inspect.isclass)]

    out = []

    for cls in classes:
        mro = list(reversed(cls.__mro__))

        for anc in mro[1:]:
            if anc.__module__ == 'builtins':
                continue

            if 'OpenMaya' in anc.__module__:
                continue

            out.append(anc)
            break

    return list(set(out))

class DataClassPool(ClassPool):
    """
    Serves custom classes for **data objects**, for example
    :class:`~pymel.core.datatypes.Matrix` instances returned by
    :py:meth:`~pymel.core.nodetypes.Transform.getMatrix`.
    """

    __unsupported_lookups__ = ['MatrixN', 'Array']

    __singular__ = __plural__ = 'data'
    __pm_mod__ = _dt

    __pm_root_classes__ = getRootDataClasses()

    def getByName(self, clsname):
        """
        Overloads :py:meth:`ClassPool.getByName` to prevent customisation of
        sensitive types such as :py:class:`pymel.core.datatypes.MatrixN`.

        :param str clsname: the name of the class to retrieve
        :return: The custom class.
        """
        if clsname in self.__unsupported_lookups__:
            raise UnsupportedLookupError(
                "Pool {} can't serve class '{}'".format(self, clsname)
                )

        return super().getByName(clsname)

data = DataClassPool()

pools = [nodes, plugs, comps, data]

def getPoolFromPmBase(pmbase):
    """
    Given a PyMEL base class, returns the most appropriate class pool
    to source a swap-in from.
    """
    for cls in pmbase.__mro__:
        for pool in pools:
            if cls in pool.__pm_root_classes__:
                return pool