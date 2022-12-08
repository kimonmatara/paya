import warnings
from collections import UserDict

import maya.OpenMaya as om
from paya.lib.typeman import *
import paya.apiutil as _au
import pymel.util as _pu
import pymel.core as p

from paya.util import LazyModule
r = LazyModule('paya.runtime')

uncap = lambda x: x[0].lower()+x[1:]

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
#--------------------------------------------------------------|    Units
#--------------------------------------------------------------|

def degToUI(val):
    """
    :param float val: An angle value in degrees.
    :return: If the UI is set to radians, *val* converted to radians;
        otherwise, the original *val*.
    :rtype: :class:`float`
    """
    val = float(val)

    if onRadians():
        val = p.util.radians(val)

    return val

def getUIAngleUnit():
    """
    :return: The current angle unit. Note that this will be returned in a
        format that can be passed along to the data type constructors (e.g.
        'degrees') rather than how it's returned by
        :func:`~pymel.internal.pmcmds.currentUnit` (e.g. 'deg').
    :rtype: :class:`str`
    """
    unit = om.MAngle.uiUnit()
    unit = _au.enumIndexToKey(unit, om.MAngle)[1:]
    return uncap(unit)

def getUIDistanceUnit():
    """
    :return: The current distance unit. Note that this will be returned in a
        format that can be passed along to the data type constructors (e.g.
        'centimeters') rather than how it's returned by
        :func:`~pymel.internal.pmcmds.currentUnit` (e.g. 'cm').
    :rtype: :class:`str`
    """
    unit = om.MDistance.uiUnit()
    unit = _au.enumIndexToKey(unit, om.MDistance)[1:]
    return unit[0].lower()+unit[1:]

def getUITimeUnit():
    """
    :return: The current time unit. Note that this will be returned in a
        format that can be passed along to the data type constructors (e.g.
        '24FPS') rather than how it's returned by
        :func:`~pymel.internal.pmcmds.currentUnit` (e.g. 'film').
    :rtype: :class:`str`
    """
    unit = om.MTime.uiUnit()
    unit = _au.enumIndexToKey(unit, om.MTime)[1:]
    return unit[0].lower()+unit[1:]

def onRadians():
    """
    :return: ``True`` if the UI is set to radians, otherwise ``False``.
    :rtype: ``bool``
    """
    return om.MAngle.uiUnit() == om.MAngle.kRadians

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Exceptions
#--------------------------------------------------------------|

class NoInterpolationKeysError(RuntimeError):
    """
    A blending or interpolation operation has no keys to work with.
    """

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Arg inspections
#--------------------------------------------------------------|

def mathInfo(item):
    p.warning("mathInfo() is deprecated. Use mathops.info() instead")
    itemInfo = info(item)
    return itemInfo['item'], itemInfo['dimension'], itemInfo['isPlug']

