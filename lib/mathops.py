from collections import UserDict
from paya.lib.plugops import *
from paya.util import conditionalExpandArgs

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Constants
#--------------------------------------------------------------|

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

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Exceptions
#--------------------------------------------------------------|

class NoInterpolationKeysError(RuntimeError):
    """
    A blending or interpolation operation has no keys to work with.
    """

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Supplemental type analysis
#--------------------------------------------------------------|

def isVectorValueOrPlug(item):
    """
    :param item: the item to inspect
    :return: ``True`` if *item* is a vector value or attribute, otherwise
        False
    :rtype: bool
    """
    if isinstance(item, p.datatypes.Vector):
        return True

    if isinstance(item, (tuple, list)):
        return len(item) is 3 and all(
            [isScalarValue(member) for member in item])

    cls = type(item)

    return issubclass(cls, r.plugs.Math3D
        ) and not issubclass(cls, r.plugs.EulerRotation)

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Unit conversion
#--------------------------------------------------------------|

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

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Soft interpolation utilities
#--------------------------------------------------------------|

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

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Arg wrangling
#--------------------------------------------------------------|

def resolveNumberOrFractionsArg(arg):
    """
    Loosely conforms a ``numberOrFractions`` user argument. If the
    argument is an integer, a range of floats is returned. Otherwise,
    the argument is passed through without further checking.
    """
    if isinstance(arg, int):
        return floatRange(0, 1, arg)

    return [info(x)[0] for x in arg]

def expandVectorArgs(*args):
    """
    Expands *args*, stopping at anything that looks like a vector value
    or plug.

    :param \*args: the arguments to expand
    :return: The expanded arguments.
    """
    return conditionalExpandArgs(
        *args, gate=lambda x: not isVectorValueOrPlug(x))

@short(listLength='ll')
def conformVectorArg(arg, listLength=None):
    """
    Conforms *arg* into a single vector value or plug, or to a list of vectors
    of the required length (to assign, say, a reference vector to every point
    in a chaining operation).

    This is loosely checked. Edge cases, like the user passing non-vector
    values, aren't caught.

    :param arg: the user vector argument to wrangle
    :type arg: tuple, list, str, :class:`~paya.runtime.plugs.Vector`,
        :class:`~paya.runtime.data.Vector`
    :param listLength/ll: if this is specified, then the argument will be
        conformed, by iterable multiplication, to a list of this length;
        if it's omitted, a single vector will be returned; defaults to None
    :return: The conformed vector argument.
    :rtype: list, :class:`~paya.runtime.plugs.Vector`,
        :class:`~paya.runtime.data.Vector`
    """
    arg = conditionalExpandArgs(
        arg, gate=lambda x: not isVectorValueOrPlug(x))

    arg = [info(x)[0] for x in arg]

    if listLength is None:
        return arg[0]

    ln = len(arg)

    if ln is listLength:
        return arg

    if ln is 1:
        return arg * listLength

    raise ValueError(
        "The resolved vector list can't be "+
        "multiplied to the required length "+
        "of {}.".format(listLength)
    )

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Matrix construction
#--------------------------------------------------------------|

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

                _vec1 = asValue(vectors[0])
                _vec2 = asValue(vectors[1])

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
                if thirdLength is None:
                    thirdLength = 1.0 # for parity with aimMatrix

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

                vec3 = vec3.normal() * thirdLength

                absAxis3 = [ax for ax in 'xyz' if \
                    ax not in (absAxis1, absAxis2)][0]

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

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Framing
#--------------------------------------------------------------|

def deflipVectors(vectors):
    """
    Returns a list where each vector is flipped if that would bring it closer
    to the preceding one. This is a value-only method.

    :param vectors: the source vectors (values)
    :type vectors: [tuple, list, :class:`~paya.runtime.data.Vector`]
    :return: The deflipped vectors.
    :rtype: [:class:`~paya.runtime.data.Vector`]
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

def getAimVectors(points):
    """
    :param points: the points
    :type points: [list, tuple, :class:`~paya.runtime.data.Point`,
        :class:`~paya.runtime.plugs.Vector`]
    :raises ValueError: Fewer than two points were provided.
    :return: Aiming vectors derived from the input points. The output list
        will always be one member shorter than the input list.
    """
    if len(points) > 1:
        points = [info(point)[0] for point in points]

        out = []

        for i, thisPoint in enumerate(points[:-1]):
            nextPoint = points[i+1]
            out.append(nextPoint-thisPoint)

        return out

    raise ValueError("Need at least two points.")

def pointsIntoUnitCube(points):
    """
    :param points: the points to normalize
    :type points: [tuple, list, :class:`~paya.runtime.data.Point`]
    :return: The points, fit inside a unit cube.
    :rtype: [:class:`~paya.runtime.data.Point`]
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

    scaleMatrix = createScaleMatrix(scaleFactor)
    return [r.data.Point(point) ^ scaleMatrix for point in points]

