"""
WIP -- unified type-checking methods for hybrid plug / value workflows.

Functions in this module expect patched PyMEL.
"""
from functools import wraps
import inspect
import maya.cmds as m
import pymel.core as p
from paya.util import short, LazyModule, conditionalExpandArgs

r = LazyModule('paya.runtime')

# def get1DOutputAttrTypeForPolyadicOperation(*operands):
#     """
#     Given a bunch of operands, returns the appropriate output attribute
#     type. Used by the maths operators.
#
#     :param \*operands: the input operands
#     :return: One of 'double', 'doubleLinear', 'doubleAngle' or 'time'
#     :rtype: :class:`str`
#     """
#     # Algorithm:
#     # Conform operands to data or plug types
#     # Find the first operand which isn't a simple type and take the type
#     # from that
#     # If all are simple types, return 'double'
#
#     out = None
#
#     for operand in operands:
#         if isinstance(operand, p.Attribute):
#             return operand.type()
#             break
#
#         if isinstance(operand, str):
#             return p.Attribute(operand).type()
#
#         if isinstance(operand, p.datatypes.Unit):
#             return {
#                 p.datatypes.Time: 'time',
#                 p.datatypes.Angle: 'doubleAngle',
#                 p.datatypes.Distance: 'doubleLinear'
#             }.get(type(operand), 'double')
#
#     return 'double'


@short(angle='a')
def mathInfo(item, angle=False):
    """
    :param item: a value or plug (simple or PyMEL type)
    :param bool angle/a: unless already typed, instantiate using
        angle / Euler rotation types; defaults to ``False``
    :return: A tuple of: conformed item, item maths dimension (or None),
        item is a plug
    """
    if isinstance(item, (float, int, bool)):
        if angle:
            item = r.data.Angle(item)

        return item, 1, False

    if isinstance(item, p.datatypes.Unit):
        return item, 1, False

    if isinstance(item, p.datatypes.Array):
        return item, len(item), False

    if isinstance(item, p.Attribute):
        return item, item.__math_dimension__, True

    if isinstance(item, str):
        try:
            item = p.Attribute(item)
            return item, item.__math_dimension__, True
        except:
            return item, None, False

    if hasattr(item, '__iter__'):
        members = list(item)

        if all((isScalarValue(member) for member in members)):
            ln = len(members)

            try:
                cls = {
                    3: p.datatypes.EulerRotation \
                        if angle else p.datatypes.Vector,
                    4: p.datatypes.Quaternion,
                    16: p.datatypes.Matrix
                }[ln]

            except KeyError:
                raise TypeError("Can't parse maths item: {}".format(item))

            return cls(item), ln, False

    raise TypeError("Can't parse maths item: {}".format(item))

def isPyMELObject(item):
    """
    :param item: the item to inspect
    :return: True if *item* is an instance of a PyMEl class, otherwise False
    :rtype: bool
    """
    return isinstance(item, (r.PyNode, p.datatypes.Array, p.datatypes.Unit))

def isPlug(item):
    """
    :param item: the item to inspect
    :return: ``True`` if *item* represents an attribute, otherwise ``False``.
    :rtype: :class:`bool`
    """
    if isinstance(item, p.Attribute):
        return True

    else:
        try:
            p.Attribute(item)
            return True

        except (p.MayaNodeError, TypeError):
            pass

    return False

def isScalarValue(value):
    """
    :param value: the value to inspect
    :return: ``True`` if *value* is an instance of :class:`int`,
        :class:`float`, :class:`bool` or
        :class:`~pymel.core.datatypes.Unit`
    :rtype: :class:`bool`
    """
    return isinstance(value, (int, float, bool, p.datatypes.Unit))

def isScalarPlug(item):
    """
    :param item: the item to inspect
    :return: ``True`` if *item* is an :class:`~pymel.core.general.Attribute`
        instance, or a string representations of a scalar (1D) Maya
        attribute, otherwise ``False``
    :rtype: :class:`bool`
    """
    try:
        item = asPlug(item)

    except:
        return False

    return item.__math_dimension__ is 1