@short(defaultUnitType='dut')
def info(item, defaultUnitType=None, quiet=False):
    """
    Returns a dict with the following keys (ordered):

    -   ``'item'``: The *item*, conformed to the most specific Paya type
        possible.

    -   ``'dimension'``: One of ``1``, ``2``, ``3``, ``4`` or ``16``.

    -   ``'unitType'``: One of ``'angle'``, ``'distance'``, ``'time'`` or
        ``None``.

    -   ``'isPlug'``: ``True`` or ``False``.

    Value conforming is performed in the following way:

    -   If *item* is a :class:`bool`, it's returned as-is.
    -   If *item* is a :class:`float` or :class:`int`, it's returned as-is
        unless a *defaultUnitType* is specified, in which case a
        :class:`~paya.runtime.data.Angle`,
        :class:`~paya.runtime.data.Distance` or
        :class:`~paya.runtime.data.Time` instance is returned. UI units
        are used in every case.
    -   If *item* is a list of floats or ints, then:

        -   If its dimension is 3 then, if *defaultUnitType* is set to
            ``'angle'``, it's instantiated as
            :class:`~paya.runtime.data.EulerRotation`; otherwise, as
            :class:`~paya.runtime.data.Vector`.

        -   If its dimension is 4, then it's always returned as a
            :class:`~paya.runtime.data.Quaternion`.

        -   If its dimension is 16, then it's always returned as a
            :class:`~paya.runtime.data.Matrix`.

        -   In all other cases, it's returned as a list with members intact.

    Plugs are returned as :class:`~paya.runtime.plugs.Attribute` instances,
    with the subtype / unit strictly based on :class:`~maya.OpenMaya.MPlug`
    analysis performed by :mod:`paya.pluginfo`.

    :param item: The item to inspect and conform.
    :param defaultUnitType/dut: one of ``'angle'``, ``'distance'``, ``'time'``
        or ``None``.
    :type defaultUnitType/dut: :class:`str`, ``None``
    :param bool quiet: don't throw an error if *item* can't be conformed to
        a math type, just pass-through the incomplete dictionary with the
        ``'item'`` field populated with the original item
    :return: The dictionary.
    :rtype: :class:`dict`
    """
    # Establish order, so that .values() can be used for quick unpacking
    # in Python 3.0
    out = {'item': None, 'dimension': None, 'unitType': None, 'isPlug': False}

    def fromAttr(x):
        plugInfo = x.plugInfo()
        out['dimension'] = plugInfo.get('mathDimension')
        out['unitType'] = plugInfo.get('mathUnitType')
        out['isPlug'] = True
        out['item'] = x

    if isinstance(item, p.Attribute):
        fromAttr(item)
    elif isinstance(item, bool):
        out['dimension'] = 1
        out['item'] = item
    elif isinstance(item, (int, float)):
        out['dimension'] = 1

        if isinstance(item, p.datatypes.Unit):
            out['item'] = item
            out['unitType'] = uncap(item.__class__.__name__)

        else:
            if defaultUnitType is None:
                out['item'] = item

            else:
                out['unitType'] = defaultUnitType

                if defaultUnitType == 'angle':
                    out['item'] = p.datatypes.Angle(
                        item, unit=getUIAngleUnit())

                elif defaultUnitType == 'distance':
                    out['item'] = p.datatypes.Distance(
                        item, unit=getUIDistanceUnit())

                else:
                    out['item'] = p.datatypes.Time(
                        item, unit=getUITimeUnit())
    elif isinstance(item, (tuple, list)):
        if all([isinstance(member, (float, int)) for member in item]):
            out['dimension'] = dimension = len(item)
            if dimension is 3:
                if defaultUnitType is None:
                    out['item'] = p.datatypes.Vector(item)
                else:
                    if defaultUnitType == 'angle':
                        out['item'] = p.datatypes.EulerRotation(
                            item,
                            unit=getUIAngleUnit()
                        )
                        out['unitType'] = 'angle'
                    else:
                        out['item'] = p.datatypes.Vector(item)
            elif dimension is 16:
                out['item'] = p.datatypes.Matrix(item)
            elif dimension is 4:
                out['item'] = p.datatypes.Quaternion(item)
            else:
                out['item'] = list(item)
        else:
            raise TypeError("Can't conform item: {}".format(item))
    elif isinstance(item, p.datatypes.Array):
        out['dimension'] = len(item.flat)
        out['item'] = item
    elif isinstance(item, str):
        item = p.Attribute(item)
        fromAttr(p.Attribute(item))
    else:
        out['item'] = item

    return out

#--------------------------------------------------------------|
#--------------------------------------------------------------|    Soft interpolation utilities
#--------------------------------------------------------------|

def floatRange(start, end, numValues):
    """
    A variant of Python's :class:`range` for floats and float plugs.

    :param start: the minimum value
    :type start: float, :class:`~paya.runtime.plugs.Math1D`
    :param end: the maximum value
    :type end: float, :class:`~paya.runtime.plugs.Math1D`
    :param int numValues: the number of values to generate
    :return: A list of float values between ``start`` and ``end``,
        inclusively.
    :rtype: [:class:`float` | :class:`~paya.runtime.plugs.Math1D`]
    """
    start, startDim, startIsPlug = mathInfo(start)
    end, endDim, endIsPlug = mathInfo(end)

    hasPlugs = startIsPlug or endIsPlug

    if hasPlugs:
        ratios = floatRange(0, 1, numValues)
        return [blendScalars(start, end, w=ratio) for ratio in ratios]

    grain = 1.0 / (numValues-1)
    ratios = [grain * x for x in range(numValues)]
    return [_pu.blend(start, end, weight=ratio) for ratio in ratios]

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
#--------------------------------------------------------------|    Blending
#--------------------------------------------------------------|

