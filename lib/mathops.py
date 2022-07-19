"""
Defines supporting methods for maths rigging and, more broadly, mixed value /
plug workflows.
"""

from collections import UserDict
from functools import wraps, reduce

import maya.OpenMaya as om
import maya.cmds as m
import pymel.core as p
from pymel.util.arrays import Array
import pymel.util as _pu

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

def asGeoPlug(item):
    """
    Attempts to conform *item* into a geometry output

    :param item: the item to inspect
    :type item: str, :class:`~paya.runtime.nodes.Transform`,
        :class:`~paya.runtime.nodes.Shape`,
        :class:`~paya.runtime.plugs.Geometry`,
    :raises TypeError: Could not derive a geometry output.
    :return: The geometry output.
    :rtype: :class:`~paya.runtime.plugs.Geometry`
    """
    if isinstance(item, str):
        try:
            return p.Attribute(item)

        except p.MayaNodeError:
            return p.PyNode(item).worldGeoOutput

    elif isinstance(item, p.Attribute):
        return item

    elif isinstance(item, (p.nodetypes.Transform, p.nodetypes.Shape)):
        return item.worldGeoOutput

    else:
        raise TypeError("Can't derive a geo output from {}.".format(item))

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

        - If its dimension is 3, it's returned as a :class:`~paya.runtime.data.Vector`
        - If its dimension is 4, it's returned as a :class:`~paya.runtime.data.Quaternion`
        - If its dimension is 16, it's returned as a :class:`~paya.runtime.data.Matrix`
        - In all other cases, it's returned as-is

    If x is a **plug**, then it's returned as an instance of the appropriate
    :class:`~paya.runtime.plugs.Attribute`

    :param x: the item to conform
    :return: The conformed item.
    :rtype: :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.data.Quaternion`, :class:`~paya.runtime.data.Matrix`
        or :class:`~paya.runtime.plugs.Attribute`
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
    :type \*matrices: :class:`~paya.runtime.data.Matrix`, :class:`~paya.runtime.plugs.Matrix`, list or str
    :return: The matrix product.
    :rtype: :class:`paya.runtime.data.Matrix` or :class:`paya.runtime.plugs.Matrix`
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

def createScaleMatrix(*args):
    """
    Quick method to create static or dynamic scale matrices. Takes one, three
    or six arguments.

    :shorthand: ``csm``
    :param \*args:
        If one argument is passed, the same scaling factor will be applied to
        the XYZ base vectors.

        If three arguments are passed, they will each be applied to the XYZ
        base vectors.

        If six arguments are passed then they will be interpreted as
        *axis: scalar* pairs.

    :return: The scale matrix.
    :rtype: :class:`paya.runtime.data.Matrix` or
        :class:`paya.runtime.plugs.Matrix`.
    """
    ln = len(args)

    if ln is 1:
        axes = ['x', 'y', 'z']
        scalars = [args[0]] * 3

    elif ln is 3:
        axes = ['x', 'y', 'z']
        scalars = args

    elif ln is 6:
        axes = list(map(lambda x: x.strip('-'), args[::2]))
        scalars = args[1::2]

    else:
        raise RuntimeError("Number of arguments must be 1, 3 or 6.")

    return r.createMatrix(
        axes[0], axisVecs[axes[0]] * scalars[0],
        axes[1], axisVecs[axes[1]] * scalars[1],
        axes[2], axisVecs[axes[2]] * scalars[2]
    )

csm = createScaleMatrix

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
        :class:`~paya.runtime.data.Vector`, :class:`~paya.runtime.data.Point`,
        :class:`~paya.runtime.plugs.Math3D`
    :param bool preserveSecondLength/psl: ignored if six arguments were passed;
        preserve the second vector's length when performing orthogonal
        construction; defaults to True
    :param thirdLength/tl: ignored is six arguments were passed; if provided,
        defines the third (derived) vector's length; defaults to None
    :type thirdLength/tl: None, :class:`float`, :class:`int`,
        :class:`~paya.runtime.plugs.Math1D`, :class:`str`
    :param bool plug/p: if you already know whether the passed arguments contain
        plugs, specify it here to avoid extraneous checks; if no arguments
        have been passed, this will specify whether the returned identity
        matrix is a plug or value; defaults to None
    :return: The constructed matrix.
    :rtype: :class:`paya.runtime.plugs.Matrix` or
        :class:`paya.runtime.data.Matrix`, depending on inputs.
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

                absAxis3 = [ax for ax in 'xyz' if ax not in (absAxis1, absAxis2)][0]

                return createMatrix(
                    absAxis1, vec1, absAxis2, vec2, absAxis3, vec3,
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

class NoInterpolationKeysError(RuntimeError):
    """
    A blending or interpolation operation has no keys to work with.
    """

class LinearInterpolator(UserDict):
    """
    Simple, dict-like interpolator implementation, similar to a linear
    animation curve in Maya. Works with any value type that can be handled by
    :func:`pymel.util.arrays.blend`, but types should not be mixed.

    :Example:

        .. code-block:: python

            interp = LinearInterpolator()
            interp[10] = 30
            interp[20] = 40
            print(interp[11])
            # Result: 31.0
    """
    def __setitem__(self, ratio, value):
        ratio = float(ratio)
        super(LinearInterpolator, self).__setitem__(ratio, value)

    def __getitem__(self, sampleRatio):
        sampleRatio = float(sampleRatio)

        try:
            return self.data[sampleRatio]

        except KeyError:
            ratios = list(sorted(self.keys()))

            ln = len(ratios)

            if ln:
                values = [self[ratio] for ratio in ratios]

                if ln is 1:
                    return values[0]

                if ln >= 2:
                    if sampleRatio <= ratios[0]:
                        return values[0]

                    if sampleRatio >= ratios[-1]:
                        return values[-1]

                    startEndRatios = zip(ratios, ratios[1:])
                    startEndValues = zip(values, values[1:])

                    for startEndRatio, startEndValue in zip(
                            startEndRatios, startEndValues):
                        startRatio, endRatio = startEndRatio

                        if sampleRatio >= startRatio and \
                                sampleRatio <= endRatio:
                            ratioRatio = (sampleRatio-startRatio
                                          ) / (endRatio-startRatio)
                            startValue, endValue = startEndValue

                            return _pu.blend(startValue,
                                             endValue, weight=ratioRatio)

                    raise RuntimeError("Could not bracket a sample value.")

        raise NoInterpolationKeysError

def floatRange(start, end, numValues):
    """
    A variant of Python's :class:`range` for floats.

    :param float start: the minimum value
    :param float end: the maximum value
    :param int numValues: the number of values to generate
    :return: A list of float values between ``start`` and ``end``,
        inclusively.
    :rtype: list
    """
    grain = (float(end)-float(start)) / (numValues-1)
    return [grain * x for x in range(numValues)]

def chaseNones(source):
    """
    Resolves ``None`` members in an iterable by filling in with neighbouring
    values. If the first member is ``None``, the next defined value is used.
    If any internal member is ``None``, the last resolved value is used.

    :param source: the iterable to fill-in
    :return: A list with no ``None`` members.
    :rtype: list
    """
    source = list(source)
    ln = len(source)

    if ln:
        nn = source.count(None)

        if nn is ln:
            raise NoInterpolationKeysError

        resolved = []

        for i, member in enumerate(source):
            if member is None:
                if i is 0:
                    for nextMember in source[1:]:
                        if nextMember is not None:
                            resolved.append(nextMember)
                            break

                else:
                    resolved.append(resolved[-1])

            else:
                resolved.append(member)

        return resolved

    return []

def blendNones(source, ratios=None):
    """
    A blending version of :func:`chaseNones`.

    :param source: the iterable to fill-in
    :param ratios: if provided, it should be a list of ratios from 0.0 to
        1.0 (one per member) to bias the blending; if omitted, it will be
        autogenerated using :func:`floatRange`; defaults to None
    :return: A list with no ``None`` members.
    :rtype: list
    """
    source = list(source)
    ln = len(source)

    if ln:
        nn = source.count(None)

        if nn is ln:
            raise NoInterpolationKeysError

        if ratios:
            ratios = list(ratios)

            if len(ratios) is not ln:
                raise RuntimeError(
                    "If provided, 'ratios' should be of "+
                    "the same length as 'source'."
                )

        else:
            ratios = floatRange(0, 1, ln)

        interpolator = LinearInterpolator()

        for ratio, member in zip(ratios, source):
            if member is not None:
                interpolator[ratio] = member

        resolved = []

        for ratio, member in zip(ratios, source):
            if member is None:
                resolved.append(interpolator[ratio])

            else:
                resolved.append(member)

        return resolved

    return []

@short(tolerance='tol')
def getAimVectorsFromPoints(points, tolerance=1e-7):
    """
    Derives aim vectors from points. Needs at least two points. The length of
    the returned list will always be one less than the length of the points.

    :param points: the source points (values)
    :param float tolerance/tol: any vectors below this length will be
        replaced by neighbouring vectors; defaults to 1e-7
    :raises NoInterpolationKeysError: none of the derived vectors were
        longer than the specified tolerance
    :return: The list of aim vectors.
    :rtype: :class:`list` of :class:`~paya.runtime.data.Vector`
    """
    points = list(map(p.datatypes.Point, points))

    if len(points) > 1:
        vectors = []

        for i, point in enumerate(points[1:], start=1):
            prev = points[i-1]
            vector = point-prev
            ln = vector.length()

            if vector.length() < tolerance:
                vector = None

            vectors.append(vector)

        return chaseNones(vectors)

def deflipVectors(vectors):
    """
    Returns a list where each vector is flipped if that would bring it closer
    to the previous one.

    :param vectors: the source vectors (values)
    :return: The deflipped vectors.
    :rtype: :class:`list` of :class:`~paya.runtime.data.Vector`
    """
    vectors = [p.datatypes.Vector(v).normal() for v in vectors]
    ln = len(vectors)

    if ln > 1:

        out = [vectors[0]]

        for i, vector in enumerate(vectors[1:], start=1):
            prev = vectors[i-1]

            neg = vector *-1
            dot = prev.dot(vector)
            negDot = prev.dot(neg)

            if negDot > dot:
                vector = neg

            out.append(vector)

        return out

    return vectors

@short(tolerance='tol')
def getAimAndUpVectorsFromPoints(points, refVector, tolerance=1e-7):
    """
    Given a list of points and a reference up vector, returns aim vectors and
    up vectors that can be used in matrix construction, for example to draw
    chains.

    :param points: the source points (values)
    :param refVector: a reference up vector
    :type refVector: :class:`~paya.runtime.data.Vector`, list
    :param float tolerance/tol: aim vectors or cross products with lengths
        below this tolerance will be replaced with neighbouring ones;
        defaults to 1e-7
    :return: A list of aim vectors and a list of up vectors
    :rtype: tuple
    """
    points = list(map(p.datatypes.Point, points))
    ln = len(points)

    if ln > 1:
        refVector = p.datatypes.Vector(refVector).normal()

        if ln is 2:
            aimVecs = [points[1]-points[0]] * 2
            upVecs = [refVector] * 2

            return aimVecs, upVecs

        else:
            aimVecs = getAimVectorsFromPoints(points, tol=tolerance)

            # Get interpolation info to use later in up vector calcs

            lengthRatios = [0.0]
            aimVecLengths = [aimVec.length() for aimVec in aimVecs]
            fullLength = sum(aimVecLengths)
            cumulLength = 0.0

            for aimVec, aimVecLength in zip(aimVecs, aimVecLengths):
                cumulLength += aimVecLength
                lengthRatios.append(cumulLength / fullLength)

            # Get up vectors

            upVecs = []

            for i, aimVec in enumerate(aimVecs[1:], start=1):
                prev = aimVecs[i-1]
                upVec = prev.normal().cross(aimVec.normal())

                if upVec.length() < tolerance:
                    upVec = None

                else:
                    upVec = upVec.normal()

                upVecs.append(upVec)

            if upVecs.count(None) == len(upVecs):
                upVecs = [refVector] * (len(aimVecs)-1)

            else:
                # First, bias towards the reference vector, dodging Nones

                _upVecs = []

                for upVec in upVecs:
                    if upVec is None:
                        _upVecs.append(upVec)

                    else:
                        neg = upVec * -1

                        if refVector.dot(neg) > refVector.dot(upVec):
                            upVec = neg

                    _upVecs.append(upVec)

                upVecs = _upVecs

                upVecs = blendNones(upVecs, lengthRatios[1:-1])
                upVecs = deflipVectors(upVecs)

            # Pad

            upVecs = [upVecs[0]] + upVecs + [upVecs[-1]]
            aimVecs.append(aimVecs[-1])

            return aimVecs, upVecs

    raise RuntimeError("Need at least two points.")

@short(tolerance='tol')
def getAimingMatricesFromPoints(
        points,
        downAxis,
        upAxis,
        refVector,
        tolerance=1e-7
):
    """
    Given a list of points and a reference up vector, returns aiming matrices
    which can be used to draw chains and other systems.

    :param points: the source points (values)
    :param str downAxis: the aiming axis
    :param str upAxis: the axis to bias towards the reference vector
    :param refVector: a reference up vector
    :type refVector: :class:`~paya.runtime.data.Vector`, list
    :param float tolerance/tol: aim vectors or cross products with lengths
        below this tolerance will be replaced with neighbouring ones;
        defaults to 1e-7
    :return: A list of matrices
    :rtype: :class:`list` of :class:`~paya.runtime.data.Matrix`
    """
    aimVectors, upVectors = getAimAndUpVectorsFromPoints(
        points, refVector, tol=tolerance
    )

    out = []

    for point, aimVector, upVector in zip(points, aimVectors, upVectors):
        matrix = createMatrix(downAxis, aimVector, upAxis, upVector, t=point
                              ).pk(t=True, r=True)

        out.append(matrix)

    return out

def pointsIntoUnitCube(points):
    """
    Normalizes points so that they fit inside a unit cube.

    :param points: the points to normalize
    :type points: list
    :return: The normalized points.
    :rtype: list of :class:`~paya.runtime.data.Point`
    """
    xVals = list(map(abs,[point[0] for point in points]))
    yVals = list(map(abs, [point[1] for point in points]))
    zVals = list(map(abs, [point[2] for point in points]))

    maxX = max(xVals)
    maxY = max(yVals)
    maxZ = max(zVals)

    maxFactor = max(maxX, maxY, maxZ)

    try:
        scaleFactor = 0.5 / maxFactor

    except ZeroDivisionError:
        scaleFactor = 1.0

    scaleMatrix = r.createMatrix()
    scaleMatrix.x *= scaleFactor
    scaleMatrix.y *= scaleFactor
    scaleMatrix.z *= scaleFactor

    return [r.data.Point(point) ^ scaleMatrix for point in points]

def expandVectorArgs(*args):
    """
    Similar to :func:`~pymel.util.arguments.expandArgs`, except it won't
    expand lists or tuples of three scalars.

    :param *args: the arguments to expand
    :return: A flattened list.
    :rtype: list
    """
    buffer = []

    def expand(elem):
        if isinstance(elem, (tuple, list)):
            elem = list(elem)

            if len(elem) is 3 and all([isScalarValue(x) for x in elem]):
                buffer.append(elem)

            else:
                for x in elem:
                    expand(x)
        else:
            buffer.append(elem)

    expand(args)

    return buffer