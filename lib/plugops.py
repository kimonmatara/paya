import maya.cmds as m
import pymel.core as p
from paya.util import LazyModule, short

r = LazyModule('paya.runtime')

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
def asGeoPlug(item, worldSpace=False):
    """
    :param item: a geometry node or plug
    :type item: str, :class:`~paya.runtime.nodes.DagNode`,
        :class:`~paya.runtime.plugs.DagNode`
    :param bool worldSpace/ws: if *item* is a node, pull its world-
        space geometry output; defaults to ``False``
    :raises RuntimeError: Could not derive a geometry output.
    :return: A geometry output.
    """
    if isinstance(item, p.Attribute):
        if isinstance(item, r.data.Geometry):
            return item

        raise RuntimeError(
            "Couldn't extract a geometry plug from: {}".format(item)
        )

    if isinstance(item, str):
        try:
            plug = p.Attribute(item)
            return asGeoPlug(plug)

        except:
            try:
                node = p.PyNode(item)

                if worldSpace:
                    return node.worldGeoOutput

                return node.localGeoOutput

            except:
                pass

    raise RuntimeError(
        "Couldn't extract a geometry plug from: {}".format(item)
    )

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