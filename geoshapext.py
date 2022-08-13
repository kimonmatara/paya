import re
import inspect
from functools import wraps
import textwrap
import inspect

import maya.cmds as m
import pymel.core as p
from paya.util import short, sigWithAddedKwargs
import paya.pools as pools

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

class copyToShape:
    """
    Decorator-with-arguments. Use it on plug functions to signal that they
    should be copied over to the shape class. Any keyword arguments
    captured by :meth:`__init__` are forwarded to
    :func:`copyPlugFuncToShapeClassDict`.

    Note that the shape classes won't pick up these 'sends' unless they
    are themselves built, or rebuilt, using :class:`ShapeExtensionMeta`.
    """
    def __init__(self, **copyToShapeKwargs):
        self.copyToShapeKwargs = copyToShapeKwargs

    def __call__(self, f):
        f.__copy_to_shape__ = self.copyToShapeKwargs
        return f

@short(worldSpaceOnly='wso', editsHistory='eh')
def copyPlugFuncToShapeClassDict(plugFunc,
                                 dictKeys,
                                 className,
                                 shapeClassDict,
                                 editsHistory=False,
                                 worldSpaceOnly=False):
    """
    Copies a plug function (method) to the dictionary of an under-construction
    shape class, with appropriate modifications.

    :param plugFunc: the function (method) on the plug class
    :param dictKeys: all the dictionary keys under which the function appears
        (there may be several if 'aliases' are used)
    :type dictKeys: [:class:`str`]
    :param str className: the shared name of the shape and plug classes
    :param dict shapeClassDict: the dictionary of the shape class being
        constructed
    :param bool editsHistory/eh: indicates that the plug function should be
        wrapped to use the shape's history input and return shapes; defaults to
        ``False``
    :param worldSpaceOnly/wso: don't add any *worldSpace/ws* keyword argument;
        always run the method on the shape's world-space geo output; defaults
        to ``False``
    """

    if editsHistory: # skip all other checks and just implement a loopback
        if worldSpaceOnly:
            raise RuntimeError(
            "Can't implement 'worldSpaceOnly' on an editor method.")

        #------------------------------------------------|    Define wrapper

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

            if type(heroPlug).__name__ == className:
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
                shape = sourcePlug.createShape()
                # Create a transformationally-matched parent
                shapePnt = shape.getParent()
                shapePnt.setMatrix(pnt.getMatrix(worldSpace=True))
                outShapes.append(shape)

            if multi:
                return outShapes

            return outShapes[0]

        #------------------------------------------------|    Edit signature / doc

        notes = \
        """
        Attached from plug class. Plug outputs are replaced with shapes. These
        should be caught, as some operations may entirely replace the original
        shape instance. History is always preserved.
        """

        wrapper.__doc__ = makeDoc([plugFunc], notes)

    else:
        # For everything non-editor related, checks must be more thorough;
        # First, look for a namesake in the shape class dict, or across the
        # PM base and its ancestors

        pmBaseCls = getattr(p.nodetypes, className)
        shapeFunc = None
        allNames = [plugFunc.__name__] + list(dictKeys)

        for name in allNames:
            try:
                shapeFunc = shapeClassDict[name]
                break

            except KeyError:
                continue

        if shapeFunc is None:
            for ancestor in pmBaseCls.__mro__:
                if ancestor is p.PyNode:
                    break

                found = False

                for name in allNames:
                    try:
                        shapeFunc = ancestor.__dict__[name]
                        found = True
                        break

                    except KeyError:
                        continue

                if found:
                    break

        # Prelim info on plug func
        plugFuncSig = inspect.signature(plugFunc)
        plugFuncTakesPlug = 'plug' in plugFuncSig.parameters

        # If a shape func was found, get signature information and construct
        # an adjusted wrapper

        if shapeFunc is not None:


            shapeFuncSig = inspect.signature(shapeFunc)
            shapeFuncTakesSpace = 'space' in shapeFuncSig.parameters

            if shapeFuncTakesSpace:
                if worldSpaceOnly:
                    raise RuntimeError(
                        ("Can't apply 'worldSpaceOnly' "+
                        "because {} shape method {}() takes 'space'.").format(
                        className, shapeFunc.__name__())
                    )

                spaceDefault = shapeFuncSig.parameters['space'].default

            if worldSpaceOnly:
                addWorldSpace = False

            else:
                addWorldSpace = True

                if shapeFuncTakesSpace:
                    worldSpaceDefault = None

                else:
                    worldSpaceDefault = False

            #------------------------------------------------|    Define wrapper

            def wrapper(callingShape, *args, **kwargs):
                plug = kwargs.pop('plug', False)

                if addWorldSpace:
                    worldSpace = kwargs.pop('worldSpace', worldSpaceDefault)

                if shapeFuncTakesSpace:
                    space = kwargs.pop('space', spaceDefault)

                    # We will have added worldSpace in this case, so
                    # apply override

                    if worldSpace is not None:
                        space = 'world' if worldSpace else 'preTransform'

                if plug:
                    # Determine which output to use

                    if shapeFuncTakesSpace:
                        if space in ('preTransform', 'object', 'world'):
                            useWorld = space == 'world'

                        else:
                            raise NotImplementedError(
                                ("Plug output is only available for "+
                                 "these spaces: 'preTransform', 'object', 'world'.")
                            )

                    elif worldSpaceOnly:
                        useWorld = True

                    else:
                        if worldSpace is not None:
                            useWorld = worldSpace

                        else:
                            useWorld = False

                    output = callingShape.getGeoOutput(ws=useWorld)

                    if plugFuncTakesPlug:
                        kwargs['plug'] = plug

                    return plugFunc(output, *args, **kwargs)

                if shapeFuncTakesSpace:
                    kwargs['space'] = space

                return shapeFunc(callingShape, *args, **kwargs)

            #------------------------------------------------|    Edit signature / doc

            # Signature should be:
            # basics taken from shape func; plug/p added in all cases;
            # worldSpace/ws added conditionally

            wrapper.__name__ = shapeFunc.__name__

            shorts = {'plug':'p'}

            addedKwargs = {'plug': False}

            if addWorldSpace:
                addedKwargs['worldSpace'] = worldSpaceDefault
                shorts['worldSpace'] = 'ws'

            wrapper.__signature__ = \
                sigWithAddedKwargs(shapeFuncSig, **addedKwargs)

            wrapper = short(**shorts)(wrapper)

            # Edit doc
            notes = \
            """
            Overloads the shape method with functionality from the plug class.
            The original has been modified in these ways:
            """

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

        else:
            # If we're here, we're copying a non-editor method that has no
            # namesake in the shape class or PM mro

            # Signature is taken from plug func, with the following changes:
            # if plug func implements plug/p, override it to False
            # if not worldSpaceOnly, add a worldSpace/ws option, defaulting to
            # False

            addWorldSpace = not worldSpaceOnly

            def wrapper(callingShape, *args, **kwargs):
                if plugFuncTakesPlug:
                    # Enforce default
                    kwargs.setdefault('plug', False)

                # Determine which output to call on

                if addWorldSpace:
                    worldSpace = kwargs.pop('worldSpace', False)

                    useWorld = worldSpace

                elif worldSpaceOnly:
                    useWorld = True

                else:
                    useWorld = False

                output = callingShape.getGeoOutput(ws=useWorld)
                return plugFunc(output, *args, **kwargs)

            sig = plugFuncSig

            if addWorldSpace:
                sig = sigWithAddedKwargs(sig, worldSpace=False)

            wrapper.__signature__ = sig
            wrapper.__name__ = plugFunc.__name__

            if addWorldSpace:
                wrapper = short(worldSpace='ws')(wrapper)

            notes = None

            if addWorldSpace or plugFuncTakesPlug:
                notes = "Adapted from a plug method."

                if addWorldSpace:
                    notes += " A *worldSpace/ws* keyword argument has been "+\
                        "added, defaulting to ``False``."

                if plugFuncTakesPlug:
                    notes += " The *plug/p* keyword argument has been "+\
                        "overriden to a default of ``False``."

                notes = textwrap.fill(notes, width=60)

            doc = makeDoc([plugFunc], notes=notes)
            wrapper.__doc__ = makeDoc([plugFunc], notes=notes)

    for key in dictKeys:
        shapeClassDict[key] = wrapper

