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

axisVecs = {
    'x': p.datatypes.Vector([1,0,0]),
    'y': p.datatypes.Vector([0,1,0]),
    'z': p.datatypes.Vector([0,0,1]),
    '-x': p.datatypes.Vector([-1,0,0]),
    '-y': p.datatypes.Vector([0,-1,0]),
    '-z': p.datatypes.Vector([0,0,-1]),
    't': p.datatypes.Point([0,0,0]),
    'translate': p.datatypes.Point([0,0,0])
}

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


class NonPlugStringError(RuntimeError):
    """
    A string passed to :func:`info` does not represent a Maya attribute.
    """


def info(item, angle=False):
    """
    Returns a tuple of three members:
    -   The item conformed to the highest-level type available
    -   The item's mathematical dimension (e.g. 16 for matrices)
    -   ``True`` if the item is a plug, otherwise ``False``

    In short: item, dimension, isplug.

    :param item: the item to process
    :type item: any type
    :raises NonPlugStringError: ``item`` is a string that could not be
        instantiated as a plug.
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
                raise NonPlugStringError(
                    "'{}' does not represent an attribute.".format(item)
                )

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
                        3: p.datatype.EulerRotation \
                            if angle else p.datatypes.Vector,
                        4: p.datatypes.Quaternion,
                        16: p.datatypes.Matrix
                    }[mathdim]

                    item = customcls(item)

                except KeyError:
                    pass

            else:
                mathdim = None

    return item, mathdim, isplug

@short(plug='p')
def asValue(x, plug=None):
    """
    If x is a plug, returns its value. Otherwise, returns x.

    :param x: the item to inspect
    :param plug/p: if you already know whether x is a plug, specify it
        here.
    :return: The value
    """
    if plug:
        return p.Attribute(x).get()

    x, xdim, xisplug = info(x)

    if xisplug:
        return x.get()

    return x

def conform(x):
    """
    If x is a **value**, then:

        - If its dimension is 3, it's returned as a :class:`~paya.datatypes.vector.Vector`
        - If its dimension is 4, it's returned as a :class:`~paya.datatypes.Quaternion`
        - If its dimension is 16, it's returned as a :class:`~paya.datatypes.Matrix`
        - In all other cases, it's returned as-is

    If x is a **plug**, then it's returned as an instance of the appropriate
    :class:`~paya.plugtypes.Attribute`

    :param x: the item to conform
    :return: The conformed item.
    :rtype: :class:`~paya.datatypes.vector.Vector`,
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
    :type \*matrices: :class:`~paya.datatypes.matrix.Matrix`, :class:`~paya.attributeMatrix.Matrix`, list or str
    :return: The matrix product.
    :rtype: :class:`~paya.datatypes.matrix.Matrix` or :class:`~paya.attributeMatrix.Matrix`
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