@short(tolerance='tol')
def getFramedAimAndUpVectors(points, upVector, tolerance=1e-7):
    """
    Value-only method.

    Returns paired lists of aim and up vectors based on points and
    *upVector*, which can be a single vector or one vector per point.

    The final up vectors are derived using cross products, and biased
    towards the provided hints. Where the points are in-line, cross products
    are either blended from neighbours or swapped out for the user up vectors.

    :param points: the starting points
    :type points: [tuple, list, :class:`~paya.runtime.data.Point`]
    :param upVector: one up hint vector, or one vector per point
    :type upVector: tuple, list, :class:`~paya.runtime.data.Vector`
    :param bool tolerance/tol: any cross products below this length will be
        interpolated from neighbours; defaults to 1e-7
    :return: A list of aim vectors and a list of up vectors.
    :rtype: ([:class:`~paya.runtime.data.Vector`],
        [:class:`~paya.runtime.data.Vector`])
    """
    refVector = upVector
    points = [r.data.Point(point) for point in points]
    ln = len(points)

    if ln > 1:
        refVecs = conformVectorArg(refVector, ll=ln)

        if ln is 2:
            aimVecs = [points[1]-points[0]] * 2
            upVecs = refVecs

            return aimVecs, upVecs

        else:
            aimVecs = getAimVectors(points)

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
            # First, bias towards the reference vectors, dodging Nones
            _upVecs = []

            for upVec, refVec in zip(upVecs, refVecs[1:-1]):
                if upVec is None:
                    _upVecs.append(upVec)

                else:
                    neg = upVec * -1

                    if refVec.dot(neg) > refVec.dot(upVec):
                        upVec = neg

                _upVecs.append(upVec)

            upVecs = _upVecs
            upVecs = blendNones(upVecs, lengthRatios[1:-1])
            upVecs = deflipVectors(upVecs)

        # Pad
        upVecs = [upVecs[0]] + upVecs + [upVecs[-1]]
        aimVecs.append(aimVecs[-1])

        return aimVecs, upVecs

    raise ValueError("Need at least two points.")

@short(
    tolerance='tol',
    framed='fra',
    squashStretch='ss',
    globalScale='gs'
)
def getChainedAimMatrices(
        points,
        aimAxis,
        upAxis,
        upVector,
        squashStretch=False,
        globalScale=None,
        framed=False,
        tolerance=1e-7
):
    """
    :param points: the starting points
    :param aimAxis: the matrix axes to align to the aiming vectors,
        for example '-y'.
    :param upAxis: the matrix axes to align to the resolved up vectors,
        for example 'x'
    :param upVector: either one up vector hint, or a list of up vectors
        (one per point)
    :type:
        tuple, list, :class:`~paya.runtime.data.Vector`, :class:`~paya.runtime.plugs.Vector`,
        [tuple, list, :class:`~paya.runtime.data.Vector`, :class:`~paya.runtime.plugs.Vector`]
    :param bool squashStretch: allow squash-and-stretch on the aiming vectors;
        defaults to False
    :param globalScale/gs: an optional plug for the scale component; defaults
        to None
    :param bool framed/fra: if there are no plugs in the passed
        parameters, perform cross product framing via
        :func:`getFramedAimAndUpVectors` (recommended when drawing chains
        with triads, for example legs); defaults to False
    :param float tolerance/tol: if *framed* is on, any cross products
        below this length will be interpolated from neighbours; defaults to
        1e-7
    :raises NotImplementedError: *framed* was requested but some of
        the arguments were plugs
    :return: Chained-aiming matrices, suitable for drawing or driving chains
        or control hierarchies.
    :rtype: [:class:`~paya.runtime.plugs.Matrix`]
    """
    pointInfos = [info(point) for point in points]
    points = [pointInfo[0] for pointInfo in pointInfos]
    num = len(points)

    if globalScale is None:
        globalScale = 1.0
        gsIsPlug = False

    else:
        globalScale, gsDim, gsIsPlug = info(globalScale)

    upVectors = conformVectorArg(upVector, ll=num)

    hasPlugs = gsIsPlug \
       or any((pointInfo[2] for pointInfo in pointInfos)) \
       or any((isPlug(upVector) for upVector in upVectors))

    if hasPlugs and framed:
        raise NotImplementedError(
            "Cross product calculations are "+
            "not available for dynamic points."
        )

    if hasPlugs and (gsIsPlug or squashStretch):
        editScale = True

        if squashStretch:
            downIndex = 'xyz'.index(aimAxis.strip('-'))

        else:
            baseScaleMtx = createScaleMatrix(globalScale)

    else:
        editScale = False

    matrices = []

    if hasPlugs or not framed:
        aimVectors = getAimVectors(points)
        aimVectors.append(aimVectors[-1])

        matrices = []

        for i, point, aimVector, upVector in zip(
            range(num),
            points,
            aimVectors,
            upVectors
        ):
            with r.Name(i+1):
                matrix = r.createMatrix(
                    aimAxis, aimVector,
                    upAxis, upVector,
                    t=point
                ).pick(t=True, r=True)

                if editScale:
                    if squashStretch:
                        aimLen = aimVector.length()
                        _aimLen = aimLen.get()

                        if _aimLen != 1.0:
                            aimLen /= _aimLen

                        factors = [globalScale] * 3
                        factors[downIndex] = aimLen

                        smtx = createScaleMatrix(*factors)

                    else:
                        smtx = baseScaleMtx

                    matrix = smtx * matrix

            matrices.append(matrix)

    else:
        aimVectors, upVectors = \
            getFramedAimAndUpVectors(points, upVectors, tol=tolerance)

        for point, aimVector, upVector in zip(
            points, aimVectors, upVectors
        ):
            matrices.append(
                createMatrix(
                    aimAxis, aimVector,
                    upAxis, upVector,
                    t=point
                ).pick(t=True, r=True)
            )

    return matrices