import paya.lib.mathops as _mo
import pymel.util as _pu
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #---------------------------------------------------|    Constructors

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

    #---------------------------------------------------|    Curve-level info

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

    #---------------------------------------------------|    Granular sampling

    @short(uValue='u')
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

    @short(turnOnPercentage='top')
    def infoAtParam(self, param, turnOnPercentage=False):
        """
        :param param: the parameter input for a ``pointOnCurveInfo`` node
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool turnOnPercentage/top: sets the ``turnOnPercentage`` flag
            of the ``pointOnCurveInfo`` node (note that this is just a
            normalization of parametric space; it is not equivalent to
            ``fractionMode`` on a ``motionPath``; defaults to False
        :return: A ``pointOnCurveInfo`` node configured for the specified
            parameter.
        :rtype: :class:`~paya.runtime.nodes.PointOnCurveInfo`
        """
        node = r.nodes.PointOnCurveInfo.createNode()
        node.attr('turnOnPercentage').set(turnOnPercentage)
        self >> node.attr('inputCurve')
        param >> node.attr('parameter')

        return node

    def pointAtParam(self, param):
        """
        :param param: the parameter to sample
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the given parameter.
        """
        return self.infoAtParam(param).attr('position')

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

    def closestParam(self, point):
        """
        Returns the closest parameter to the given point.

        :param point: the reference point
        :type point: list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The sampled parameter.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.initNearestPointOnCurve(point).attr('parameter')

    paramAtPoint = closestParam

    def closestPoint(self, point):
        """
        Returns the closest point to the given point.

        :param point: the reference point
        :type point: list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The sampled point.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.initNearestPointOnCurve().attr('position')

    def pointAtFraction(self, fraction):
        """
        :param fraction: the length fraction at which to sample a point
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the specified length fraction.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        mp = self.initMotionPath(fraction, fractionMode=True)
        return mp.attr('allCoordinates')

    def paramAtLength(self, length):
        """
        Returns the parameter at the given length along the curve.

        :param length: the length at which to sample a parameter
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :return: :class:`~paya.runtime.plugs.Math1D`
        """
        fullLength = self.length()
        fraction = length / fullLength
        point = self.pointAtFraction(fraction)
        return self.paramAtPoint(point)

    #---------------------------------------------------|    Edits

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
        removeMultipleKnots='rmk',
        atStart='ats',
        useSegment='seg'
    )
    def extendToPoint(
            self,
            point,
            atStart=False,
            removeMultipleKnots=False,
            useSegment=False
    ):
        """
        Extends this curve to the specified point.

        :param point: the vector along which to extend
        :type point: list, tuple, str,
            :class:`paya.runtime.data.Point`,
            :class:`paya.runtime.plugs.Vector`
        :param bool atStart/ats: extend from the start of the curve instead
            of the end; defaults to False
        :param bool removeMultipleKnots/rmk: remove multiple knots; defaults
            to False
        :param bool useSegment/seg: extend by attaching a straight-line
            segment
        :return: The modified curve output.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        if useSegment:
            points = list(self.controlPoints())
            startPoint = points[0 if atStart else -1]
            startPoint.cl(n='start')
            segment = self.createLine(startPoint, point)

            return self.attach(segment, kmk=not removeMultipleKnots)

        return self.initExtendCurve(
            extendMethod='Point',
            inputPoint=point,
            start=1 if atStart else 0,
            removeMultipleKnots=removeMultipleKnots
        ).attr('outputCurve').setClass(type(self))

    @short(
        removeMultipleKnots='rmk',
        atStart='ats'
    )
    def extendByVector(
            self,
            vector,
            atStart=False,
            removeMultipleKnots=False,
            useSegment=False
    ):
        """
        Extends this curve along the specified vector.

        :param vector: the vector along which to extend
        :type vector: list, tuple, str,
            :class:`paya.runtime.data.Vector`,
            :class:`paya.runtime.plugs.Vector`
        :param bool atStart/ats: extend from the start of the curve instead
            of the end; defaults to False
        :param bool removeMultipleKnots/rmk: remove multiple knots; defaults
            to False
        :return: The modified curve output.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        controlPoints = list(self.controlPoints())
        startPoint = controlPoints[0 if atStart else -1]
        endPoint = startPoint + vector

        if useSegment:
            segment = self.createLine(startPoint, endPoint)
            return self.attach(segment, kmk=not removeMultipleKnots)

        return self.extendToPoint(
            endPoint,
            ats=atStart,
            rmk=removeMultipleKnots
        )

    @short(
        linear='lin',
        circular='cir',
        extrapolate='ext',
        atStart='ats',
        atBothEnds='abe',
        removeMultipleKnots='rmk'
    )
    def extendByDistance(
            self,
            distance,
            linear=False,
            circular=False,
            extrapolate=False,
            atStart=None,
            atBothEnds=None,
            removeMultipleKnots=False
    ):
        """
        Extends this curve by distance.

        .. note::

            Unlike Maya's ``extendCurve`` node, if *atBothEnds* is requested,
            the extension distance at each end will be halved.

        :param distance: the distance (length) to extend by
        :type distance: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool linear/lin: use the 'Linear' mode of the
            ``extendCurve`` node; defaults to True
        :param bool circular/cir: use the 'Linear' mode of the
            ``extendCurve`` node; defaults to False
        :param bool extrapolate/ext: use the 'extrpolate' mode of the
            ``extendCurve`` node; defaults to False
        :param bool atStart/ats: extend from the start of the curve instead
            of the end; defaults to False
        :param bool atBothEnds/abe: extend from both ends of the curve;
            defauls to False
        :param bool removeMultipleKnots: remove multiple knots; defaults to
            False
        :return: The modified curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        distance, distanceDim, distanceIsPlug = _mo.info(distance)

        if atBothEnds:
            distance *= 0.5

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
            distance=distance,
            removeMultipleKnots=removeMultipleKnots,
            start=start
        ).attr('outputCurve').setClass(type(self))

    @short(
        atStart='ats',
        atBothEnds='abe',
        point='pt',
        linear='lin',
        circular='cir',
        extrapolate='ext',
        useSegment='seg',
        removeMultipleKnots='rmk'
    )
    def extend(
            self,
            distPointOrVec,
            point=None,
            linear=None,
            circular=None,
            extrapolate=None,
            useSegment=False,
            removeMultipleKnots=False,
            atStart=None,
            atBothEnds=None
    ):
        """
        Extends this curve.

        :param distPointOrVec: a distance, point or vector for the extension
        :type distPointOrVec: float, tuple, list, str,
            :class:`~paya.runtime.data.Point`
            :class:`~paya.runtime.data.Vector`
            :class:`~paya.runtime.plugs.Math1D`
            :class:`~paya.runtime.plugs.Vector`
        :param bool point: if *distPointOrVec* is a 3D value or plug,
            interpret it as a point rather than a vector; defaults to True
            if *distPointOrVec* is an instance of
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
        :param bool removeMultipleKnots/rmk: remove multiple knots; defaults to False
        :param bool atStart/ats: extend from the start of the curve rather than the end;
            defaults to False
        :param bool atBothEnds/abe: if extending by distance, extend from
            both ends of the curve; defaults to False
        :return: The extended curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        distPointOrVec, \
        distPointOrVecDim, \
        distPointOrVecIsPlug = _mo.info(distPointOrVec)

        if distPointOrVecDim is 1:
            if useSegment:
                raise RuntimeError(
                    "Extension by segment is not available for distance."
                )

            return self.extendByDistance(
                distPointOrVec,
                lin=linear,
                cir=circular,
                ext=extrapolate,
                rmk=removeMultipleKnots,
                ats=atStart,
                abe=atBothEnds
            )

        if distPointOrVecDim is 3:
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
                if isinstance(distPointOrVec, r.data.Point):
                    point = True

                else:
                    point = False

            if point:
                meth = self.extendToPoint

            else:
                meth = self.extendByVector

            return meth(
                distPointOrVec,
                ats=atStart,
                rmk=removeMultipleKnots,
                seg=useSegment
            )

        raise TypeError(
            "Not a 1D or 3D numerical type: {}".format(distPointOrVec)
        )

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