def isScalarValueOrPlug(item):
    """
    :param item: the item to inspect
    :return: ``True`` if *item* represents a scalar value or plug,
        otherwise ``False``.
    :rtype: :class:`bool`
    """
    return isScalarValue(item) or isScalarPlug(item)

def isVectorValueOrPlug(item):
    """
    :param item: the item to inspect
    :return: ``True`` if *item* is a vector value or attribute, otherwise
        False
    :rtype: bool
    """
    if isinstance(item, (p.datatypes.Vector, p.datatypes.Point)) \
        or (isinstance(item, r.plugs.Math3D)
            and not isinstance(item, r.plugs.EulerRotation)):
        return True

    if isinstance(item, str):
        try:
            plug = p.Attribute(item)

        except:
            return False

        return (isinstance(plug, r.plugs.Math3D)
            and not isinstance(plug, r.plugs.EulerRotation))

    if hasattr(item, '__iter__'):
        return len(list(item)) is 3 and all(map(isScalarValue, item))

    return False

def isParamVectorPair(item):
    """
    :param item: the item to inspect
    :return: ``True`` if *item* is a pair of *scalar: vector*, otherwise
        ``False``
    """
    if hasattr(item, '__iter__'):
        members = list(item)

        if len(members) is 2:
            return isScalarValueOrPlug(
                members[0]) and isVectorValueOrPlug(members[1])

    return False

def isTripleScalarValueOrPlug(item):
    """
    Three scalar plugs in a list will not return ``True``; they must be
    delivered as a numeric compound instead.

    :param item: the item to inspect
    :return: ``True`` if *item* represents a 3D vector or Euler rotation plug
        or value, otherwise ``False``.
    :rtype: ``bool``
    """
    if isinstance(item, p.datatypes.Array):
        return len(item) is 3

    if isinstance(item, p.Attribute):
        return item.__math_dimension__ is 3

    if isinstance(item, str):
        try:
            return p.Attribute(item).__math_dimension__ is 3

        except:
            return False

    if hasattr(item, '__iter__'):
        members = list(item)
        return len(members) is 3 \
               and all((isScalarValue(member) for member in members))

    return False

@short(listLength='ll')
def conformVectorArg(arg, listLength=None):
    """
    For methods that expect a vector argument which may also be a multi
    (for example *upVector* on
    :meth:`~paya.runtime.plugs.NurbsCurve.distributeMatrices`). Attributes
    are conformed but not checked for type.

    :param arg: strictly a single vector or a list of vectors; deeper nesting
        will throw an error
    :type arg: :class:`tuple` | :class:`list` | :class:`str`,
        :class:`paya.runtime.data.Vector` | :class:`paya.runtime.plugs.Vector`,
        [:class:`tuple` | :class:`list` | :class:`str`,
        :class:`paya.runtime.data.Vector` | :class:`paya.runtime.plugs.Vector`]
    :param listLength/ll: the preferred output length; defaults to ``None``
    :type listLength/ll: ``None`` | :class:`int`
    :return: A conformed vector, or list of conformed vectors.
    :rtype: :class:`paya.runtime.data.Vector` | :class:`paya.runtime.plugs.Vector` |
        [:class:`paya.runtime.data.Vector` | :class:`paya.runtime.plugs.Vector`]
    """
    d = {'numTupleExpansions': 0}

    def conform(item):
        if isinstance(item, p.datatypes.Vector):
            return item

        elif isinstance(item, p.general.Attribute):
            return item

        elif isinstance(item, str):
            return p.Attribute(item) # allow to error

        elif hasattr(item, '__iter__'):
            members = list(item)

            if len(members) is 3:
                if all((isScalarValue(member) for member in members)):
                    return p.datatypes.Vector(members)

                else:
                    d['numTupleExpansions'] += 1
                    return [conform(member) for member in members]
            else:
                d['numTupleExpansions'] += 1
                return [conform(member) for member in members]

        else:
            raise TypeError(
                "Can't parse as vector plug or value: {}".format(item)
            )

    conformed = conform(arg)

    if d['numTupleExpansions'] is 0: # single vector
        if listLength is None:
            return conformed

        else:
            return [conformed] * listLength

    elif d['numTupleExpansions'] is 1: # list of vectors
        if listLength is None:
            return conformed

        else:
            numMembers = len(conformed)

            if numMembers is 1:
                # forgive and multiply a single member list
                return conformed * listLength

            if numMembers is listLength:
                return conformed

            raise ValueError("Wrong number of vectors.")

    else:
        raise ValueError("Nested vectors.")

