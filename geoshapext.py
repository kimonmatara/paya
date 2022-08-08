"""
Decorators and descriptors for use in geometry shape classes
(e.g. :class:`paya.runtime.nodes.NurbsCurve`) to help adapt and install
functionality from plug counterparts
(e.g. :class:`paya.runtime.plugs.NurbsCurve`).

See :func:`addPlugToSampler`, :class:`editorFromPlug` and
:class:`samplerFromPlug`.
"""
import inspect, re
from functools import wraps
from paya.util import short, \
    findKeyInClassDicts, sigWithAddedKwargs, LazyModule

import maya.cmds as m
import pymel.core as p

pools = LazyModule('paya.pools')

#------------------------------------------|    User-facing

def addPlugToSampler(f):
    """
    Decorator for :term:`static` shape methods that return sampled values
    (for example tangents). Tags the function as expecting an extension from
    the plug class. When the class is rebuilt by the
    :class:`nodes <paya.pools.NodeClassPool>` pool, a :term:`dynamic` version of
    the method is sourced from the namesake plug class, and used to add
    a *plug/p=False* option to shape method.
    """
    f.__add_plug_to_sampler__ = True
    return f

class _StandinFromPlug:
    __instance__ = None

    def __new__(cls):
        if cls.__instance__ is None:
            cls.__instance__ = object.__new__(cls)

        return cls.__instance__

class samplerFromPlug(_StandinFromPlug):
    """
    Stand-in marker object. If encountered when the class is being rebuilt by
    the :class:`nodes <paya.pools.NodeClassPool>` pool, the following happens:

    -   A base implementation of a :term:`static` sampler method with the same
        name is sought amongst **inherited classes** only.

    -   A :term:`dynamic` counterpart is sought on the plug counterpart (or
        its ancestors).

    -   The two are combined into a new shape method with added *plug/p=False*
        and, if the original shape method wrangles spaces,
        *worldSpace/ws=False* options.

    :Example:

        Given a plug method that looks like this:

        .. code-block:: python

            class NurbsCurve: # plug class

                def normal(self, parameter):
                    '''
                    Hook up pointOnCurveInfo, return its outpu
                    '''

        And an entry in the shape class that looks like this:

        .. code-block:: python

            class NurbsCurve: # shape class

                normal = samplerFromPlug()

        The entry is then resolved to:

        .. code-block:: python

            class NurbsCurve: # shape class

                @short(plug='p', worldSpace='ws'
                def normal(self, parameter, space='preTransform', plug=False, worldSpace=None):
                    '''
                    Calls inherited implementation of normal() if plug is False,
                    otherwise picks a plug output based on space options and calls
                    the plug method on that.
                    '''

    .. warning::

        This should **not** be used if the :term:`static` method
        implementation is in the current class, since the stand-in will
        replace the method (or vice versa) in the dictionary. In this case
        use :func:`addPlugToSampler` instead.

    """
    __instance__ = None

class editorFromPlug(_StandinFromPlug):
    """
    Stand-in marker object. If encountered when the class is being rebuilt by
    :class:`nodes <paya.pools.NodeClassPool>`, the following happens:

    -   A method with the same name is retrieved from the plug class.
    -   The method is modified in the following ways:

        -   A *worldSpace/ws=False* keyword argument is added
        -   The method is rerouted to run off of a
            :meth:`history input <paya.runtime.nodes.DeformableShape.getHistoryPlug>`
            and to return shapes instead of plugs, mimicking the behaviour of
            standard Maya modelling commands with construction history on.
    """
    __instance__ = None

#------------------------------------------|    Utilities

def getFuncRst(f):
    try:
        f = f.__wrapped__
    except:
        pass

    mod = inspect.getmodule(f).__name__
    mt = re.match(r"^paya.hybridgeotypes\.(?:.*)$", mod)

    if mt:
        mod = 'paya.runtime.hybridgeos'

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

    chunks = ['.. rubric:: Adapted Method']

    if notes:
        notes = inspect.cleandoc(notes)
        chunks.append(notes)

    # Get main documentation
    for source in sources:
        doc = inspect.getdoc(source)

        if doc:
            header = '.. rubric:: Documentation from {}'.format(
                getFuncRst(source))

            doc = '\n'.join([header, '', doc])
            chunks.append(doc)

    if chunks:
        out = '\n\n'.join(chunks)
        return out

    return 'This method has no documentation.'

#------------------------------------------|    Implementation

def _deriveShapeEditorFromPlugEditor(plugFunc, clsname):
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

        if type(heroPlug).__name__ == clsname:
            heroPlug >> callingShape.geoInput
            outShapes.append(callingShape)

        else:
            m.warning("Shape {} will be replaced.".format(self))
            origName = callingShape.basename()
            callingShape.rename('tmp')
            heroShape = heroPlug.createShape(under=pnt)
            heroShape.rename(origName)
            p.delete(callingShape)
            outShapes.append(heroShape)

        for sourcePlug in sourcePlugs[1:]:
            # shape = sourcePlug.createShape(under=pnt)
            shape = sourcePlug.createShape()
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
    return wrapper