@short(weight='w')
def blendScalars(scalarA, scalarB, weight=0.5):
    """
    Blends between two scalar values or plugs.

    :param scalarA: the first scalar
    :type scalarA: float, str, :class:`~paya.runtime.plugs.Math1D`
    :param scalarB: the second scalar
    :type scalarB: float, str, :class:`~paya.runtime.plugs.Math1D`
    :param weight/w: the weight; when this is at 1.0, *scalarB*
        will have fully taken over; defaults to 0.t
    :type weight/w: float, str, :class:`~paya.runtime.plugs.Math1D`
    :return:
    """
    scalarA, dimA, isPlugA = mathInfo(scalarA)
    scalarB, dimB, isPlugB = mathInfo(scalarB)
    weight, weightDim, weightIsPlug = mathInfo(weight)

    if isPlugA or isPlugB or weightIsPlug:
        node = r.nodes.BlendTwoAttr.createNode()
        node.attr('input')[0].put(scalarA, p=isPlugA)
        node.attr('input')[1].put(scalarB, p=isPlugB)
        node.attr('attributesBlender').put(weight, p=weightIsPlug)

        return node.attr('output')

    return _pu.blend(scalarA, scalarB, weight=weight)

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
        matrix, dim, isplug = mathInfo(matrix)

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

@short(manageScale='ms',
       preserveSecondLength='psl',
       thirdLength='tl',
       translate='t',
       plug='p')
def createMatrix(*rowHints,
                 manageScale=True,
                 preserveSecondLength=False,
                 thirdLength=None,
                 translate=None,
                 plug=None):
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
    :param bool manageScale/ms: set this to ``False`` to allow scale to be
        defined by incidental operations; useful when you intend to discard
        scale later anyway; defaults to ``True``
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
        translate, translateDim, translateIsPlug = mathInfo(translate)

        if plug is None and translateIsPlug:
            plug = True

    if manageScale:
        if thirdLength is None:
            thirdLengthIsDefined = False

        else:
            thirdLengthIsDefined = True
            thirdLength, thirdLengthDim, thirdLengthIsPlug = mathInfo(thirdLength)

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
        vectorInfos = list(map(mathInfo, rowHints[1::2]))
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

                initMtx = createMatrix(axis1, _vec1,
                                       axis2, _vec2, p=False).pick(r=True)

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

                if manageScale:
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

                    scaleMtx = createMatrix(absAxis1, sVec1,
                                            absAxis2, sVec2,
                                            absAxis3, sVec3)

                    matrix = scaleMtx * matrix.pk(r=True)

                # Add translate information
                if translate is not None:
                    matrix = matrix * translate.asTranslateMatrix()

                return matrix

            else: # Hard + explicit construction
                matrix = r.nodes.FourByFourMatrix.createNode().attr('output')

                if manageScale:
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

        else: # Soft implementation
            if ortho:
                if manageScale and thirdLength is None:
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

                if manageScale:
                    if preserveSecondLength:
                        vec2 = _vec2.normal() * vec2.length()

                    else:
                        vec2 = _vec2

                    vec3 = vec3.normal() * thirdLength

                else:
                    vec2 = _vec2

                absAxis3 = [ax for ax in 'xyz' if \
                    ax not in (absAxis1, absAxis2)][0]

                return createMatrix(absAxis1, vec1,
                                    absAxis2, vec2,
                                    absAxis3, vec3,
                                    t=translate,
                                    p=False,
                                    ms=manageScale)

            else: # Explicit construction
                matrix = p.datatypes.Matrix()

                if manageScale and thirdLengthIsDefined:
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
        # Construct an identity matrix

        if plug:
            matrix = r.nodes.FourByFourMatrix.createNode().attr('output')

            if manageScale and thirdLengthIsDefined:
                (axisVecs['z'] * thirdLength) >> matrix.z

            if translate is not None:
                translate >> matrix.t

            return matrix

        else:
            matrix = p.datatypes.Matrix()

            if manageScale and thirdLengthIsDefined:
                matrix.z = axisVecs['z'] * thirdLength

            if translate is not None:
                matrix.t = translate

            return matrix

cm = createMatrix

