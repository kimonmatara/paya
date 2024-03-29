import traceback
import inspect
import os
import re
import sys

import maya.cmds as m
import pymel.core.nodetypes
import pymel.core.general
import pymel.core.datatypes

import paya
from paya.util import path_to_dotpath, LazyModule
import paya.pluginfo as _pi

payaroot = os.path.dirname(paya.__file__)

uncap = lambda x: x[0].lower()+x[1:]

#----------------------------------------------------------------|
#----------------------------------------------------------------|    Errors
#----------------------------------------------------------------|

class MissingTemplateError(RuntimeError):
    """
    A template module could not be found for a requested class.
    """

class NoPyMELCounterpartError(RuntimeError):
    """
    Raised by a subclass of :class:`ShadowPool` when a PyMEL base
    can't be found for a requested Paya class.
    """

class ClassTooBasicError(RuntimeError):
    """
    The class that was requested from a PyMEL-shadowing class pool is
    an ancestor of one of the terminating classes in __roots__.
    """

class UnsupportedLookupError(RuntimeError):
    """
    The class pool does not allow lookups for the attempted name.
    """

#----------------------------------------------------------------|
#----------------------------------------------------------------|    ABC
#----------------------------------------------------------------|

class ClassPoolBrowser:
    """
    Browsing wrapper for a class pool instance. Classes can be retrieved
    using dotted or keyed syntax.
    """

    def __init__(self, pool):
        self.__pool__ = pool

    def __getattr__(self, item):
        return self.__pool__.getByName(item)

    def __getitem__(self, item):
        return self.__pool__.getByName(item)

    def __repr__(self):
        return 'paya.runtime.{}'.format(self.__pool__.shortName())


class ClassPool:
    """
    Abstract base class for collections of custom Paya classes.
    """
    __unsupported_lookups__ = []
    __singular__ = None # e.g. 'node'
    __plural__ = None # e.g. 'nodes'
    __meta_base__ = type
    __doctitle__ = None # e.g. 'Plug (Attribute) Types'

    #------------------------------------------------------------|    Init

    def __init__(self):
        self._cache = {}

    def browse(self):
        """
        :return: A browser object for this pool.
        :rtype: :class:`ClassPoolBrowser`.
        """
        return ClassPoolBrowser(self)

    #------------------------------------------------------------|    Basic inspections

    def dirPath(self):
        """
        :return: The full directory path for the template package.
        :rtype: str
        """
        return os.path.join(payaroot, self.__singular__+'types')

    def longName(self):
        """
        :return: The long name of this pool, for example 'nodetypes'.
        :rtype: str
        """
        return self.__singular__+'types'

    def shortName(self):
        """
        :return: The short name of this pool, for example 'nodes'.
        :rtype: str
        """
        return self.__plural__

    #------------------------------------------------------------|    Purge

    def purge(self, quiet=False):
        """
        Purges cached information.
        """
        self._cache.clear()

        searchString = 'paya.'+self.longName()
        modsToDelete = [name for name in sys.modules if searchString in name]

        for modToDelete in modsToDelete:
            del(sys.modules[modToDelete])

        if not quiet:
            print("Purged {} classes.".format(self.__singular__))

    #------------------------------------------------------------|    Retrieval

    def readClass(self, clsname):
        """
        Locates, sources and returns a class by name. No rebuilding or
        cache management is performed.

        :param str clsname: the name of the class to retrieve
        :return: The retrieved class.
        :rtype: :class:`str`
        """
        dirpath = self.dirPath()
        requiredModBasename = clsname[0].lower()+clsname[1:]
        foundModuleFile = None

        for root, dirs, files in os.walk(dirpath):
            for fil in files:
                head, tail = os.path.splitext(fil)

                if (head and head[0] in ('.', '_')) \
                        or (not head) \
                        or (tail != '.py'):
                    continue

                if head == requiredModBasename:
                    foundModuleFile = os.path.join(root, fil)

        if foundModuleFile is None:
            raise MissingTemplateError(
                "Couldn't find template for class '{}'.".format(clsname)
            )

        # Convert the file path to a dotpath and source the module
        modName = path_to_dotpath(foundModuleFile)
        exec("import "+modName) in locals()

        mod = eval(modName)
        return getattr(mod, clsname)

    def getByName(self, clsname):
        """
        Retrieves a class by name. Lookups are cached.

        :param str clsname: The name of the class to retrieved.
        :return: The retrieved class.
        :rtype: :class:`str`
        """
        if clsname in self.__unsupported_lookups__:
            raise UnsupportedLookupError(
                "This class pool does not serve '{}'.".format(clsname)
            )

        try:
            return self._cache[clsname]

        except KeyError:
            self._cache[clsname] = cls = self.readClass(clsname)

        return cls

    #------------------------------------------------------------|    Repr

    def __repr__(self):
        return "{}()".format(self.__class__.__name__)


