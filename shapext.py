from functools import wraps
import inspect
import textwrap
import re

import maya.cmds as m
import pymel.core as p
from paya.util import sigWithAddedKwargs, short
import paya.pools as pools
import paya.plugtree as _pt


class copyToShapeAsEditor:
    def __init__(self, **config):
        self._config = config

    def __call__(self, f):
        f.__geo_editor__ = True
        f.__geo_editor_config__ = self._config
        return f

class copyToShapeAsSampler:
    def __init__(self, **config):
        self._config = config

    def __call__(self, f):
        f.__geo_sampler__ = True
        f.__geo_sampler_config__ = self._config
        return f

class copyToShape:
    def __init__(self, **config):
        self._config = config

    def __call__(self, f):
        f.__geo_verbatim__ = True
        f.__geo_verbatim_config__ = self._config
        return f


def removeNativeUnitsWrapper(f):
    if getattr(f, '__nativeunits__', False):
        f = f.__wrapped__

    return f

def getFuncRst(f):
    try:
        f = f.__wrapped__
    except:
        pass

    mod = inspect.getmodule(f).__name__

    # paya.nodetypes.transform.Transform
    pat = r"^paya\.(.*?types)\..*$"

    mt = re.match(pat, mod)

    if mt:
        longPoolName = mt.groups()[0]
        pool = pools.poolsByLongName[longPoolName]
        shortName = pool.shortName()
        mod = "paya.runtime.{}".format(shortName)

    return ":meth:`{}.{}`".format(mod, f.__qualname__)


def makeDoc(sources, notes=None):
    """
    :param sources: the functions to inspect for docstrings, in
        order of preference
    :type sources: [:class:`~types.FunctionType`]
    :param notes: optional notes to prepend; defaults to ``None``
    :return: The constructed docstring.
    :rtype: str
    """
    chunks = []

    if notes:
        header = ['.. note::','']
        header += ['    '+line for line in notes.split('\n')]
        header = '\n'.join(header)
        chunks.append(header)

    # Get main documentation
    for source in sources:
        doc = inspect.getdoc(source)

        if doc:
            header = '.. rubric:: Documentation from {}:'.format(
                getFuncRst(source))

            doc = '\n'.join([header, '', doc])
            chunks.append(doc)

    if chunks:
        out = '\n\n'.join(chunks)
        return out

    return 'This method has no documentation.'

def copyPlugVerbatimToShapeClassDict(plugFunc, dictKeys, config, shapeClsName, dct):
    for key in dictKeys:
        dct[key] = plugFunc

def copyPlugEditorToShapeClassDict(plugFunc, dictKeys,
                                   config, shapeClsName,
                                   dct):

    @wraps(plugFunc)
    def wrapper(callingShape, *args, **kwargs):
        workingPlug = callingShape.getHistoryPlug(create=True)
        result = plugFunc(workingPlug, *args, **kwargs)

        multi = isinstance(result, (tuple, list))

        if multi:
            sourcePlugs = result

        else:
            sourcePlugs = [result]

        outShapes = []
        heroPlug = sourcePlugs[0]
        pnt = callingShape.getParent()

        # If the output is compatible with self, pipe into
        # self; otherwise create a shape from the hero plug
        # and replace self with it entirely, as Maya's commands
        # do it--this does means the original PyNode instance
        # will be obsolete, and should be replaced with the caught
        # shape return.

        if type(heroPlug).__name__ == shapeClsName:
            heroPlug >> callingShape.geoInput
            outShapes.append(callingShape)

        else:
            m.warning("Shape {} will be replaced.".format(callingShape))
            origName = callingShape.basename()
            callingShape.rename('tmp')
            heroShape = heroPlug.createShape(under=pnt)
            heroShape.rename(origName)
            p.delete(callingShape)
            outShapes.append(heroShape)

        for sourcePlug in sourcePlugs[1:]:
            # shape = sourcePlug.createShape(under=pnt)
            shape = sourcePlug.createShape()
            # Create a transformationally-matched parent
            shapePnt = shape.getParent()
            shapePnt.setMatrix(pnt.getMatrix(worldSpace=True))
            outShapes.append(shape)

        if multi:
            return outShapes

        return outShapes[0]

    notes = \
    """
    Attached from plug class. Plug outputs are replaced with shapes. These
    should be caught, as some operations may entirely replace the original
    shape instance. History is always preserved.
    """
    wrapper.__doc__ = makeDoc([plugFunc], notes)

    for dictKey in dictKeys:
        dct[dictKey] = wrapper

