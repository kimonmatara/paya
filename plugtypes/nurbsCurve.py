import paya.lib.mathops as _mo
import pymel.util as _pu
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Constructors
    #---------------------------------------------------------------|

    @short(upVector='up', radius='rad')
    def createArc(self, points, upVector=None, radius=None):
        raise NotImplementedError

    @classmethod
    @short(
        degree='d',
        numCVs='cvs'
    )
    def createLine(
            cls,
            startPoint,
            endPoint,
            degree=None,
            numCVs=None
    ):
        """
        Configures a ``makeNurbsSquare`` node to generate a single NURBS
        curve output for a line and returns the output.

        :param startPoint: the start point of the line
        :type startPoint: tuple, list, str, :class:`~paya.runtime.plugs.Math1D`
        :param startPoint: the end point of the line
        :type endPoint: tuple, list, str, :class:`~paya.runtime.plugs.Math1D`
        :param degree/d: the curve degree; if omitted, it is automatically
            derived from 'numCVs'; if 'numCVs' is also omitted, defaults to 1
        :param int numCVs/cvs: the number of CVs; if omitted, it is
            automatically derived from 'degree'; if 'degree' is also omitted,
            defaults to 2
        :return: The curve output.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        #---------------------|    Gather info

        if numCVs is None and degree is None:
            degree = 1
            numCVs = 2

        elif numCVs is None:
            numCVs = degree + 1

        elif degree is None:
            if numCVs is 2:
                degree = 1

            elif numCVs is 3:
                degree = 2

            else:
                degree = 3

        numSpans = numCVs - degree

        startPoint = _mo.info(startPoint)[0]
        endPoint = _mo.info(endPoint)[0]
        vector = endPoint - startPoint
        mag = vector.length()

        #---------------------|    Configure node to create a line of magnitude 1.0

        node = r.nodes.MakeNurbsSquare.createNode()
        node.attr('spansPerSide').set(numSpans)
        node.attr('normal').set([0.0, 0.0, 1.0])
        node.attr('center').set([0.5, 0.5, 0.0])
        node.attr('sideLength1').set(1.0)
        node.attr('sideLength2').set(1.0)
        node.attr('degree').set(degree)
        output = node.attr('outputCurve3')

        #---------------------|    Transform

        scaleMatrix = r.createScaleMatrix(1.0, mag, 1.0)

        matrix = r.createMatrix(
            'y', vector,
            'x', [1, 0, 0],
            t=startPoint
        ).pk(t=True, r=True)

        matrix = scaleMatrix * matrix

        return output.transform(matrix)

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Sampling
    #---------------------------------------------------------------|

    #--------------------------------------|    Curve-level

    @short(reuse='re')
    def info(self, reuse=True):
        """
        :param bool reuse/re: Reuse any previously-connected ``curveInfo``
            node; defaults to True
        :return: A ``curveInfo`` node connected to this curve output.
        :rtype: :class:`~paya.runtime.nodes.CurveInfo`
        """
        if reuse:
            existing = self.outputs(type='curveInfo')

            if existing:
                return existing[0]

        node = r.nodes.CurveInfo.createNode()
        self >> node.attr('inputCurve')
        return node

    def length(self):
        """
        :return: The arc length of this curve output.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.info().attr('arcLength')

    def controlPoints(self):
        """
        :return: The ``.controlPoints`` multi-attribute of a connected
            ``curveInfo`` node.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        plug = self.info().attr('controlPoints')
        plug.evaluate()
        return plug

    #--------------------------------------|    Info (bundled) sampling

    def initMotionPath(self, *uValue, **config):
        """
        Connects and configures a ``motionPath`` node.

        :param uValue: an optional value or input for the ``uValue`` attribute
        :type uValue: float, :class:`~paya.runtime.plugs.Math1D`
        :param \*\*config: if provided, these should be an unpacked
            mapping of *attrName: attrSource* to configure the node's
            attributes; sources can be values or plugs
        :return: The ``motionPath`` node.
        :rtype: :class:`~paya.runtime.nodes.MotionPath`
        """
        if uValue:
            if 'uValue' in config:
                raise RuntimeError(
                    "'uValue' must either be passed as a "+
                    "positional or keyword argument, not both."
                )

            uValue = uValue[0]

        elif 'uValue' in config:
            uValue = config.pop('uValue')

        else:
            uValue = 0.0

        mp = r.nodes.MotionPath.createNode()
        self >> mp.attr('geometryPath')
        uValue >> mp.attr('uValue')

        for attrName, attrSource in config.items():
            attrSource >> mp.attr(attrName)

        return mp

    def infoAtParam(self, param):
        """
        :param point: the sample parameter
        :return: A ``pointOnCurveInfo`` node configured for the specified
            parameter.
        :rtype: :class:`~paya.runtime.nodes.PointOnCurveInfo`
        """
        node = r.nodes.PointOnCurveInfo.createNode()
        self >> node.attr('inputCurve')
        param >> node.attr('parameter')
        return node

    def infoAtPoint(self, point):
        """
        :param point: the sample point
        :return: A ``pointOnCurveInfo`` node configured for the specified
            point.
        :rtype: :class:`~paya.runtime.nodes.PointOnCurveInfo`
        """
        return self.infoAtParam(self.paramAtPoint(point))

    def infoAtFraction(self, fraction):
        """
        :param fraction: the length fraction to sample at
        :return: A ``pointOnCurveInfo`` node configured for the specified
            length fraction.
        :rtype: :class:`~paya.runtime.nodes.PointOnCurveInfo`
        """
        return self.infoAtParam(self.paramAtFraction(fraction))

    def infoAtLength(self, length):
        """
        :param fraction: the length to sample at
        :return: A ``pointOnCurveInfo`` node configured for the specified
            length.
        :rtype: :class:`~paya.runtime.nodes.PointOnCurveInfo`
        """
        return self.infoAtParam(self.paramAtLength(length))

    def initNearestPointOnCurve(self, point):
        """
        Connects and configures a ``nearestPointOnCurve`` node.

        :param point: the reference point
        :return: The ``nearestPointOnCurve`` node.
        :rtype: :class:`~paya.runtime.nodes.NearestPointOnCurve`
        """
        node = r.nodes.NearestPointOnCurve.createNode()
        self >> node.attr('inputCurve')
        point >> node.attr('inPosition')
        return node

    #--------------------------------------|    Point sampling

    def pointAtParam(self, param):
        """
        :param param: the parameter to sample
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the given parameter.
        """
        return self.infoAtParam(param).attr('position')

    def pointAtFraction(self, fraction):
        """
        :param fraction: the length fraction at which to sample a point
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the specified length fraction.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        mp = self.initMotionPath(fraction, fractionMode=True)
        return mp.attr('allCoordinates')

    def pointAtLength(self, length):
        """
        :param length: the length
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the given length.
        """
        fraction = length / self.length()
        return self.pointAtFraction(fraction)

    def closestPoint(self, point):
        """
        :param point: the reference point
        :type point: list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The closest point to the given reference point.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.initNearestPointOnCurve().attr('position')

    #--------------------------------------|    Param sampling

    def paramAtPoint(self, point):
        """
        :alias: ``closestParam``
        :param point: the reference point
        :type point: list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The closest parameter to the given point.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.initNearestPointOnCurve(point).attr('parameter')

    closestParam = paramAtPoint

    def paramAtFraction(self, fraction):
        """
        :param fraction: the length fraction
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The parameter at the given length fraction.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        point = self.pointAtFraction(fraction)
        return self.closestParam(point)

    def paramAtLength(self, length):
        """
        :param length: the length to sample at.
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The parameter at the given length.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        fraction = length / self.length()
        return self.paramAtFraction(fraction)

    #--------------------------------------|    Length sampling

    def lengthAtFraction(self, fraction):
        """
        :param fraction: the fraction
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The length at the given length fraction.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.length() * fraction

    def lengthAtParam(self, param):
        """
        :param param: the parameter
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The length at the given parameter.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.detachCurve(param, keep=0)[0].length()

    def lengthAtFraction(self, fraction):
        """
        :param fraction: the length fraction
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The length at the given fraction.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        param = self.paramAtFraction(fraction)
        return lengthAtParam(param)

    def lengthAtPoint(self, point):
        """
        :param point: the point
        :type point: list, tuple, :class:`~paya.runtime.data.Point`,
             :class:`~paya.runtime.plugs.Vector`
        :return: The length at the given point.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        param = self.paramAtPoint(point)
        return lengthAtParam(param)

    #--------------------------------------|    Fraction sampling

    def fractionAtParam(self, param):
        """
        :param param: the parameter
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The length fraction at the given parameter.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.lengthAtParam(param) / self.length()

    def fractionAtPoint(self, point):
        """
        :param point: the point
        :type point: list, tuple, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Point`
        :return: The length fraction at the given point.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        param = self.paramAtPoint(point)
        return self.fractionAtParam(param)

    def fractionAtLength(self, length):
        """
        :param length: the reference length
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The length fraction at the given length.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return length / self.length()

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Extensions
    #---------------------------------------------------------------|

    @short(
        blend='bl',
        blendBias='bb',
        parameter='p',
        blendKnotInsertion='bki',
        reverse1='rv1',
        reverse2='rv2',
        keepMultipleKnots='kmk'
    )
    def attach(
            self,
            otherCurve,
            blend=False,
            blendBias=0.5,
            parameter=0.1,
            blendKnotInsertion=False,
            reverse1=False,
            reverse2=False,
            keepMultipleKnots=True
    ):
        """
        Attaches a curve to this one.

        :param otherCurve: the curve to attach
        :typ otherCurve: str, :class:`~paya.runtime.plugs.NurbsCurve`
        :param bool blend/bl: perform a blended attachment; defaults to False
        :param blendBias/bb: the blend bias; defaults to 0.5
        :type blendBias/bb: float, :class:`~paya.runtime.plugs.Math1D`
        :param parameter/p: a parameter for the blend knot insertion;
            defaults to 0.1
        :type parameter/p: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool blendKnotInsertion/bki: insert a blend not; defaults to
            False
        :param bool reverse1: reverse this curve; defaults to False
        :param bool reverse2: reverse the other curve; defaults to False
        :param bool keepMultipleKnots/kmk: keep multiple knots; defaults to
            True
        :return: The combined curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.AttachCurve.createNode()
        self >> node.attr('inputCurve1')
        otherCurve >> node.attr('inputCurve2')

        node.attr('method').set(1 if blend else 0)
        blendBias >> node.attr('blendBias')
        parameter >> node.attr('parameter')
        node.attr('blendKnotInsertion').set(blendKnotInsertion)
        node.attr('reverse1').set(reverse1)
        node.attr('reverse2').set(reverse2)
        node.attr('keepMultipleKnots').set(keepMultipleKnots)

        return node.attr('outputCurve')

    def initExtendCurve(self, **config):
        """
        Connects and configures an ``extendCurve`` node.

        :param \*\*config: if provided, this should be an unpacked mapping
            of *attrName: attrSource* to configure the node attributes.
            Attribute sources can be values or plugs.
        :return: The ``extendCurve`` node.
        :rtype: :class:`~paya.runtime.nodes.ExtendCurve`
        """
        node = r.nodes.ExtendCurve.createNode()
        self >> node.attr('inputCurve1')

        for attrName, attrSource in config.items():
            attrSource >> node.attr(attrName)

        return node

    @short(
        keepMultipleKnots='kmk',
        atStart='ats',
        useSegment='seg'
    )
    def extendByVector(
            self,
            vector,
            atStart=False,
            keepMultipleKnots=True,
            useSegment=False
    ):
        """
        :param vector: the vector along which to extend
        :type vector: list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool atStart/ats: extend from the start instead of the end;
            defaults to False
        :param bool keepMultipleKnots/kmk: keep multiple knots; defaults to
            True
        :param bool useSegment/seg: extend using an attached segment instead
            of an ``extendCurve`` node; defaults to False
        :return: This curve, extended along the specified vector.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        points = list(self.controlPoints())
        startPoint = points[0 if atStart else -1]
        endPoint = startPoint + vector

        if useSegment:
            segment = self.createLine(startPoint, endPoint)

            if atStart:
                inp = self.reverse()
                out = inp.attach(segment, kmk=keepMultipleKnots)
                return out.reverse()

            else:
                return self.attach(segment, kmk=keepMultipleKnots)

        return self.initExtendCurve(
            extendMethod='Point',
            inputPoint=endPoint,
            start=1 if atStart else 0,
            removeMultipleKnots=not keepMultipleKnots
        ).attr('outputCurve').setClass(type(self))

    @short(
        keepMultipleKnots='kmk',
        atStart='ats',
        useSegment='seg'
    )
    def extendToPoint(
            self,
            point,
            atStart=False,
            keepMultipleKnots=True,
            useSegment=False
    ):
        """
        :param point: the point to reach for
        :type point: list, tuple, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool atStart/ats: extend from the start instead of the end;
            defaults to False
        :param bool keepMultipleKnots/kmk: keep multiple knots; defaults to
            True
        :param bool useSegment/seg: extend using an attached segment instead
            of an ``extendCurve`` node; defaults to False
        :return: This curve, extended to meet the specified point
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        if useSegment:
            allPoints = list(self.controlPoints())
            startPoint = allPoints[0 if atStart else -1]
            segment = self.createLine(startPoint, point)

            if atStart:
                inp = self.reverse()
                out = inp.attach(segment, kmk=keepMultipleKnots)
                return out.reverse()

            else:
                return self.attach(segment, kmk=keepMultipleKnots)

        return self.initExtendCurve(
            extendMethod='Point',
            inputPoint=point,
            start=1 if atStart else 0,
            removeMultipleKnots=not keepMultipleKnots
        ).attr('outputCurve').setClass(type(self))

    @short(
        atStart='ats',
        atBothEnds='abe',
        keepMultipleKnots='kmk',
        circular='cir',
        linear='lin',
        extrapolate='ext'
    )
    def extendByLength(
            self,
            length,
            atStart=False,
            atBothEnds=False,
            keepMultipleKnots=True,
            circular=False,
            linear=False,
            extrapolate=False
    ):
        """
        :param length: the length by which to extend
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool atStart/ats: extend from the start instead of the end;
            defaults to False
        :param bool atBothEnds/abe: extend from both ends; note that, in this
            case, the length at either end will be halved; defaults to False
        :param bool keepMultipleKnots/kmk: keep multiple knots; defaults to
            True
        :param bool circular/cir: use the 'circular' mode of the
            ``extendCurve`` node; defaults to False
        :param bool linear/lin: use the 'linear' mode of the
            ``extendCurve`` node; defaults to True
        :param bool extrapolate/ext: use the 'extrapolate' mode of the
            ``extendCurve`` node; defaults to False
        :return: This curve, extended by the specified length.
        """
        length = _mo.info(length)[0]

        if atBothEnds:
            length *= 0.5

        if circular:
            extensionType = 'Circular'

        elif extrapolate:
            extensionType = 'Extrapolate'

        else:
            extensionType = 'Linear'

        if atStart:
            start = 'Start'

        elif atBothEnds:
            start = 'Both'

        else:
            start = 'End'

        return self.initExtendCurve(
            extendMethod='Distance',
            extensionType=extensionType,
            distance=length,
            removeMultipleKnots=not keepMultipleKnots,
            start=start
        ).attr('outputCurve')

    @short(
        atStart='ats',
        atBothEnds='abe',
        point='pt',
        linear='lin',
        circular='cir',
        extrapolate='ext',
        useSegment='seg',
        keepMultipleKnots='kmk'
    )
    def extend(
            self,
            lenPointOrVec,
            point=None,
            linear=None,
            circular=None,
            extrapolate=None,
            useSegment=False,
            keepMultipleKnots=False,
            atStart=None,
            atBothEnds=None
    ):
        """
        Extends this curve in a variety of ways.

        :param lenPointOrVec: a length, point or vector for the extension
        :type lenPointOrVec: float, tuple, list, str,
            :class:`~paya.runtime.data.Point`
            :class:`~paya.runtime.data.Vector`
            :class:`~paya.runtime.plugs.Math1D`
            :class:`~paya.runtime.plugs.Vector`
        :param bool point: if *lenPointOrVec* is a 3D value or plug,
            interpret it as a point rather than a vector; defaults to True
            if *lenPointOrVec* is an instance of
            :class:`~paya.runtime.data.Point`, otherwise False
        :param bool linear/lin: if extending by distance, use the 'linear'
            mode of the ``extendCurve`` node; defaults to True
        :param bool circular/cir: if extending by distance, use the 'circular'
            mode of the ``extendCurve`` node; defaults to False
        :param bool extrapolate/ext: if extending by distance, use the
            'extrapolate' mode of the ``extendCurve`` node; defaults to False
        :param bool useSegment/seg: if extending by vector or point, don't use
            an ``extendCurve`` node; instead, attach a line segment; defaults
            to False
        :param bool keepMultipleKnots/kmk: keep multiple knots; defaults to
            True
        :param bool atStart/ats: extend from the start of the curve rather than the end;
            defaults to False
        :param bool atBothEnds/abe: if extending by length, extend from both
            ends of the curve; defaults to False
        :return: The extended curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        lenPointOrVec, \
        lenPointOrVecDim, \
        lenPointOrVecIsPlug = _mo.info(lenPointOrVec)

        if lenPointOrVecDim is 1:
            if useSegment:
                raise RuntimeError(
                    "Extension by segment is not available "+
                    "for extension-by-length."
                )

            return self.extendByLength(
                lenPointOrVec,
                lin=linear,
                cir=circular,
                ext=extrapolate,
                kmk=keepMultipleKnots,
                ats=atStart,
                abe=atBothEnds
            )

        if lenPointOrVecDim is 3:
            if any([linear, circular, extrapolate]):
                raise RuntimeError(
                    "The linear / circular / extrapolate "+
                    "modes are not available for "+
                    "point / vector."
                )

            if atBothEnds:
                raise RuntimeError(
                    "Extension at both ends is not "+
                    "available for point / vector."
                )

            if point is None:
                if isinstance(lenPointOrVec, r.data.Point):
                    point = True

                else:
                    point = False

            if point:
                meth = self.extendToPoint

            else:
                meth = self.extendByVector

            return meth(
                lenPointOrVec,
                ats=atStart,
                rmk=removeMultipleKnots,
                seg=useSegment
            )

        raise TypeError(
            "Not a 1D or 3D numerical type: {}".format(lenPointOrVec)
        )

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Retraction
    #---------------------------------------------------------------|

    @short(relative='r')
    def subCurve(self, minValue, maxValue, relative=False):
        """
        Connects and configures a ``subCurve`` node and returns its output.

        :param minValue: a source for the ``minValue`` attribute
        :type minValue: float, :class:`~paya.runtime.plugs.Math1D`
        :param maxValue: a source for the ``maxValue`` attribute
        :type maxValue: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool relative/r: set the node to 'relative'; defaults to False
        :return: The sub-curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.SubCurve.createNode()
        self >> node.attr('inputCurve')
        minValue >> node.attr('minValue')
        maxValue >> node.attr('maxValue')
        node.attr('relative').set(relative)

        return node.attr('outputCurve').setClass(type(self))

    @short(select='sel')
    def detach(self, *parameters, select=None):
        """
        Detaches this curve at the specified parameter(s).

        :param \*parameters: the parameter(s) at which to 'cut' the curve
        :type \*parameters: float, :class:`~paya.runtime.plugs.Math1D`
        :param select/sel: a subset of output indices to include in the
            return; ``keep`` attributes will configured accordingly
        :return: [:class:`~paya.runtime.plugs.NurbsCurve`]
        """
        parameters = _pu.expandArgs(*parameters)

        if not parameters:
            raise RuntimeError("No parameter(s) specified.")

        node = r.nodes.DetachCurve.createNode()

        self >> node.attr('inputCurve')

        for i, parameter in enumerate(parameters):
            parameter >> node.attr('parameter')[i]

        node.attr('outputCurve').evaluate()
        outputIndices = range(len(parameters)-1)

        if select is None:
            selectedIndices = outputIndices

        else:
            selectedIndices = _pu.expandArgs(select)

            for outputIndex in outputIndices:
                node.attr('keep')[
                    outputIndex].set(outputIndex in selectedIndices)

        return [node.attr('outputCurve'
            )[selectedIndex] for selectedIndex in selectedIndices]

    @short(atStart='ats', atBothEnds='abe')
    def retract(self, length, atStart=None, atBothEnds=None):
        """
        Retracts this curve.

        :param length: the retraction length
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool atStart/ats: retract at the start of the curve instead
            of the end; defaults to False
        :param atBothEnds: retract at both ends of the curve; defaults to
            False
        :return: The modified curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        cutLength, cutLengthDim, cutLengthIsPlug = _mo.info(length)

        if atStart:
            cutLengths = [cutLength]
            select = 1

        elif atBothEnds:
            cutLength *= 0.5
            cutLengths = [cutLength, self.length()-cutLength]
            select = 1

        else:
            cutLengths = [self.length()-cutLength]
            select = 0

        params = [self.paramAtLength(cutLength) for cutLength in cutLengths]

        return self.detach(*params, select=select)[0]

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Domain
    #---------------------------------------------------------------|

    def reverse(self):
        """
        :return: The reversed curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.ReverseCurve.createNode()
        self >> node.attr('inputCurve')
        return node.attr('outputCurve')

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Conversions
    #---------------------------------------------------------------|

    @short(economy='eco')
    def toBezier(self, economy=True):
        """
        Converts this NURBS curve to a Bezier curve.

        :param bool economy/eco: just return ``self`` if this is already
            a Bezier curve; defaults to True
        :return: The bezier curve.
        :rtype: :class:`~paya.runtime.plugs.BezierCurve`
        """
        if economy:
            if isinstance(self, r.plugs.BezierCurve):
                return self

        node = r.nodes.NurbsCurveToBezier.createNode()
        self >> node.attr('inputCurve')
        return node.attr('outputCurve')

    @short(economy='eco')
    def toNurbs(self, economy=True):
        """
        Converts this Bezier curve to a NURBS curve.

        :param bool economy/eco: just return ``self`` if this is already
            a NURBS curve; defaults to True
        :return: The NURBS curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        if economy:
            if type(self) is r.plugs.NurbsCurve:
                return self

        node = r.nodes.BezierCurveToNurbs.createNode()
        self >> node.attr('inputCurve')
        return node.attr('outputCurve')

    @short(tolerance='tol', keepRange='kr')
    def bSpline(self, tolerance=0.1, keepRange=1):
        """
        :param keepRange/kr: An index or enum key for the ``.keepRange``
            mode:

            - 0: '0 to 1'
            - 1: 'Original' (the default)
            - 2: '0 to #spans'

        :type keepRange/kr: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param tolerance/tol: the fit tolerance; defaults to 0.1
        :type tolerance/tol: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The B-spline.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.FitBspline.createNode()
        self >> node.attr('inputCurve')
        tolerance >> node.attr('tolerance')
        node.attr('keepRange').set(keepRange)

        return node.attr('outputCurve')

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Rebuild
    #---------------------------------------------------------------|

    def initRebuildCurve(self, **config):
        """
        Connects and configures a ``rebuildCurve`` node.

        :param \*\*config: if provided, should be an unpacked mapping of
            *attrName: attrSource* to configure attributes on the node.
            Attribute sources can be plugs or values.
        :return: The ``rebuildCurve`` node.
        :rtype: :class:`~paya.runtime.nodes.RebuildCurve`
        """
        node = r.nodes.RebuildCurve.createNode()
        self >> node.attr('inputCurve')

        for attrName, attrSource in config.items():
            attrSource >> node.attr(attrName)

        return node

    def degreeRebuild(self, degree):
        raise NotImplementedError

    def cvRebuild(self, numCVs):
        raise NotImplementedError

    def spanRebuild(self, numSpans):
        raise NotImplementedError

    def cleanRebuild(self):
        raise NotImplementedError

    def linearRebuild(self, numCVs):
        raise NotImplementedError

    def cageRebuild(self):
        raise NotImplementedError

    def matchRebuild(self, other):
        raise NotImplementedError

    def normalizeRange(self):
        raise NotImplementedError

    # @short(
    #     tolerance='tol',
    #     keepRange='kr',
    #     multipleEndKnots='mek'
    # )
    # def rebuildForCVs(
    #         self,
    #         numCVs,
    #         tolerance=0.1,
    #         keepRange=1,
    #         multipleEndKnots=False
    # ):
    #     """
    #     RebuildCurve can't rebuild to match some combinations of numCVs/degree.
    #     In those cases throw an error, otherwise would have to create a shape.
    #
    #     Also implement a createArc() constructor.
    #     """
    #
    #
    #     """
    #     Rebuilds this curve to hit the requested number of CVs. Degree will be
    #     preserved wherever possible.
    #
    #     :param tolerance/tol: the fit tolerance; defaults to 0.1
    #     :type tolerance/tol: float, :class:`~paya.runtime.plugs.Math1D`
    #     :param keepRange/kr: An index or enum key for the ``.keepRange``
    #         mode:
    #
    #         - 0: '0 to 1'
    #         - 1: 'Original' (the default)
    #         - 2: '0 to #spans'
    #
    #     :type keepRange/kr: int, str, :class:`~paya.runtime.plugs.Math1D`
    #     :return: The rebuilt curve.
    #     :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
    #     """
    #     # Resolve the degree
    #     currentDegree = self.getShapeMFn().degree()
    #
    #     if numCVs is 2:
    #         maxDegree = 1
    #
    #     elif numCVs is 3:
    #         maxDegree = 2
    #
    #     elif numCVs > 3:
    #         maxDegree = currentDegree
    #
    #     else:
    #         raise ValueError("Invalid number of CVs: {}".format(numCVs))
    #
    #     degree = min(currentDegree, maxDegree)
    #     spans = numCVs-degree
    #
    #     return self.initRebuildCurve(
    #         rebuildType='Uniform',
    #         spans=spans,
    #         tolerance=tolerance,
    #         endKnots=1 if multipleEndKnots else 0,
    #         keepEndPoints=True,
    #         keepTangents=1,
    #         degree=degree
    #     ).attr('outputCurve')