class RebuiltClassPool(ClassPool):

    __meta_base__ = type

    def getMeta(self, clsname):
        """
        :param str clsname: the name of the class being retrieved
        :return: An appropriate metaclass for the requested class.
        :rtype: type
        """
        return self.__meta_base__

    def inventBasesDict(self, clsname):
        """
        :param clsname: the name of the class being retrieved
        :raise NotImplementedError: Invention is not implemented for this pool.
        :return: Bases and a dict that can be used to construct a stand-in
            class in the absence of a template.
        :rtype: (tuple, dict)
        """
        raise NotImplementedError(
            "Invention is not implemented for this pool.")

    def conformBases(self, clsname, bases):
        """
        Given a tuple of bases, returns a modified, where necessary,
        version that can be used to construct a final class.

        :param str clsname: the name of the class being retrieved
        :param tuple bases: either an empty tuple, or bases retrieved from a
            template class
        :return: The bases.
        :rtype: (type,)
        """
        raise NotImplementedError

    def conformDict(self, clsname, dct):
        """
        Given a class dictionary, returns a modified, where necessary,
        version that can be used to construct a final class.

        :param str clsname: the name of the class being retrieved
        :param dict dct: either an empty dictionary, or the dictionary of
            a template class
        :return: The dictionary.
        :rtype: dict
        """
        dct = dct.copy()
        dct['__module__'] = 'paya.runtime.'+self.shortName()
        dct['__paya_pool__'] = self

        return dct

    def getBasesDictFromTemplate(self, clsname):
        cls = self.readClass(clsname)
        bases = self.conformBases(clsname, cls.__bases__)
        dct = self.conformDict(clsname, dict(cls.__dict__))

        return bases, dct

    def buildClass(self, clsname):
        """
        Builds a final class. If a template is available, it is used.
        Otherwise, if this pool implements invention, the class is invented.
        If this pool doesn't implement invention, an exception is raised.

        :param str clsname: the name of the class to build
        :raises MissingTemplateError: A template couldn't be found, and this
            pool doesn't implement invention.
        :return: The built class.
        :rtype: type
        """
        try:
            bases, dct = self.getBasesDictFromTemplate(clsname)

        except MissingTemplateError as exc:
            try:
                bases, dct = self.inventBasesDict(clsname)

            except NotImplementedError:
                raise exc

        # Build the class from the bases and the dict
        meta = self.getMeta(clsname)
        cls = type.__new__(meta, clsname, bases, dct)

        # Modify the module field into a 'runtime' format only after
        # the class is built
        cls.__module__ = 'paya.runtime.'+self.shortName()

        return cls

    def getByName(self, clsname):
        """
        Retrieves a class by name. Lookups are cached.

        :param str clsname: The name of the class to retrieved.
        :return: The retrieved class.
        :rtype: :class:`str`
        """
        if clsname in self.__unsupported_lookups__:
            raise UnsupportedLookupError(
                "This class pool does not serve '{}'.".format(clsname)
            )

        try:
            return self._cache[clsname]

        except KeyError:
            self._cache[clsname] = cls = self.buildClass(clsname)

        return cls