def copyPlugSamplerToShapeClassDict(plugFunc, dictKeys,
                                    config, shapeClsName,
                                    dct, pmbase):

    funcName = plugFunc.__name__
    shapeFunc = None
    allNames = set(dictKeys + [funcName])
    worldSpaceOnly = config.get('worldSpaceOnly', False)

    for name in allNames:
        try:
            shapeFunc = dct[name]
            break

        except KeyError:
            pass

        found = False

        for anc in pmbase.__mro__:
            try:
                shapeFunc = anc.__dict__[funcName]
                found = True
                break

            except KeyError:
                pass

        if found:
            break

    if shapeFunc is not None:

        # If there's a PyMEL base function, can only supplant with a
        # plug counterpart that itself can take plug/p=False to return
        # a non-dynamic output.

        plugFuncSig = inspect.signature(plugFunc)

        if 'plug' not in plugFuncSig.parameters:
            raise RuntimeError(
                ("Can't overwrite base PyMEL shape method {}() "+
                "with sampler, because sampler does not "+
                "implement plug=False.").format(shapeFunc.__name__))

        #-------------------------|    Wrap / extend a PM base method

        # Get info on pm base method
        shapeFuncSig = inspect.signature(shapeFunc)
        shapeFuncTakesSpace = 'space' in shapeFuncSig.parameters

        if shapeFuncTakesSpace:
            if worldSpaceOnly:
                raise RuntimeError((
                    "Can't wrap with 'worldSpaceOnly' because the "+
                    "original PyMEL method {}() takes a 'space'"+
                    " kwarg.").format(shapeFunc.__name__))

            spaceDefault = shapeFuncSig.parameters['space'].default

        addWorldSpace = shapeFuncTakesSpace or not worldSpaceOnly

        if addWorldSpace:
            worldSpaceDefault = None if shapeFuncTakesSpace else False

        def wrapper(callingShape, *args, **kwargs):
            # Wrangle incoming args

            if addWorldSpace:
                worldSpace = kwargs.pop('worldSpace', worldSpaceDefault)

            if shapeFuncTakesSpace:
                space = kwargs.pop('space', spaceDefault)

                if addWorldSpace:
                    if worldSpace is not None:
                        space = 'world' if worldSpace else 'preTransform'

            plug = kwargs.pop('plug', False)

            if plug:
                # Determine which output to use
                if worldSpaceOnly:
                    useWorld = True

                elif shapeFuncTakesSpace:
                    if space in ('preTransform', 'object', 'world'):
                        useWorld = space == 'world'
                    else:
                        raise RuntimeError(
                            "Plug output is only supported for the"+
                            " 'preTransform', 'object' and 'world' "+
                            "spaces.")

                else:
                    useWorld = False

                output = callingShape.getGeoOutput(ws=useWorld)
                kwargs['plug'] = True

                return plugFunc(output, *args, **kwargs)

            # Revert to shape method
            if shapeFuncTakesSpace:
                kwargs['space'] = space

            return shapeFunc(callingShape, *args, **kwargs)

        #--------------|    Edit signature

        # add keyword arguments
        shorts = {'plug':'p'}

        addedKwargs = {'plug': False}

        if addWorldSpace:
            shorts['worldSpace'] = 'ws'
            addedKwargs['worldSpace'] = worldSpaceDefault

        sig = sigWithAddedKwargs(shapeFuncSig, **addedKwargs)

        wrapper.__signature__ = sig
        wrapper.__name__ = shapeFunc.__name__

        wrapper = short(**shorts)(wrapper)

        #--------------|    Edit doc

        notes = \
        """
        Overloads {} with functionality from the plug class. The original
        has been modified in these ways:
        """.format(getFuncRst(shapeFunc))

        notes = inspect.cleandoc(notes)

        bullets = [
            "A *plug/p* keyword argument has been added with a "+
            "default of ``False``. Pass ``True`` to invoke "+
            "the plug method."
        ]

        if addWorldSpace:
            if shapeFuncTakesSpace:
                bullets.append(
                    "A *worldSpace/ws* keyword argument has been "+
                    "added, with a default of ``None``. If specified, "+
                    "this will override *space* to "+
                    "``'preTransform'`` or ``'world'``. Plug "+
                    "output is only available for the "+
                    "``'preTransform'``, ``'object'`` and "+
                    "``'world'`` enumerators; other modes will "+
                    "throw :class:`NotImplementedError`."
                )

            else:
                bullets.append(
                    "A *worldSpace/ws* keyword has been added, "+
                    "with a default of ``False``. This will determine "+
                    "which geometry output will be used for the plug"+
                    " implementation."
                )

        bullets = ['- '+bullet for bullet in bullets]
        bullets = '\n'.join(bullets)

        notes = '\n\n'.join([notes, bullets])

        wrapper.__doc__ = makeDoc([shapeFunc, plugFunc], notes=notes)

        for key in dictKeys:
            dct[key] = wrapper

    else:
        #-------------------------|    Create a 'fresh' wrapper

        sig = inspect.signature(plugFunc)
        plugFuncTakesPlug = 'plug' in sig.parameters

        def wrapper(callingShape, *args, **kwargs):
            if plugFuncTakesPlug:
                kwargs.setdefault('plug', False)

            if worldSpaceOnly:
                worldSpace = True

            else:
                worldSpace = kwargs.pop('worldSpace', False)

            outputPlug = callingShape.getGeoOutput(ws=worldSpace)

            return plugFunc(outputPlug, *args, **kwargs)

        #-----------|   Edit signature

        # If plug func takes 'plug', override it to a default of False

        if plugFuncTakesPlug:
            index = None
            params = list(sig.parameters.values())

            for i, param in enumerate(params):
                if param.name == 'plug':
                    index = i
                    break

            params[index] = params[index].replace(default=False)
            sig = sig.replace(parameters=params)

        shorts = {}

        # Add worldSpace/ws
        if not worldSpaceOnly:
            sig = sigWithAddedKwargs(sig, worldSpace=False)
            shorts['worldSpace'] = 'ws'

        wrapper.__signature__ = sig
        wrapper.__name__ = funcName

        if plugFuncTakesPlug:
            shorts['plug'] = 'p'

        if shorts:
            wrapper = short(**shorts)(wrapper)

        #-----------|   Edit doc

        note_entries = []

        if worldSpaceOnly:
            note_entries.append("Adapted from the world-space plug method.")

        else:
            note_entries.append("Adapted from the plug method. "+
                "A *worldSpace/ws* keyword argument has been added, "+
                "with a default of ``False``. This will determine which "+
                "geometry output the method will be called on.")

        if plugFuncTakesPlug:
            note_entries.append("The *plug* argument default has been overriden to ``False``.")

        notes = ' '.join(note_entries)
        notes = textwrap.fill(notes, width=60)

        wrapper.__doc__ = makeDoc([plugFunc], notes=notes)

        for key in dictKeys:
            dct[key] = wrapper


