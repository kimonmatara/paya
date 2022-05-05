"""
Defines supporting methods for maths rigging and, more broadly, mixed value /
plug workflows.
"""

from functools import wraps, reduce

import maya.cmds as m
import pymel.core as p
from pymel.util.arrays import Array
from paya.util import short, LazyModule

r = LazyModule('paya.runtime')

isScalarValue = lambda x: isinstance(x, (int, float, bool))

def getBaseVector(axis):
    """
    Given an axis letter (or 't' for 'translate'), returns an appropriate
    :class:`~paya.datatypes.Vector` or :class:`~paya.datatypes.Point` instance.

    :param str axis: the axis for which to retrieve a
        :class:`~paya.datatypes.Vector` or :class:`~paya.datatypes.Point`;
        must be one of: 'x', 'y', 'z', '-x', '-y', '-z' or 't'
        (for 'translate')
    :return: The vector or point.
    :rtype: :class:`~paya.datatypes.Vector` or :class:`~paya.datatypes.Point`
    """
    return {
        'x': p.datatypes.Vector([1,0,0]),
        'y': p.datatypes.Vector([0,1,0]),
        'z': p.datatypes.Vector([0,0,1]),
        '-x': p.datatypes.Vector([-1,0,0]),
        '-y': p.datatypes.Vector([0,-1,0]),
        '-z': p.datatypes.Vector([0,0,-1]),
        't': p.datatypes.Vector([0,0,0])
    }[axis]

def isTupleOrListOfScalarValues(x):
    """
    :param x: the item to inspect
    :return: True if x is a tuple or list of scalar values, otherwise False.
    :rtype: bool
    """
    return isinstance(x, (tuple, list)) and \
           all([isScalarValue(member) for member in x])

class NativeUnits(object):
    """
    Context manager. Switches Maya to centimetres and radians.
    """
    def __enter__(self):
        self._prevlinear = m.currentUnit(q=True, linear=True)
        self._prevangle = m.currentUnit(q=True, angle=True)

        m.currentUnit(linear='cm')
        m.currentUnit(angle='rad')

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        m.currentUnit(linear=self._prevlinear)
        m.currentUnit(angle=self._prevangle)

        return False

def nativeUnits(f):
    """
    Decorator version of :class:`NativeUnits`.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        with NativeUnits():
            result = f(*args, **kwargs)

        return result

    return wrapper

def info(item):
    """
    Returns a tuple of three members:
    -   The item conformed to the highest-level type available
    -   The item's mathematical dimension (e.g. 16 for matrices)
    -   ``True`` if the item is a plug, otherwise ``False``

    In short: item, dimension, isplug.

    :param item: the item to process
    :type item: any type
    :return: :class:`tuple`
    """
    if isinstance(item, p.Attribute):
        isplug = True

    else:
        if isinstance(item, str):
            try:
                item = p.Attribute(item)
                isplug = True

            except:
                isplug = False

        else:
            isplug = False

    if isplug:
        mathdim = item.__math_dimension__

    else:
        if isinstance(item, Array):
            mathdim = len(item.flat)

        else:
            if isScalarValue(item):
                mathdim = 1

            elif isTupleOrListOfScalarValues(item):
                mathdim = len(item)

                try:
                    customcls = {
                        3: p.datatypes.Vector,
                        4: p.datatypes.Quaternion,
                        16: p.datatypes.Matrix
                    }[mathdim]

                    item = customcls(item)

                except KeyError:
                    pass

            else:
                mathdim = None

    return item, mathdim, isplug

def conform(x):
    """
    If x is a **value**, then:

        - If its dimension is 3, it's returned as a :class:`~paya.datatypes.Vector`
        - If its dimension is 4, it's returned as a :class:`~paya.datatypes.Quaternion`
        - If its dimension is 16, it's returned as a :class:`~paya.datatypes.Matrix`
        - In all other cases, it's returned as-is

    If x is a **plug**, then it's returned as an instance of the appropriate
    :class:`~paya.plugtypes.Attribute`

    :param x: the item to conform
    :return: The conformed item.
    :rtype: :class:`~paya.datatypes.Vector`,
        :class:`~paya.datatypes.Quaternion`, :class:`~paya.datatypes.Matrix`
        or :class:`~paya.plugtypes.Attribute`
    """
    return info(x)[0]

def multMatrices(*matrices):
    """
    Performs efficient multiplication of any combination of matrix values or
    plugs. Consecutive values are reduced and consecutive plugs are grouped
    into ``multMatrix`` nodes.

    If any of the matrices are plugs, the return will also be a plug.
    Otherwise, it will be a value.

    :param \*matrices: the matrices to multiply (unpacked)
    :type \*matrices: :class:`Matrix`, :class:`AttributeMath16D`, list or str
    :return: The matrix product.
    :rtype: :class:`Matrix` or :class:`AttributeMath16D`
    """
    outElems = []
    plugStates = []

    for matrix in matrices:
        matrix, dim, isplug = info(matrix)

        if not isplug:
            if outElems:
                if not plugStates[-1]:
                    outElems[-1] *= matrix
                    continue

        outElems.append(matrix)
        plugStates.append(isplug)

    if len(outElems) is 1:
        return outElems[0]

    node = r.nodes.MultMatrix.createNode()

    for i, elem, plugState in zip(
        range(len(outElems)),
        outElems,
        plugStates
    ):
        node.attr('matrixIn')[i].put(elem, p=plugState)

    return node.attr('matrixSum')

mm = multMatrices