class ShadowPool(RebuiltClassPool):
    """
    Abstract base class for pools that directly shadow PyMEL namesakes.
    """
    __pm_mod__ = None # e.g. pymel.core.nodetypes
    __roots__ = []

    #------------------------------------------------------------|    Metaclass

    class ShadowPoolMeta(type):
        """
        Base metaclass for PyMEL-shadowing Paya classes.
        """
        def mro(cls):
            """
            Defines the method resolution order

            :return:
            """
            pool = cls.__dict__['__paya_pool__']
            defaultmro = super().mro()
            outmro = [cls]

            # Basic idea: if a PyMEL class is encountered:
            # 1) Ensure preceding member is a Paya shadow
            # 2) If the PyMEL class is the pool's roots, append
            # 3) the rest of the mro and bolt

            for i, member in enumerate(defaultmro[1:], start=1):
                modname = member.__dict__['__module__']

                if 'pymel.' in modname:
                    previous = outmro[i-1]

                    if not('paya.' in previous.__dict__['__module__'] \
                           and previous.__name__ == member.__name__):

                        try:
                            subclass = pool.getByName(member.__name__)
                            outmro.append(subclass)

                        except UnsupportedLookupError:
                            pass

                    outmro.append(member)

                    if member in pool.__roots__:
                        outmro += defaultmro[i+1:]
                        break

                elif 'paya.' in modname:
                    outmro.append(member)

                else:
                    outmro += defaultmro[i:]
                    break

            return outmro

        # The following never gets called for shadowed nodes, but it does get
        # called for parsed subtypes
        def __new__(meta, clsname, bases, dct):
            modname = dct['__module__']

            shortPoolNameMt = re.match(
                r"^.*?paya\.runtime\.([^.]+).*$",
                modname
            )

            if shortPoolNameMt:
                shortPoolName = shortPoolNameMt.groups()[0]
                pool = globals()['poolsByShortName'][shortPoolName]

            else:
                longPoolNameMt = re.match(
                    r"^.*?paya\.([^.]+).*$",
                    modname
                )

                longPoolName = longPoolNameMt.groups()[0]
                pool = globals()['poolsByLongName'][longPoolName]

            dct['__paya_pool__'] = pool

            return super().__new__(meta, clsname, bases, dct)


    __meta_base__ = ShadowPoolMeta

    #------------------------------------------------------------|    Init

    def __init__(self):
        super().__init__()
        self.metacache = {}

    #------------------------------------------------------------|    Retrieval

    def getFromPyMELInstance(self, inst):
        """
        Given a PyMEL instance, returns an appropriate Paya class for
        reassignment.
        """
        lookup = inst.__class__.__name__
        return self.getByName(lookup)

    def inventBasesDict(self, clsname):
        """
        :param clsname: the name of the class being retrieved
        :raise NotImplementedError: Invention is not implemented for this pool.
        :return: Bases and a dict that can be used to construct a stand-in
            class in the absence of a template.
        :rtype: (tuple, dict)
        """
        bases = self.conformBases(clsname, tuple())
        dct = self.conformDict(clsname, {})

        return bases, dct

    def conformDict(self, clsname, dct):
        """
        Given a class dictionary, returns a modified, where necessary,
        version that can be used to construct a final class.

        :param str clsname: the name of the class being retrieved
        :param dict dct: either an empty dictionary, or the dictionary of
            a template class
        :return: The dictionary.
        :rtype: dict
        """
        dct = super().conformDict(clsname, dct).copy()
        pmbase = self.getPmBase(clsname)

        if '__new__' in dct:
            raise RuntimeError("Can't override __new__ on Paya classes.")

        # Prevent Paya shadow classes from ever instantiating
        def __new__(cls, *args, **kwargs):
            inst = pmbase.__new__(pmbase, *args, **kwargs)
            inst.__class__ = cls

            return inst

        dct['__new__'] = __new__

        return dct


    def conformBases(self, clsname, bases):
        """
        Given a tuple of bases, returns a modified, where necessary,
        version that can be used to construct a final class.

        :param str clsname: the name of the class being retrieved
        :param tuple bases: either an empty tuple, or bases retrieved from a
            template class
        :return: The bases.
        :rtype: (type,)
        """
        bases = [base for base in bases if base is not object]
        requiredPmBase = self.getPmBase(clsname)

        if not any([issubclass(base, requiredPmBase) for base in bases]):
            # Append, so that any user-inserted abstract classes can be
            # evaluated first through multiple inheritance
            bases.append(requiredPmBase)

        return tuple(bases)

    def getMeta(self, clsname):
        """
        :param str clsname: the name of the class being retrieved
        :return: An appropriate metaclass for the requested class.
        :rtype: type
        """
        pmbase = self.getPmBase(clsname)
        pmMeta = type(pmbase)

        try:
            ourMeta = self.metacache[pmMeta]

        except KeyError:
            ourMeta = self.__meta_base__

            if not issubclass(ourMeta, pmMeta):
                # Dynamically construct a new meta to dodge compatibility
                # issues

                if ourMeta is type:
                    # This pool has no defined metaclass, default to the
                    # PM metaclass
                    ourMeta = pmMeta

                else:
                    metaname = pmMeta.__name__+'PayaShadow'
                    metabases = (ourMeta, pmMeta)
                    metadict = dict(ourMeta.__dict__)
                    ourMeta = type(metaname, metabases, metadict)

                self.metacache[pmMeta] = ourMeta

        return ourMeta

    def getPmBase(self, clsname):
        """
        :param str clsname: the class being retrieved
        :return: A PyMEL base for the requested class.
        :rtype: type
        """
        try:
            pmbase = getattr(self.__pm_mod__, clsname)

            for root in self.__roots__:
                if pmbase is root:
                    break # ok

                if issubclass(root, pmbase):
                    raise ClassTooBasicError(
                    "The pool does not support subclassing"+
                    " from {}.".format(pmbase)
                )

            return pmbase

        except AttributeError:
            raise NoPyMELCounterpartError(
                ("No PyMEL base could be found for '{}' inside"+
                " {}.").format(clsname, self.__pm_mod__)
            )