def describeAndConformVectorArg(vector):
    """
    Used by methods that receive multiple forms of up vector hints in a
    single argument.

    :param vector: the argument to inspect
    :raises RuntimeError: Couldn't parse the argument.
    :return: One of:

            - tuple of ``'single'``, conformed vector value or plug
            - tuple of ``'keys'``, list of conformed *param, vector* pairs
            - tuple of ``'multi'``, list of conformed vectors
    :rtype: One of:

            - (:class:`str`, :class:`paya.runtime.data.Vector` | :class:`paya.runtime.plugs.Vector`)
            - (:class:`str`, [(:class:`int` | :class:`float` | :class:`~paya.runtime.plugs.Math1D`, :class:`paya.runtime.data.Vector` | :class:`paya.runtime.plugs.Vector`))]
            - (:class:`str`, [:class:`paya.runtime.data.Vector` | :class:`paya.runtime.plugs.Vector`])
    """
    if isVectorValueOrPlug(vector):
        return ('single', conformVectorArg(vector))

    if hasattr(vector, '__iter__'):
        vector = list(vector)

        if all(map(isParamVectorPair, vector)):
            outDescr = 'keys'
            params = [mathInfo(pair[0])[0] for pair in vector]
            vectors = [conformVectorArg(pair[1]) for pair in vector]
            outContent = list(zip(params, vectors))

            return outDescr, outContent

        elif all(map(isVectorValueOrPlug, vector)):
            return ('multi', [conformVectorArg(member) for member in vector])

        else:
            raise RuntimeError(
                "Couldn't parse up vector argument: {}".format(vector)
            )

def resolveNumberOrFractionsArg(arg):
    """
    Loosely conforms a ``numberOrFractions`` user argument. If the
    argument is an integer, a range of floats is returned. Otherwise,
    the argument is passed through without further checking.
    """
    if isinstance(arg, int):
        return floatRange(0, 1, arg)

    return [mathInfo(x)[0] for x in arg]

def expandVectorArgs(*args):
    """
    Expands *args*, stopping at anything that looks like a vector value
    or plug.

    :param \*args: the arguments to expand
    :return: The expanded arguments.
    """
    return conditionalExpandArgs(
        *args, gate=lambda x: not isVectorValueOrPlug(x))

def asPlug(item, quiet=False):
    """
    If *item* is already an instance of
    :class:`~pymel.core.general.Attribute`, it is passed through; otherwise,
    it's used to create an instance of :class:`~pymel.core.general.Attribute`.
    The advantage of checking first is that custom class assignments are
    preserved.

    Use this form to check whether an attribute exists:
    ``bool(asPlug(item, quiet=True))``

    :param item: the attribute instance or string
    :type item: :class:`str` | :class:`~pymel.core.general.Attribute`
    :param bool quiet: catch any errors raised when attempting to instantiate
        :class:`~pymel.core.general.Attribute` and return ``None``; defaults
        to ``False``
    :return: The attribute instance.
    :rtype: :class:`~pymel.core.general.Attribute`
    """
    if isinstance(item, p.Attribute):
        return item

    return p.Attribute(item)