class ShapeExtensionMeta(type):

    def __new__(meta, clsname, bases, dct):
        # Find matching plug class
        plugCls = pools.plugs.getByName(clsname)

        editors = {} # {funcName: {dictKeys: [], func: func, config:{}}}
        samplers = {} # {funcName: {dictKeys: [], func: func, config:{}}}
        verbatim = {}  # {funcName: {dictKeys: [], func: func, config:{}}}

        for k, v in plugCls.__dict__.items():
            if inspect.isfunction(v):
                funcName = v.__name__

                if getattr(v, '__geo_editor__', False):
                    if funcName in editors:
                        editors[funcName]['dictKeys'].append(k)

                    else:
                        editors[funcName] = {
                            'dictKeys': [k],
                            'func': removeNativeUnitsWrapper(v),
                            'config': v.__geo_editor_config__
                        }

                elif getattr(v, '__geo_sampler__', False):
                    if funcName in samplers:
                        samplers[funcName]['dictKeys'].append(k)

                    else:
                        samplers[funcName] = {
                            'dictKeys': [k],
                            'func': removeNativeUnitsWrapper(v),
                            'config': v.__geo_sampler_config__
                        }

                elif getattr(v, '__geo_verbatim__', False):
                    if funcName in verbatim:
                        verbatim[funcName]['dictKeys'].append(k)

                    else:
                        verbatim[funcName] = {
                            'dictKeys': [k],
                            'func': removeNativeUnitsWrapper(v),
                            'config': v.__geo_verbatim_config__
                        }

        # Copy editors
        for funcName, info in editors.items():
            copyPlugEditorToShapeClassDict(
                info['func'], info['dictKeys'], info['config'], clsname, dct)

        # Copy samplers
        pmbase = getattr(p.nodetypes, clsname)

        for funcName, info in samplers.items():
            copyPlugSamplerToShapeClassDict(
                info['func'], info['dictKeys'], info['config'], clsname, dct, pmbase)

        # Copy verbatims
        for funcName, info in verbatim.items():
            copyPlugVerbatimToShapeClassDict(
                info['func'], info['dictKeys'], info['config'], clsname, dct)

        return super().__new__(meta, clsname, bases, dct)


