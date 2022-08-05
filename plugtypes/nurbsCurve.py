from warnings import warn

import maya.OpenMaya as om
import paya.lib.mathops as _mo
import paya.lib.plugops as _po
import paya.lib.nurbsutil as _nu
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #-------------------------------------------------------|
    #-------------------------------------------------------|    Constructors
    #-------------------------------------------------------|

    @classmethod
    @short(
        radius='r',
        directionVector='dv',
        toggleArc='tac',
        sections='s',
        degree='d'
    )
    def createArc(
            cls,
            *points,
            directionVector=None,
            radius=1.0,
            toggleArc=False,
            sections=8,
            degree=3,
            guard=None
    ):
        """
        :param points: two or three points, packed or unpacked
        :type points: tuple, list, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.data.Vector`
        :param directionVector/dv:
            on two-point arcs this defaults to [0, 0, 1] (Z) and defines
            the arc's 'normal';
            on three point arcs it must be provided explicitly if 'guard'
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
        :param bool guard: for three-point arcs only: prevent the arc
            from disappearing with an error when the input points are
            collinear; defaults to True if *directionVector* was provided,
            otherwise False.
        :return: An output for a circular arc.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        points = _mo.expandVectorArgs(*points)

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
            if guard is None:
                if directionVector is None:
                    guard = False

                else:
                    guard = True

            elif guard and directionVector is None:
                raise ValueError(
                    "The direction vector is required for three"+
                    "-point arcs if 'guard' has been "+
                    "requested."
                )

            node = r.nodes.MakeThreePointCircularArc.createNode()
            points[0] >> node.attr('point1')
            points[1] >> node.attr('point2')
            points[2] >> node.attr('point3')
            sections >> node.attr('sections')
            degree >> node.attr('degree')

            if guard:
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

    #-------------------------------------------------------|
    #-------------------------------------------------------|    Sampling
    #-------------------------------------------------------|

    #--------------------------------------------------|    Curve-level

    @short(parametric='par', uniform='uni')
    def _resolveNumberOrValues(self,
                               numberOrValues, parametric=False,
                               uniform=False):
        """
        Utility method. If *numberOrValues* is a tuple or list, it's passed-
        through as-is. If it's a number:

        -   If *parametric*:

            -   If *uniform*, return a list of (umin -> umax) values
                spaced by length

            -   Otherwise, return a list of (umin -> umax) values in
                parametric space (there will be bunching)

        -   Otherwise, return a list of 0 -> 1 fractions.
        """
        if isinstance(numberOrValues, (tuple, list)):
            return numberOrValues

        if parametric:
            if uniform:
                fractions = _mo.floatRange(0, 1, numberOrValues)
                mfn = self.getShapeMFn()
                length = mfn.length()

                values = [mfn.findParamFromLength(
                    length * f) for f in fractions]

            else:
                umin, umax = self.getKnotDomain(p=False)
                values = _mo.floatRange(umin, umax, numberOrValues)

        else:
            values = _mo.floatRange(0, 1, numberOrValues)

        return values

    @short(reuse='re')
    def info(self, reuse=True):
        """
        :param bool reuse/re: where available, retrieve an already-connected
            node; defaults to True
        :return: A ``curveInfo`` node configured for this curve output.
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
        :return: The length of this curve.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.info(re=True).attr('arcLength')

    def motionPath(self, **config):
        """
        Creates a ``motionPath`` node and connects it to this curve. All other
        configuration is performed via *\*\*config*.

        :param \*\*config: a *source: plug* mapping to configure the node's
            attributes; sources can be plugs or values
        :return: The ``motionPath`` node.
        :rtype: :class:`~paya.runtime.nodes.MotionPath`
        """
        node = r.nodes.MotionPath.createNode()
        self >> node.attr('geometryPath')

        for k, v in config.items():
            v >> node.attr(k)

        return node

    #--------------------------------------------------|    Get info bundles

    @short(reuse='re')
    def initNearestPointOnCurve(self, point, reuse=True):
        """
        Initialises a ``nearestPointOnCurve`` node.

        :param point: the reference point
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool reuse/re: where available, retrieve any already-connected
            node with the same configuration; defaults to True
        :return: The ``nearestPointOnCurve`` node.
        :rtype: :class:`~paya.runtime.nodes.NearestPointOnCurve`
        """
        point, pointDim, pointIsPlug = _mo.info(point)

        if reuse:
            existingNodes = self.outputs(type='nearestPointOnCurve')

            for existingNode in existingNodes:
                pointOnNode = existingNode.attr('inPosition')
                pointOnNodeInputs = pointOnNode.inputs(plugs=True)

                if pointIsPlug and pointOnNodeInputs:
                    if point == pointOnNodeInputs[0]:
                        return existingNode

                elif (not pointIsPlug) and (not pointOnNodeInputs):
                    if point.isEquivalent(pointOnNode.get()):
                        return existingNode

        node = r.nodes.NearestPointOnCurve.createNode()
        self >> node.attr('inputCurve')
        node.attr('inPosition').put(point, p=pointIsPlug)

        return node

    @short(fractionMode='fr', uValue='u')
    def motionPathAtParam(self, param, **config):
        """
        Creates a ``motionPath`` and hooks it up to the specified parameter.
        All other configuration is performed via \*\*config*. Flags *uValue*
        and *fractionMode* will always be overriden.

        :param param: the parameter at which to create the ``motionPath`` node
        :rtype param: float, :class:`~paya.runtime.plugs.Math1D`
        :param \*\*config: a *source: plug* mapping to configure the node's
            attributes; sources can be plugs or values
        :return: The ``motionPath`` node.
        :rtype: :class:`~paya.runtime.nodes.MotionPath`
        """
        config['uValue'] = param
        config['fractionMode'] = False

        return self.motionPath(**config)

    @short(fractionMode='fr', uValue='u')
    def motionPathAtFraction(self, fraction, **config):
        """
        Creates a ``motionPath`` and hooks it up to the specified fraction.
        All other configuration is performed via \*\*config*. Flags *uValue*
        and *fractionMode* will always be overriden.

        :param fraction: the fraction at which to create the ``motionPath``
            node
        :rtype fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param \*\*config: a *source: plug* mapping to configure the node's
            attributes; sources can be plugs or values
        :return: The ``motionPath`` node.
        :rtype: :class:`~paya.runtime.nodes.MotionPath`
        """
        config['uValue'] = fraction
        config['fractionMode'] = True

        return self.motionPath(**config)

    @short(reuse='re', turnOnPercentage='top')
    def infoAtParam(self, param, reuse=True, turnOnPercentage=False):
        """
        Configures a ``pointOnCurveInfo`` node at the specified parameter.

        :param param: the parameter to sample
        :rtype param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool reuse/re: where available, retrieve an already-connected
            node with the same configuration; defaults to True
        :param bool turnOnPercentage/top: sets the 'turnOnPercentage'
            attribute on the node; defaults to ``False``
        :return: The ``pointOnCurveInfo`` node.
        :rtype: :class:`~paya.runtime.nodes.PointOnCurveInfo`
        """
        param, paramDim, paramIsPlug = _mo.info(param)
        turnOnPercentage, topDim, topIsPlug = _mo.info(turnOnPercentage)

        if reuse:
            existingNodes = self.outputs(type='pointOnCurveInfo')

            for existingNode in existingNodes:
                paramOnNode = existingNode.attr('parameter')
                paramOnNodeInputs = paramOnNode.inputs(plugs=True)

                if paramIsPlug and paramOnNodeInputs:
                    paramsMatch = param == paramOnNodeInputs[0]

                elif (not paramIsPlug) and (not paramOnNodeInputs):
                    paramsMatch = param == paramOnNode.get()

                else:
                    paramsMatch = False

                if paramsMatch:
                    topOnNode = existingNode.attr('turnOnPercentage')
                    topOnNodeInputs = topOnNode.inputs(plugs=True)

                    if topIsPlug and topOnNodeInputs:
                        if turnOnPercentage == topOnNodeInputs[0]:
                            return existingNode

                    elif (not topIsPlug) and (not topOnNodeInputs):
                        if turnOnPercentage == topOnNode.get():
                            return existingNode

        node = r.nodes.PointOnCurveInfo.createNode()
        self >> node.attr('inputCurve')
        node.attr('parameter').put(param, p=paramIsPlug)
        node.attr('turnOnPercentage').put(turnOnPercentage, p=topIsPlug)

        return node

    #--------------------------------------------------|    Get points

    def getCVs(self):
        """
        :return: The ``controlPoints`` info array for this curve. In Paya this
            can be iterated-over, or flattened into a list with
            :class:`list() <list>`.
        :rtype: [:class:`~paya.runtime.plugs.Vector`]
        """
        out = self.info().attr('controlPoints')
        out.evaluate()
        return out

    def pointAtCV(self, cvIndex):
        """
        :param int cvIndex: the index of the control vertex to sample
        :return: The position of the specified control vertex.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.getCVs()[cvIndex]

    def pointAtParam(self, param):
        """
        :alias: ``getPointAtParam``
        :param param: the parameter to sample
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the specified parameter.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        node = self.infoAtParam(param)
        return node.attr('position')

    getPointAtParam = pointAtParam

    def pointAtFraction(self, fraction):
        """
        :param param: the fraction to sample
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the specified fraction.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.motionPathAtFraction(fraction).attr('allCoordinates')

    def pointAtLength(self, length):
        """
        :param param: the length to sample
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :return: A point at the specified length.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.pointAtFraction(length / self.length())

    def closestPoint(self, refPoint):
        """
        :param refPoint: the reference point
        :type refPoint: tuple, list, str, :class:`~paya.runtime.plugs.Vector`
        :return: The closest point on this curve to *refPoint*.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.initNearestPointOnCurve(refPoint).attr('position')

    @short(parametric='par', uniform='uni')
    def distributePoints(self, numberOrValues, parametric=False, uniform=False):
        """
        :param numberOrValues: this can be either a single scalar or
            a list of scalars, indicating how many points to generate
            or at which fractions or parameters to generate them, respectively
        :type numberOrValues: int, :class:`~paya.runtime.plugs.Math1D`,
            [int, :class:`~paya.runtime.plugs.Math1D`]
        :param bool parametric/par: generate points at parameters, not
            fractions; defaults to False
        :param bool uniform/uni: if *parametric* is ``True`` and
            *numberOrValues* is a number, generate parameters initially
            distributed by length, not parametric space; defaults to
            False
        :return: Points, distributed along this curve.
        :rtype: [:class:`~paya.runtime.plugs.Vector`]
        """
        values = self._resolveNumberOrValues(numberOrValues,
                                             parametric=parametric,
                                             uniform=uniform)

        if parametric:
            meth = self.pointAtParam

        else:
            meth = self.pointAtFraction

        for i, value in enumerate(values):
            with r.Name(i+1, padding=3):
                out.append(meth(value))

        return out

    #--------------------------------------------------|    Get params

    @short(plug='p')
    def getKnotDomain(self, plug=True):
        """
        :param bool plug/p: return plugs, not values; defaults to True
        :param bool plug/p: indicate that one or more arguments are
            passed as arguments, and therefore a plug output is required,
            or force a plug output in every case; defaults to False
        :return: The min and max U parameters on this curve.
        :rtype: (:class:`float` | :class:`~paya.runtime.plugs.Math1D`,
            :class:`float` | :class:`~paya.runtime.plugs.Math1D`)
        """
        if plug:
            return self.paramAtLength(0.0), self.paramAtFraction(1.0)

        mfn = self.getShapeMFn()
        minPtr = om.MScriptUtil().asDoublePtr()
        maxPtr = om.MScriptUtil().asDoublePtr()

        result = mfn.getKnotDomain(minPtr, maxPtr)

        return (
            om.MScriptUtil(minPtr).asDouble(),
            om.MScriptUtil(maxPtr).asDouble(),
        )

    @short(plug='p')
    def paramAtStart(self, plug=True):
        """
        :param bool plug/p: return plugs, not values; defaults to True
        :return: The parameter at the start of this curve.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.paramAtLength(0.0)

        return self.getKnotDomain(p=False)[0]

    @short(plug='p')
    def paramAtEnd(self, plug=True):
        """
        :param bool plug/p: return plugs, not values; defaults to True
        :return: The parameter at the end of this curve.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.paramAtFraction(1.0)

        return self.getKnotDomain(p=False)[1]

    def paramAtPoint(self, point):
        """
        This is a 'forgiving' implementation, and uses the closest point.

        :alias: ``closestParam`` ``getParamAtPoint``
        :param point: the reference point
        :type point: tuple, list, str, :class:`~paya.runtime.plugs.Vector`,
            :class:`~paya.runtime.data.Point`
        :return: The nearest parameter to the reference point.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.initNearestPointOnCurve(point).attr('parameter')

    closestParam = getParamAtPoint = paramAtPoint

    @short(plug='p')
    def paramAtFraction(self, fraction, plug=True):
        """
        :param fraction: the fraction to sample
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: indicate that one or more arguments are
            passed as arguments, and therefore a plug output is required,
            or force a plug output in every case; defaults to False
        :return: The parameter at the given fraction.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            point = self.pointAtFraction(fraction)
            out = self.paramAtPoint(point)
        else:
            mfn = self.getShapeMFn()
            length = mfn.length()
            targetLength = length * fraction
            out = mfn.findParamFromLength(targetLength)

        return out

    def paramAtLength(self, length):
        """
        :alias: ``findParamFromLength``
        :param length: the length at which to sample a parameter
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The parameter at the given length.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        fraction = length / self.length()
        return self.paramAtFraction(fraction)

    findParamFromLength = paramAtLength

    @short(parametric='par', uniform='uni')
    def distributeParams(self, numberOrValues,
                         parametric=False, uniform=False):
        """
        If *parametric* is True, the return will be values, not plugs.

        :param numberOrValues: this can be either a single scalar or
            a list of scalars, indicating how many parameters to generate
            or at which fractions or parameters to generate them, respectively
        :type numberOrValues: int, :class:`~paya.runtime.plugs.Math1D`,
            [int, :class:`~paya.runtime.plugs.Math1D`]
        :param bool parametric/par: don't use length fractions; defaults to
            False
        :param bool uniform/uni: if *parametric* is ``True`` and
            *numberOrValues* is a number, generate parameters initially
            distributed by length, not parametric space; defaults to
            False
        :return: Parameters, distributed along this curve.
        :rtype: [float, :class:`~paya.runtime.plugs.Math1D`]
        """
        values = self._resolveNumberOrValues(numberOrValues,
                                             parametric=parametric,
                                             uniform=uniform)

        if parametric:
            return values

        out = []

        for i, value in enumerate(values):
            with r.Name(i+1, padding=3):
                out.append(self.paramAtFraction(value))

        return out
    #--------------------------------------------------|    Get lengths

    def lengthAtFraction(self, fraction):
        """
        :param fraction: the fraction to inspect
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The curve length at the specified fraction.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.length() * fraction

    def lengthAtParam(self, param):
        """
        :alias: ``findLengthFromParam``
        :param param: the parameter to inspect
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The curve length at the specified parameter.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.detach(param, select=0)[0].length()

    findLengthFromParam = lengthAtParam

    def lengthAtPoint(self, point):
        """
        This is a 'forgiving' implementation, and uses the closest point.

        :param point: the point to inspect
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The curve length at the specified point.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        param = self.paramAtPoint(point)
        return self.lengthAtParam(param)

    #--------------------------------------------------|    Get fractions

    def distributeFractions(self, number):
        """
        Convenience method. Equivalent to
        :meth:`floatRange(0, 1, number) <paya.lib.mathops.floatRange>`.

        :param int number: the number of fractions to generate
        :return: A uniform list of fractions.
        :rtype: [float]
        """
        return _mo.floatRange(0, 1, number)

    def fractionAtPoint(self, point):
        """
        This is a 'forgiving' implementation, and uses the closest point.

        :param point: the point at which to sample a fraction
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The length fraction at the specified point.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.lengthAtPoint(point) / self.length()

    def fractionAtParam(self, param):
        """
        :param param: the parameter at which to sample a fraction
        :type param: float, str, :class:`~paya.runtime.plugs.Math1D`
        :return: The length fraction at the specified parameter.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return self.lengthAtParam(param) / self.length()

    def fractionAtLength(self, length):
        """
        :param length: the length at which to sample a fraction
        :type length: float, str, :class:`~paya.runtime.plugs.Math1D`
        :return: The length fraction at the specified length.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        return length / self.length()

    #--------------------------------------------------|    Get normals

    @short(normalize='nr')
    def normal(self, param, normalize=False):
        """
        .. note::

            Even though the Maya docs for the API method state that the vector
            is normalized, in practice this is only the case when *space* is
            'world'. Since spaces are irrelevant within the plug context, this
            method defaults to a non-normalized output.

        :alias: ``normalAtParam``
        :param param: the parameter at which to sample the normal
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: return the normalized normal;
            defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.infoAtParam(param).attr(
            'normalizedNormal' if normalize else 'normal'
        )

    normalAtParam = normal

    @short(normalize='nr')
    def normalAtFraction(self, fraction, normalize=False):
        """
        :param fraction: the fraction at which to sample the normal
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: return the normalized normal;
            defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        mp = self.motionPathAtFraction(fraction)
        mp.configFollow('y', 'x')

        if normalize:
            return mp.normalizedNormal

        return mp.normal

    @short(normalize='nr')
    def normalAtLength(self, length, normalize=False):
        """
        :param length: the length at which to sample the normal
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: return the normalized normal;
            defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        fraction = length / self.length()
        return self.normalAtFraction(fraction, nr=normalize)

    @short(normalize='nr')
    def normalAtPoint(self, point, normalize=False):
        """
        :param point: the point at which to sample the normal
        :type point: tuple, list, str,
            :class:`~paya.runtime.plugs.Vector`,
            :class:`~paya.runtime.data.Point`
        :param bool normalize/nr: return the normalized normal;
            defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtPoint(point)
        return self.normalAtParam(param, nr=normalize)

    #--------------------------------------------------|    Get tangents

    @short(normalize='nr')
    def tangent(self, param, normalize=False):
        """
        .. note::

            Even though the Maya docs for the API method state that the vector
            is normalized, in practice this is only the case when *space* is
            'world'. Since spaces are irrelevant within the plug context, this
            method defaults to a non-normalized output.

        :alias: ``tangentAtParam``
        :param param: the parameter at which to sample the tangent
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: return the normalized tangent;
            defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.infoAtParam(param).attr(
            'normalizedTangent' if normalize else 'tangent'
        )

    tangentAtParam = tangent

    @short(normalize='nr')
    def tangentAtFraction(self, fraction, normalize=False):
        """
        :param fraction: the fraction at which to sample the tangent
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: normalize the output vector; defaults to
            False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        mp = self.motionPathAtFraction(fraction)
        mp.configFollow('y', 'x')
        return getattr(mp, 'normalizedTangent' if normalize else 'tangent')

    @short(normalize='nr')
    def tangentAtPoint(self, point, normalize=False):
        """
        :param point: the point at which to sample the normals
        :type point: list, tuple, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool normalize/nr: normalize the output vector; defaults to
            False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtPoint(point)
        return self.tangentAtParam(param, nr=normalize)

    @short(normalize='nr')
    def tangentAtLength(self, length, normalize=False):
        """
        :param length: the length at which to sample the tangent
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: normalize the output vector; defaults to
            False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        fraction = length / self.length()
        return self.tangentAtFraction(fraction, nr=normalize)

    #--------------------------------------------------|    Get up vectors

    @short(interpolation='i',
           resolution='res',
           fromEnd='fe',
           asRemapValue='arv')
    def solveUpVectorsByParallelTransport(self,
                                          normal,
                                          resolution=9,
                                          fromEnd=False,
                                          asRemapValue=False,
                                          interpolation='Linear'
                                          ):
        """
        :param normal: the starting normal
        :type normal: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param int resolution/res: the number of solutions to perform;
            higher values improve accuracy at the cost of performance;
            defaults to 9
        :param bool fromEnd/fe: indicate that *normal* is at the end of the
            curve, and solve from there instead; defaults to False
        :param bool asRemapValue/arv: return an already-configured
            `remapValue <paya.runtime.nodes.RemapValue>` node; defaults to
            False
        :param interpolation/i: an integer plug or value defining which type
            of interpolation should be applied to any subsequently sampled
            values; this tallies with the color interpolation enums on a
            :class:`remapValue <paya.runtime.nodes.RemapValue>` node, which
            are:

            - 0 ('None', you wouldn't usually want this)
            - 1 ('Linear') (the default)
            - 2 ('Smooth')
            - 3 ('Spline')

        :type interpolation/i: int, :class:`~paya.runtime.plugs.Math1D`
        :return: If *asRemapValue*, a configured
            `remapValue <paya.runtime.nodes.RemapValue>` node; otherwise,
            zipped pairs of *parameter: vector*
        :rtype: :class:`~paya.runtime.nodes.RemapValue` |
            [(:class:`~paya.runtime.plugs.Math1D`,
            :class:`~paya.runtime.plugs.Vector`)]
        """

        umin, umax = self.getKnotDomain(p=False)

        # Get params, but initially uniform
        fractions = _mo.floatRange(0, 1, resolution)
        params = [self.paramAtFraction(f, p=False) for f in fractions]

        tangents = [self.tangentAtParam(p) for p in params]

        # Solve
        upVectors = _mo.parallelTransport(normal, tangents, fe=fromEnd)
        out = list(zip(params, upVectors))

        if asRemapValue:
            out = self.getRemapValueFromVectorKeys(out, i=interpolation)

        return out

    @short(interpolation='i')
    def getRemapValueFromVectorKeys(self, keymap, interpolation='Linear'):
        """
        :param keymap: zipped pairs of *param, up vector*, indicating known
            vectors between which to interpolate
        :param interpolation/i: an integer plug or value defining which type
            of interpolation should be applied to any subsequently sampled
            values; this tallies with the color interpolation enums on a
            :class:`remapValue <paya.runtime.nodes.RemapValue>` node, which
            are:

            - 0 ('None', you wouldn't usually want this)
            - 1 ('Linear') (the default)
            - 2 ('Smooth')
            - 3 ('Spline')

        :return: A :class:`remapValue <paya.runtime.nodes.RemapValue>` node,
            with a ``color`` attribute configured using *param, vector* pairs
            returned by a method such as
            :meth:`solveUpVectorsByParallelTransport`.
        :rtype: :class:`~paya.runtime.nodes.RemapValue`
        """
        rv = r.nodes.RemapValue.createNode()
        rv.setColors(keymap, i=interpolation)
        return rv

    @short(interpolation='i',
           asRemapValue='arv')
    def solveUpVectorsKeyedLinear(self,
                                  paramVectorKeys,
                                  interpolation='Linear',
                                  asRemapValue=False):
        """
        This mostly just passes *paramVectorKeys* through, since there's
        no 'solving' to be done.

        :param keymap: zipped pairs of *param, up vector*, indicating known
            vectors between which to interpolate
        :param bool asRemapValue/arv: pass the output along to
            :meth:`getRemapValueFromVectorKeys` and return the node; defaults
            to False
        :param interpolation/i: passed along to
            :meth:`getRemapValueFromVectorKeys` if *asRemapValue* was
            requested
        :return: If *asRemapValue*, the
            :class:`remapValue <paya.runtime.nodes.RemapValue>` node;
            otherwise, zipped *param, up vector* pairs
        :rtype: [:class:`int` | :class:`~paya.runtime.plugs.Math1D`,
             :class:`~paya.runtime.data.Vector` |
             :class:`~paya.runtime.plugs.Vector`]
        """
        out = list(paramVectorKeys)

        if len(out) < 2:
            raise ValueError("Need at least two keys (start / end).")

        if asRemapValue:
            out = self.getRemapValueFromVectorKeys(out, i=interpolation)

        return out

    @short(interpolation='i',
           resolution='res',
           unwindSwitch='uws',
           asRemapValue='arv'
           )
    def solveUpVectorsKeyedParallelTransport(self,
                                             paramVectorKeys,
                                             interpolation='Linear',
                                             resolution=9,
                                             unwindSwitch=0,
                                             asRemapValue=False):
        """
        Generates bidirectional parallel transport solutions between
        known up vectors, and blends between them by angle.

        :param paramVectorKeys: zipped pairs of *param, up vector*,
            indicating known vectors between which to interpolate
        :param int resolution/res: the number of parallel-transport solutions
            to generate across the curve; higher values improve accuracy
            at the cost of performance; defaults to 9
        :param unwindSwitch/uws: an integer, or list of integers, to control
            how the parallel transport solutions will be blended:

            - 0 (shortest, the default)
            - 1 (positive)
            - 2 (negative)

            If this is a list, it should be one less than the number
            of *param, vector* pairs passed through *paramVectorKeys*.

        :param bool asRemapValue/arv: pass the output along to
            :meth:`getRemapValueFromVectorKeys` and return the node; defaults
            to False
        :param interpolation/i: passed along to
            :meth:`getRemapValueFromVectorKeys` if *asRemapValue* was
            requested
        :return: If *asRemapValue*, the
            :class:`remapValue <paya.runtime.nodes.RemapValue>` node;
            otherwise, zipped *param, up vector* pairs
        :rtype: [:class:`int` | :class:`~paya.runtime.plugs.Math1D`,
             :class:`~paya.runtime.data.Vector` |
             :class:`~paya.runtime.plugs.Vector`]
        """

        paramVectorKeys = list(paramVectorKeys)
        numKeys = len(paramVectorKeys)

        if numKeys < 2:
            raise ValueError("Need at least two keys (start / end).")

        numSegments = numKeys-1

        if isinstance(unwindSwitch, (tuple, list)):
            if len(unwindSwitch) is not numSegments:
                raise ValueError(
                    "If 'unwindSwitch' is a list, it "+
                    "should be of length "+
                    "paramUpVectorKeys-1.")

            unwindSwitches = unwindSwitch

        else:
            unwindSwitches = [unwindSwitch] * numSegments

        segmentResolutions = _mo._resolvePerSegResForBlendedParallelTransport(
            numSegments, resolution
        )

        params, normals = zip(*paramVectorKeys)

        # Init per-segment info bundles
        infoPacks = []

        for i, param, normal, segmentResolution in zip(
            range(numSegments),
            params[:-1],
            normals[:-1],
            segmentResolutions
        ):
            infoPack = {
                'startParam': param,
                'nextParam': params[i+1],
                'startNormal': normals[i],
                'endNormal': normals[i+1],
                'unwindSwitch': unwindSwitches[i],
                'tangentSampleParams': _mo.floatRange(
                    param, params[i+1],
                    segmentResolution)
            }

            infoPacks.append(infoPack)

        # Add tangent samples to each bundle, taking care not to
        # replicate overlapping samples
        for i, infoPack in enumerate(infoPacks):
            with r.Name('segment', i+1, padding=2):
                inner = i > 0
                tangentSampleParams = infoPack['tangentSampleParams'][:]

                if inner:
                    del(tangentSampleParams[i])

                infoPack['tangents'] = tangents = []

                for x, tangentSampleParam in enumerate(
                        tangentSampleParams):
                    with r.Name('tangent', x+1):
                        tangents.append(
                            self.tangentAtParam(tangentSampleParam)
                        )

                if inner:
                    tangents.insert(0, infoPacks[i-1]['tangents'][-1])

        # Run the parallel transport per-segment
        for i, infoPack in enumerate(infoPacks):
            with r.Name('segment', i+1, padding=2):
                infoPack['normals'] = _mo.blendBetweenCurveNormals(
                    infoPack['startNormal'],
                    infoPack['endNormal'],
                    infoPack['tangents'],
                    uws=infoPack['unwindSwitch']
                )

        # Get flat params, normals for the whole system
        outParams = []
        outNormals = []

        for i, infoPack in enumerate(infoPacks):
            lastIndex = len(infoPack['tangents'])

            if i < numSegments-1:
                lastIndex -= 1

            last = i == numSegments-1

            theseParams = infoPack['tangentSampleParams'][:lastIndex]
            theseNormals = infoPack['normals'][:lastIndex]

            outParams += theseParams
            outNormals += theseNormals

        out = list(zip(outParams, outNormals))

        if asRemapValue:
            out = self.getRemapValueFromVectorKeys(out, i=interpolation)

        return out

    #--------------------------------------------------|    Get matrices

    @short(upVector='upv',
           upObject='uo',
           aimCurve='aic',
           closestPoint='cp',
           globalScale='gs',
           squashStretch='ss')
    def matrixAtParam(self,
                      param,
                      primaryAxis,
                      secondaryAxis,

                      upVector=None,
                      upObject=None,
                      aimCurve=None,
                      closestPoint=True,

                      globalScale=None,
                      squashStretch=False):
        """
        If no up vector information is provided, the curve normal will be used
        (not usually advisable).

        :param param: the parameter at which to sample the matrix
        :type param: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param str primaryAxis: the primary (aim / tangent) axis for the matrix,
            e.g. '-y'
        :param str secondaryAxis: the secondary (up / normal) axis for the
            matrix, e.g. 'x'
        :param upVector/upv: if this is provided then it will be used
            directly; if *upObject* has also been provided, this vector
            will be multiplied by the object's matrix; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param upObject/uo: if *aimUpVector* has been provided, it will
            be multiplied by this object's world matrix (similar to
            'Object Rotation Up' on ``motionPath``); otherwise, this object
            will be used as a single aim interest (similar to 'Object Up' on
            ``motionPath``); defaults to None
        :type upObject/uo: None, str, :class:``paya.runtime.nodes.Transform`
        :param aimCurve/aic: a curve to pull aiming interest points from,
            similar to a ``curveWarp`` setup; defaults to None
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity,
            not matched parameter; defaults to True
        :param globalScale/gs: a base scaling factor; this must be a plug;
            values are ignored; defaults to None
        :type globalScale/gs: None, :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow tangent scaling; defaults to False
        :raises ValueError: misconfigured argument(s)
        :return: A matrix at the specified parameter.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        #---------------------------------------|    Prep

        if upVector and aimCurve:
            raise ValueError("Unsupported combo: up vector and aim curve")

        if upObject and aimCurve:
            raise ValueError("Unsupported combo: up object and aim curve")

        if upVector:
            upVector = _mo.conformVectorArg(upVector)

        if upObject:
            upObject = r.PyNode(upObject)

        if aimCurve:
            aimCurve = _po.asGeoPlug(aimCurve)

        if globalScale is None:
            gsIsPlug = False
            globalScale = 1.0

        else:
            globalScale, gsDim, gsIsPlug = _mo.info(globalScale)

            if gsIsPlug:
                globalScale = globalScale.normal()

            else:
                # Ignore any non-plug values, since scale will be
                # normalized
                globalScale = 1.0
                gsIsPlug = False

        info = self.infoAtParam(param)
        position = info.attr('position')
        tangent = info.attr('tangent')

        #---------------------------------------|    Resolve up vector

        if upVector:
            if upObject:
                upVector *= upObject.attr('wm')

        elif aimCurve:
            if closestPoint:
                interest = aimCurve.closestPoint(position)

            else:
                interest = aimCurve.pointAtParam(param)

            upVector = interest-position

        elif upObject:
            upVector = upObject.getWorldPosition(p=True)-position

        else:
            upVector = info.attr('normal')

        #---------------------------------------|    Build matrix

        matrix = r.createMatrix(
            primaryAxis, tangent,
            secondaryAxis, upVector,
            t=position
        ).pk(t=True, r=True)

        if gsIsPlug or squashStretch:
            factors = [globalScale] * 3

            if squashStretch:
                tanScale = tangent.length().normal()
                tanIndex = 'xyz'.index(primaryAxis.strip('-'))
                factors[tanIndex] = tanScale

            smtx = r.createScaleMatrix(*factors)
            matrix = smtx * matrix

        return matrix

    @short(upVector='upv',
           upObject='uo',
           aimCurve='aic',
           closestPoint='cp',
           globalScale='gs',
           squashStretch='ss')
    def matrixAtFraction(self,
                      fraction,
                      primaryAxis,
                      secondaryAxis,

                      upVector=None,
                      upObject=None,
                      aimCurve=None,
                      closestPoint=True,

                      globalScale=None,
                      squashStretch=False):
        """
        Unlike :meth:`matrixAtParam`, builds from a ``motionPath`` instead
        a ``pointOnCurveInfo`` node, although any performance improvement
        will be negated if an aim curve is used with *closestPoint* set to
        ``False``. If no up vector arguments are provided, the curve normal
        will be used (not usually advisable).

        :param fraction: the fraction at which to sample the matrix
        :type fraction: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param str primaryAxis: the primary (aim / tangent) axis for the matrix,
            e.g. '-y'
        :param str secondaryAxis: the secondary (up / normal) axis for the
            matrix, e.g. 'x'
        :param upVector/upv: if this is provided then it will be used
            directly; if *upObject* has also been provided, this vector
            will be multiplied by the object's matrix; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param upObject/uo: if *aimUpVector* has been provided, it will
            be multiplied by this object's world matrix (similar to
            'Object Rotation Up' on ``motionPath``); otherwise, this object
            will be used as a single aim interest (similar to 'Object Up' on
            ``motionPath``); defaults to None
        :type upObject/uo: None, str, :class:``paya.runtime.nodes.Transform`
        :param aimCurve/aic: a curve to pull aiming interest points from,
            similar to a ``curveWarp`` setup; defaults to None
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity,
            not matched parameter; defaults to True
        :param globalScale/gs: a base scaling factor; this must be a plug;
            values are ignored; defaults to None
        :type globalScale/gs: None, :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow tangent scaling; defaults to False
        :raises ValueError: misconfigured argument(s)
        :return: A matrix at the specified fraction.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        #---------------------------------------|    Prep

        if upVector and aimCurve:
            raise ValueError("Unsupported combo: up vector and aim curve")

        if upObject and aimCurve:
            raise ValueError("Unsupported combo: up object and aim curve")

        if upVector:
            upVector = _mo.conformVectorArg(upVector)

        if upObject:
            upObject = r.PyNode(upObject)

        if aimCurve:
            aimCurve = _po.asGeoPlug(aimCurve)

        if globalScale is None:
            gsIsPlug = False
            globalScale = 1.0

        else:
            globalScale, gsDim, gsIsPlug = _mo.info(globalScale)

            if gsIsPlug:
                globalScale = globalScale.normal()

            else:
                # Ignore any non-plug values, since scale will be
                # normalized
                globalScale = 1.0
                gsIsPlug = False

        mp = self.motionPathAtFraction(fraction)
        position = mp.attr('allCoordinates')

        #---------------------------------------|    Resolve up vector

        mpKwargs = {}

        if upVector:
            mpKwargs['worldUpVector'] = upVector

            if upObject:
                mpKwargs['worldUpObject'] = upObject

        elif aimCurve:
            if closestPoint:
                interest = aimCurve.closestPoint(position)

            else:
                param = self.paramAtPoint(position)
                interest = aimCurve.pointAtParam(param)

            mpKwargs['worldUpVector'] = interest-position

        elif upObject:
            mpKwargs['worldUpObject'] = upObject

        mp.configFollow(primaryAxis, secondaryAxis, **mpKwargs)

        #---------------------------------------|    Build matrix

        orimtx = mp.attr('orientMatrix')
        tmtx = position.asTranslateMatrix()
        matrix = orimtx.pk(r=True) * tmtx

        if gsIsPlug or squashStretch:
            factors = [globalScale] * 3

            if squashStretch:
                tangent = orimtx.getAxis(primaryAxis)
                tanScale = tangent.length().normal()
                tanIndex = 'xyz'.index(primaryAxis.strip('-'))
                factors[tanIndex] = tanScale

            smtx = r.createScaleMatrix(*factors)
            matrix = smtx * matrix

        return matrix

    def matrixAtLength(self, length, *args, **kwargs):
        """
        Converts *length* to a fraction and defers to
        :meth:`matrixAtFraction`.
        """
        fraction = self.fractionAtLength(length)
        return self.matrixAtFraction(fraction, *args, **kwargs)

    def matrixAtPoint(self, point, *args, **kwargs):
        """
        Finds the closest parameter to *point* and defers to
        :meth:`matrixAtParam`.
        """
        param = self.paramAtPoint(point, *args, **kwargs)

    @r.nativeUnits
    @short(
        parametric='par',
        uniform='uni',

        upVector='upv',
        upObject='uo',
        aimCurve='aic',
        closestPoint='cp',

        globalScale='gs',
        squashStretch='ss',

        interpolation='i',
        parallelTransport='pt',
        unwindSwitch='uws',
        resolution='res'
    )
    def distributeMatrices(self,
                           numberOrValues,
                           primaryAxis,
                           secondaryAxis,

                           parametric=False,
                           uniform=False,

                           upVector=None,
                           upObject=None,
                           aimCurve=None,
                           closestPoint=True,

                           globalScale=None,
                           squashStretch=False,

                           interpolation='Linear',
                           parallelTransport=False,
                           unwindSwitch=0,
                           resolution=9
                           ):
        """
        :param numberOrValues: an integer indicating how many fractions
            (or parameters, if *parametric* is ``True``) to sample across
            the curve, or an explicit list of fractions or parameters
        :type paramOrValues: int,
            [int | str | :class:`~paya.runtime.plugs.Math1D`]
        :param str primaryAxis: the primary (aim / tangent) axis for the
            matrix, e.g. '-y'
        :param str secondaryAxis: the secondary (up / normal) axis for the
            matrix, e.g. 'x'
        :param bool parametric/par: if *numberOrValues* is a number, generate
            U values and not fractions; if it's a list, interpret its members
            as parameters and not fractions; defaults to False
        :param bool uniform/uni: if *numberOrValues* is a number, and *parametric*
            is ``True``, initialised parameter values should be distributed
            by length, not U space; defaults to False
        :param upVector/upv: this can be:

            -   a single up vector
            -   a list of up vectors (one per resolved sample point as
                indicated by *numberOrValues*)
            -   a list of pairs of *parameter, up vector*, indicating known
                up vectors between which to interpolate; note that the keys
                must always be parameters, even if *parametric* is ``False``
            -   None (defer to other up vector clues)

        :type upVector/uv:
            :class:`tuple`, :class:`list`, :class:`str`, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`,
            [:class:`tuple`, :class:`list`, :class:`str`, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`],
            [[float | :class:`~paya.runtime.plugs.Math1D`,
                :class:`tuple` | :class:`list` | :class:`str` |
                :class:`~paya.runtime.data.Vector`,
                :class:`~paya.runtime.plugs.Vector`]]
        :param upObject/uo: a single transform, or a list of transforms, used
            in the same way as in motion paths: if combined with *upVector*,
            creates an 'Object Rotation Up' setup; otherwise, works as an aim
            interest for the up vector; defaults to None
        :type upObject/uo: None, str, :class:`~paya.runtime.nodes.Transform`,
            [str, :class:`~paya.runtime.nodes.Transform`]
        :param aimCurve/aic: used to pull up vector interest points, similar
            to :class:`curveWarp <paya.runtime.nodes.CurveWarp`
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity, not
            matched parameter; defaults to True
        :param globalScale/gs: a baseline scaling factor; since output matrices
            are always normalized for scale, if this is not a plug it will
            effectively be replaced with 1.0; defaults to None
        :type globalScale/gs: None, int, :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow tangent scaling; defaults to False
        :param interpolation: an integer plug or value specifying which type
            of interpolation to use when *upVector* has been provided as
            *param, vector* pairs; tallies with the color interpolation enums
            on a :class:`remapValue <paya.runtime.nodes.RemapValue>` node, which
            are:

            - 0 ('None', you wouldn't usually want this)
            - 1 ('Linear') (the default)
            - 2 ('Smooth')
            - 3 ('Spline')

        :type interpolation/i: int, :class:`~paya.runtime.plugs.Math1D`
        :param bool parallelTransport/pt: if a single up vector hint is
            passed, either through *upVector* or *upObject*, propagate
            it across the curve using parallel transport; alternatively,
            if *upVector* was passed as *param, vector* keys, run
            parallel transport bidirectionally on each segment; defaults to
            False
        :param int resolution/res: the number of parallel transport solutions
            to perform; higher numbers improve accuracy at the cost of
            performance; defaults to 9
        :param unwindSwitch/uws: used if *upVector* was passed as *param,
            vector* pairs and *parallelTransport* was requested; an integer,
            or list of integers, to control how the parallel transport
            solutions will be blended:

            - 0 (shortest, the default)
            - 1 (positive)
            - 2 (negative)

            If this is a list, it should be one less than the number
            of *param, vector* pairs passed through *upVector*.
        :type unwindSwitch/uwd: int, :class:`~paya.runtime.plugs.Math1D`
        :return: The generated matrices.
        :rtype: [:class:`~paya.runtime.plugs.Matrix`]
        """

        #-------------------------------------|    Analyse args

        vals = self._resolveNumberOrValues(numberOrValues,
                                           parametric=parametric,
                                           uniform=uniform)
        number = len(vals)

        # Get info on upObject
        singleUpObject = False
        multiUpObjects = False

        if upObject:
            if hasattr(upObject, '__iter__') and not (
                    _po.isPyMELObject(upObject) or isinstance(upObject, str)):

                upObject = [r.PyNode(member) for member in upObject]
                multiUpObjects = True

            else:
                upObject = r.PyNode(upObject)
                singleUpObject = True

        # Get info on upVector
        singleUpVector = False
        multiUpVectors = False
        keyedUpVectors = False

        if upVector:
            if _mo.isVectorValueOrPlug(upVector):
                singleUpVector = True
                upVector = _mo.conformVectorArg(upVector)

            elif hasattr(upVector, '__iter__'): # iterable, but not a single vector
                members = list(upVector)
                upVector = members

                if all((_mo.isVectorValueOrPlug(
                        member) for member in members)):

                    if len(members) is not number:
                        raise ValueError("Wrong number of up vector members.")

                    multiUpVectors = True

                elif ((hasattr(member, '__iter__') \
                       and len(member) is 2 for member in members)):

                    if len(members) < 2:
                        raise ValueError("Need at least two vector keys (start / end).")

                    keyedUpVectors = True

                else:
                    raise ValueError(
                        "Couldn't interpret the 'upVector' argument.")

        #-------------------------------------|    Expand to dicts

        # One per call to matrixAt~

        basedict = {'globalScale': globalScale, 'squashStretch': squashStretch}
        kwdicts = []

        for i in range(number):
            kwdicts.append(basedict.copy())

        def distribute(key, vals):
            for kwdict, val in zip(kwdicts, vals):
                kwdict[key] = val

        def replicate(key, val):
            for kwdict in kwdicts:
                kwdict[key] = val

        if upVector:
            if aimCurve:
                raise ValueError("Unsupported combo: up vector and aim curve")

            if singleUpVector:
                if upObject:
                    if singleUpObject:
                        upVector *= upObject.attr('wm')

                        if parallelTransport:
                            rv = self.solveUpVectorsByParallelTransport(
                                upVector, res=resolution, arv=True, i=interpolation)

                            if parametric:
                                sampleParams = vals

                            else:
                                sampleParams = [self.paramAtFraction(f) for f in vals]

                            upVectors = [rv.sampleColor(p) for p in sampleParams]
                            distribute('upVector', upVectors)

                        else:
                            replicate('upVector', upVector)

                    else: # multiple up objects
                        if parallelTransport:
                            raise ValueError(
                                "Unsupported combo: multiple up objects, "+
                                "single up vector and parallel transport."
                            )

                        upVectors = [upVector \
                                     * upObj.attr('wm') for upObj in upObject]

                        distribute('upVector', upVectors)

                else:
                    if parallelTransport:
                        rv = self.solveUpVectorsByParallelTransport(
                            upVector, res=resolution, arv=True, i=interpolation)

                        if parametric:
                            sampleParams = vals

                        else:
                            sampleParams = [self.paramAtFraction(f) for f in vals]

                        upVectors = [rv.sampleColor(p) for p in sampleParams]
                        distribute('upVector', upVectors)

                    else:
                        replicate('upVector', upVector)

            elif multiUpVectors:
                upVectors = upVector

                if parallelTransport:
                    raise ValueError(
                        "Unsupported combo: multiple up "+
                        "vectors and parallel transport."
                    )

                if upObject:
                    if singleUpObject:
                        upVectors = [upVector \
                                     * upObject.attr('wm') \
                                     for upVector in upVectors]

                    else:
                        upObjects = upObject
                        upVectors = [upVector * upObject.attr('wm') \
                                     for upVector, upObject in \
                                     zip(upVectors, upObjects)]

                distribute('upVector', upVectors)

            else: # only remaining option is keyed up vectors
                keymap = upVector

                if upObject:
                    positions, upVectors = zip(*keymap)

                    if singleUpObject:
                        upVectors = [upVector * \
                                     upObject.attr('wm') \
                                     for upVector in upVectors]

                    else: # multi
                        if len(upObject) is not len(upVectors):
                            raise ValueError(
                                "Unequal numbers of up "+
                                "objects and up vector keys."
                            )

                        upVectors = [upVector * upObj.attr('wm') \
                                     for upVector, upObj \
                                     in zip(upVectors, upObject)]

                    keymap = zip(positions, upVectors)

                # Solve
                if parallelTransport:
                    rv = self.solveUpVectorsKeyedParallelTransport(
                        keymap, i=interpolation, res=resolution,
                        uws=unwindSwitch, arv=True
                    )

                else:
                    rv = self.solveUpVectorsKeyedLinear(
                        keymap, i=interpolation, arv=True)

                # The rv setup expects parameters, not fractions
                if parametric:
                    sampleParams = vals

                else:
                    sampleParams = [self.paramAtFraction(f) for f in vals]

                upVectors = [rv.sampleColor(p) for p in sampleParams]
                distribute('upVector', upVectors)

        else:
            if aimCurve:
                if upObject:
                    raise ValueError("Unsupported "+
                                     "combo: aim curve and up object.")

                replicate('aimCurve', aimCurve)
                replicate('closestPoint', closestPoint)

            elif upObject:
                if multiUpObjects:
                    distribute('upObject', upObject)

                else:
                    replicate('upObject', upObject)

            elif parallelTransport:
                raise ValueError(
                    "Parallel transport needs vector "+
                    "keys or a starting vector.")

        out = []

        meth = self.matrixAtParam if parametric else self.matrixAtFraction

        for i, kwdict in enumerate(kwdicts):
            with r.Name(i+1, padding=3):
                matrix = meth(vals[i], primaryAxis, secondaryAxis, **kwdict)
            out.append(matrix)

        return out

    #-------------------------------------------------------|
    #-------------------------------------------------------|    Editing
    #-------------------------------------------------------|

    #--------------------------------------------------|    Conversions

    @short(force='f')
    def toBezier(self, force=False):
        """
        Converts this NURBS curve to a Bezier curve.

        :param bool force/f: when this is ``False``, this plug will be
            passed through as-is if it's already a Bezier curve;
            defaults to False
        :return: The bezier curve.
        :rtype: :class:`~paya.runtime.plugs.BezierCurve`
        """
        if not force:
            if isinstance(self, r.plugs.BezierCurve):
                return self

        node = r.nodes.NurbsCurveToBezier.createNode()
        self >> node.attr('inputCurve')
        return node.attr('outputCurve')

    @short(force='f')
    def toNurbs(self, force=False):
        """
        Converts this Bezier curve to a NURBS curve.

        :param bool force/f: when this is ``False``, this plug will be
            passed through as-is if it's already a Bezier curve;
            defaults to False
        :return: The NURBS curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        if not force:
            if type(self) is r.plugs.NurbsCurve:
                return self

        node = r.nodes.BezierCurveToNurbs.createNode()
        self >> node.attr('inputCurve')
        return node.attr('outputCurve')

    @short(tolerance='tol', keepRange='kr')
    def bSpline(self, tolerance=0.001, keepRange=1):
        """
        :param keepRange/kr: An index or enum key for the node's
            `keepRange`` enumerator:

            - 0: '0 to 1'
            - 1: 'Original' (the default)
            - 2: '0 to #spans'

        :type keepRange/kr: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param tolerance/tol: the fit tolerance; defaults to 0.001
        :type tolerance/tol: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The B-spline.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.FitBspline.createNode()
        self >> node.attr('inputCurve')
        tolerance >> node.attr('tolerance')
        node.attr('keepRange').set(keepRange)

        return node.attr('outputCurve')

    @short(
        spans='s',
        degree='d',
        keepRange='kr',
        endKnots='end',
        keepEndPoints='kep',
        keepTangents='kt',
        keepControlPoints='kcp',
        tolerance='tol',
        rebuildType='rt',
        matchCurve='mc'
    )
    def rebuild(self, spans=None, degree=None, keepRange=1,
            endKnots=0, keepEndPoints=True, keepTangents=True,
            keepControlPoints=False, tolerance=0.01,
            rebuildType=0, matchCurve=None):
        """
        Same signature as the API method. If any arguments are omitted, they
        are derived from the curve's current state.

        :param spans/s: the target number of spans; defaults to the current
            number of spans
        :type spans: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param degree/d: the target degree, one of 1, 2, 3, 5 or 7; defaults
            to the current degree
        :type degree/d: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param keepRange/kr: an integer or label for the enumerator on
            ``rebuildCurve``, namely:

            - 0 ('0 to 1')
            - 1 ('Original') (the default)
            - 2 ('0 to #spans')

        :type keepRange/kr: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param endKnots/end: an integer or label for the enumerator on
            ``rebuildCurve``, namely:

            - 0 ('Non Multiple end knots')
            - 1 ('Multiple end knots')

        :type endKnots/end: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param keepEndPoints/kep: keep end points; defaults to True
        :type keepEndPoints/kep: bool, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param keepTangents/kt: keep tangents; defaults to True
        :type keepTangents/kt: bool, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param keepControlPoints/kcp: keep control points; defaults to False
        :type keepControlPoints/kcp: bool, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param tolerance/tol: the rebuild tolerance; defaults to 0.01
        :type tolerance/tol: float, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param matchCurve/mc: a curve shape or input for the 'Match Knots'
            mode; if provided, *rebuildType* will be overriden to 2;
            defaults to None
        :type matchCurve/mc: str, :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param rebuildType/rt: an integer or label for the enumerator on
            ``rebuildCurve``, namely:

            - 0 ('Uniform') (the default)
            - 1 ('Reduce Spans')
            - 2 ('Match Knots')
            - 3 ('Remove Multiple Knots')
            - 4 ('Curvature')
            - 5 ('End Conditions')
            - 6 ('Clean')

        :type rebuildType/rt: int, str, :class:`~paya.runtime.plugs.Math1D`
        :return: The rebuilt curve.
        """
        #--------------------------------------|    Wrangle args

        if matchCurve:
            rebuildType = 2
            matchCurve = _po.asGeoPlug(matchCurve)

        mfn = self.getShapeMFn()

        if spans is None:
            spans = mfn.numSpans()

        if degree is None:
            degree = mfn.degree()

        #--------------------------------------|    Configure node

        node = r.nodes.RebuildCurve.createNode()
        self >> node.attr('inputCurve')

        if matchCurve:
            matchCurve >> node.attr('matchCurve')

        for source, attrName in zip(
            [spans, degree, keepRange, endKnots,
             keepEndPoints, keepTangents,
             keepControlPoints, tolerance,
             rebuildType],
            ['spans', 'degree', 'keepRange', 'endKnots',
             'keepEndPoints', 'keepTangents',
             'keepControlPoints', 'tolerance',
             'rebuildType']
        ):
            source >> node.attr(attrName)

        return node.attr('outputCurve')

    #--------------------------------------------------|    Rebuilds

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

    def cageRebuild(self):
        """
        :return: A linear curve with the same CVs as this one.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        return self.rebuild(degree=1, keepControlPoints=True)

    def reverse(self):
        """
        :return: The reversed curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.ReverseCurve.createNode()
        self >> node.attr('inputCurve')
        return node.attr('outputCurve')

    #--------------------------------------------------|    Retractions

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

    #--------------------------------------------------|    Extensions

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
        :param bool useSegment/seg: for improved accuracy, extend using an
            attached line segment instead of the 'Linear' mode of an
            ``extendCurve`` node; defaults to False
        :return: This curve, extended along the specified vector.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        points = self.getCVs()
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
        :param bool useSegment/seg: for improved accuracy, extend using an
            attached line segment instead of the 'Linear' mode of an
            ``extendCurve`` node; defaults to False
        :return: This curve, extended to meet the specified point
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        if useSegment:
            allPoints = self.getCVs()
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
            an ``extendCurve`` node; for improved accuracy, attach a line
            segment instead; defaults to False
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

    #--------------------------------------------------|    Misc

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

        # The following is 0.1 and not 0.0 to avoid node calc errors; the
        # output will be switched out anyway
        extendLength = extendLength.minClamp(0.1)

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