def createScaleMatrix(*args):
    """
    Quick(er) method to create static or dynamic scale matrices. Takes one,
    three or six arguments.

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

    return createMatrix(
        axes[0], axisVecs[axes[0]] * scalars[0],
        axes[1], axisVecs[axes[1]] * scalars[1],
        axes[2], axisVecs[axes[2]] * scalars[2]
    )

csm = createScaleMatrix

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
        points = [mathInfo(point)[0] for point in points]

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
    return [p.datatypes.Point(point) ^ scaleMatrix for point in points]

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
    points = [p.datatypes.Point(point) for point in points]
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
    pointInfos = [mathInfo(point) for point in points]
    points = [pointInfo[0] for pointInfo in pointInfos]
    num = len(points)

    if globalScale is None:
        globalScale = 1.0
        gsIsPlug = False

    else:
        globalScale, gsDim, gsIsPlug = mathInfo(globalScale)

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

@short(fromEnd='fe')
def parallelTransport(normal, tangents, fromEnd=False):
    """
    Implements **parallel transport** as described in the
    `Houdini demonstration by Manuel Casasola Merkle
    <https://www.sidefx.com/tutorials/parallel-transport/>`_
    based on the `paper by Hanson and Ma
    <https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.65.7632&rep=rep1&type=pdf>`_.

    If any of the arguments are plugs, the outputs will be plugs as well. The
    first output normal is a pass-through of the *normal* argument.

    :param normal: the starting normal (or up vector)
    :type normal: list, tuple, :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.plugs.Vector`
    :param tangents: the tangent samples along the curve
    :type tangents: [list, tuple, :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.plugs.Vector`]
    :param bool fromEnd/fe: indicate that *normal* is at the end, not the
        start, of the sequence, and solve accordingly; defaults to False
    :return: The resolved normals / up vectors.
    :rtype: [:class:`paya.runtime.data.Vector`],
        [:class:`paya.runtime.plugs.Vector`]
    """
    tangents = list(tangents)

    if fromEnd:
        tangents = tangents[::-1]

    normal, normalDim, normalIsPlug = mathInfo(normal)
    tangentInfos = [mathInfo(tangent) for tangent in tangents]
    tangents = [tangentInfo[0] for tangentInfo in tangentInfos]

    normal = normal.rejectFrom(tangents[0]) # perpendicularise, otherwise
                                            # whole calc goes wonky

    tangentPlugStates = [tangentInfo[2] for tangentInfo in tangentInfos]
    hasTangentPlugs = any(tangentPlugStates)

    if hasTangentPlugs:
        allTangentsArePlugs = all(tangentPlugStates)

    else:
        allTangentsArePlugs = False

    hasPlugs = hasTangentPlugs or normalIsPlug
    outNormals = [normal]

    if hasPlugs:
        # Force everything to plugs for simplicity
        tangents = forceVectorsAsPlugs(tangents)

        normal = forceVectorsAsPlugs([normal])[0]
        outNormals[0] = normal

        for i, thisTangent in enumerate(tangents[:-1]):
            with r.Name('solve', i+1, padding=3):
                nextTangent = tangents[i+1]

                dot = thisTangent.dot(nextTangent, nr=True)
                inline = dot.abs().ge(1.0-1e-7)

                binormal = thisTangent.cross(
                    nextTangent, nr=True, ig=inline)

                theta = dot.acos()
                thisNormal = outNormals[i]

                nextNormal = inline.ifElse(
                    thisNormal,
                    thisNormal.rotateByAxisAngle(binormal, theta)
                )

                outNormals.append(nextNormal)

    else:
        # Soft implementation
        for i, thisTangent in enumerate(tangents[:-1]):
            nextTangent = tangents[i+1]
            dot = thisTangent.dot(nextTangent, nr=True)

            if dot >= 1.0-1e-7:
                nextNormal = outNormals[i]

            else:
                binormal = thisTangent.cross(nextTangent, nr=True)
                theta = _pu.acos(dot)

                nextNormal = outNormals[i
                    ].rotateByAxisAngle(binormal, theta)

            outNormals.append(nextNormal)

    if fromEnd:
        outNormals = outNormals[::-1]

    return outNormals

@short(ratios='rat', unwindSwitch='uws')
def blendCurveNormalSets(normalsA,
                         normalsB,
                         tangents,
                         ratios=None,
                         unwindSwitch=0):
    """
    Blends between two sets of normals along a curve. The number of
    tangents, normalsA, normalsB and ratios must be the same. If any inputs
    are plugs then the outputs will also be plugs.

    :param normalsA: the first set of normals
    :type normalsA: [list, tuple,
        :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.plugs.Vector`]
    :param normalsB: the first set of normals
    :type normalsB: [list, tuple,
        :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.plugs.Vector`]
    :param tangents: the curve tangents around which to rotate the normals
    :type tangents: [list, tuple,
        :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.plugs.Vector`]
    :param ratios/rat: per-normal blend ratios; if omitted, a uniform range of
        floats will be generated automatically; defaults to None
    :type ratios/rat: None, [float, :class:`~paya.runtime.plugs.Math1D`]
    :param unwindSwitch/uws: an integer value or attribute to pick between:

        - 0 for shortest angle unwinding (the default)
        - 1 for positive angle unwinding
        - 2 for negative angle unwinding

    :type unwindSwitch/uws: int, :class:`~paya.runtime.plugs.Math1D`
    :type unwindSwitch/uws: int, :class:`~paya.runtime.plugs.Math1D`
    :raises ValueError: Unequal argument lengths.
    :return: The blended set of curve normals.
    :rtype: :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.plugs.Vector`
    """
    #-------------------------------|    Wrangle args / early escape

    # Check lengths
    numTangents = len(tangents)
    numNormalsA = len(normalsA)
    numNormalsB = len(normalsB)

    if numTangents is numNormalsA is numNormalsB:
        if ratios is None:
            ratios = floatRange(0, 1, numTangents)
            numRatios = numTangents

        else:
            ratios = list(ratios)
            numRatios = len(ratios)

            if numRatios is not numTangents:
                raise ValueError("Unequal argment lengths.")

    else:
        raise ValueError("Unequal argment lengths.")

    tangentInfos = [mathInfo(tangent) for tangent in tangents]
    tangents = [tangentInfo[0] for tangentInfo in tangentInfos]
    
    normalAInfos = [mathInfo(normalA) for normalA in normalsA]
    normalsA = [normalAInfo[0] for normalAInfo in normalAInfos]
    
    normalBInfos = [mathInfo(normalB) for normalB in normalsB]
    normalsB = [normalBInfo[0] for normalBInfo in normalBInfos]

    ratioInfos = [mathInfo(ratio) for ratio in ratios]
    ratios = [ratioInfo[0] for ratioInfo in ratioInfos]

    uwInfo = mathInfo(unwindSwitch)
    unwindSwitch = uwInfo[0]

    hasPlugs = uwInfo[2] \
        or any((tangentInfo[2] for tangentInfo in tangentInfos)) \
        or any((normalAInfo[2] for normalAInfo in normalAInfos)) \
        or any((normalBInfo[2] for normalBInfo in normalBInfos)) \
        or any((ratioInfo[2] for ratioInfo in ratioInfos))

    if hasPlugs:
        tangents = forceVectorsAsPlugs(tangents)
        normalsA = forceVectorsAsPlugs(normalsA)
        normalsB = forceVectorsAsPlugs(normalsB)

    #-------------------------------|    Iterate

    out = []

    for i, tangent, normalA, normalB, ratio in zip(
        range(numRatios), tangents, normalsA,
        normalsB, ratios
    ):
        normalA.setClass(r.plugs.Vector)
        normalB.setClass(r.plugs.Vector)

        blended = normalA.blend(normalB,
                                clockNormal=tangent,
                                unwindSwitch=unwindSwitch,
                                weight=ratio)
        out.append(blended)

    return out

@short(ratios='rat', unwindSwitch='uws')
def bidirectionalParallelTransport(startNormal,
                                   endNormal,
                                   tangents,
                                   ratios=None,
                                   unwindSwitch=0):
    """
    Blends between a forward and backward parallel-transport solution. If
    either *startNormal* or *endNormal* are ``None``, the solution will
    only be performed in one direction and returned on its own.

    :param startNormal: the normal at the start of the blend range
    :type startNormal: list, tuple,
        :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.plugs.Vector`
    :param endNormal: list, tuple,
        :class:`~paya.runtime.data.Vector`,
        :class:`~paya.runtime.plugs.Vector`
    :param tangents: tangents along the blend range; one normal will
        be generated per tangent; the more tangents, the higher the
        accurace of the parallel transport solve
    :param ratios: if provided, should be a list of float values or plugs
        (one per tangent); if omitted, a uniform float range will be generated
        automatically; defaults to None
    :type ratios: None, [float, :class:`~paya.runtime.plugs.Math1D`]
    :param unwindSwitch/uws: an integer value or attribute to pick between:

        - 0 for shortest angle unwinding (the default)
        - 1 for positive angle unwinding
        - 2 for negative angle unwinding

    :type unwindSwitch/uws: int, :class:`~paya.runtime.plugs.Math1D`
    :raises ValueError: One of:

        - Unequal numbers of tangents and ratios (if provided)
        - Both *startNormal* and *endNormal* are ``None``

    :return: The normals.
    :rtype: [:class:`~paya.runtime.plugs.Vector`]
    """
    if (startNormal is None) and (endNormal is None):
        raise ValueError(
            "Please provide a start normal and / or an end normal.")

    if ratios:
        if len(ratios) != len(tangents):
            raise ValueError("Unequal numbers of ratios and tangents.")

    fwds = bwds = None

    if startNormal is not None:
        fwds = parallelTransport(startNormal, tangents)

    if endNormal is not None:
        bwds = parallelTransport(endNormal, tangents[::-1])[::-1]

    if fwds:
        if bwds:
            return blendCurveNormalSets(fwds, bwds, tangents,
                                        rat=ratios, uws=unwindSwitch)
        return fwds

    return bwds