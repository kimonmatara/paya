"""
Tools for adapting and copying functionality on geo plug classes over to
their shape counterparts.
"""

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

@short(
    worldSpaceOnly='wso',
    editsHistory='eh',
    bezierInterop='bio',
    replace='rep'
)
def copyPlugFuncToShapeClassDict(plugFunc,
                                 dictKeys,
                                 className,
                                 shapeClassDict,
                                 editsHistory=False,
                                 worldSpaceOnly=False,
                                 bezierInterop=True,
                                 replace=False
                                 ):
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
    :param bool worldSpaceOnly/wso: don't add any *worldSpace/ws* keyword argument;
        always run the method on the shape's world-space geo output; defaults
        to ``False``
    :param bool bezierInterop/bio: ignored if *editsHistory* is ``False``;
        consider NURBS and Bezier types to be interoperable (i.e. connect
        a NURBS output directly to a hero shape and vice versa, without
        swapping the shape)
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

            heroPlugCls = type(heroPlug)
            workingPlugCls = type(workingPlug)

            passthrough = (heroPlugCls is workingPlugCls) or (
                    bezierInterop and {heroPlugCls, workingPlugCls
                    } == {r.plugs.BezierCurve, r.plugs.NurbsCurve})

            if passthrough:
                heroPlug >> callingShape.geoInput
                outShapes.append(callingShape)

            else:
                m.warning("Shape {} will be replaced.".format(callingShape))
                origName = callingShape.basename()
                callingShape.rename('tmp')
                heroShape = heroPlug.createShape(p=pnt)
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
        # Look for namesake implementation on PM base or shape dict

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

        if shapeFunc is None:
            # We're copying a function for which there's no existing namesake;
            # wrap with an added worldSpace=False kwarg, unless worldSpaceOnly

            plugFuncSig = inspect.signature(plugFunc)
            addWorldSpace = not worldSpaceOnly

            def wrapper(callingShape, *args, **kwargs):
                if addWorldSpace:
                    worldSpace = kwargs.pop('worldSpace', False)
                    useWorld = worldSpace

                else:
                    useWorld = worldSpaceOnly

                output = callingShape.getGeoOutput(ws=useWorld)
                return plugFunc(output, *args, **kwargs)

            sig = plugFuncSig

            if addWorldSpace:
                sig = sigWithAddedKwargs(sig, worldSpace=False)

            wrapper.__wrapped__ = plugFunc
            wrapper.__signature__ = sig
            wrapper.__name__ = plugFunc.__name__

            notes = None

            if worldSpaceOnly:
                notes = \
                """
                Added from a plug method; only runs in world-space.
                """

            if addWorldSpace:
                wrapper = short(worldSpace='ws')(wrapper)

                notes = \
                """
                Added from a plug method; a *worldSpace/ws* keyword argument
                has been added, defaulting to ``False``.
                """

            notes = textwrap.fill(inspect.cleandoc(notes), width=60)
            wrapper.__doc__ = makeDoc([plugFunc], notes=notes)

        else:
            raise RuntimeError(
                ("Can't copy {}() to shape class as one or more of the "+
                 "dictionary names are in use."
                 ).format(shapeFunc.__name__))

    for key in dictKeys:
        shapeClassDict[key] = wrapper

def expandShapeClassDict(clsname, classDict):
    """
    Expands the dictionary of an under-construction shape class with any
    methods in the namesake plugs class that have been decorated with
    :class:`@copyToShape <copyToShape>`.

    :param str clsname: the name of the shape class
    :param classDict: the dictionary of the shape class
    """
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