def _addPlugToSampler(methodName, shapeFunc, clsname):
    # Gather information

    plugcls = pools.plugs.getByName(clsname)

    try:
        plugFunc = findKeyInClassDicts(methodName, plugcls)

    except KeyError:
        raise RuntimeError(("{}: No plug counterpart found for static "+
                            "sampler {}().").format(methodName, clsname))

    shapeFuncSig = inspect.signature(shapeFunc)
    shapeFuncExpectsSpace = 'space' in shapeFuncSig.parameters
    shapeFuncExpectsWorldSpace = 'worldSpace' in shapeFuncSig.parameters

    if shapeFuncExpectsSpace:
        spaceDefault = shapeFuncSig.parameters['space'].default

        addWorldSpace = not shapeFuncExpectsWorldSpace

    else:
        addWorldSpace = False

    expectWorldSpace = addWorldSpace or shapeFuncExpectsWorldSpace

    if expectWorldSpace:
        if addWorldSpace:
            worldSpaceDefault = None

        else:
            worldSpace = spaceFuncSig.parameters['worldSpace'].default

    # Define stand-in

    def wrapper(self, *args, **kwargs):
        if expectWorldSpace:
            worldSpace = kwargs.pop('worldSpace', worldSpaceDefault)

        if shapeFuncExpectsSpace:
            space = kwargs.pop('space', spaceDefault)

            if expectWorldSpace:
                if worldSpace is not None:
                    space = 'world' if worldSpace else 'preTransform'

        plug = kwargs.pop('plug', False)

        if plug:
            if shapeFuncExpectsSpace:
                if space in ('preTransform', 'object'):
                    pullWorldPlug = False

                elif space == 'world':
                    pullWorldPlug = True

                else:
                    raise NotImplementedError(
                        "Plug output is only supported for these space "+
                        "options: 'object', 'preTransform' and 'world'."
                    )

            elif expectWorldSpace:
                pullWorldPlug = worldSpace

            else:
                pullWorldPlug = False

            plugOutput = self.getGeoOutput(worldSpace=pullWorldPlug)

            return plugFunc(plugOutput, *args, **kwargs)

        if shapeFuncExpectsSpace:
            kwargs['space'] = space

        if shapeFuncExpectsWorldSpace:
            kwargs['worldSpace'] = worldSpace

        return shapeFunc(self, *args, **kwargs)

    # Edit signature:
    # 1) Change name
    # 2) Formulate doc
    # 3) Edit arguments

    # Add arguments
    kwargs = {'plug': False}

    if addWorldSpace:
        kwargs['worldSpace'] = worldSpaceDefault

    wrapper.__signature__ = sigWithAddedKwargs(shapeFuncSig, **kwargs)

    # Edit name
    wrapper.__name__ = methodName

    # Add shorthands
    shortsKw = {'plug':'p'}

    if addWorldSpace:
        shortsKw['worldSpace'] = 'ws'

    wrapper = short(**shortsKw)(wrapper)

    # Edit doc

    notes = [
        "The following keyword arguments have been added:",
        "",
        "- **plug/p** (:class:`bool`) - return live attributes rather than values; defaults to ``False``"
    ]

    if addWorldSpace:
        if shapeFuncExpectsSpace:
            notes.append(
                "- **worldSpace/ws** (:class:`bool`) - if specified, overrides *space* to 'preTransform' or 'world'; defaults to ``None``"
            )

        else:
            notes.append(
                "- **worldSpace/ws** (:class:`bool`) - return a world-space value or plug; defaults to ``False``"
            )

    notes = '\n'.join(notes)
    wrapper.__doc__ = makeDoc([shapeFunc, plugFunc], notes)

    return wrapper

#------------------------------------------|    Class expansion callable

def expandShapeClass(cls):
    # Called by the nodes pool to extend geometry shape classes.
    clsname = cls.__name__
    plugcls = None

    for k, v in cls.__dict__.items():
        if inspect.isfunction(v):
            if getattr(v, '__add_plug_to_sampler__', False):
                setattr(cls, k, _addPlugToSampler(k, v, clsname))

        elif isinstance(v, samplerFromPlug):
            # Find inherited sampler implementation

            try:
                shapeFunc = findKeyInClassDicts(k, cls, start=1)

            except:
                raise RuntimeError(
                    ("{}: Couldn't find an inherited implementation for "+
                     "shape sampler '{}'.").format(clsname, k))

            setattr(cls, k, _addPlugToSampler(k, shapeFunc, clsname))

        elif isinstance(v, editorFromPlug):
            if plugcls is None:
                plugcls = pools.plugs.getByName(clsname)

            # Get function directly by attr access (Python 3.x--
            # in 2.7 would need to retrieve from dict)

            plugFunc = getattr(plugcls, k)

            setattr(cls, k,
                    _deriveShapeEditorFromPlugEditor(plugFunc, clsname))