def expandShapeClassDict(clsname, classDict):
    plugClass = pools.plugs.getByName(clsname)

    toProcess = {}  # where: {plugFuncName:
                    # {dictKeys:[str], copytoShapeKwargs:{}, plugFunc:f}}

    for k, v in plugClass.__dict__.items():
        if inspect.isfunction(v):
            try:
                copyToShapeKwargs = getattr(v, '__copy_to_shape__')

            except AttributeError:
                continue

            plugFunc = v
            plugFuncName = plugFunc.__name__

            if plugFuncName in toProcess:
                toProcess[plugFuncName]['dictKeys'].append(k)

            else:
                toProcess[plugFuncName] = \
                    {'dictKeys':[k],
                     'copyToShapeKwargs':copyToShapeKwargs,
                     'plugFunc': plugFunc}

    for plugFuncName, info in toProcess.items():
        copyPlugFuncToShapeClassDict(
            info['plugFunc'],
            info['dictKeys'],
            clsname,
            classDict,
            **info['copyToShapeKwargs']
        )

class ShapeExtensionMeta(type):
    """
    When this metaclass is assigned to, or used to rebuild, a template class
    for a geometry shape, it will look in the matching plug class for any
    methods decorated with :class:`@copyToShape <copyToShape>` and copy them
    over.
    """
    def __new__(meta, clsname, bases, dct):
        expandShapeClassDict(clsname, dct)

        return super().__new__(meta, clsname, bases, dct)