@short(
    preserveSecondLength='psl',
    thirdLength='tl',
    translate='t',
    plug='p'
)
def createMatrix(
        *rowHints,
        preserveSecondLength=False,
        thirdLength=None,
        translate=None,
        plug=None
):
    """
    Constructs static or dynamic transformation matrices.

    :shorthand: ``cm``

    :param \*rowHints: If provided, this must comprise exactly **four** or
        **five** arguments, in both cases passed as unpacked pairs of
        row identifier: vector input or value.

        If **four** arguments are passed, they will be used to construct an
        orthogonal matrix, with the first vector as the 'aim' and the second
        as the 'up', for example:

        .. code-block:: python

            matrix = r.createMatrix('y', loc1.t, 'x', loc2.t)

        If **six** arguments are passed, they will be used to directly
        populate the matrix rows. This may result in a non-orthornormal
        (shear) matrix.

        .. code-block:: python

            matrix = r.createMatrix('y', loc1.t, 'x', loc2.t, 'z', loc3.t)

        If this argument is omitted, an identity matrix will be returned.

    :param translate/t: A **translate** component for the matrix; this can be
        a point value or plug; defaults to None
    :type translate/t: :class:`str`, :class:`list`, :class:`tuple`,
        :class:`~paya.datatypes.Vector`, :class:`~paya.datatypes.Point`,
        :class:`~paya.plugtypes.math3D.Math3D`
    :param bool preserveSecondLength/psl: ignored if six arguments were passed;
        preserve the second vector's length when performing orthogonal
        construction; defaults to True
    :param thirdLength/tl: ignored is six arguments were passed; if provided,
        defines the third (derived) vector's length; defaults to None
    :type thirdLength/tl: None, :class:`float`, :class:`int`,
        :class:`~paya.plugtypes.math1D.Math1D`, :class:`str`
    :param bool plug/p: if you already know whether the passed arguments contain
        plugs, specify it here to avoid extraneous checks; if no arguments
        have been passed, this will specify whether the returned identity
        matrix is a plug or value; defaults to None
    :return: The constructed matrix.
    :rtype: :class:`paya.plugtypes.matrix.Matrix` or
        :class:`paya.datatypes.matrix.Matrix`, depending on inputs.
    """
    #-------------------------------------------------------------|    Gather info

    if translate is not None:
        translate, translateDim, translateIsPlug = info(translate)

        if plug is None and translateIsPlug:
            plug = True

    if thirdLength is None:
        thirdLengthIsDefined = False

    else:
        thirdLengthIsDefined = True
        thirdLength, thirdLengthDim, thirdLengthIsPlug = info(thirdLength)

        if plug is None and thirdLengthIsPlug:
            plug = True

    if rowHints:
        ln = len(rowHints)

        if ln not in (4, 6):
            raise RuntimeError(
                "If provided, 'rowHints' must comprise exactly four or "+
                "six arguments."
            )

        axes = rowHints[::2]
        vectorInfos = list(map(info, rowHints[1::2]))
        vectors = [vectorInfo[0] for vectorInfo in vectorInfos]

        ortho = ln is 4

        if plug is None and any([vectorInfo[2] for vectorInfo in vectorInfos]):
            plug = True

    if plug is None:
        plug = False

    #-------------------------------------------------------------|    Dispatch

    if rowHints:
        if plug:
            if ortho:
                # Configure an aimMatrix node; this *must* be initialised with
                # a value-only, normalized version of the intended matrix to
                # avoid artefacts

                node = r.nodes.AimMatrix.createNode()

                _vec1 = asValue(vectors[0], p=vectorInfos[0][2])
                _vec2 = asValue(vectors[1], p=vectorInfos[1][2])

                axis1, axis2 = axes

                initMtx = createMatrix(
                    axis1, _vec1, axis2, _vec2,
                    p=False
                ).pick(r=True)

                node.attr('inputMatrix').set(initMtx)

                # Configure

                node.attr('primaryInputAxis').set(axisVecs[axis1])
                node.attr('primaryMode').set(2)

                node.attr('primaryTargetVector'
                         ).put(vectorInfos[0][0], p=vectorInfos[0][2])

                node.attr('secondaryInputAxis').set(axisVecs[axis2])
                node.attr('secondaryMode').set(2)

                node.attr('secondaryTargetVector'
                         ).put(vectorInfos[1][0], p=vectorInfos[1][2])

                matrix = node.attr('outputMatrix')

                # Add scaling information

                absAxis1 = axes[0].strip('-')
                absAxis2 = axes[1].strip('-')
                absAxis3 = [ax for ax in 'xyz' if ax not in (absAxis1, absAxis2)][0]

                sVec1 = axisVecs[absAxis1] * vectors[0].length()

                sVec2 = axisVecs[absAxis2]

                if preserveSecondLength:
                    sVec2 *= vectors[1].length()

                else:
                    sVec2 *= matrix.getAxis(absAxis2).length()

                sVec3 = axisVecs[absAxis3]

                if thirdLengthIsDefined:
                    sVec3 *= thirdLength

                else:
                    sVec3 *= matrix.getAxis(absAxis3).length()

                scaleMtx = createMatrix(
                    absAxis1, sVec1, absAxis2, sVec2, absAxis3, sVec3
                )

                matrix = scaleMtx * matrix.pk(r=True)

                # Add translate information

                if translate is not None:
                    matrix = matrix * translate.asTranslateMatrix()

                return matrix

            else:
                matrix = r.nodes.FourByFourMatrix.createNode().attr('output')

                if thirdLengthIsDefined:
                    vectors[2] = vectors[2].normal() * thirdLength

                for axis, vector in zip(axes, vectors):
                    absAxis = axis.strip('-')

                    if '-' in axis:
                        vector *= -1.0

                    vector >> getattr(matrix, absAxis)

                if translate:
                    translate >> matrix.t

                return matrix

        else:
            if ortho:
                vec1, vec2 = vectors
                axis1, axis2 = axes

                absAxis1 = axis1.strip('-')

                if '-' in axis1:
                    vec1 *= -1.0

                absAxis2 = axis2.strip('-')

                if '-' in axis2:
                    vec2 *= -1.0

                consec = '{}{}'.format(absAxis1, absAxis2) in 'xyzxy'

                if consec:
                    vec3 = vec1.cross(vec2)
                    _vec2 = vec3.cross(vec1)

                else:
                    vec3 = vec2.cross(vec1)
                    _vec2 = vec1.cross(vec3)

                if preserveSecondLength:
                    vec2 = _vec2.normal() * vec2.length()

                else:
                    vec2 = _vec2

                if thirdLengthIsDefined:
                    vec3 = vec3.normal() * thirdLength

                axis3 = [ax for ax in 'xyz' if ax not in (absAxis1, absAxis2)][0]

                return createMatrix(
                    axis1, vec1, axis2, vec2, axis3, vec3,
                    t=translate, p=False
                )

            else:
                matrix = r.datatypes.Matrix()

                if thirdLengthIsDefined:
                    vectors[2] = vectors[2].normal() * thirdLength

                for axis, vector in zip(axes, vectors):
                    absAxis = axis.strip('-')

                    if '-' in axis:
                        vector *= -1.0

                    setattr(matrix, absAxis, vector)

                if translate:
                    matrix.t = translate

                return matrix

    else:
        if plug:
            matrix = r.nodes.FourByFourMatrix.createNode().attr('output')

            if thirdLengthIsDefined:
                (axisVecs['z'] * thirdLength) >> matrix.z

            if translate is not None:
                translate >> matrix.t

            return matrix

        else:
            matrix = r.data.Matrix()

            if thirdLengthIsDefined:
                matrix.z = axisVecs['z'] * thirdLength

            if translate is not None:
                matrix.t = translate

            return matrix

cm = createMatrix