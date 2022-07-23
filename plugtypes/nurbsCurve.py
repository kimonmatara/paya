import paya.lib.mathops as _mo
import pymel.util as _pu
import paya.lib.nurbsutil as _nu
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Constructors
    #---------------------------------------------------------------|

    @classmethod
    @short(
        radius='r',
        directionVector='dv',
        toggleArc='tac',
        sections='s',
        degree='d',
        collinear='col'
    )
    def createArc(
            cls,
            *points,
            directionVector=None,
            radius=1.0,
            toggleArc=False,
            sections=8,
            degree=3,
            collinear=None
    ):
        """
        :param points: two or three points, packed or unpacked
        :type points: tuple, list, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.data.Vector`
        :param directionVector/dv:
            on two-point arcs this defaults to [0, 0, 1] (Z) and defines
            the arc's 'normal';
            on three point arcs it must be provided explicitly if 'collinear'
            is requested, and it is used to jitter the input points to avoid
            Maya errors
        :type directionVector/dv: None, tuple, list,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param radius/r: for two-point arcs only: the arc radius; defaults to
            1.0
        :type radius/r: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool toggleArc/tac: for two-point arcs only: draw the arc
            on the outside; defaults to False
        :param sections/s: the number of arc sections; defaults to 8
        :type sections/s: int, :class:`~paya.runtime.plugs.Math1D`
        :param degree/d: the arc degree; defaults to 3
        :type degree/d: int, :class:`~paya.runtime.plugs.Math1D`
        :param bool collinear/col: for three-point arcs only: prevent the arc
            from disappearing with an error when the input points are
            collinear; defaults to True if *directionVector* was provided,
            otherwise False.
        :return: An output for a circular arc.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        num = len(points)

        if num is 1:
            points = points[0]
            num = len(points)

        if num is 2:
            node = r.nodes.MakeTwoPointCircularArc.createNode()
            points[0] >> node.attr('point1')
            points[1] >> node.attr('point2')

            if directionVector:
                directionVector >> node.attr('directionVector')

            toggleArc >> node.attr('toggleArc')
            degree >> node.attr('degree')
            sections >> node.attr('sections')
            radius >> node.attr('radius')

            return node.attr('outputCurve').setClass(r.plugs.NurbsCurve)

        elif num is 3:
            if collinear is None:
                if directionVector is None:
                    collinear = False

                else:
                    collinear = True

                print('The direction vector is ', directionVector)
                print('Collinear has been resolved to ', collinear)

            elif collinear and directionVector is None:
                raise ValueError(
                    "The direction vector is required for three"+
                    "-point arcs if 'collinear' has been "+
                    "requested."
                )

            node = r.nodes.MakeThreePointCircularArc.createNode()
            points[0] >> node.attr('point1')
            points[1] >> node.attr('point2')
            points[2] >> node.attr('point3')
            sections >> node.attr('sections')
            degree >> node.attr('degree')

            if collinear:
                return node.getCompensatedOutputCurve(directionVector)

            else:
                return node.attr('outputCurve')

        raise ValueError("Need two or three points.")

    @classmethod
    @short(degree='d', numCVs='cvs')
    def createLine(cls, startPoint, endPoint, degree=None, numCVs=None):
        """
        :param startPoint: the start point of the line
        :type startPoint: tuple, list, str, :class:`~paya.runtime.plugs.Math1D`
        :param startPoint: the end point of the line
        :type endPoint: tuple, list, str, :class:`~paya.runtime.plugs.Math1D`
        :param degree/d: the curve degree; if omitted, it is automatically
            derived from 'numCVs'; if 'numCVs' is also omitted, defaults to 1
        :param int numCVs/cvs: the number of CVs; if omitted, it is
            automatically derived from 'degree'; if 'degree' is also omitted,
            defaults to 2
        :return: A curve output for a straight line.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        #---------------------|    Gather info

        if degree is not None:
            degree = _mo.info(degree)[0]

        if numCVs is not None:
            numCVs = _mo.info(numCVs)[0]

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
        numSpans >> node.attr('spansPerSide')
        node.attr('normal').set([0.0, 0.0, 1.0])
        node.attr('center').set([0.5, 0.5, 0.0])
        node.attr('sideLength1').set(1.0)
        node.attr('sideLength2').set(1.0)
        degree >> node.attr('degree')
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

    def getCVs(self):
        """
        :return: The ``.controlPoints`` multi-attribute of a connected
            ``curveInfo`` node.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        plug = self.info().attr('controlPoints')
        plug.evaluate()
        return plug

    #--------------------------------------|    Info (bundled) sampling

    def initMotionPath(self, **config):
        """
        Connects and configures a ``motionPath`` node.

        :param uValue: an optional value or input for the ``uValue`` attribute
        :type uValue: float, :class:`~paya.runtime.plugs.Math1D`
        :param \*\*config: an unpacked mapping of *attrName: attrSource*;
            sources can be values or plugs
        :return: The ``motionPath`` node.
        :rtype: :class:`~paya.runtime.nodes.MotionPath`
        """
        mp = r.nodes.MotionPath.createNode()
        self >> mp.attr('geometryPath')

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
        param = _nu.conformUParamArg(param)
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

    def pointAtCV(self, cv):
        """
        :param cv: the CV to sample
        :type cv: int, :class:`~paya.runtime.comps.NurbsCurveCV`
        :return: A point position at the specified CV.
        """
        return self.info().attr('controlPoints')[int(cv)]

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
        mp = self.initMotionPath(uValue=fraction, fractionMode=True)
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
        return self.initNearestPointOnCurve(point).attr('position')

    #--------------------------------------|    Param sampling

    def paramAtPoint(self, point):
        """
        This is a 'forgiving' implementation; a closest param will still be
        returned if the point is not on the curve.

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
        return self.detach(param, select=0)[0].length()

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

    #--------------------------------------|    Binormal sampling

    def binormalAtParam(self, param):
        """
        :param param: the parameter at which to sample the binormal
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.infoAtParam(param).binormal

    def binormalAtFraction(self, fraction):
        """
        :param fraction: the fraction at which to sample the binormal
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtFraction(fraction)
        return self.binormalAtParam(param)

    def binormalAtLength(self, length):
        """
        :param length: the length at which to sample the binormal
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtLength(length)
        return self.binormalAtParam(param)

    def binormalAtPoint(self, point):
        """
        :param point: the point at which to sample the binormal
        :type point: list, tuple, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`,
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtPoint(point)
        return self.binormalAtParam(param)

    #--------------------------------------|    Matrix sampling

    @short(
        squashStretch='ss',
        upVector='upv',
        upObject='upo',
        aimCurve='aic',
        fraction='fr',
        globalScale='gs',
        matchedCurve='mc'
    )
    def _matrixAtParamOrFraction(
            self,
            paramOrFraction,
            tangentAxis,
            upAxis,
            squashStretch=False,
            upVector=None,
            upObject=None,
            aimCurve=None,
            fraction=False,
            globalScale=None,
            matchedCurve=False
    ):
        #----------------------------------|    Conform arguments

        if not fraction:
            if isinstance(paramOrFraction, r.Component):
                paramOrFraction = float(paramOrFraction)

        if upVector:
            upVector = _mo.info(upVector)[0]

        if upObject:
            upObject = r.PyNode(upObject)

        if aimCurve:
            aimCurve = _mo.asGeoPlug(aimCurve, ws=True)

        if globalScale is None:
            globalScale = 1.0
            gsIsPlug = False

        else:
            globalScale, gsDim, gsIsPlug = _mo.info(globalScale)

        if aimCurve:

            #------------------------------|    pointOnCurveInfo implementation

            # Use pointOnCurveInfo

            if fraction:
                param = self.paramAtFraction(paramOrFraction)

            else:
                param = paramOrFraction

            poci = self.infoAtParam(param)

            # Get vecs

            tangent = poci.attr('tangent')
            position = poci.attr('position')

            if upVector:
                if upObject:
                    upVector = upVector * upObject.attr('wm')

            elif upObject:
                upVector = upObject.getWorldPosition(p=True)-position

            elif aimCurve:
                if matchedCurve:
                    interest = aimCurve.pointAtParam(param)

                else:
                    interest = aimCurve.closestPoint(position)

                upVector = interest-position

            else:
                upVector = poci.attr('normal')

            matrix = r.createMatrix(
                tangentAxis, tangent,
                upAxis, upVector,
                t=position
            ).pk(t=True, r=True)

        else:
            #------------------------------|    motionPath implementation

            mp = r.nodes.MotionPath.createNode()
            self >> mp.attr('geometryPath')

            paramOrFraction >> mp.attr('uValue')
            mp.attr('fractionMode').set(fraction)

            mp.configFollow(tangentAxis, upAxis, wu=upVector, wuo=upObject)

            # Edit the matrix
            rsmtx = mp.attr('orientMatrix')

            if squashStretch:
                tangent = rsmtx.getAxis(tangentAxis)

            tmtx = mp.attr('allCoordinates').asTranslateMatrix()
            matrix = rsmtx.pk(r=True) * tmtx

        #----------------------------------|    Configure scaling

        if gsIsPlug or squashStretch:
            if gsIsPlug:
                _globalScale = globalScale.get()

                if _globalScale != 1.0:
                    globalScale /= _globalScale

            factors = [globalScale] * 3

            if squashStretch:
                tangentLength = tangent.length()
                _tangentLength = tangentLength.get()

                if _tangentLength != 1.0:
                    tangentLength /= _tangentLength

                tangentIndex = 'xyz'.index(tangentAxis.strip('-'))
                factors[tangentIndex] = tangentLength

            smtx = r.createScaleMatrix(*factors)
            matrix = smtx * matrix

        return matrix

    @short(
        squashStretch='ss',
        upVector='upv',
        upObject='upo',
        aimCurve='aic',
        fraction='fr',
        globalScale='gs',
        matchedCurve='mc'
    )
    def matrixAtParam(
            self,
            param,
            tangentAxis,
            upAxis,
            squashStretch=False,
            upVector=None,
            upObject=None,
            aimCurve=None,
            globalScale=None,
            matchedCurve=False
    ):
        """
        :param param: the parameter at which to sample the matrix
        :type param: float, str, :class:`~paya.runtime.Math1D`
        :param str tangentAxis: the axis to align to the curve tangent
        :param str upAxis: the axis to align to the resolved up vector
        :param bool squashStretch/ss: incorporate tangent stretching
            (dynamic only); defaults to False
        :param upVector/upv: used as an up vector on its own, or extracted from
            *upObject*; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an up curve; defaults to None
        :type aimCurve/aic: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param upObject/upo: used as an aiming interest on its own, or as a source
            for *upVector*; defaults to None
        :type upObject/upo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool fraction/fr: interpret *paramOrFraction* as a fraction;
            defaults to False
        :param globalScale/gs: used to drive scaling; the scale will be
            normalised; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *aimCurve* has the
            same U domain as this curve, to avoid unnecessary closest-point
            calculations; defaults to False
        :return: A matrix at the specified parameter, constructed using the
            most efficient DG configuration for the given options.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        return self._matrixAtParamOrFraction(
            param,
            tangentAxis,
            upAxis,
            ss=squashStretch,
            upv=upVector,
            upo=upObject,
            aic=aimCurve,
            gs=globalScale,
            mc=matchedCurve,
            fr=False
        )

    @short(
        squashStretch='ss',
        upVector='upv',
        upObject='upo',
        aimCurve='aic',
        fraction='fr',
        globalScale='gs',
        matchedCurve='mc'
    )
    def matrixAtFraction(
            self,
            fraction,
            tangentAxis,
            upAxis,
            squashStretch=False,
            upVector=None,
            upObject=None,
            aimCurve=None,
            globalScale=None,
            matchedCurve=False
    ):
        """
        :param fraction: the fraction at which to sample the matrix
        :type fraction: float, str, :class:`~paya.runtime.Math1D`
        :param str tangentAxis: the axis to align to the curve tangent
        :param str upAxis: the axis to align to the resolved up vector
        :param bool squashStretch/ss: incorporate tangent stretching
            (dynamic only); defaults to False
        :param upVector/upv: used as an up vector on its own, or extracted from
            *upObject*; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an up curve; defaults to None
        :type aimCurve/aic: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param upObject/upo: used as an aiming interest on its own, or as a source
            for *upVector*; defaults to None
        :type upObject/upo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool fraction/fr: interpret *paramOrFraction* as a fraction;
            defaults to False
        :param globalScale/gs: used to drive scaling; the scale will be
            normalised; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *aimCurve* has the
            same U domain as this curve, to avoid unnecessary closest-point
            calculations; defaults to False
        :return: A matrix at the specified fraction, constructed using the
            most efficient DG configuration for the given options.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        return self._matrixAtParamOrFraction(
            fraction,
            tangentAxis,
            upAxis,
            ss=squashStretch,
            upv=upVector,
            upo=upObject,
            aic=aimCurve,
            gs=globalScale,
            mc=matchedCurve,
            fr=True
        )

    @short(
        squashStretch='ss',
        upVector='upv',
        upObject='upo',
        aimCurve='aic',
        fraction='fr',
        globalScale='gs',
        matchedCurve='mc'
    )
    def matrixAtLength(
            self,
            length,
            tangentAxis,
            upAxis,
            squashStretch=False,
            upVector=None,
            upObject=None,
            aimCurve=None,
            globalScale=None,
            matchedCurve=False
    ):
        """
        :param length: the length at which to sample the matrix
        :type length: float, str, :class:`~paya.runtime.Math1D`
        :param str tangentAxis: the axis to align to the curve tangent
        :param str upAxis: the axis to align to the resolved up vector
        :param bool squashStretch/ss: incorporate tangent stretching
            (dynamic only); defaults to False
        :param upVector/upv: used as an up vector on its own, or extracted from
            *upObject*; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an up curve; defaults to None
        :type aimCurve/aic: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param upObject/upo: used as an aiming interest on its own, or as a source
            for *upVector*; defaults to None
        :type upObject/upo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool fraction/fr: interpret *paramOrFraction* as a fraction;
            defaults to False
        :param globalScale/gs: used to drive scaling; the scale will be
            normalised; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *aimCurve* has the
            same U domain as this curve, to avoid unnecessary closest-point
            calculations; defaults to False
        :return: A matrix at the specified length, constructed using the
            most efficient DG configuration for the given options.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        return self._matrixAtParamOrFraction(
            self.fractionAtLength(length),
            tangentAxis,
            upAxis,
            ss=squashStretch,
            upv=upVector,
            upo=upObject,
            aic=aimCurve,
            gs=globalScale,
            mc=matchedCurve,
            fr=True
        )

    @short(
        squashStretch='ss',
        upVector='upv',
        upObject='upo',
        aimCurve='aic',
        fraction='fr',
        globalScale='gs',
        matchedCurve='mc'
    )
    def matrixAtPoint(
            self,
            point,
            tangentAxis,
            upAxis,
            squashStretch=False,
            upVector=None,
            upObject=None,
            aimCurve=None,
            globalScale=None,
            matchedCurve=False
    ):
        """
        :param point: the point at which to sample the matrix
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Point`
        :param str tangentAxis: the axis to align to the curve tangent
        :param str upAxis: the axis to align to the resolved up vector
        :param bool squashStretch/ss: incorporate tangent stretching
            (dynamic only); defaults to False
        :param upVector/upv: used as an up vector on its own, or extracted from
            *upObject*; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an up curve; defaults to None
        :type aimCurve/aic: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param upObject/upo: used as an aiming interest on its own, or as a source
            for *upVector*; defaults to None
        :type upObject/upo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool fraction/fr: interpret *paramOrFraction* as a fraction;
            defaults to False
        :param globalScale/gs: used to drive scaling; the scale will be
            normalised; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *aimCurve* has the
            same U domain as this curve, to avoid unnecessary closest-point
            calculations; defaults to False
        :return: A matrix at the specified point, constructed using the
            most efficient DG configuration for the given options.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        return self._matrixAtParamOrFraction(
            self.paramAtPoint(point),
            tangentAxis,
            upAxis,
            ss=squashStretch,
            upv=upVector,
            upo=upObject,
            aic=aimCurve,
            gs=globalScale,
            mc=matchedCurve,
            fr=False
        )

    #--------------------------------------|    Distributions

    def distributePoints(self, numberOrFractions):
        """
        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :type numberOrFractions: tuple, list or int
        :return: World-space points distributed along the length of the curve.
        :rtype: [:class:`~paya.runtime.plugs.Vector`]
        """
        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)
        return [self.pointAtFraction(fraction) for fraction in fractions]

    def distributeParams(self, numberOrFractions):
        """
        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :type numberOrFractions: tuple, list or int
        :return: Parameters distributed along the length of the curve.
        :rtype: [:class:`~paya.runtime.plugs.Math1D`]
        """
        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)
        return [self.paramAtFraction(fraction) for fraction in fractions]

    def distributeLengths(self, numberOrFractions):
        """
        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :type numberOrFractions: tuple, list or int
        :return: Fractional lengths along the curve.
        :rtype: [:class:`~paya.runtime.plugs.Math1D`]
        """
        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)
        return [self.lengthAtFraction(fraction) for fraction in fractions]

    @short(
        upVector='upv',
        aimCurve='aic',
        squashStretch='ss',
        globalScale='gs',
        matchedCurve='mc'
    )
    def distributeMatrices(
            self,
            numberOrFractions,
            tangentAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            squashStretch=False,
            globalScale=None,
            matchedCurve=None
    ):
        """
        If neither *upVector* or *aimCurve* are provided, curve normals are
        used.

        :param numberOrFractions: a single number of a list of explicit
            length fractions at which to generate matrices
        :type numberOrFractions: int, [float, :class:`~paya.runtime.plugs.Math1D`]
        :param str tangentAxis: the matrix axis to map to the curve tangent,
            for example '-y'
        :param str upAxis: the matrix axis to align to the resolved up vector, for
            example 'x'
        :param upVector/upv: if provided, should be either a single up vector or a
            a list of up vectors (one per fraction); defaults to None
        :type upVector/upv:
            None,
            list, tuple, :class:`~paya.runtime.data.Vector`, :class:`~paya.runtime.plugs.Vector`,
            [list, tuple, :class:`~paya.runtime.data.Vector`, :class:`~paya.runtime.plugs.Vector`]
        :param aimCurve/aic: an 'up' curve, as seen for example on Maya's
            ``curveWarp``; defaults to None
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.Transform`,
            :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param bool squashStretch/ss: allow tangent scaling; defaults to False
        :param globalScale/gs: a global scaling factor; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *aimCurve* has the
            same U domain as this curve, to avoid closest-point calculations;
            defaults to False
        :return: Matrices, distributed along the curve.
        :rtype: [:class:`~paya.runtime.plugs.Matrix`]
        """
        #----------------------------------------|    Resolve args

        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)
        number = len(fractions)

        if upVector:
            upVectors = _mo.conformVectorArg(upVector, ll=number)

        else:
            upVectors = [None] * number

        #----------------------------------------|    Execute

        out = []

        for i, fraction in enumerate(fractions):
            with r.Name(i+1):
                matrix = self.matrixAtFraction(
                    fraction,
                    tangentAxis,
                    upAxis,
                    upv=upVectors[i],
                    aic=aimCurve,
                    ss=squashStretch,
                    gs=globalScale,
                    mc=matchedCurve
                )

                out.append(matrix)

        return out

    @short(
        upVector='upv',
        aimCurve='aic',
        globalScale='gs',
        squashStretch='ss',
        matchedCurve='mc'
    )
    def distributeAimingMatrices(
            self,
            numberOrFractions,
            aimAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            globalScale=None,
            squashStretch=False,
            matchedCurve=False
    ):
        """
        Similar to :meth:`distributeMatrices` except that here the matrices
        are aimed at each other for a 'chain-like' effect. If neither
        *upVector* or *aimCurve* are provided, curve normals are used.

        :param numberOrFractions: a single number of a list of explicit
            length fractions at which to generate matrices
        :type numberOrFractions: int, [float, :class:`~paya.runtime.plugs.Math1D`]
        :param str tangentAxis: the matrix axis to map to the curve tangent,
            for example '-y'
        :param str upAxis: the matrix axis to align to the resolved up vector, for
            example 'x'
        :param upVector/upv: if provided, should be either a single up vector or a
            a list of up vectors (one per fraction); defaults to None
        :type upVector/upv:
            None,
            list, tuple, :class:`~paya.runtime.data.Vector`, :class:`~paya.runtime.plugs.Vector`,
            [list, tuple, :class:`~paya.runtime.data.Vector`, :class:`~paya.runtime.plugs.Vector`]
        :param aimCurve/aic: an 'up' curve, as seen for example on Maya's
            ``curveWarp``; defaults to None
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.Transform`,
            :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param bool squashStretch/ss: allow tangent scaling; defaults to False
        :param globalScale/gs: a global scaling factor; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *aimCurve* has the
            same U domain as this curve, to avoid closest-point calculations;
            defaults to False
        :return: Matrices, distributed along the curve.
        :rtype: [:class:`~paya.runtime.plugs.Matrix`]
        """

        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)
        number = len(fractions)

        mps = [self.initMotionPath(
            fractionMode=True, uValue=fraction) for fraction in fractions]

        points = [mp.attr('allCoordinates') for mp in mps]

        aimVectors = _mo.getAimVectors(points)
        aimVectors.append(aimVectors[-1])

        if upVector:
            upVectors = _mo.conformVectorArg(upVector, ll=number)

        else:
            upVectors = []

            if aimCurve:
                aimCurve = _mo.asGeoPlug(aimCurve, ws=True)

                for i in range(number):
                    if matchedCurve:
                        param = self.paramAtFraction(fractions[i])
                        interest = aimCurve.pointAtParam(param)

                    else:
                        interest = aimCurve.closestPoint(points[i])

                    upVectors.append(interest-points[i])

            else:
                # configure follow on the motion paths and pull
                # the normal vectors

                for i, mp in enumerate(mps):
                    mp.attr('follow').set(True)
                    mp.setFrontAxis(aimAxis)
                    mp.setUpAxis(upAxis)
                    mp.attr('worldUpType').set('Normal')
                    matrix = mp.attr('orientMatrix')
                    upVector = matrix.getAxis(upAxis)
                    upVectors.append(upVector)

        return _mo.getChainedAimMatrices(
            points,
            aimAxis,
            upAxis,
            upVectors,
            ss=squashStretch,
            gs=globalScale
        )

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
        multipleKnots='mul'
    )
    def attach(
            self,
            *curves,
            blend=False,
            blendBias=0.5,
            parameter=0.1,
            blendKnotInsertion=False,
            reverse1=False,
            reverse2=False,
            multipleKnots=True
    ):
        """
        Attaches one or more curves to this one.

        :param \*curves: one or more curves to attach to this one
        :type \*curves: str, :class:`~paya.runtime.plugs.NurbsCurve`
        :param bool blend: use blended attachments; defaults to False
        :param blendBias/bb: ignored if more than two curves are
            involved; the bias for blended attachments; defaults to 0.5
        :type blendBias/bb: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool blendKnotInsertion: ignored if more than two curves
            are involved; add a blend knot; defaults to False
        :param float parameter/p: ignored if more than two curves are
            involved or *blendKnotInsertion* is False; the parameter for
            the blend knot; defaults to 0.1
        :param bool reverse1/rv1: ignored if more than two curves are
            involved; reverse the first curve; defaults to False
        :param bool reverse2/rv2: ignored if more than two curves are
            involved; reverse the second curve; defaults to False
        :param bool multipleKnots: keep multiple knots; defaults to True
        :return: The combined curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        curves = list(_pu.expandArgs(*curves))
        num = len(curves)

        if not num:
            raise ValueError("No curves were specified to attach to.")

        node = r.nodes.AttachCurve.createNode()

        if num > 1:
            allCurves = [self] + curves

            for i, curve in enumerate(allCurves):
                curve >> node.attr('inputCurves')[i]

        else:
            self >> node.attr('inputCurve1')
            curves[0] >> node.attr('inputCurve2')

        node.attr('method').set(1 if blend else 0)
        node.attr('blendKnotInsertion').set(blendKnotInsertion)
        blendBias >> node.attr('blendBias')
        parameter >> node.attr('parameter')
        node.attr('reverse1').set(reverse1)
        node.attr('reverse2').set(reverse2)
        node.attr('keepMultipleKnots').set(multipleKnots)

        return node.attr('outputCurve')

    def initExtendCurve(self, **config):
        """
        Connects and configures an ``extendCurve`` node.

        :param \*\*config: an unpacked mapping of *attrName: attrSource*
            for attribute configuration; sources can be values or plugs
        :return: The ``extendCurve`` node.
        :rtype: :class:`~paya.runtime.nodes.ExtendCurve`
        """
        node = r.nodes.ExtendCurve.createNode()
        self >> node.attr('inputCurve1')

        for attrName, attrSource in config.items():
            attrSource >> node.attr(attrName)

        return node

    @short(
        multipleKnots='mul',
        atStart='ats',
        useSegment='seg'
    )
    def extendByVector(
            self,
            vector,
            atStart=False,
            multipleKnots=True,
            useSegment=False
    ):
        """
        :param vector: the vector along which to extend
        :type vector: list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool atStart/ats: extend from the start instead of the end;
            defaults to False
        :param bool multipleKnots/mul: keep multiple knots; defaults to
            True
        :param bool useSegment/seg: extend using an attached segment instead
            of an ``extendCurve`` node; defaults to False
        :return: This curve, extended along the specified vector.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        points = list(self.getCVs())
        startPoint = points[0 if atStart else -1]
        endPoint = startPoint + vector

        if useSegment:
            segment = self.createLine(startPoint, endPoint)

            if atStart:
                inp = self.reverse()
                out = inp.attach(segment, mul=multipleKnots)
                return out.reverse()

            else:
                return self.attach(segment, mul=multipleKnots)

        return self.initExtendCurve(
            extendMethod='Point',
            inputPoint=endPoint,
            start=1 if atStart else 0,
            removeMultipleKnots=not multipleKnots
        ).attr('outputCurve')
    
    @short(
        multipleKnots='mul',
        atStart='ats',
        useSegment='seg'
    )
    def extendToPoint(
            self,
            point,
            atStart=False,
            multipleKnots=True,
            useSegment=False
    ):
        """
        :param point: the point to reach for
        :type point: list, tuple, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool atStart/ats: extend from the start instead of the end;
            defaults to False
        :param bool multipleKnots/mul: keep multiple knots; defaults to
            True
        :param bool useSegment/seg: extend using an attached segment instead
            of an ``extendCurve`` node; defaults to False
        :return: This curve, extended to meet the specified point
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        if useSegment:
            allPoints = list(self.getCVs())
            startPoint = allPoints[0 if atStart else -1]
            segment = self.createLine(startPoint, point)

            if atStart:
                inp = self.reverse()
                out = inp.attach(segment, kmk=multipleKnots)
                return out.reverse()

            else:
                return self.attach(segment, kmk=multipleKnots)

        return self.initExtendCurve(
            extendMethod='Point',
            inputPoint=point,
            start=1 if atStart else 0,
            removeMultipleKnots=not multipleKnots
        ).attr('outputCurve')
    
    @short(
        atStart='ats',
        atBothEnds='abe',
        multipleKnots='mul',
        circular='cir',
        linear='lin',
        extrapolate='ext'
    )
    def extendByLength(
            self,
            length,
            atStart=False,
            atBothEnds=False,
            multipleKnots=True,
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
        :param bool multipleKnots/mul: keep multiple knots; defaults to
            True
        :param bool circular/cir: use the 'circular' mode of the
            ``extendCurve`` node; defaults to False
        :param bool linear/lin: use the 'linear' mode of the
            ``extendCurve`` node; defaults to False
        :param bool extrapolate/ext: use the 'extrapolate' mode of the
            ``extendCurve`` node; defaults to True
        :return: This curve, extended by the specified length.
        """
        length = _mo.info(length)[0]

        if atBothEnds:
            length *= 0.5

        if circular:
            extensionType = 'Circular'

        elif linear:
            extensionType = 'Linear'

        else:
            extensionType = 'Extrapolate'

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
            removeMultipleKnots=not multipleKnots,
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
        multipleKnots='mul'
    )
    def extend(
            self,
            lenPointOrVec,
            point=None,
            linear=None,
            circular=None,
            extrapolate=None,
            useSegment=False,
            multipleKnots=True,
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
        :param bool multipleKnots/mul: keep multiple knots; defaults to
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
                mul=multipleKnots,
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
                mul=multipleKnots,
                seg=useSegment
            )

        raise TypeError(
            "Not a 1D or 3D numerical type: {}".format(lenPointOrVec)
        )

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Retractions
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
        minValue = _nu.conformUParamArg(minValue)
        maxValue = _nu.conformUParamArg(maxValue)

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
        parameters = [_nu.conformUParamArg(param) for param in parameters]

        if not parameters:
            raise RuntimeError("No parameter(s) specified.")

        node = r.nodes.DetachCurve.createNode()

        self >> node.attr('inputCurve')

        for i, parameter in enumerate(parameters):
            parameter >> node.attr('parameter')[i]

        node.attr('outputCurve').evaluate()
        outputIndices = range(len(parameters)+1)

        if select is None:
            selectedIndices = outputIndices

        else:
            selectedIndices = _pu.expandArgs(select)

            for outputIndex in outputIndices:
                node.attr('keep')[
                    outputIndex].set(outputIndex in selectedIndices)

        out = [node.attr('outputCurve'
            )[selectedIndex] for selectedIndex in selectedIndices]

        return out

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
    #---------------------------------------------------------------|    Rebuilds
    #---------------------------------------------------------------|

    def reverse(self):
        """
        :return: The reversed curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.ReverseCurve.createNode()
        self >> node.attr('inputCurve')
        return node.attr('outputCurve')

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

    def initRebuild(self, **config):
        """
        Connects and configures a ``rebuildCurve`` node.

        :param \*\*config: an unpacked mapping of *attrName: attrSource*;
            sources can be values or plugs
        :return: The ``rebuildCurve`` node.
        :rtype: :class:`~paya.runtime.nodes.RebuildCurve`
        """
        node = r.nodes.RebuildCurve.createNode()
        self >> node.attr('inputCurve')

        for k, v in config.items():
            v >> node.attr(k)

        return node

    @short(
        degree='d',
        endKnots='end',
        keepRange='kr',
        keepEndPoints='kep',
        keepTangents='kt'
    )
    def cvRebuild(
            self,
            numCVs,
            degree=None,
            endKnots='Multiple end knots',
            keepRange='Original',
            keepControlPoints=False,
            keepEndPoints=True,
            keepTangents=False
    ):
        """
        Rebuilds this curve to the specified number of CVs.

        :param int degree/d: the degree to build to; defaults to this curve's
            (current) degree if omitted
        :param endKnots/end: An enum index or label:

            - 0: 'Non Multiple end knots'
            - 1: 'Multiple end knots' (the default)
        :type endKnots: int, str
        :param keepRange/kr: An enum index or label:

            - 0: '0 to 1'
            - 1: 'Original' (the default)
            - 2: '0 to #spans'
        :type keepRange/kr: int, str
        :param bool keepEndPoints/kep: keep end points; defaults to True
        :param bool keepTangents/kt: keep tangents; defaults to False
        :return: The rebuilt curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        if degree is None:
            degree = self.getShapeMFn().degree()

        minNumCVs = degree+1

        if numCVs < minNumCVs:
            raise RuntimeError(
                "At least {} CVs required for degree {}.".format(
                    minNumCVs,
                    degree
                )
            )

        return self.rebuild(
            s=numCVs-degree,
            d=degree,
            end=endKnots,
            kr=keepRange,
            kep=keepEndPoints,
            kt=keepTangents
        )


    @short(
        matchCurve='mc',
        rebuildType='rt',
        degree='d',
        tolerance='tol',
        smooth='sm',
        endKnots='end',
        keepRange='kr',
        keepControlPoints='kcp',
        keepEndPoints='kep',
        keepTangents='kt',
        spans='s'
    )
    def rebuild(
            self,
            rebuildType='Uniform',
            spans=None,
            degree=None,
            tolerance=0.01,
            smooth=-3,
            endKnots='Multiple end knots',
            keepRange='Original',
            keepControlPoints=False,
            keepEndPoints=True,
            keepTangents=False,
            matchCurve=None
    ):
        """
        :param rebuildType/rt: An enum index or label:

            - 0: 'Uniform' (the default)
            - 1: 'Reduce Spans'
            - 2: 'Match Knots'
            - 3: 'No Mults'
            - 4: 'Curvature'
            - 5: 'End Conditions'
            - 6: 'Clean'
        :type rebuildType/rt: int, str
        :param spans/s: the number of spans to build to; defaults to this
            curve's (current) number of spans if omitted
        :type spans/s: int, :class:`~paya.runtime.plugs.Math1D`
        :param int degree/d: the degree to build to; defaults to this curve's
            (current) degree if omitted
        :param float tolerance/tol: the fit tolerance; defaults to 0.01
        :param float smooth/sm: the 'smoothing' factor; defaults to -3.0
        :param endKnots/end: An enum index or label:

            - 0: 'Non Multiple end knots'
            - 1: 'Multiple end knots' (the default)
        :type endKnots: int, str
        :param keepRange/kr: An enum index or label:

            - 0: '0 to 1'
            - 1: 'Original' (the default)
            - 2: '0 to #spans'
        :type keepRange/kr: int, str
        :param bool keepControlPoints/kcp: keep control points; defaults to
            False
        :param bool keepEndPoints/kep: keep end points; defaults to True
        :param bool keepTangents/kt: keep tangents; defaults to False
        :param matchCurve/mc: ignored if *rebuildType* is not 2 or 'Match Knots`;
            a NURBS curve attribute whose knots to match; defaults to None
        :type matchCurve/mc: None, str, :class:`~paya.runtime.plugs.NurbsCurve`
        :return: The rebuilt curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        fn = self.getShapeMFn()

        if degree is None:
            degree = fn.degree()

        if spans is None:
            spans = fn.numSpans()

        node = r.nodes.RebuildCurve.createNode()
        self >> node.attr('inputCurve')

        node.attr('rt').set(rebuildType)
        node.attr('d').set(degree)
        spans >> node.attr('s')
        node.attr('tol').set(tolerance)
        node.attr('sm').set(smooth)
        node.attr('end').set(endKnots)
        node.attr('kr').set(keepRange)
        node.attr('kcp').set(keepControlPoints)
        node.attr('kep').set(keepEndPoints)
        node.attr('kt').set(keepTangents)

        if matchCurve:
            matchCurve >> node.attr('mc')

        return node.attr('outputCurve')

    def cageRebuild(self):
        """
        :return: A linear curve with the same CVs as this one.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        return self.rebuild(degree=1, keepControlPoints=True)

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    Misc
    #---------------------------------------------------------------|

    @short(weight='w')
    def blend(self, otherCurve, weight=0.5):
        """
        Blends this curve output towards *otherCurve* via an ``avgCurves``
        node. You may get unexpected results if the curves don't match
        in terms of spans, degree etc.

        :param otherCurve: the curve to blend towards
        :type otherCurve: str, :class:`~paya.runtime.plugs.NurbsCurve`
        :param weight/w: the blend weight; the other curve will take over
            fully at 1.0; defaults to 0.5
        :type weight/w: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The blended curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.AvgCurves.createNode()
        node.attr('automaticWeight').set(False)
        node.attr('normalizeWeights').set(False)
        self >> node.attr('inputCurve1')
        otherCurve >> node.attr('inputCurve2')
        weight >> node.attr('weight2')
        (1-node.attr('weight2')) >> node.attr('weight1')

        return node.attr('outputCurve')

    @short(
        atStart='ats',
        vector='v',
        linear='lin',
        extrapolate='ext',
        circular='cir',
        multipleKnots='mul'
    )
    def setLength(
            self,
            targetLength,
            atStart=False,
            vector=None,
            linear=None,
            circular=None,
            extrapolate=None,
            multipleKnots=True
    ):
        """
        Uses gated retractions and extensions to force the length of this
        curve.

        :param targetLength: the target length
        :type targetLength: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool atStart/ats: anchor the curve at the end rather than the
            start; defaults to False
        :param vector: a vector along which to extend; this is recommended for
            spine setups where tangency should be more tightly controlled; if
            this is omitted, the *linear / circular / extrapolate* modes will
            be used instead
        :type vector: None, tuple, list, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool circular/cir: ignored if *vector* was provided; use the
            'circular' mode of the ``extendCurve`` node; defaults to False
        :param bool linear/lin: ignored if *vector* was provided;
            use the 'linear' mode of the ``extendCurve`` node; defaults to
            False
        :param bool extrapolate/ext: ignored if *vector* was provided;
            use the 'extrapolate' mode of the ``extendCurve`` node; defaults
            to True
        :param bool multipleKnots: keep multiple knots; defaults to True
        :return:
        """
        baseLength = self.length()

        retractLength = baseLength-targetLength
        retractLength = retractLength.minClamp(0.0)

        extendLength = targetLength-baseLength
        extendLength = extendLength.minClamp(0.0)

        if vector is None:
            extension = self.extendByLength(
                extendLength,
                cir=circular, lin=linear, ext=extrapolate,
                mul=multipleKnots,
                ats=atStart
            )

        else:
            vector = _mo.info(vector)[0]
            vector = vector.normal() * extendLength

            extension = self.extendByVector(
                vector,
                ats=atStart,
                mul=multipleKnots,
                seg=True
            )

        retraction = self.retract(retractLength, ats=atStart)

        return baseLength.ge(targetLength).ifElse(retraction, extension)