class NodeClassPool(ShadowPool):
    """
    Administers custom Paya classes for nodes. A browser for this pool can
    be accessed on :mod:`paya.runtime` as ``.nodes``.
    """

    __singular__ = 'node'
    __plural__ = 'nodes'
    __pm_mod__ = pymel.core.nodetypes
    __roots__ = [pymel.core.nodetypes.DependNode]
    __doctitle__ ='Node Types'

    def conformDict(self, clsname, dct):
        """
        Given a class dictionary, returns a modified, where necessary,
        version that can be used to construct a final class.

        :param str clsname: the name of the class being retrieved
        :param dict dct: either an empty dictionary, or the dictionary of
            a template class
        :return: The dictionary.
        :rtype: dict
        """
        dct = super().conformDict(clsname, dct)
        dct['__is_subtype__'] = False

        return dct

nodes = NodeClassPool()


class CompClassPool(ShadowPool):
    """
    Administers custom Paya classes for components. A browser for this pool can
    be accessed on :mod:`paya.runtime` as ``.comps``.
    """
    __singular__ = 'comp'
    __plural__ = 'comps'
    __pm_mod__ = pymel.core.general
    __roots__ = [pymel.core.general.Component]
    __doctitle__ ='Component Types'


comps = CompClassPool()


class PlugClassPool(ShadowPool):
    """
    Administers custom Paya classes for plugs (attributes). Relies on
    :mod:`~paya.pluginfo`. A browser for this pool can
    be accessed on :mod:`paya.runtime` as ``.plugs``.
    """
    # To-Do: Could be a little faster:
    # At the moment getFromPyMELInstance() only sources the plug info
    # to the get the class name, and then that gets passed along to
    # getByName() which re-sources the path for subsequent operations

    __singular__ = 'plug'
    __plural__ = 'plugs'
    __pm_mod__ = pymel.core.general
    __roots__ = [pymel.core.general.Attribute]
    __doctitle__ ='Plug (Attribute) Types'

    def getFromPyMELInstance(self, inst):
        """
        Given a PyMEL instance, returns an appropriate Paya class for
        reassignment.
        """
        info = _pi.getInfoFromAttr(inst)
        return self.getByName(info['type'][-1])

    def getByName(self, clsname):
        try:
            cls = self._cache[clsname]
        except KeyError:
            path = _pi.getPath(clsname)

            self._cache[clsname] = cls = \
                self.buildClassFromTreePath(path)

        return cls

    def buildClassFromTreePath(self, path):
        clsname = path[-1]
        try:
            bases, dct = self.getBasesDictFromTemplate(clsname)
        except MissingTemplateError:
            bases, dct = self.inventBasesDict(clsname)

        # Build the class from the bases and the dict
        meta = self.getMeta(clsname)
        cls = type.__new__(meta, clsname, bases, dct)

        # Modify the module field into a 'runtime' format only after
        # the class is built
        cls.__module__ = 'paya.runtime.'+self.shortName()

        return cls

    def getPmBase(self, clsname):
        """
        :param str clsname: the class being retrieved
        :return: A PyMEL base for the requested class.
        :rtype: type
        """
        return pymel.core.general.Attribute

    def conformBases(self, clsname, bases):
        """
        Given a tuple of bases, returns a modified, where necessary,
        version that can be used to construct a final class.

        :param str clsname: the name of the class being retrieved
        :param tuple bases: either an empty tuple, or bases retrieved from a
            template class
        :return: The bases.
        :rtype: (type,)
        """
        # Requirements:
        # The last of the bases must be a subclass of the plug tree
        # base.

        bases = [base for base in bases if base is not object]
        ptPath = _pi.getPath(clsname)

        ln = len(ptPath)

        if clsname == 'Attribute':
            requiredBase = pymel.core.general.Attribute
        else:
            requiredBaseName = ptPath[-2]
            requiredBase = self.getByName(requiredBaseName)

        if not any([issubclass(
                base, requiredBase) for base in bases]):
            bases.append(requiredBase)

        return tuple(bases)