@short(worldSpace='ws')
def asGeoPlug(item, worldSpace=None):
    """
    Attempts to extract a geometry output plug from *item*.

    :param item: the item to inspect
    :type item: str, :class:`~paya.runtime.plugs.Geometry`,
        :class:`~paya.runtime.nodes.Shape`,
        :class:`~paya.runtime.nodes.Transform`,
    :param bool worldSpace/ws: ignored if *item* is a plug; specifies
        whether to pull the world-space or local-space output of a
        geometry shape or transform; if omitted, defaults to ``False``
        if *item* is a shape, and ``True`` if it's a transform
    :raises TypeError: Can't extract a geo plug from *item*.
    :return: The geometry output.
    :rtype: :class:`~paya.runtime.plugs.Geometry`
    """
    plug = None
    xform = None
    shape = None

    if isinstance(item, p.PyNode):
        if isinstance(item, p.Attribute):
            plug = item

        elif isinstance(item, p.nodetypes.Shape):
            shape = item

        elif isinstance(item, p.nodetypes.Transform):
            xform = item

        else:
            raise TypeError(
                "Not an attribute, transform or shape: {}".format(item)
            )

    elif isinstance(item, str):
        try:
            plug = p.Attribute(item)

        except:
            plug = None

        if plug is None:
            try:
                node = p.PyNode(item)

            except:
                raise TypeError(
                    "Can't interpret as Attribute or PyNode: {}".format(item)
                )

            if isinstance(node, p.nodetypes.Transform):
                xform = node

            elif isinstance(node, p.nodetypes.Shape):
                shape = node

            else:
                raise TypeError(
                    "Not a transform or shape: {}".format(item)
            )

    else:
        raise TypeError(
            "Not a string, PyNode or Attribute: {}".format(item)
        )

    if plug is not None:
        if isinstance(plug, r.plugs.Geometry):
            return plug

        else:
            typ = plug.type()

            if typ in ['TdataCompound', 'Tdata']:
                return plug

            else:
                raise TypeError(
                    "Not sure this is a geometry plug: {}".format(plug)
                )

    elif shape is not None:
        if worldSpace is None:
            return shape.localGeoOutput

        return shape.worldGeoOutput if worldSpace else shape.localGeoOutput

    if worldSpace is None:
        return xform.worldGeoOutput

    return xform.worldGeoOutput if worldSpace else xform.localGeoOutput

def asValue(item):
    """
    Equivalent to :func:`asPlug(item).get() <asPlug>`.
    """
    return asPlug(item).get()

def asCompIndexOrPlug(item):
    """
    Used by methods which accept component arguments as indices
    (integers or floats) or scalar plugs (for example, NURBS curve parameter
    drivers), but not as instances of :class:`~pymel.core.general.Component`.

    If *item* is a simple scalar type, it's passed-through as-is. Otherwise,
    if it describes a Maya component, its first index is returned as a float
    or integer. Otherwise, an attempt is made to return it as an
    :class:`~pymel.core.general.Attribute` instance. The attribute is not
    checked for type.

    .. note::

        This method relies on the relevant Paya component type implementing
        ``index()``, which may not always be the case.

    :param item: the item to conform
    :raises TypeError: Can't parse specified item.
    :return: A scalar index / parameter value or an attribute.
    :rtype: :class:`int` | :class:`float` |
        :class:`~pymel.core.general.Attribute`
    """
    if isScalarValue(item):
        return item

    if isinstance(item, p.Component):
        return item.index()

    elif isinstance(item, p.Attribute):
        return item

    elif isinstance(item, str):
        try:
            return p.Attribute(item)

        except:
            return p.Component(item).index()

