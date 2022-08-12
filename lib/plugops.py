import maya.cmds as m
import pymel.core.datatypes as _dt
import pymel.core as p
from paya.util import LazyModule, short

r = LazyModule('paya.runtime')

def isPyMELObject(item):
    """
    :param item: the item to inspect
    :return: True if *item* is an instance of a PyMEl class, otherwise FAlse
    :rtype: bool
    """
    return isinstance(item, (r.PyNode, _dt.Array, _dt.Unit))

def sameValueInput(plugA, plugB):
    """
    Returns ``True`` if either of the following:

    -   *plugA* and *plugB* have the same input
    -   Neither *plugA* nor *plugB* have an input, but they hav the same
        value

    :param plugA: the first attribute to inspect
    :type plugA: :class:`~paya.runtime.plugs.Attribute`
    :param plugB: the second attribute to inspect
    :type plugB: :class:`~paya.runtime.plugs.Attribute`
    :return: The comparison result.
    :rtype: bool
    """
    if not isinstance(plugA, r.Attribute):
        plugA = r.Attribute(plugA)

    if not isinstance(plugB, r.Attribute):
        plugB = r.Attribute(plugB)

    inputsA = plugA.inputs(plugs=True)
    inputsB = plugB.inputs(plugs=True)

    if inputsA and inputsB:
        return inputsA[0] == inputsB[0]

    elif (not inputsA) and (not inputsB):
        return plugA.get() == plugB.get()

    return False

def getInputOrValue(plug):
    """
    :param plug: the plug to inspect
    :type plug: :class:`~paya.runtime.plugs.Attribute`
    :return: If the plug has an input, its input; otherwise, its value.
    """
    if not isinstance(plug, r.Attribute):
        plug = r.Attribute(plug)

    inputs = plug.inputs(plugs=True)

    if inputs:
        return inputs[0]

    return plug.get()

def isPlug(item):
    """
    :param item: the item to inspect
    :return: ``True`` if *item* represents an attribute, otherwise ``False``.
    :rtype: bool
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
    :rtype: bool
    """
    return isinstance(value, (int, float, bool, p.datatypes.Unit))

@short(angle='a')
def info(item, angle=False):
    """
    :param item: a value or plug (simple or PyMEL type)
    :param bool angle/a: where possible, conform to one of the following:

        - :class:`~paya.runtime.data.Angle`
        - :class:`~paya.runtime.data.EulerRotation`
        - :class:`~paya.runtime.plugs.Angle`
        - :class:`~paya.runtime.plugs.EulerRotation`

        Defaults to False.

    :return: A tuple of: conformed item, item maths dimension (or None),
        item is a plug
    """
    if isinstance(item, (float, int, bool, p.datatypes.Unit)):
        if angle:
            return r.data.Angle(item), 1, False

        return item, 1, False

    if isinstance(item, p.datatypes.Array):
        return item, len(item), False

    if isinstance(item, (tuple, list)):
        dim = len(item)

        try:
            cls = {
                3: r.data.EulerRotation if angle else r.data.Vector,
                4: r.data.Quaternion,
                16: r.data.Matrix
            }[dim]

            if all([isScalarValue(member) for member in item]):
                return cls(item), dim, False

            return list(item), dim, False

        except KeyError:
            return list(item), dim, False

    if isinstance(item, str):
        try:
            plug = p.Attribute(item)
            dim = plug.__math_dimension__

            if angle:
                try:
                    plug.__class__ = {1: r.plugs.Angle,
                        3: r.plugs.EulerRotation}.get(dim)

                except KeyError:
                    pass

            return plug, plug.__math_dimension__, True

        except:
            return item, None, False

    if isinstance(item, p.Attribute):
        return item, item.__math_dimension__, True

    raise TypeError("Can't parse type: {}".format(type(item)))

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

    if isinstance(item, r.PyNode):
        if isinstance(item, r.Attribute):
            plug = item

        elif isinstance(item, r.nodetypes.Shape):
            shape = item

        elif isinstance(item, r.nodetypes.Transform):
            xform = item

        else:
            raise TypeError(
                "Not an attribute, transform or shape: {}".format(item)
            )

    elif isinstance(item, str):
        try:
            plug = r.Attribute(item)

        except:
            plug = None

        if plug is None:
            try:
                node = r.PyNode(item)

            except:
                raise TypeError(
                    "Can't interpret as Attribute or PyNode: {}".format(item)
                )

            if isinstance(node, r.nodetypes.Transform):
                xform = node

            elif isinstance(node, r.nodetypes.Shape):
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
    :param item: the item to inspect
    :return: If *item* represents a plug, its value; otherwise, the conformed
        *item*.
    """
    item, dim, isplug = info(item)

    if isplug:
        return item.get()

    return item