plugs = PlugClassPool()

def getRootDataClasses():
    """
    :return: Terminating classes detected from :mod:`pymel.core.datatypes`.
    """
    classes = [pair[1] for pair in \
           inspect.getmembers(pymel.core.datatypes, inspect.isclass)]

    out = []

    for cls in classes:
        mro = cls.__mro__[::-1]

        for anc in mro[1:]:
            if anc.__module__ == 'builtins':
                continue

            if 'OpenMaya' in anc.__module__:
                continue

            out.append(anc)
            break

    return list(set(out))


class DataClassPool(ShadowPool):
    """
    Administers custom Paya classes for data types (e.g. vectors). An instance
    of this pool can be accessed on :mod:`paya.runtime` as ``.data``.
    """

    __singular__ = __plural__ = 'data'
    __roots__ = getRootDataClasses()
    __pm_mod__ = pymel.core.datatypes
    __unsupported_lookups__ = ['VectorN', 'MatrixN', 'Array']
    __doctitle__ = 'Data Types'

data = DataClassPool()


class ParsedNodeSubtypePoolMeta(type):
    def __new__(meta, clsname, bases, dct):
        if clsname != 'ParsedNodeSubtypePool':
            baseclsname = re.match(r"^Parsed(.*?)SubtypePool$", clsname).groups()[0]
            dct['__nodeType__'] = \
                nodeType = baseclsname[0].lower()+baseclsname[1:]

            dct['__singular__'] = nodeType
            dct['__plural__'] = nodeType+'s'
            dct['__pm_mod__'] = pymel.core.nodetypes

            pmbase = getattr(pymel.core.nodetypes, baseclsname)

            dct['__roots__'] = [pmbase]
            dct['__doctitle__'] = '{} Subtypes'.format(baseclsname)

        return super().__new__(meta, clsname, bases, dct)