def conformPlugsInArg(arg):
    """
    Used by :class:`plugCheck`. Looks for plugs recursively in an argument
    received by a Paya method; if any are found, they are conformed to
    :class:`~paya.runtime.plugs.Attribute` instances.

    :param arg: an argument received by a Paya method
    :return: tuple of:

        -   the original argument, with conformed plug members,
        -   ``True`` if plugs were found, ``False`` if they weren't

    :rtype: :class:`tuple`
    """

    d = {'found': False}

    def conform(item):
        if isinstance(item, p.Attribute):
            d['found'] = True
            return item

        if isinstance(item, str):
            try:
                out = p.Attribute(item)
                d['found'] = True
                return out

            except:
                return item

        if hasattr(item, '__iter__'
            ) and not isinstance(item, (p.datatypes.Array, p.PyNode)):
            return [conform(member) for member in item]

        return item

    arg = conform(arg)
    return arg, d['found']

def forceVectorsAsPlugs(vectors):
    """
    If any of the provided vectors are plugs, they are passed-through
    as-is; those that aren't are used as values for array attributes
    on a utility node, which are passed along instead.

    :param vectors: the vectors to inspect
    :type vectors: [list, tuple,
        :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.plugs.Vector`]
    :return: The conformed vector outputs.
    :rtype: [:class:`~paya.runtime.plugs.Vector`]
    """

    vectorInfos = [mathInfo(vector) for vector in vectors]
    plugStates = [vectorInfo[2] for vectorInfo in vectorInfos]

    if all(plugStates):
        return [vectorInfo[0] for vectorInfo in vectorInfos]

    nd = r.nodes.Network.createNode(n='vecs_as_plugs')
    array = nd.addVectorAttr('vector', multi=True)

    out = []
    index = 0

    for vectorInfo in vectorInfos:
        if vectorInfo[2]:
            out.append(vectorInfo[0])

        else:
            array[index].set(vectorInfo[0])
            out.append(array[index])
            index += 1

    return out


class plugCheck:
    """
    Decorator-with-arguments for methods that take a *plug* keyword argument
    which defaults to ``None``, meaning its behaviour will depend on whether
    any incoming arguments are plugs.

    Instantiate it with a list of argument names; when the function is called,
    if *plug* still resolves as ``None``, the arguments will be checked for
    plugs, and the *plug* keyword overriden to ``True`` where necessary before
    delegating to the original function. As a bonus, any plug arguments will
    be conformed to :class:`~paya.runtime.plugs.Attribute` instances.

    If the plug is passed specifically by the user as ``True`` or ``False``,
    the function will be called immediately--in essence the user becomes
    responsible for any errors thence.

    :Example:

        .. code-block:: python

            @plugCheck('param')
            def tangentAtParam(self, param, plug=None):
                # At this point, if plug was passed-through as None, the
                # decorator will have resolved it to True / False

                if plug:
                    # Run the 'hard' implementation
                else:
                    # Run the 'soft' implementation
    """

    def __init__(self, *argNames):
        if argNames:
            self._argNames = argNames

        else:
            raise RuntimeError("No argument names were specified.")

    def __call__(self, f):
        sig = inspect.signature(f)

        if 'plug' in sig.parameters:
            plugDefault = sig.parameters['plug'].default

            if plugDefault is None:
                argNames = self._argNames

                @wraps(f)
                def wrapper(*args, **kwargs):
                    plug = kwargs.get('plug')

                    if plug is not None:
                        # User takes responsibility
                        return f(*args, **kwargs)

                    binding = sig.bind(*args, **kwargs)

                    for argName in argNames:
                        try:
                            argVal = binding.arguments[argName]
                            newArgVal, plugsFound = conformPlugsInArg(argVal)

                            if plugsFound:
                                binding.arguments[argName] = newArgVal
                                binding.arguments['plug'] = True

                        except KeyError:
                            continue

                    return f(*binding.args, **binding.kwargs)

                return wrapper

            else:
                raise RuntimeError(
                    "Can't wrap {}(): 'plug' must default to None".format(f.__name__)
                )
        else:
            raise RuntimeError(
                "Can't wrap {}(): no 'plug' argument in signature".format(f.__name__)
            )