class ParsedNodeSubtypePool(NodeClassPool,
                           metaclass=ParsedNodeSubtypePoolMeta):

    def inventBasesDict(self, clsname):
        """
        :raises NotImplementedError: Not supported on parsed-subtype pools.
        """
        raise NotImplementedError(
            "Invention is not implemented for this pool.")

    def getCrossPoolRoot(self):
        """
        :return: A class from a 'base' class pool, to be used as the basis
            for all classes returned by this one.
        :rtype: :class:`type`
        """
        nodeType = self.__nodeType__

        return nodes.getByName(nodeType[0].upper()+nodeType[1:])

    def attrName(self):
        """
        :return: The name of the string node attribute that will be inspected
            for the type name.
        :rtype: :class:`str`
        """
        return '{}Type'.format(self.__nodeType__)

    def buildClass(self, clsname):
        """
        Builds a final class. If a template is available, it is used.
        Otherwise, if this pool implements invention, the class is invented.
        If this pool doesn't implement invention, an exception is raised.

        :param str clsname: the name of the class to build
        :raises MissingTemplateError: A template couldn't be found, and this
            pool doesn't implement invention.
        :return: The built class.
        :rtype: type
        """
        bases, dct = self.getBasesDictFromTemplate(clsname)
        cls = type(clsname, bases, dct)
        cls.__module__ = 'paya.runtime.'+self.shortName()

        return cls

    def conformDict(self, clsname, dct):
        """
        Given a class dictionary, returns a modified, where necessary,
        version that can be used to construct a final class.

        :param str clsname: the name of the class being retrieved
        :param dict dct: either an empty dictionary, or the dictionary of
            a template class
        :return: The dictionary.
        :rtype: dict
        """
        dct = RebuiltClassPool.conformDict(self, clsname, dct)
        dct['__is_subtype__'] = True

        return dct

    def conformBases(self, clsname, bases):
        """
        Given a tuple of bases, returns a modified, where necessary,
        version that can be used to construct a final class.

        :param str clsname: the name of the class being retrieved
        :param tuple bases: either an empty tuple, or bases retrieved from a
            template class
        :return: The bases.
        :rtype: (type,)
        """
        bases = [b for b in bases if b is not object]
        requiredBase = self.getCrossPoolRoot()

        if not any([issubclass(base, requiredBase) for base in bases]):
            bases.append(requiredBase)

        return tuple(bases)

class ParsedNetworkSubtypePool(ParsedNodeSubtypePool):
    """
    Administers subtypes for 'network' nodes.
    """

networks = ParsedNetworkSubtypePool()


# class ParsedContainerSubtypePool(ParsedNodeSubtypePool):
#     """
#     Administers subtypes for 'container' nodes.
#     """
#
# containers = ParsedContainerSubtypePool()


class PartClassPool(ClassPool):

    __singular__ = 'part'
    __plural__ = 'parts'
    __doctitle__ = 'Part Types'

parts = PartClassPool()


# class GuideClassPool(ClassPool):
#
#     __singular__ = 'guide'
#     __plural__ = 'guides'
#     __doctitle__ = 'Guide Types'
#
# guides = GuideClassPool()
#
#
class RigClassPool(ClassPool):

    __singular__ = 'rig'
    __plural__ = 'rigs'
    __doctitle__ = 'Rig Types'

rigs = RigClassPool()

#----------------------------------------------------------------|
#----------------------------------------------------------------|    REGISTRY
#----------------------------------------------------------------|

pools = [nodes, comps, plugs, data, networks, parts, rigs]
poolsByShortName = {pool.shortName(): pool for pool in pools}
poolsByLongName = {pool.longName():pool for pool in pools}