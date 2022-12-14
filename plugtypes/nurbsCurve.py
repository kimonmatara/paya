import maya.OpenMaya as om
import maya.cmds as m
import pymel.util as _pu

from paya.lib.typeman import plugCheck
import paya.lib.mathops as _mo
import paya.lib.typeman as _tm
import paya.lib.nurbsutil as _nu
from paya.geoshapext import copyToShape
from paya.util import short, resolveFlags
import paya.runtime as r


class NurbsCurve:

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    CONSTRUCTORS
    #---------------------------------------------------------------|

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
        points = _tm.expandVectorArgs(*points)

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

            return node.attr('outputCurve').setClass(type(self))

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
            degree = _mo.info(degree)['item']

        if numCVs is not None:
            numCVs = _mo.info(numCVs)['item']

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

        startPoint = _mo.info(startPoint)['item']
        endPoint = _mo.info(endPoint)['item']
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
    #---------------------------------------------------------------|    SHAPE GENERATION
    #---------------------------------------------------------------|

    @short(dispCV='dcv')
    def createShape(self, dispCV=True, **kwargs):
        """
        Overloads :meth:`paya.runtime.plugs.Geometry.createShape` to add the
        *dispCV/dcv* argument.

        :param bool dispCV/dcv: display CVs on the curve shape; defaults to
            ``True``
        :param \*\*kwargs: forwarded to
            :meth:`paya.runtime.plugs.Geometry.createShape`
        :return: The generated shape.
        :rtype: :class:`~paya.runtime.nodes.NurbsCurve`
        """
        shape = super(r.plugs.NurbsCurve, self).createShape(**kwargs)
        shape.attr('dispCV').set(dispCV)
        return shape

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    CODE UTILITIES
    #---------------------------------------------------------------|

    @short(parametric='par',
           uniform='uni')
    def _resolveNumberFractionsOrParams(self,
                                        numberFractionsOrParams,
                                        parametric=False,
                                        uniform=False):
        """
        Utility method. Resolves the *numberFractionsOrParams* argument on
        distribution methods into a list of fractions or parameters.

        If *numberFractionsOrParams* is a list, it will merely be conformed
        and passed back. Otherwise, the return will always be values, not
        plugs.

        :param numberFractionsOrParams: one of:

            -   a single integer value, specifying how many fraction or
                parameter values to return, or

            -   a user list of fractions or parameters, which can be values
                or plugs

        :type numberFractionsOrParams: :class:`float`,
            [:class:`float` | :class:`~paya.runtime.plugs.Math1D`]
        :param bool parametric/par: if *numberFractionsOrParams* is a number,
            generate parameters, not fractions; defaults to ``False``
        :param bool uniform/uni: if generating parameters, distribute them
            by length, not parametric space; defaults to ``False``
        :return: If 'parametric' is True, a list of parameters; otherwise,
             a list of fractions.
        :rtype: [:class:`float`, :class:`~paya.runtime.plugs.Math1D`]
        """
        if hasattr(numberFractionsOrParams, '__iter__'):
            return [_mo.info(x)['item'] for x in numberFractionsOrParams]

        else:
            number = numberFractionsOrParams

            if parametric:
                if uniform:
                    fractions = _mo.floatRange(0, 1, number)
                    return [self.paramAtFraction(
                        fraction, p=False) for fraction in fractions]

                umin, umax = self.knotDomain(p=False)
                return _mo.floatRange(umin, umax, number)

            else:
                return _mo.floatRange(0, 1, number)

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    INIT UTIL NODES
    #---------------------------------------------------------------|

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
        point, pointDim, pointUnitType, pointIsPlug = \
            _mo.info(point).values()

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

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    SPOT INSPECTIONS
    #---------------------------------------------------------------|

    def numCVs(self):
        """
        This is a :term:`static`-only operation.

        :return: The number of CVs on this curve.
        :rtype: :class:`int`
        """
        mfn = self.getShapeMFn()
        return mfn.numCVs()

    def numSpans(self):
        """
        This is a :term:`static`-only operation.

        :return: The number of spans on this curve.
        :rtype: :class:`int`
        """
        mfn = self.getShapeMFn()
        return mfn.numSpans()

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    CURVE-LEVEL SAMPLING
    #---------------------------------------------------------------|

    def findExistingInfoNode(self):
        """
        :return: The first :class:`curveInfo <paya.runtime.nodes.CurveInfo>`
            node connected to this curve, or ``None``.
        :rtype: ``None`` | :class:`paya.runtime.nodes.CurveInfo`
        """
        existing = self.outputs(type='curveInfo')

        if existing:
            return existing[0]

    @copyToShape()
    @short(reuse='re', plug='p')
    def info(self, reuse=True, plug=False):
        """
        :param bool reuse/re: where available, retrieve an already-connected
            node; defaults to True
        :param bool plug/p: return a :class:`curveInfo <paya.runtime.nodes.CurveInfo>`
            node rather than information in a dict; defaults to ``False``
        :return: If *plug* is ``True``, a
            :class:`curveInfo <paya.runtime.nodes.CurveInfo>` node;
            otherwise, a dictionary with the following keys: ``'arcLength'``,
            ``'controlPoints'``, ``'knots'``
        :rtype: :class:`dict` | :class:`paya.runtime.nodes.CurveInfo`
        """
        if plug:
            if reuse:
                existing = self.findExistingInfoNode()

                if existing:
                    return existing

            node = r.nodes.CurveInfo.createNode()
            self >> node.attr('inputCurve')

            return node

        return {
            'arcLength': self.length(p=False),
            'knots': self.getKnots(p=False),
            'controlPoints': self.getControlVerts(p=False)
        }

    @short(plug='p')
    def length(self, plug=False):
        """
        If *plug* is False, a temporary
        :class:`curveInfo <paya.runtime.nodes.CurveInfo>` node will be used
        instead of :meth:`maya.OpenMaya.MFnNurbsCurve.length` to ensure
        correct space management.

        This method will *always* use a
        :param bool plug/p: return a plug, not just a value; defaults
            to ``False``
        :return: The length of this curve.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        existing = self.findExistingInfoNode()

        if plug:
            if existing:
                return existing.attr('arcLength')

            else:
                return self.info(plug=True, re=False).attr('arcLength')

        else:
            if existing:
                return existing.attr('arcLength').get()

            node = self.info(plug=True, re=False)
            length = node.attr('arcLength').get()
            r.delete(node)
            return length

    @short(plug='p')
    def getKnots(self, plug=False):
        """
        :param plug/p: return the ``knots`` array of a
            :class:`curveInfo <paya.runtime.nodes.CurveInfo>` node, not just
            a list of values; defaults to ``False``
        :return: [:class:`int`] | [:class:`paya.runtime.plugs.Math1D`]
        """
        if plug:
            out = self.info(plug=True).attr('knots')
            out.evaluate()
            return out

        else:
            mfn = self.getShapeMFn()
            arr = om.MDoubleArray()
            mfn.getKnots(arr)
            return [arr[i] for i in range(arr.length())]

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    LOCAL-LEVEL SAMPLING
    #---------------------------------------------------------------|

    #-----------------------------------------------|    Motion paths

    @copyToShape(worldSpaceOnly=True)
    def motionPath(self, **config):
        """
        Creates a ``motionPath`` node and connects it to this curve. All other
        configuration is performed via *config*.

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

    @copyToShape(worldSpaceOnly=True)
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

    @copyToShape(worldSpaceOnly=True)
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

    #-----------------------------------------------|    PointOnCurveInfo

    def _findExistingInfoAtParam(self, param, turnOnPercentage=False):
        param, paramDim, paramUnitType, paramIsPlug = \
            _mo.info(param).values()
        turnOnPercentage, topDim, topUnitType, topIsPlug = \
            _mo.info(turnOnPercentage).values()
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

    @copyToShape(worldSpaceOnly=True)
    @short(reuse='re',
           plug='p',
           turnOnPercentage='top')
    @plugCheck('param')
    def infoAtParam(self,
                    param,
                    reuse=True,
                    plug=None,
                    turnOnPercentage=False):
        """
        :param param: the curve parameter to inspect
        :type param: :class:`float`, :class:`~paya.runtime.plugs.Math1D`
        :param bool turnOnPercentage/top: per the namesake attribute on
            :class:`pointOnCurveInfo <paya.runtime.nodes.PointOnCurveInfo>`,
            interpret *param* a percentage ratio within parametric space
            (note that this is not the same as ``fractionMode`` on
            motion paths; defaults to ``False``
        :param bool reuse/re: if *plug* is ``True``, reuse any matching
            :class:`pointOnCurveInfo <paya.runtime.nodes.PointOnCurveInfo>` nodes;
            defaults to ``True``
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        return a
            :class:`pointOnCurveInfo <paya.runtime.nodes.PointOnCurveInfo>`
            node rather than a dictonary of values; default is auto-configured
            based on arguments
        :return: If *plug* is ``True``, a
            :class:`pointOnCurveInfo <paya.runtime.nodes.PointOnCurveInfo>` node;
            otherwise, a dictionary with the followingk keys: ``'position'``,
            ``'tangent'``, ``'normalizedTangent'``, ``'normal'``,
            ``'normalizedNormal'``
        :rtype: :class:`~paya.runtime.nodes.PointOnCurveInfo`, :class:`dict`
        """
        if plug:
            if reuse:
                existing = self._findExistingInfoAtParam(
                param, turnOnPercentage=turnOnPercentage)

                if existing is not None:
                    return existing

            node = r.nodes.PointOnCurveInfo.createNode()
            self >> node.attr('inputCurve')
            param >> node.attr('parameter')
            turnOnPercentage >> node.attr('turnOnPercentage')

            return node

        if turnOnPercentage:
            umin, umax = self.knotDomain(p=False)
            param = _pu.blend(umin, umax, weight=param)

        tangent = self.tangentAtParam(param, p=False)
        normalizedTangent = tangent.normal()
        normal = self.normalAtParam(param, p=False)
        normalizedNormal = normal.normal()
        position = self.pointAtParam(param, p=False)

        return {
            'position': position,
            'tangent': tangent,
            'normalizedTangent': normalizedTangent,
            'normal': normal,
            'normalizedNormal': normalizedNormal
        }

    #-----------------------------------------------|    CV

    @copyToShape()
    @short(plug='p')
    def getControlVerts(self, plug=False):
        """
        :param bool plug/p: return plugs rather than values;
            defaults to ``False``
        :return: The members of the ``controlPoints`` info array for this
            curve.
        :rtype: [:class:`~paya.runtime.plugs.Vector`],
            [:class:`~paya.runtime.data.Point`]
        """
        if plug:
            out = self.info(plug=True).attr('controlPoints')
            out.evaluate()
            return list(out)

        mfn = self.getShapeMFn()
        arr = om.MPointArray()
        mfn.getCVs(arr, om.MSpace.kWorld)

        return [r.data.Point(arr[x]) for x in range(arr.length())]

    @copyToShape()
    @short(plug='p')
    def getControlVert(self, cvIndex, plug=False):
        """
        :alias: ``pointAtCV``
        :param int cvIndex: the index of the CV to inspect
        :param bool plug/p: return a plug, not just a value; defaults
            to ``False``
        :return: The position of the specified CV.
        """
        if plug:
            return self.getControlVerts(plug=True)[cvIndex]

        mfn = self.getShapeMFn()
        point = om.MPoint()
        mfn.getCV(cvIndex, point, om.MSpace.kWorld)
        return r.data.Point(point)

    pointAtCV = getControlVert

    #-----------------------------------------------|    Point

    @copyToShape()
    @short(parametric='par', plug='p')
    def pointAt(self, paramOrFraction, parametric=True, plug=None):
        """
        Dispatches :meth:`pointAtParam` if ``parametric=True``, otherwise
        :meth:`pointAtFraction`.

        :param bool parametric/par: interpret *paramOrFraction* as a U
            parameter rather than a length fraction; defaults to ``False``
        """
        if parametric:
            return self.pointAtParam(paramOrFraction, p=plug)

        return self.pointAtFraction(paramOrFraction, p=plug)

    @copyToShape()
    @short(plug='p')
    @plugCheck('param')
    def pointAtParam(self, param, plug=None):
        """
        :param param: the parameter to sample
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: A point at the specified parameter.
        :rtype: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            node = self.infoAtParam(param, plug=True)
            return node.attr('position')

        mfn = self.getShapeMFn()
        pt = om.MPoint()
        mfn.getPointAtParam(param, pt, om.MSpace.kWorld)
        return r.data.Point(pt)

    @copyToShape()
    @short(plug='p')
    @plugCheck('length')
    def pointAtLength(self, length, plug=None):
        """
        :param length: the length to sample
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: return a plug, not a value; if ``False``,
            *param* must be a value; defaults to ``False``
        :return: A point at the specified length.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            fraction = length / self.length(p=True)
            return self.pointAtFraction(fraction, p=True)

        return self.pointAtParam(
            self.paramAtLength(length, p=False), p=False)

    @copyToShape()
    @short(plug='p')
    @plugCheck('fraction')
    def pointAtFraction(self, fraction, plug=None):
        """
        :param fraction: the fraction to sample
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: A point at the specified fraction.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.motionPathAtFraction(fraction).attr('allCoordinates')

        targetLength = self.length(p=False) * fraction
        param = self.paramAtLength(targetLength, plug=False)
        point = self.pointAtParam(param, p=False)
        return point

    @copyToShape()
    @short(plug='p')
    @plugCheck('refPoint')
    def nearestPoint(self, refPoint, plug=None):
        """
        :param refPoint: the reference point
        :type refPoint: tuple, list, str, :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The closest point on this curve to *refPoint*.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.initNearestPointOnCurve(refPoint).attr('position')

        mfn = self.getShapeMFn()

        paramUtill = om.MScriptUtil()
        paramPtr = paramUtill.asDoublePtr()

        point = mfn.closestPoint(om.MPoint(refPoint),
                                 paramPtr, 0.001, om.MSpace.kWorld)

        return r.data.Point(point)

    @copyToShape()
    @short(plug='p',
           parametric='par',
           uniform='uni')
    @plugCheck('numberFractionsOrParams')
    def distributePoints(self,
                         numberFractionsOrParams,
                         parametric=False,
                         uniform=False,
                         plug=None):
        """
        :param numberFractionsOrParams: one of:

            -   a single integer value, specifying how many fraction or
                parameter values to return, or

            -   a user list of fractions or parameters, which can be values
                or plugs

        :param bool parametric/par: if *numberFractionsOrParams* is a number,
            generate parameters, not fractions; defaults to ``False``
        :param bool uniform/uni: if generating parameters, distribute them
            by length, not parametric space; defaults to ``False``
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: A list of point values or plugs.
        :rtype: [:class:`~paya.runtime.data.Point`
            | :class:`~paya.runtime.plugs.Vector`]
        """
        fractionsOrParams = \
            self._resolveNumberFractionsOrParams(numberFractionsOrParams,
                                                 par=parametric,
                                                 uni=uniform)

        meth = self.pointAtParam if parametric else self.pointAtFraction

        return [meth(fractionOrParam,
                     p=plug) for fractionOrParam in fractionsOrParams]

    #-----------------------------------------------|    Param

    @copyToShape()
    @short(plug='p')
    def paramAtStart(self, plug=False):
        """
        :param bool plug/p: return plugs, not values; defaults to False
        :return: The parameter at the start of this curve.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.paramAtLength(0.0, p=True)

        return self.knotDomain(plug=False)[0]

    @copyToShape()
    @short(plug='p')
    def paramAtEnd(self, plug=False):
        """
        :param bool plug/p: return plugs, not values; defaults to False
        :return: The parameter at the end of this curve.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.paramAtFraction(1.0, p=True)

        return self.knotDomain(plug=False)[1]

    @copyToShape()
    @short(plug='p')
    def knotDomain(self, plug=False):
        """
        :param bool plug/p: return plugs, not values; defaults to ``False``
        :return: The min and max U parameters on this curve.
        :rtype: (:class:`float` | :class:`~paya.runtime.plugs.Math1D`,
            :class:`float` | :class:`~paya.runtime.plugs.Math1D`)
        """
        if plug:
            found = [output for output in self.outputs(
                plugs=True, type='network') if \
                output.attrName() == 'domainQuery']

            if found:
                node = found[0].node()
                return (node.attr('umin'), node.attr('umax'))

            with r.Name('domainQuery'):
                node = r.nodes.Network.createNode()

            umin = node.addAttr('umin')
            umax = node.addAttr('umax')

            self.paramAtFraction(0.0, p=True) >> umin
            self.paramAtFraction(1.0, p=True) >> umax
            self >> node.addAttr('domainQuery', at='message')

            return umin, umax

        self.evaluate()
        mfn = self.getShapeMFn()
        minPtr = om.MScriptUtil().asDoublePtr()
        maxPtr = om.MScriptUtil().asDoublePtr()

        result = mfn.getKnotDomain(minPtr, maxPtr)

        return (
            om.MScriptUtil(minPtr).asDouble(),
            om.MScriptUtil(maxPtr).asDouble(),
        )

    @copyToShape()
    @short(plug='p')
    @plugCheck('point')
    def paramAtPoint(self, point, plug=None):
        """
        This is a 'forgiving' implementation, and uses the closest point.

        :alias: ``nearestParam``
        :param point: the reference point
        :type point: tuple, list, str, :class:`~paya.runtime.plugs.Vector`,
            :class:`~paya.runtime.data.Point`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The nearest parameter to the reference point.
        :rtype: :class:`float`, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.initNearestPointOnCurve(point).attr('parameter')

        point = om.MPoint(point)
        mfn = self.getShapeMFn()
        paramUtil = om.MScriptUtil()
        paramPtr = paramUtil.asDoublePtr()
        mfn.closestPoint(point, paramPtr, 0.001, om.MSpace.kWorld)

        return paramUtil.getDouble(paramPtr)

    nearestParam = paramAtPoint

    @copyToShape()
    @short(plug='p')
    @plugCheck('fraction')
    def paramAtFraction(self, fraction, plug=None):
        """
        :param fraction: the fraction to sample
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The parameter at the given fraction.
        :rtype: :class:`float`, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            point = self.pointAtFraction(fraction, plug=True)
            out = self.paramAtPoint(point, plug=True)
        else:
            # Length space doesn't matter for this calculation
            mfn = self.getShapeMFn()
            length = mfn.length()
            targetLength = length * fraction
            out = mfn.findParamFromLength(targetLength)

        return out

    @copyToShape()
    @short(plug='p')
    @plugCheck('length')
    def paramAtLength(self, length, plug=None):
        """
        :param length: the length at which to sample a parameter
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The parameter at the given length.
        :rtype: :class:`float`, :class:`~paya.runtime.plugs.Math1D`
        """
        fraction = length / self.length(p=plug)
        return self.paramAtFraction(fraction, p=plug)

    @copyToShape()
    @short(parametric='par',
           uniform='uni',
           plug='p')
    @plugCheck('numberFractionsOrParams')
    def distributeParams(self,
                         numberFractionsOrParams,
                         parametric=False,
                         uniform=False,
                         plug=None):
        """
        :param numberFractionsOrParams: one of:

            -   a single integer value, specifying how many fraction or
                parameter values to return, or

            -   a user list of fractions or parameters, which can be values
                or plugs

        :type numberFractionsOrParams: :class:`float`,
            [:class:`float` | :class:`~paya.runtime.plugs.Math1D`]
        :param bool parametric/par: if *numberFractionsOrParams* is a number,
            generate parameters, not fractions; defaults to ``False``
        :param bool uniform/uni: if generating parameters, distribute them
            by length, not parametric space; defaults to ``False``
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: A list of parameter plugs or values.
        :rtype: [:class:`float` | :class:`~paya.runtime.plugs.Math1D`]
        """
        fractionsOrParams = \
            self._resolveNumberFractionsOrParams(
                numberFractionsOrParams,
                par=parametric,
                uni=uniform
            )

        if parametric:
            params = fractionsOrParams

        else:
            params = [self.paramAtFraction(f,
                        p=plug) for f in fractionsOrParams]

        return params

    #-----------------------------------------------|    Length

    @copyToShape()
    @short(plug='p')
    @plugCheck('fraction')
    def lengthAtFraction(self, fraction, plug=None):
        """
        :param fraction: the fraction to inspect
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The curve length at the specified fraction.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        return self.length(plug=plug) * fraction

    @copyToShape()
    @short(plug='p', checkDomain='cd')
    @plugCheck('param')
    def lengthAtParam(self, param, plug=None, checkDomain=True):
        """
        Differs from the PyMEl / API
        :meth:`~pymel.core.nodetypes.NurbsCurve.findLengthFromParam` in that
        it returns properly-spaced curve lengths.

        :param param: the parameter to inspect
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool checkDomain/cd: perform gating against the current curve
            knot domain to prevent sampling errors at the very start or end
            of the curve; defaults to ``True``
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The curve length at the specified parameter.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            if checkDomain:
                inf = _mo.info(param)

                if inf['isPlug']:
                    zero = r.plugs.Math1D.createAttr('zero')
                    length = self.length(p=True)
                    umin, umax = self.knotDomain(plug=True)
                    midParam = umin.blend(umax, weight=0.5)

                    isAtMin = param.le(umin)
                    isAtMax = param.ge(umax)

                    detachParam = isAtMin.ifElse(
                        midParam,
                        isAtMax.ifElse(
                            midParam,
                            param
                        )
                    )

                    return isAtMin.ifElse(
                        zero,
                        isAtMax.ifElse(
                            length,
                            self.detach(detachParam, select=0)[0].length(plug=True)
                        )
                    )

                else:
                    umin, umax = self.knotDomain()

                    if param <= umin:
                        return r.plugs.Math1D.createAttr('zero')

                    if param >= umax:
                        return self.length(p=True)

                    return self.detach(param, select=0)[0].length(plug=True)
            return self.detach(param, select=0)[0].length(plug=True)

        else:
            umin, umax = self.knotDomain()

            if param <= umin:
                return 0.0

            if param >= umax:
                return self.length()

            # Use nodes instead of MFn to get a properly spaced reading
            output = self.detach(param, select=0)[0]
            length = output.length(p=False)

            _node = str(output.node())

            m.evalDeferred(
                "import maya.cmds as m\nif m.objExists('{}'):\n\tm.delete('{}')".format(
                    _node, _node)
            )

            return length

    @copyToShape()
    @short(plug='p')
    def lengthAtPoint(self, point, plug=None):
        """
        This is a 'forgiving' implementation, and uses the closest point.

        :param point: the point to inspect
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The curve length at the specified point.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        param = self.paramAtPoint(point, p=plug)
        return self.lengthAtParam(param, p=plug)

    @copyToShape()
    @short(parametric='par',
           uniform='uni',
           plug='p')
    @plugCheck('numberFractionsOrParams')
    def distributeLengths(self,
                          numberFractionsOrParams,
                          parametric=False,
                          uniform=False, plug=None):
        """
        :param numberFractionsOrParams: one of:

            -   a single integer value, specifying how many fraction or
                parameter values to return, or

            -   a user list of fractions or parameters, which can be values
                or plugs

        :type numberFractionsOrParams: :class:`float`,
            [:class:`float` | :class:`~paya.runtime.plugs.Math1D`]
        :param bool parametric/par: if *numberFractionsOrParams* is a number,
            generate parameters, not fractions; defaults to ``False``
        :param bool uniform/uni: if generating parameters, distribute them
            by length, not parametric space; defaults to ``False``
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: A list of lengths.
        :rtype: [:class:`float` | :class:`~paya.runtime.plugs.Math1D`]
        """
        fractionsOrParams = self._resolveNumberFractionsOrParams(
            numberFractionsOrParams,
            par=parametric,
            uni=uniform)

        meth = self.lengthAtParam if parametric else self.lengthAtFraction

        return [meth(fractionOrParam,
                     p=plug) for fractionOrParam in fractionsOrParams]

    #-----------------------------------------------|    Fraction

    @copyToShape()
    @short(plug='p')
    @plugCheck('point')
    def fractionAtPoint(self, point, plug=None):
        """
        This is a 'forgiving' implementation, and uses the closest point.

        :param point: the point at which to sample a fraction
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The length fraction at the specified point.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        return self.lengthAtPoint(point, p=plug) / self.length(p=plug)

    @copyToShape()
    @short(plug='p')
    @plugCheck('param')
    def fractionAtParam(self, param, plug=None):
        """
        :param param: the parameter at which to sample a fraction
        :type param: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The length fraction at the specified parameter.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        return self.lengthAtParam(param, p=plug) / self.length(p=plug)

    @copyToShape()
    @short(plug='p')
    @plugCheck('length')
    def fractionAtLength(self, length, plug=None):
        """
        :param length: the length at which to sample a fraction
        :type length: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The length fraction at the specified length.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        return length / self.length(p=plug)

    @copyToShape()
    def distributeFractions(self, number):
        """
        Convenience method. Equivalent to
        :func:`floatRange(0, 1, number) <paya.lib.mathops.floatRange>`.

        :param int number: the number of fractions to generate
        :return: A uniform list of fractions.
        :rtype: [float]
        """
        return _mo.floatRange(0, 1, number)

    #-----------------------------------------------|    Normal

    @copyToShape()
    @short(normalize='nr', plug='p')
    @plugCheck('param')
    def normalAtParam(self, param, normalize=False, plug=None):
        """
        :param param: the parameter at which to sample the normal
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: return the normalized normal;
            defaults to False
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.infoAtParam(param, plug=True).attr(
                'normalizedNormal' if normalize else 'normal'
            )

        if normalize:
            mfn = self.getShapeMFn()
            normal = r.data.Vector(mfn.normal(param, om.MSpace.kWorld))

        else:
            node = self.infoAtParam(param, plug=True, reuse=False)
            normal = node.attr('normal').get()

        return normal

    @copyToShape()
    @short(normalize='nr', plug='p')
    @plugCheck('fraction')
    def normalAtFraction(self, fraction, normalize=False, plug=None):
        """
        :param fraction: the fraction at which to sample the normal
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: return the normalized normal;
            defaults to False
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            mp = self.motionPathAtFraction(fraction)
            mp.configFollow('y', 'x')

            normal = mp.attr('orientMatrix').getAxis('x')

            if normalize:
                normal = normal.normal()

            return normal

        param = self.paramAtFraction(fraction, p=False)
        return self.normalAtParam(param, p=False)

    @copyToShape()
    @short(normalize='nr', plug='p')
    @plugCheck('length')
    def normalAtLength(self, length, normalize=False, plug=None):
        """
        :param length: the length at which to sample the normal
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: return the normalized normal;
            defaults to False
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        fraction = length / self.length(p=plug)
        return self.normalAtFraction(fraction, nr=normalize, p=plug)

    @copyToShape()
    @short(normalize='nr', plug='p')
    @plugCheck('point')
    def normalAtPoint(self, point, normalize=False, plug=None):
        """
        :param point: the point at which to sample the normal
        :type point: tuple, list, str,
            :class:`~paya.runtime.plugs.Vector`,
            :class:`~paya.runtime.data.Point`
        :param bool normalize/nr: return the normalized normal;
            defaults to False
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtPoint(point, p=plug)
        return self.normalAtParam(param, nr=normalize, p=plug)

    #-----------------------------------------------|    Tangent

    @copyToShape()
    @short(normalize='nr', plug='p')
    @plugCheck('param')
    def tangentAtParam(self, param, normalize=False, plug=None):
        """
        :param param: the parameter at which to sample the tangent
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool normalize/nr: return the normalized tangent;
            defaults to False
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.infoAtParam(param, p=True).attr(
                'normalizedTangent' if normalize else 'tangent'
            )

        else:
            if normalize:
                mfn = self.getShapeMFn()
                tangent = r.data.Vector(mfn.tangent(param, om.MSpace.kWorld))

            else:
                info = self.infoAtParam(param, p=True, re=False)
                tangent = info.attr('tangent').get()
                r.delete(info)

            return tangent

    @copyToShape()
    @short(normalize='nr', plug='p')
    @plugCheck('fraction')
    def tangentAtFraction(self, fraction, normalize=False, plug=None):
        """
        :param fraction: the fraction at which to sample the tangent
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :param bool normalize/nr: normalize the output vector; defaults to
            False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            mp = self.motionPathAtFraction(fraction)
            mp.configFollow('y', 'x')
            tangent = mp.attr('orientMatrix').getAxis('y')

            if normalize:
                tangent = tangent.normal()

            return tangent

        param = self.paramAtFraction(fraction, p=False)
        return self.tangentAtParam(param, p=False)

    @copyToShape()
    @short(normalize='nr', plug='p')
    @plugCheck('param')
    def tangentAtLength(self, length, normalize=False, plug=None):
        """
        :param length: the length at which to sample the tangent
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :param bool normalize/nr: normalize the output vector; defaults to
            False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        fraction = length / self.length(p=plug)
        return self.tangentAtFraction(fraction, nr=normalize, p=plug)

    @copyToShape()
    @short(normalize='nr', plug='p')
    def tangentAtPoint(self, point, normalize=False, plug=None):
        """
        :param point: the point at which to sample the normals
        :type point: list, tuple, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool normalize/nr: normalize the output vector; defaults to
            False
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtPoint(point, plug=plug)
        return self.tangentAtParam(param, nr=normalize, p=plug)

    @copyToShape()
    @short(plug='p', normalize='nr')
    def distributeTangents(self,
                           numberFractionsOrParams,
                           plug=None,
                           normalize=False,
                           parametric=False,
                           uniform=True):
        """
        :param numberFractionsOrParams: this should either be

            -   A number of fractions or parameters to sample along the curve,
                or
            -   An explicit list of fractions or parameters at which to construct
                the tangents
        :param bool plug/p: return attribute outputs, not values; defaults to
            ``False``
        :param bool normalize/nr: normalize the tangents; defaults to
            ``False``
        :param bool parametric/par: interpret *numberOrFractions* as
            parameters, not fractions; defaults to ``False``
        :param bool uniform/uni: if *parametric* is ``True``, and
            *numberFractionsOrParams* is a number, initial parameters should
            be distributed by length, not parametric space; defaults to
            ``False``
        :return: A list of tangents.
        :rtype: [:class:`~paya.runtime.data.Vector`] |
            [:class:`~paya.runtime.plugs.Vector`]
        """
        fractionsOrParams = self._resolveNumberFractionsOrParams(
            numberFractionsOrParams,
            par=parametric,
            uni=uniform)

        if parametric:
            meth = self.tangentAtParam
        else:
            meth = self.tangentAtFraction

        return [meth(x, p=plug, nr=normalize) for x in fractionsOrParams]

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    UP VECTORS
    #---------------------------------------------------------------|

    @copyToShape(worldSpaceOnly=True)
    @short(plug='p', sampler='sam')
    def upVectorAtParam(self, param, sampler=None, plug=None):
        """
        :param param: the parameter at which to sample the up vector
        :type param: :class:`float`, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :param sampler/sam: an up vector sampler to use; sampler can be
            created using :meth:`createUpVectorSampler`; if this is omitted,
            then the last sampler created using
            ``createUpVectorSampler(setAsDefault=True)`` will be retrieved;
            defaults to ``None``
        :type sampler/sam: :class:`str`, :class:`~paya.runtime.nodes.Network`,
            :class:`~paya.runtime.networks.CurveUpVectorSampler`
        :raises RuntimeError: No default up vector sampler has been configured
            on this curve output.
        :return: An up vector at the specified parameter. A default up vector
            sampler must have been configured on this curve using
            :meth:`createUpVectorSampler`.
        :rtype: :class:`~paya.runtime.networks.CurveUpVectorSampler`
        """
        if sampler is None:
            sampler = self.getDefaultUpVectorSampler()

            if sampler is None:
                raise RuntimeError(
                    "No default up vector sampler has "+
                    "been configured on this curve output."
                )

        else:
            sampler = r.PyNode(sampler).asSubtype()

        return sampler.sampleAtParam(param, plug=plug)

    @copyToShape(worldSpaceOnly=True)
    @short(plug='p')
    def upVectorAtFraction(self, fraction, plug=None, **kwargs):
        """
        Converts *fraction* into a parameter and defers to
        :meth:`upVectorAtParam`.

        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :param \*\*kwargs: forwarded to :meth:`upVectorAtParam`
        """
        param = self.paramAtFraction(fraction, p=plug)
        return self.upVectorAtParam(param, p=plug, **kwargs)

    @copyToShape(worldSpaceOnly=True)
    @short(plug='p')
    def upVectorAtLength(self, length, plug=None, **kwargs):
        """
        Finds the parameter at the specified length and defers to
        :meth:`upVectorAtParam`.

        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :param \*\*kwargs: forwarded to :meth:`upVectorAtParam`
        """
        param = self.paramAtLength(length, p=plug)
        return self.upVectorAtParam(param, p=plug, **kwargs)

    @copyToShape(worldSpaceOnly=True)
    @short(plug='p')
    def upVectorAtPoint(self, point, plug=None, **kwargs):
        """
        Finds the closest parameter to the specified point and defers to
        :meth:`upVectorAtParam`.

        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :param \*\*kwargs: forwarded to :meth:`upVectorAtParam`
        """
        param = self.paramAtPoint(point, p=plug)
        return self.upVectorAtParam(param, p=plug, **kwargs)

    @copyToShape(worldSpaceOnly=True)
    @short(resolution='res',
           unwindSwitch='uws',
           interpolation='i',
           aimCurve='aic',
           upObject='uo',
           upVector='upv',
           parallelTransport='pt',
           setAsDefault='sad',
           closestPoint='cp'
           )
    def createUpVectorSampler(self,
                              resolution=9,
                              unwindSwitch=0,
                              interpolation='Linear',
                              aimCurve=None,
                              closestPoint=True,
                              upObject=None,
                              upVector=None,
                              parallelTransport=False,
                              setAsDefault=True
                              ):
        """
        Depending on options, returns one of the following up-vector samplers:

        -   :class:`~paya.runtime.networks.CurveUpVectorAimCurveSampler`
        -   :class:`~paya.runtime.networks.CurveUpVectorIkSplineStyleSampler`
        -   :class:`~paya.runtime.networks.CurveUpVectorMpStyleSampler`
        -   :class:`~paya.runtime.networks.CurveUpVectorPtSampler`
        -   :class:`~paya.runtime.networks.CurveUpVectorPtKeysSampler`

        Not all options can be combined. If all options are omitted, an
        optimised curve normal sampler will be returned.

        Use :meth:`~paya.runtime.networks.CurveUpVectorSampler.sampleAtParam`
        on the returned object to pull up vectors.

        :param upVector/upv: this can be a single up vector, or zipped pairs
            of *parameter: vector*, indicating known up vectors at specific
            points; if a single up vector is provided then, if it's combined
            with *upObject*, the vector is multiplied by the object's world
            matrix (similar to 'Object Rotation Up' on
            :class:`motionPath <paya.runtime.nodes.MotionPath>` nodes);
            otherwise, the vector is used on its own; if pairs are provided
            then they will be blended using parallel-transport or linearly
            (similar to IK spline twist); defaults to ``None``
        :type upVector/upv: :class:`None`, :class:`zip`, :class:`list`,
            :class:`tuple`, :class:`str`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`,
            [[:class:`float` | :class:`str` | :class:`~paya.runtime.plugs.Math1D`],
            [:class:`tuple` | :class:`list`,
            :class:`paya.runtime.data.Vector`,
            :class:`paya.runtime.plugs.Vector`]]
        :param upObject/uo: if provided on its own, works as an aiming interest
            (similar to 'Object Up' mode on
            :class:`motionPath <paya.runtime.nodes.MotionPath>` nodes);
            if combined with *upVector*, the object's world matrix is used to
            multiply the up vector; defaults to ``None``
        :type upObject/uo: str, :class:`~paya.runtime.nodes.Transform`
        :param int resolution/res: if using parallel transport, the number of
            solutions to generate; higher values improve accuracy at the
            expense of interactivity; defaults to 9
        :param unwindSwitch/uws: an integer value or plug, or a list of integer
            values or plugs (one per segment, i.e.
            ``len(paramVectorKeys)-1``) specifying how to resolve angle-
            blending edge cases in per-segment parallel transport:

            -   ``0`` (shortest, the default)
            -   ``1`` (positive)
            -   ``2`` (negative)

        :type unwindSwitch/uws: :class:`int`, :class:`str`,
            :class:`~paya.runtime.plugs.Math1D`,
            [:class:`int` | :class:`str` | :class:`~paya.runtime.plugs.Math1D`]
        :param interpolation/i:: defines how to interpolate values from the
            sparse parallel-transport solutions:

            -   ``0`` (``'None'``) (you wouldn't normally want this)
            -   ``1`` (``'Linear'``) (the default)
            -   ``2`` (``'Smooth'``)
            -   ``3`` (``'Spline'``)

        :type interpolation/i: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool parallelTransport/pt: use parallel-transport;
            defaults to False
        :param aimCurve: an aim-curve from which to pull aiming interest
            points, similarly to the option on
            :class:`curveWarp <paya.runtime.nodes.CurveWarp>` nodes; defaults
            to None
        :type aimCurve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity
            rather than matched parameter; defaults to ``True``
        :param bool setAsDefault/sad: make this the default fallback up vector
            source for other sampling operations; defaults to ``True``
        :raises NotImplementedError: The requested options can't be combined.
        :return: The sampler system.
        :rtype: :class:`~paya.runtime.networks.CurveUpVectorSampler`
        """
        if upVector is not None:
            if aimCurve:
                raise NotImplementedError(
                    "Unsupported combo: up vector and aim curve")

            upvType, upvContent = _tm.describeAndConformVectorArg(upVector)

            if upvType == 'keys':
                # Create a spline-style or parallel-transport segments system
                if parallelTransport:
                    sampler = r.networks.CurveUpVectorPtKeysSampler.create(
                        self,
                        upvContent,
                        resolution=resolution,
                        interpolation=interpolation,
                        unwindSwitch=unwindSwitch
                    )

                else:
                    sampler = r.networks.CurveUpVectorIkSplineStyleSampler.create(
                        self,
                        upvContent,
                        interpolation=interpolation)

            elif upvType == 'single':
                # Create either a parallel-transport solution, or a motion-
                # path style set up
                if parallelTransport:
                    if upObject is not None:
                        raise NotImplementedError(
                            "Unsupported combo: up vector and up object")

                    sampler = r.networks.CurveUpVectorPtSampler.create(
                        self,
                        upvContent,
                        resolution=resolution,
                        interpolation=interpolation)

                else:
                    sampler = r.networks.CurveUpVectorMpStyleSampler.create(
                        self, uo=upObject, upv=upVector)

            else: # 'multi'
                raise ValueError(
                    "upVector/upv should be a single up vector, or (param, "+
                    "vector) pairs")

        elif upObject is not None:
            if aimCurve:
                raise NotImplementedError(
                    "Unsupported combo: up object and aim curve")

            sampler = r.networks.CurveUpVectorMpStyleSampler.create(
                self, uo=upObject, upv=upVector)

        elif aimCurve is not None:
            # Create an aim curve setup
            sampler = r.networks.CurveUpVectorAimCurveSampler.create(
                self,
                aimCurve,
                closestPoint=closestPoint)

        else:
            sampler = r.networks.CurveUpVectorMpStyleSampler.create(self)

        if setAsDefault:
            sampler.setAsDefault()

        return sampler

    @copyToShape(worldSpaceOnly=True)
    def getUpVectorSamplers(self):
        """
        :return: All :meth:`up vector samplers <createUpVectorSampler>`
            created on this curve output.
        :rtype: [:class:`~paya.runtime.networks.CurveUpVectorSampler`]
        """
        nodes = [output.node().asSubtype() \
                 for output in self.outputs(type='network', plugs=True)]

        return [node for node in nodes \
                if isinstance(node, r.networks.CurveUpVectorSampler)]

    @copyToShape(worldSpaceOnly=True)
    def getDefaultUpVectorSampler(self):
        """
        :return: The last :meth:`up vector sampler <createUpVectorSampler>`
            that was created on this curve with ``setAsDefault=True``.
        :rtype: :class:`~paya.runtime.networks.CurveUpVectorSampler`
        """
        for output in self.outputs(type='network', plugs=True):
            if output.attrName() == 'defaultFor':
                out = output.node().asSubtype()
                return out

    @copyToShape(worldSpaceOnly=True)
    def clearUpVectorSamplers(self):
        """
        Removes all up vector samplers and their dependencies.

        .. warning::

            This *will* break any rigging that hangs off one or more of the
            samplers.
        """
        for sampler in self.getUpVectorSamplers():
            sampler.remove()

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    MATRICES
    #---------------------------------------------------------------|

    def _softMatrixAt(
            self,
            paramOrFraction,
            primaryAxis,
            secondaryAxis,
            upVector=None,
            upObject=None,
            aimCurve=None,
            closestPoint=True,
            upVectorSampler=None,
            defaultToNormal=None,
            parametric=True
    ):
        if parametric:
            param = paramOrFraction

        else:
            param = self.paramAtFraction(paramOrFraction, p=False)

        point = self.pointAtParam(param, p=False)
        tangent = self.tangentAtParam(param, p=False)

        if upVector is not None:
            upVector = r.data.Vector(upVector)

            if upObject is not None:
                upObject = r.PyNode(upObject)
                upVector *= upObject.getMatrix(worldSpace=True)

        elif upObject is not None:
            upObject = r.PyNode(upObject)
            upVector = upObject.getWorldPosition() - point

        elif aimCurve:
            aimCurve = _tm.asGeoPlug(aimCurve, ws=True)

            if closestPoint:
                interest = aimCurve.nearestPoint(point, p=False)

            else:
                interest = aimCurve.pointAtParam(param, p=False)

            upVector = interest-point

        else:
            if upVectorSampler:
                upVectorSampler = r.PyNode(upVectorSampler).asSubtype()

            elif not defaultToNormal:
                upVectorSampler = self.getDefaultUpVectorSampler()

            if upVectorSampler is None:
                upVector = self.normalAtParam(param, p=False)

            else:
                upVector = upVectorSampler.sampleAtParam(param, p=False)

        matrix = r.createMatrix(
            primaryAxis, tangent,
            secondaryAxis, upVector,
            t=point).pick(t=True, r=True)

        return matrix

    @copyToShape(worldSpaceOnly=True)
    @short(upVector='uvp',
           upObject='uo',
           aimCurve='aic',
           closestPoint='cp',
           upVectorSampler='ups',
           defaultToNormal='dtn',
           globalScale='gs',
           squashStretch='ss',
           plug='p')
    @plugCheck('param',
               'upVector',
               'globalScale')
    def matrixAtParam(self,
                      param,

                      primaryAxis,
                      secondaryAxis,

                      upVector=None,
                      upObject=None,

                      aimCurve=None,
                      closestPoint=True,

                      upVectorSampler=None,
                      defaultToNormal=None,

                      globalScale=None,
                      squashStretch=False,

                      plug=None):
        """
        .. note::
            Unlike :meth:`matrixAtFraction`, which uses a
            :class:`motionPath <paya.runtime.nodes.MotionPath>` node, this
            builds off of a
            :class:`pointOnCurveInfo <paya.runtime.nodes.PointOnCurveInfo>`.

        :param param: the parameter at which to construct the matrix
        :type param: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param str primaryAxis: the primary (aim) matrix axis, for example
            '-y'
        :param str secondaryAxis: the secondary (up) matrix axis, for example
            'x'
        :param upVector/upv: if provided on its own, used directly; if combined
            with *upObject*, multiplied by the object's world matrix, similar
            to the 'Object Rotation Up' mode on :class:`motion path
            <paya.runtime.nodes.MotionPath>` nodes; defaults to ``None``
        :type upVector/upv: None, str, tuple, list,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param upObject/uo: similar to :class:`motion path
            <paya.runtime.nodes.MotionPath>` nodes, if provided on its own,
            used as an aiming interest ('Object Up' mode); if combined with
            *upVector*, the up vector is multiplied by the object's world
            matrix ('Object Rotation Up' mode); defaults to ``None``
        :type upObject/uo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param aimCurve/aic: a curve from which to pull aiming interests,
            similar to the option on
            :class:`curveWarp <paya.runtime.nodes.CurveWarp>` nodes; defaults
            to ``None``
        :type aimCurve/aic: None, str,
            :class:`paya.runtime.plugs.NurbsCurve`,
            :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity,
            not matched parameters; defaults to ``True``
        :param upVectorSampler/ups: an up vector sampler created using
            :meth:`createUpVectorSampler`; defaults to ``None``
        :type upVectorSampler/ups: None, str, :class:`~paya.runtime.nodes.Network`,
            :class:`~paya.runtime.networks.CurveUpVectorSampler`
        :param bool defaultToNormal/dtn: when all other up vector options are
            exhausted, don't fall back to any 'default' up vector sampler
            previously created using
            :meth:`createUpVectorSampler(setAsDefault=True) <createUpVectorSampler>`;
            instead, use the curve normal (the curve normal will be used anyway
            if no default sampler is defined); defaults to ``False``
        :param globalScale/gs: a baseline scaling factor; note that scale will
            be normalized in all cases, so if this is value rather than a plug,
            it will have no practical effect; defaults to ``None``
        :type globalScale/gs: None, float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow squashing and stretching of the
            *primaryAxis* on the output matrix; defaults to ``False``
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: A matrix at the specified position.
        :rtype: :class:`paya.runtime.data.Matrix`, :class:`paya.runtime.plugs.Matrix`
        """
        if plug:
            if globalScale is not None:
                globalScale, gsDim, gsUnitType, gsIsPlug = \
                    _mo.info(globalScale).values()

                if gsIsPlug:
                    globalScale = globalScale.normal()

                else:
                    globalScale = 1.0
            else:
                globalScale = 1.0
                gsIsPlug = False

            poci = self.infoAtParam(param, p=True)
            point = poci.attr('position')
            tangent = poci.attr('tangent')

            if upVector is not None:
                upVector = _tm.conformVectorArg(upVector)

                if upObject is not None:
                    upObject = r.PyNode(upObject)
                    upVector *= upObject.attr('wm')

            elif upObject is not None:
                upObject = r.PyNode(upObject)
                interest = upObject.getWorldPosition(plug=True)
                upVector = interest-point

            elif aimCurve is not None:
                aimCurve = _tm.asGeoPlug(aimCurve, ws=True)

                if closestPoint:
                    interest = aimCurve.nearestPoint(point, p=True)

                else:
                    param = self.paramAtPoint(point, p=True)
                    interest = aimCurve.pointAtParam(param, p=True)

                upVector = interest-point

            else:
                if upVectorSampler is not None:
                    upVectorSampler = r.PyNode(upVectorSampler).asSubtype()

                elif not defaultToNormal:
                    upVectorSampler = self.getDefaultUpVectorSampler()

                if upVectorSampler is not None:
                    param = self.paramAtFraction(fraction, p=True)
                    upVector = upVectorSampler.sampleAtParam(param, p=True)

                else:
                    upVector = poci.attr('normal')

            matrix = r.createMatrix(primaryAxis,
                                    tangent,
                                    secondaryAxis,
                                    upVector,
                                    t=point
                                    ).pick(t=True, r=True)

            if gsIsPlug or squashStretch:
                factors = [globalScale] * 3

                if squashStretch:
                    tangentScale = tangent.length().normal()
                    tangentAxisIndex = 'xyz'.index(primaryAxis.strip('-'))
                    factors[tangentAxisIndex] = tangentScale

                smtx = r.createScaleMatrix(*factors)
                matrix = smtx * matrix

            return matrix

        return self._softMatrixAt(
            param,
            primaryAxis,
            secondaryAxis,
            upVector=upVector,
            upObject=upObject,
            aimCurve=aimCurve,
            closestPoint=closestPoint,
            upVectorSampler=upVectorSampler,
            defaultToNormal=defaultToNormal,
            parametric=True
        )

    @copyToShape(worldSpaceOnly=True)
    @short(upVector='uvp',
           upObject='uo',
           aimCurve='aic',
           closestPoint='cp',
           upVectorSampler='ups',
           defaultToNormal='dtn',
           globalScale='gs',
           squashStretch='ss',
           plug='p')
    @plugCheck('fraction',
               'upVector',
               'globalScale')
    def matrixAtFraction(self,
                         fraction,

                         primaryAxis,
                         secondaryAxis,

                         upVector=None,
                         upObject=None,

                         aimCurve=None,
                         closestPoint=True,

                         upVectorSampler=None,
                         defaultToNormal=None,

                         globalScale=None,
                         squashStretch=False,
                         plug=None):
        """
        .. note::
            Unlike :meth:`matrixAtParam`, which uses a
            :class:`pointOnCurveInfo <paya.runtime.nodes.PointOnCurveInfo` node,
            this builds off of a
            :class:`motionPath <paya.runtime.nodes.MotionPath>`.

        :param fraction: the fraction at which to construct the matrix
        :type fraction: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param str primaryAxis: the primary (aim) matrix axis, for example
            '-y'
        :param str secondaryAxis: the secondary (up) matrix axis, for example
            'x'
        :param upVector/upv: if provided on its own, used directly; if combined
            with *upObject*, multiplied by the object's world matrix, similar
            to the 'Object Rotation Up' mode on :class:`motion path
            <paya.runtime.nodes.MotionPath>` nodes; defaults to ``None``
        :type upVector/upv: None, str, tuple, list,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param upObject/uo: similar to :class:`motion path
            <paya.runtime.nodes.MotionPath>` nodes, if provided on its own,
            used as an aiming interest ('Object Up' mode); if combined with
            *upVector*, the up vector is multiplied by the object's world
            matrix ('Object Rotation Up' mode); defaults to ``None``
        :type upObject/uo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param aimCurve/aic: a curve from which to pull aiming interests,
            similar to the option on :class:`curveWarp <paya.runtime.nodes.CurveWarp>`
            nodes; defaults to ``None``
        :type aimCurve/aic: None, str,
            :class:`paya.runtime.plugs.NurbsCurve`,
            :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity,
            not matched parameters; defaults to ``True``
        :param upVectorSampler/ups: an up vector sampler created using
            :meth:`createUpVectorSampler`; defaults to ``None``
        :type upVectorSampler/ups: None, str, :class:`~paya.runtime.nodes.Network`,
            :class:`~paya.runtime.networks.CurveUpVectorSampler`
        :param bool defaultToNormal/dtn: when all other up vector options are
            exhausted, don't fall back to any 'default' up vector sampler
            previously created using
            :meth:`createUpVectorSampler(setAsDefault=True) <createUpVectorSampler>`;
            instead, use the curve normal (the curve normal will be used anyway
            if no default sampler is defined); defaults to ``False``
        :param globalScale/gs: a baseline scaling factor; note that scale will
            be normalized in all cases, so if this is value rather than a plug,
            it will have no practical effect; defaults to ``None``
        :type globalScale/gs: None, float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow squashing and stretching of the
            *primaryAxis* on the output matrix; defaults to ``False``
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: A matrix at the specified position.
        :rtype: :class:`paya.runtime.data.Matrix`, :class:`paya.runtime.plugs.Matrix`
        """
        if plug:
            if globalScale is not None:
                globalScale, gsDim, gsUnitType, gsIsPlug = \
                    _mo.info(globalScale).values()

                if gsIsPlug:
                    globalScale = globalScale.normal()

                else:
                    globalScale = 1.0
            else:
                globalScale = 1.0
                gsIsPlug = False

            mp = self.motionPathAtFraction(fraction)
            point = mp.attr('allCoordinates')
            configKw = {}

            if upVector is not None:
                configKw['worldUpVector'] = upVector
                configKw['worldUpObject'] = upObject

            elif upObject is not None:
                configKw['worldUpObject'] = upObject

            elif aimCurve is not None:
                aimCurve = _tm.asGeoPlug(aimCurve, ws=True)

                if closestPoint:
                    interest = aimCurve.nearestPoint(point, p=True)

                else:
                    param = self.paramAtPoint(point, p=True)
                    interest = aimCurve.pointAtParam(param, p=True)

                configKw['worldUpVector'] = interest-point

            else:
                if upVectorSampler is not None:
                    upVectorSampler = r.PyNode(upVectorSampler).asSubtype()

                elif not defaultToNormal:
                    upVectorSampler = self.getDefaultUpVectorSampler()

                if upVectorSampler is not None:
                    param = self.paramAtFraction(fraction, p=True)
                    configKw['worldUpVector'
                        ] = upVectorSampler.sampleAtParam(param, p=True)

                # In all other cases, just leave it to configFollow() to
                # default to the normal

            mp.configFollow(primaryAxis, secondaryAxis, **configKw)

            rsmatrix = mp.attr('orientMatrix')

            if gsIsPlug or squashStretch:
                factors = [globalScale] * 3

                if squashStretch:
                    tangent = rsmatrix.getAxis(primaryAxis)
                    tangentScale = tangent.length().normal()
                    tangentAxisIndex = 'xyz'.index(primaryAxis.strip('-'))
                    factors[tangentAxisIndex] = tangentScale

                smtx = r.createScaleMatrix(*factors)
                rsmatrix = smtx * rsmatrix.pick(r=True)

            else:
                rsmatrix = rsmatrix.pick(r=True)

            tmtx = point.asTranslateMatrix()
            return rsmatrix * tmtx

        return self._softMatrixAt(
            fraction,
            primaryAxis,
            secondaryAxis,
            upVector=upVector,
            upObject=upObject,
            aimCurve=aimCurve,
            closestPoint=closestPoint,
            upVectorSampler=upVectorSampler,
            defaultToNormal=defaultToNormal,
            parametric=False
        )

    @copyToShape(worldSpaceOnly=True)
    @short(parametric='par',
           plug='p')
    def matrixAtParamOrFraction(self,
                 paramOrFraction,
                 primaryAxis,
                 secondaryAxis,
                 parametric=True,
                 plug=None,
                 **kwargs):
        """
        Dispatches :meth:`matrixAtParam` or :meth:`matrixAtFraction`. See
        either of those for full parameter information.

        :param paramOrFraction: the parameter or fraction at which
            to construct a matrix
        :type paramOrFraction: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param str primaryAxis: the primary (aim) matrix axis, for example
            '-y'
        :param str secondaryAxis: the secondary (up) matrix axis, for example
            'x'
        :param bool parametric: interpret *paramOrFraction* as a U parameter
            rather than a length fraction; defaults to ``True``
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :param \*\*kwargs: forwarded to :meth:`matrixAtParam` or
            :meth:`matrixAtFraction
        :return: A matrix at the specified position.
        :rtype: :class:`paya.runtime.data.Matrix`,
            :class:`paya.runtime.plugs.Matrix`
        """
        meth = self.matrixAtParam if parametric else self.matrixAtFraction

        return meth(paramOrFraction,
                    primaryAxis,
                    secondaryAxis,
                    p=plug, **kwargs)

    @copyToShape(worldSpaceOnly=True)
    @short(plug='p')
    def matrixAtPoint(self, point,
                      primaryAxis, secondaryAxis,
                      plug=None, **kwargs):
        """
        Finds the closest parameter to *point* and dispatches
        :meth:`matrixAtParam`. See that method for full parameter information.

        :param point: the reference point
        :type point: tuple, list, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param str primaryAxis: the primary (aim) matrix axis, for example
            '-y'
        :param str secondaryAxis: the secondary (up) matrix axis, for example
            'x'
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :param \*\*kwargs: forwarded to :meth:`matrixAtParam`
        :return: A matrix at the specified position.
        :rtype: :class:`paya.runtime.data.Matrix`,
            :class:`paya.runtime.plugs.Matrix`
        """
        param = self.paramAtPoint(point, p=plug)

        return self.matrixAtParam(param, primaryAxis,
                                  secondaryAxis, p=plug, **kwargs)

    @copyToShape(worldSpaceOnly=True)
    @short(plug='p')
    def matrixAtLength(self, length,
                      primaryAxis, secondaryAxis,
                      plug=None, **kwargs):
        """
        Finds the parameter at *length* and dispatches
        :meth:`matrixAtParam`. See that method for full parameter information.

        :param length: the partial length at which to construct the matrix
        :type length: tuple, list, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param str primaryAxis: the primary (aim) matrix axis, for example
            '-y'
        :param str secondaryAxis: the secondary (up) matrix axis, for example
            'x'
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :param \*\*kwargs: forwarded to :meth:`matrixAtParam`
        :return: A matrix at the specified position.
        :rtype: :class:`paya.runtime.data.Matrix`,
            :class:`paya.runtime.plugs.Matrix`
        """
        param = self.paramAtLength(length, p=plug)

        return self.matrixAtParam(param, primaryAxis,
                                  secondaryAxis, p=plug, **kwargs)

    def _distributeMatrices(
            self,
            numberFractionsOrParams,
            primaryAxis,
            secondaryAxis,

            parametric=False,
            uniform=False,

            upVector=None,
            upObject=None,

            aimCurve=None,
            closestPoint=True,

            upVectorSampler=None,
            defaultToNormal=None,

            globalScale=None,
            squashStretch=False,

            plug=True):

        #--------------------------------|    Resolve params / fractions

        fractionsOrParams = self._resolveNumberFractionsOrParams(
            numberFractionsOrParams,
            parametric=parametric,
            uniform=uniform
        )

        num = len(fractionsOrParams)

        #--------------------------------|    Resolve multi args

        if upObject is None:
            upObjects = [None] * num

        elif isinstance(upObject, (tuple, list)):
            if len(upObject) is not num:
                raise ValueError("Incorrect number of up objects.")

            upObjects = [r.PyNode(x) for x in upObject]

        if upVector is None:
            upVectors = [None] * num

        else:
            descr, upVector = _tm.describeAndConformVectorArg(upVector)

            if descr == 'multi':
                upVectors = upVector
                if len(upVector) is not num:
                    raise ValueError("Incorrect number of up vectors.")

                upVectors = upVector

            elif descr == 'single':
                upVectors = [_tm.conformVectorArg(upVector)] * num

            else:
                raise ValueError(
                    "Up vector argument was neither a "+
                    "single vector nor a list of vectors.")

        #--------------------------------|    Dispatch

        out = []

        meth = self.matrixAtParam if parametric else self.matrixAtFraction

        for i, fractionOrParam, upVector, upObject in zip(
            range(num), fractionsOrParams, upVectors, upObjects
        ):
            with r.Name(i+1):
                matrix = meth(
                    fractionOrParam,
                    primaryAxis,
                    secondaryAxis,
                    upVector=upVector,
                    upObject=upObject,
                    aimCurve=aimCurve,
                    closestPoint=closestPoint,
                    upVectorSampler=upVectorSampler,
                    defaultToNormal=defaultToNormal,
                    globalScale=globalScale,
                    squashStretch=squashStretch,
                    plug=plug)

                out.append(matrix)

        return out

    def _distributeAimingMatrices(
            self,
            numberFractionsOrParams,
            primaryAxis,
            secondaryAxis,

            parametric=False,
            uniform=False,

            upVector=None,
            upObject=None,

            aimCurve=None,
            closestPoint=True,

            upVectorSampler=None,
            defaultToNormal=None,

            globalScale=None,
            squashStretch=False,

            plug=True):

        fractionsOrParams = self._resolveNumberFractionsOrParams(
            numberFractionsOrParams,
            par=parametric,
            uni=uniform)

        number = len(fractionsOrParams)

        # Convert to params and go from there
        if parametric:
            params = fractionsOrParams

        else:
            params = [self.paramAtFraction(f,
                    p=plug) for f in fractionsOrParams]

        points = [self.pointAtParam(param, p=plug) for param in params]

        aimVectors = [nextPoint-thisPoint for \
                      thisPoint, nextPoint in zip(points, points[1:])]

        aimVectors.append(aimVectors[-1])

        # Analyse up vector / up object
        if upVector is not None:
            upVecType, upVector = _tm.describeAndConformVectorArg(upVector)

            if upVecType == 'multi':
                if len(upVector) is not number:
                    raise ValueError("Wrong number of up vectors.")

                multiUpVector = True

            else:
                multiUpVector = False

        if upObject is not None:
            if hasattr(upObject, '__iter__') \
                    and not isinstance(upObject, r.PyNode):
                if len(upObject) is not number:
                    raise ValueError("Wrong number of up objects.")

                upObject = list(map(r.PyNode, upObject))
                multiUpObject = True

            else:
                upObject = r.PyNode(upObject)
                multiUpObject = False

        if (upVector is not None) or (upObject is not None):
            if upVector is not None:
                if multiUpVector:
                    upVectors = upVector

                    if upObject is not None:
                        if multiUpObject:
                            upObjects = upObject
                            upVectors = [upVector \
                                         * upObject.attr('wm').get(p=plug) \
                                         for upVector, upObject \
                                         in zip(upVectors, upObjects)]

                        else:
                            upVectors = [upVector \
                                         * upObject.attr('wm').get(p=plug) \
                                         for upVector in upVectors]

                else:
                    if upObject is not None:
                        if multiUpObject:
                            upObjects = upObject
                            upVectors = [upVector \
                                         * upObject.attr('wm').get(p=plug) \
                                         for upObject in upObjects]
                        else:
                            upVector *= upObject.attr('wm').get(p=plug)
                            upVectors = [upVector] * number

                    else:
                        upVectors = [upVector] * number

            else: # up object only
                if multiUpObject:
                    upObjects = upObject
                    interests = [upObject.getWorldPosition(p=plug) \
                                 for upObject in upObjects]

                    upVectors = [interest-point for interest, point \
                                 in zip(interests, points)]

                else:
                    interest = upObject.getWorldPosition(p=plug)
                    upVectors = [interest-point for point in points]

        elif aimCurve:
            if closestPoint:
                interests = [aimCurve.nearestPoint(
                    point, p=plug) for point in points]

            else:
                interests = [aimCurve.pointAtParam(
                    param, p=plug) for param in params]

            upVectors = [interest-point for \
                         interest, point in zip(interests, points)]

        else:
            if upVectorSampler is not None:
                upVectorSampler = r.PyNode(upVectorSampler).asSubtype()

            elif not defaultToNormal:
                upVectorSampler = self.getDefaultUpVectorSampler()

            if upVectorSampler is None:
                upVectors = [self.normalAtParam(
                    param, p=plug) for param in params]

            else:
                upVectors = [upVectorSampler.sampleAtParam(
                        param, p=plug) for param in params]

        if plug:
            if globalScale is None:
                globalScale = 1.0
                gsIsPlug = False

            else:
                globalScale, gsDim, gsUnitType, gsIsPlug = \
                    _mo.info(globalScales).values()

            if squashStretch:
                aimIndex = 'xyz'.index(primaryAxis.strip('-'))

        matrices = []

        for aimVector, upVector, point in zip(
            aimVectors, upVectors, points
        ):
            matrix = r.createMatrix(
                primaryAxis, aimVector,
                secondaryAxis, upVector,
                t=point
            ).pick(t=True, r=True)

            if plug and (gsIsPlug or squashStretch):
                factors = [globalScale] * 3

                if squashStretch:
                    factors[aimIndex] = aimVector.length().normal()

                smtx = r.createScaleMatrix(*factors)
                matrix = smtx * matrix

            matrices.append(matrix)

        return matrices

    @copyToShape(worldSpaceOnly=True)
    @short(parametric='par',
           uniform='uni',
           chain='cha',
           upVector='upv',
           upObject='uo',
           aimCurve='aic',
           closestPoint='cp',
           upVectorSampler='ups',
           defaultToNormal='dtn',
           globalScale='gs',
           squashStretch='ss',
           plug='p')
    @plugCheck('numberFractionsOrParams',
               'upVector',
               'globalScale')
    def distributeMatrices(
            self,
            numberFractionsOrParams,

            primaryAxis,
            secondaryAxis,

            parametric=False,
            uniform=False,

            chain=False,

            upVector=None,
            upObject=None,

            aimCurve=None,
            closestPoint=True,

            upVectorSampler=None,
            defaultToNormal=None,

            globalScale=None,
            squashStretch=False,

            plug=None):
        """
        :param numberFractionsOrParams: this should either be

            -   A number of fractions or parameters to generate along the curve,
                or
            -   An explicit list of fractions or parameters at which to construct
                the matrices

        :param str primaryAxis: the primary (aim) matrix axis, for example
            '-y'
        :param str secondaryAxis: the secondary (up) matrix axis, for example
            'x'
        :param bool parametric/par: interpret *numberOrFractions* as
            parameters, not fractions; defaults to ``False``
        :param bool uniform/uni: if *parametric* is ``True``, and
            *numberFractionsOrParams* is a number, initial parameters should
            be distributed by length, not parametric space; defaults to
            ``False``
        :param bool chain/cha: aim each matrix towards the next in the
            series, similar to chain joints; defaults to ``False``
        :param upVector/upv: either

            -   A single up vector, or
            -   A list of up vectors (one per matrix)

            If up vectors are provided on their own, they are used directly;
            if they are combined with 'up objects' (*upObject*), they are
            multiplied by the objects' world matrices, similar
            to the 'Object Rotation Up' mode on :class:`motion path
            <paya.runtime.nodes.MotionPath>` nodes; defaults to ``None``
        :type upVector/upv: :class:`None`, :class:`str`, :class:`tuple`, :class:`list`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`,
            [:class:`None` | :class:`str` | :class:`tuple` | :class:`list` |
            :class:`~paya.runtime.data.Vector` |
            :class:`~paya.runtime.plugs.Vector`]
        :param upObject/uo: this can be a single transform, or a list of
            transforms (one per sample point); if provided on its own, used
            as an aiming interest (similar to 'Object Up' mode on
            :class:`motionPath <paya.runtime.nodes.MotionPath>` nodes); if
            combined with *upVector*, the vector will be multiplied with the
            object's matrix (similar to 'Object Rotation Up'); defaults to
            ``None``
        :type upObject/uo: ``None``, :class:`str`,
            :class:`~paya.runtime.nodes.Transform`
        :param aimCurve/aic: a curve from which to pull aiming interests,
            similar to the option on :class:`curveWarp <paya.runtime.nodes.CurveWarp>`
            nodes; defaults to ``None``
        :type aimCurve/aic: None, str,
            :class:`paya.runtime.plugs.NurbsCurve`,
            :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity,
            not matched parameters; defaults to ``True``
        :param upVectorSampler/ups: an up vector sampler created using
            :meth:`createUpVectorSampler`; defaults to ``None``
        :type upVectorSampler/ups: None, str, :class:`~paya.runtime.nodes.Network`,
            :class:`~paya.runtime.networks.CurveUpVectorSampler`
        :param bool defaultToNormal/dtn: when all other up vector options are
            exhausted, don't fall back to any 'default' up vector sampler
            previously created using
            :meth:`createUpVectorSampler(setAsDefault=True) <createUpVectorSampler>`;
            instead, use the curve normal (the curve normal will be used anyway
            if no default sampler is defined); defaults to ``False``
        :param globalScale/gs: a baseline scaling factor; note that scale will
            be normalized in all cases, so if this is value rather than a plug,
            it will have no practical effect; defaults to ``None``
        :type globalScale/gs: None, float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow squashing and stretching of the
            *primaryAxis* on the output matrix; defaults to ``False``
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: A matrix at the specified position.
        :rtype: :class:`paya.runtime.data.Matrix`,
            :class:`paya.runtime.plugs.Matrix`
        """
        if chain:
            meth = self._distributeAimingMatrices

        else:
            meth = self._distributeMatrices

        return meth(
            numberFractionsOrParams,
            primaryAxis, secondaryAxis,
            parametric=parametric,
            uniform=uniform,
            upVector=upVector,
            upObject=upObject,
            aimCurve=aimCurve,
            closestPoint=closestPoint,
            upVectorSampler=upVectorSampler,
            defaultToNormal=defaultToNormal,
            globalScale=globalScale,
            squashStretch=squashStretch,
            plug=plug
        )

    @copyToShape(worldSpaceOnly=True)
    @short(
        parametric='ar',
        uniform='uni',
        upVector='upv',
        upObject='uo',
        aimCurve='aic',
        closestPoint='cp',
        upVectorSampler='ups',
        defaultToNormal='dtn',
        globalScale='gs',
        squashStretch='ss',
        chain='cha',
        displayLocalAxis='dla',
        radius='rad',
        rotateOrder='ro',
        parent='p',
        freeze='fr',
        decompose='dec',
        plug='p'
    )
    def distributeJoints(self,
                         numberFractionsOrParams,
                         primaryAxis, secondaryAxis,

                         parametric=False,
                         uniform=False,

                         upVector=None,
                         upObject=None,
                         aimCurve=None,
                         closestPoint=True,

                         upVectorSampler=None,
                         defaultToNormal=None,

                         globalScale=None,
                         squashStretch=False,

                         chain=False,
                         displayLocalAxis=True,
                         radius=1.0,
                         rotateOrder='xyz',
                         parent=None,
                         freeze=True,
                         decompose=True,

                         plug=False):
        """
        Distributes joints along this curve. Pass *plug/p=True* for live
        connections.

        :param numberFractionsOrParams: this should either be

            -   A number of fractions or parameters to generate along the curve,
                or
            -   An explicit list of fractions or parameters at which to construct
                the matrices

        :param str primaryAxis: the primary (aim) matrix axis, for example
            '-y'
        :param str secondaryAxis: the secondary (up) matrix axis, for example
            'x'
        :param bool parametric/par: interpret *numberOrFractions* as
            parameters, not fractions; defaults to ``False``
        :param bool uniform/uni: if *parametric* is ``True``, and
            *numberFractionsOrParams* is a number, initial parameters should
            be distributed by length, not parametric space; defaults to
            ``False``
        :param upVector/upv: either

            -   A single up vector, or
            -   A list of up vectors (one per matrix)

            If up vectors are provided on their own, they are used directly;
            if they are combined with 'up objects' (*upObject*), they are
            multiplied by the objects' world matrices, similar
            to the 'Object Rotation Up' mode on :class:`motion path
            <paya.runtime.nodes.MotionPath>` nodes; defaults to ``None``
        :type upVector/upv: :class:`None`, :class:`str`, :class:`tuple`, :class:`list`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`,
            [:class:`None` | :class:`str` | :class:`tuple` | :class:`list` |
            :class:`~paya.runtime.data.Vector` |
            :class:`~paya.runtime.plugs.Vector`]
        :param upObject/uo: this can be a single transform, or a list of
            transforms (one per sample point); if provided on its own, used
            as an aiming interest (similar to 'Object Up' mode on
            :class:`motionPath <paya.runtime.nodes.MotionPath>` nodes); if
            combined with *upVector*, the vector will be multiplied with the
            object's matrix (similar to 'Object Rotation Up'); defaults to
            ``None``
        :type upObject/uo: ``None``, :class:`str`,
            :class:`~paya.runtime.nodes.Transform`
        :param aimCurve/aic: a curve from which to pull aiming interests,
            similar to the option on
            :class:`curveWarp <paya.runtime.nodes.CurveWarp>`
            nodes; defaults to ``None``
        :type aimCurve/aic: None, str,
            :class:`paya.runtime.plugs.NurbsCurve`,
            :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity,
            not matched parameters; defaults to ``True``
        :param upVectorSampler/ups: an up vector sampler created using
            :meth:`createUpVectorSampler`; defaults to ``None``
        :type upVectorSampler/ups: None, str,
            :class:`~paya.runtime.nodes.Network`,
            :class:`~paya.runtime.networks.CurveUpVectorSampler`
        :param bool defaultToNormal/dtn: when all other up vector options are
            exhausted, don't fall back to any 'default' up vector sampler
            previously created using
            :meth:`createUpVectorSampler(
                setAsDefault=True) <createUpVectorSampler>`;
            instead, use the curve normal (the curve normal will be used anyway
            if no default sampler is defined); defaults to ``False``
        :param globalScale/gs: a baseline scaling factor; note that scale will
            be normalized in all cases, so if this is value rather than a plug,
            it will have no practical effect; defaults to ``None``
        :type globalScale/gs: None, float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow squashing and stretching of the
            *primaryAxis* on the output matrix; defaults to ``False``
        :param bool chain/cha: create the joints as a contiguous chain with
            aimed, rather than tangent-based, matrix orientation; defaults to
            ``False``
        :param bool displayLocalAxis/dla: display the local matrix
            axes; defaults to ``True``
        :param float radius/rad: the joint display radius; defaults to 1.0
        :param rotateOrder/ro: the rotate order for the joint; defaults
            to ``'xyz'``
        :type rotateOrder/ro: ``None``, :class:`str`, :class:`int`,
            :class:`~paya.runtime.plugs.Math1D`
        :param parent/p: an optional destination parent for the joints
        :type parent/p: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool freeze/fr: zero-out transformations (except translate)
            at the initial pose; defaults to ``True``
        :param bool decompose/dec: if ``False``, connect to
            ``offsetParentMatrix`` instead of driving the joint's SRT
            channels; note that, if *freeze* is requested, the initial matrix
             will *always* be applied via decomposition and then frozen;
             defaults to ``True``
        :param bool plug/p: drive the joints dynamically; defaults to
            ``False``
        :return: The individual joints or a chain (if *chain* was requested).
        :rtype: [:class:`~paya.runtime.nodes.Joint`] |
            :class:`~paya.lib.skel.Chain`
        """
        matrices = self.distributeMatrices(
            numberFractionsOrParams,
            primaryAxis, secondaryAxis,
            par=parametric, uni=uniform,
            upv=upVector, uo=upObject,
            aic=aimCurve, cp=closestPoint,
            ups=upVectorSampler, dtn=defaultToNormal,
            gs=globalScale, ss=squashStretch,
            cha=chain, p=plug
        )

        joints = []

        for i, matrix in enumerate(matrices):
            with r.Name(i+1):
                joint = r.nodes.Joint.create(wm=matrix, p=parent,
                                             ro=rotateOrder,
                                             dla=displayLocalAxis,
                                             fr=freeze, dec=decompose)
                joints.append(joint)

        if chain:
            for thisJoint, nextJoint in zip(joints, joints[1:]):
                nextJoint.setParent(thisJoint)

            return r.Chain(joints)

        return joints

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    EDITING
    #---------------------------------------------------------------|

    #-----------------------------------------------|    Conversions

    @copyToShape(editsHistory=True,
                 bezierInterop=False)
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

    @copyToShape(editsHistory=True,
                 bezierInterop=False)
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

    @copyToShape(editsHistory=True)
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

    #-----------------------------------------------|    Attach / detach

    @copyToShape(editsHistory=True)
    @short(relative='r')
    def subCurve(self, minValue, maxValue, relative=False):
        """
        Connects and configures a ``subCurve`` node and returns its output.

        :alias: ``sub``
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

        return node.attr('outputCurve')

    sub = subCurve

    @copyToShape(editsHistory=True)
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
        .. note::

            If more than one curves are passed-in, the result may
            be different from calling :meth:`detach` per pair, because
            the ``inputCurves`` array will be used on the node.

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
        curves = [_tm.asGeoPlug(curve) for curve in _pu.expandArgs(*curves)]
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

    @copyToShape(editsHistory=True)
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

    #-----------------------------------------------|    Length editing

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

    @copyToShape(editsHistory=True)
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
        cutLength, cutLengthDim, cutLengthUnitType, cutLengthIsPlug = \
            _mo.info(length).values()

        if atStart:
            cutLengths = [cutLength]
            select = 1

        elif atBothEnds:
            cutLength *= 0.5
            cutLengths = [cutLength, self.length(p=True)-cutLength]
            select = 1

        else:
            cutLengths = [self.length(p=True)-cutLength]
            select = 0

        params = [self.paramAtLength(cutLength,
                                     p=True) for cutLength in cutLengths]

        return self.detach(*params, select=select)[0]

    @copyToShape(editsHistory=True)
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
            start; defaults to ``False``
        :param vector: a vector along which to extend; this is recommended for
            spine setups where tangency should be more tightly controlled; if
            this is omitted, the *linear / circular / extrapolate* modes will
            be used instead
        :type vector: None, tuple, list, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool circular/cir: ignored if *vector* was provided; use the
            'circular' mode of the ``extendCurve`` node; defaults to ``False``
        :param bool linear/lin: ignored if *vector* was provided;
            use the 'linear' mode of the ``extendCurve`` node; defaults to
            ``False``
        :param bool extrapolate/ext: ignored if *vector* was provided;
            use the 'extrapolate' mode of the ``extendCurve`` node; defaults
            to ``Tru``e``
        :param bool multipleKnots: keep multiple knots; defaults to ``True``
        :return:
        """
        baseLength = self.length(p=True)

        retractLength = baseLength-targetLength
        retractLength = retractLength.minClamp(0.0)

        extendLength = targetLength-baseLength

        # The following is 0.1 and not 0.0 to avoid node calc errors; the
        # output will be switched out anyway
        extendLength = extendLength.minClamp(0.1)

        if vector is None:
            extension = self.extendByLength(
                extendLength,
                cir=circular,
                lin=linear,
                ext=extrapolate,
                mul=multipleKnots,
                ats=atStart
            )

        else:
            vector = _mo.info(vector)['item']
            vector = vector.normal() * extendLength

            extension = self.extendByVector(
                vector,
                ats=atStart,
                mul=multipleKnots,
                seg=True
            )

        retraction = self.retract(retractLength, ats=atStart)
        return baseLength.ge(targetLength).ifElse(retraction, extension)

    @copyToShape(editsHistory=True)
    @short(atStart='ats',
           atEnd='ate',
           point='pt',
           linear='lin',
           circular='cir',
           extrapolate='ext',
           multipleKnots='mul')
    def extendByLength(self,
                          length,
                          circular=None,
                          linear=None,
                          extrapolate=None,
                          atStart=None,
                          atEnd=None,
                          multipleKnots=True):
        """
        :param length: the length to add to the curve
        :type length: :class:`float`, :class:`~paya.runtime.plugs.Math1D`
        :param bool circular: use a circular extension; defaults to ``False``
        :param bool linear: use a linear extension; defaults to ``True``
        :param bool extrapolate: use an extrapolated extension; defaults to
            ``False``
        :param bool atStart: extend at the start of the curve; defaults to
            ``False``
        :param bool atEnd: extend at the start of the curve; defaults to
            ``True``
        :param bool multipleKnots/mul: preserve multiple knots; defaults to
            ``True``
        :return: This curve output, extended accordingly.
        :rtype: :class:`NurbsCurve`
        """

        if (atStart is None) and (atEnd is None):
            atStart, atEnd = False, True

        circular, linear, extrapolate = resolveFlags(
            circular, linear, extrapolate,
            radio=1
        )

        lenInfo = r.mathInfo(length)
        length, lenIsPlug = lenInfo['item'], lenInfo['isPlug']

        if lenIsPlug:
            # Guard
            lenIsZero = length.le(1e-7)
            safeLength = length.minClamp(1.0)
            length = lenIsZero.ifElse(safeLength, length)

        elif length == 0.0:
            r.warning("Requested length is 0.0, skipping.")
            return self

        #---------------------------|    Configure node

        node = r.nodes.ExtendCurve.createNode()
        self >> node.attr('inputCurve1')
        node.attr('extensionType').set(0 if linear else 1 if circular else 2)
        length >> node.attr('distance')

        if atStart:
            if atEnd:
                node.attr('start').set(2)
            else:
                node.attr('start').set(1)
        else:
            node.attr('start').set(0)

        node.attr('removeMultipleKnots').set(not multipleKnots)
        output = node.attr('outputCurve')

        if lenIsPlug:
            # Guard
            output = lenIsZero.ifElse(self, output)

        return output

    @copyToShape(editsHistory=True)
    @short(atStart='ats',
           useSegment='seg',
           multipleKnots='mul')
    def extendByVector(self,
                       vector,
                       atStart=False,
                       useSegment=False,
                       multipleKnots=True):
        """
        :param vector: the vector along which to extend
        :type vector: :class:`list` [:class:`float`],
            :class:`str`, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param atStart: extend at the start of the curve; defaults to
            ``False``
        :param bool useSegment/seg: uses an attached line segment for the
            extension; defaults to ``False``
        :param bool multipleKnots/mul: preserve multiple knots; defaults to
            ``True``
        :return: This curve output, extended along the specified vector.
        :rtype: :class:`NurbsCurve`
        """
        #---------------------------------|    Wrangle info

        vector = r.conform(vector)
        vecIsPlug = isinstance(vector, r.Attribute)

        if (not vecIsPlug) and vector.length() <= 1e-7:
            r.warning("Requested length is 0.0, skipping.")
            return self

        #---------------------------------|    Resolve end point

        anchorCVIndex = 0 if atStart else self.numCVs()-1
        anchor = self.pointAtCV(anchorCVIndex, plug=True)
        point = anchor + vector

        #---------------------------------|    Dispatch

        if useSegment:
            # NB no guarding necessary
            line = self.createLine(anchor, point)

            if atStart:
                return self.reverse().attach(
                    line, mul=multipleKnots).reverse()

            return self.attach(line, mul=multipleKnots)

        else:
            node = r.nodes.ExtendCurve.createNode()

            node.attr('distance').set(1.0) # for guarding
            self >> node.attr('inputCurve1')
            point >> node.attr('inputPoint')
            node.attr('removeMultipleKnots').set(not multipleKnots)
            node.attr('start').set(1 if atStart else 0)

            if vecIsPlug:
                # Guard by switching mode out
                length = vector.length()
                lenIsZero = length.le(1e-7)

                methodWhenZero = node.addAttr('methodWhenZero', dv=0)
                methodWhenNotZero = node.addAttr('methodWhenNotZero', dv=2)

                lenIsZero.ifElse(methodWhenZero,
                    methodWhenNotZero) >> node.attr('extendMethod')

            output = node.attr('outputCurve')

            if vecIsPlug:
                output = lenIsZero.ifElse(self, output)

            return output

    @copyToShape(editsHistory=True)
    @short(atStart='ats',
           useSegment='seg',
           multipleKnots='mul')
    def extendByPoint(self,
                       point,
                       atStart=False,
                       useSegment=False,
                       multipleKnots=True):
        """
        :param point: the point towards which to extend
        :type point: :class:`list` [:class:`float`],
            :class:`str`, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param atStart: extend at the start of the curve; defaults to
            ``False``
        :param bool useSegment/seg: uses an attached line segment for the
            extension; defaults to ``False``
        :param bool multipleKnots/mul: preserve multiple knots; defaults to
            ``True``
        :return: This curve output, extended towards the specified point.
        :rtype: :class:`NurbsCurve`
        """
        point = r.conform(point)
        pointIsPlug = isinstance(point, r.Attribute)

        anchorCVIndex = 0 if atStart else self.numCVs()-1

        if not pointIsPlug:
            _anchor = self.pointAtCV(anchorCVIndex, plug=False)
            _vec = point-_anchor

            if _vec.length() <= 1e-7:
                r.warning("Requested length is 0.0, skipping.")
                return self

        anchor = self.pointAtCV(anchorCVIndex, plug=True)

        #---------------------------------|    Dispatch

        if useSegment:
            line = self.createLine(anchor, point)

            if atStart:
                return self.reverse().attach(
                    line, mul=multipleKnots).reverse()

            return self.attach(line, mul=multipleKnots)

        else:
            node = r.nodes.ExtendCurve.createNode()

            node.attr('distance').set(1.0) # for guarding
            self >> node.attr('inputCurve1')
            point >> node.attr('inputPoint')
            node.attr('removeMultipleKnots').set(not multipleKnots)
            node.attr('start').set(1 if atStart else 0)

            if vecIsPlug:
                # Guard by switching mode out

                vector = point-anchor
                length = vector.length()
                lenIsZero = length.le(1e-7)

                methodWhenZero = node.addAttr('methodWhenZero', dv=0)
                methodWhenNotZero = node.addAttr('methodWhenNotZero', dv=2)

                lenIsZero.ifElse(methodWhenZero,
                    methodWhenNotZero) >> node.attr('extendMethod')

            output = node.attr('outputCurve')

            if vecIsPlug:
                output = lenIsZero.ifElse(self, output)

            return output

    @copyToShape(editsHistory=True)
    @short(atStart='ats',
           atEnd='ate',
           point='pt',
           vector='vec',
           length='ln',
           multipleKnots='mul',
           useSegment='seg')
    def extend(self,
               atStart=None,
               atEnd=None,
               point=None,
               vector=None,
               length=None,
               multipleKnots=True,
               useSegment=False):
        """
        :param length: the length to add to the curve; defaults to ``None``
        :type length: :class:`float`, :class:`~paya.runtime.plugs.Math1D`
        :param vector: the vector along which to extend; defaults to ``None``
        :type vector: :class:`list` [:class:`float`],
            :class:`str`, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param point: the point towards which to extend; defaults to ``None``
        :type point: :class:`list` [:class:`float`],
            :class:`str`, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param atStart: extend at the start of the curve; defaults to
            ``False``
        :param atEnd: extend at the start of the curve; defaults to
            ``True``
        :param bool useSegment/seg: uses an attached line segment for the
            extension (vector / point only); defaults to ``False``
        :param bool multipleKnots/mul: preserve multiple knots; defaults to
            ``True``
        :raises ValueError: One of:

            -   More than one of *vector*, *point* or *length* were specified.
            -   Both *atStart* and *atEnd* were specified when extending with
                point / vector.
            -   None of *vector*, *point* or *length* were specified.
            -   The *useSegment* option was requested when extending by curve.

        :return: This curve output, extended accordingly.
        :rtype: :class:`NurbsCurve`
        """

        if point is not None:
            if (vector is not None) or (length is not None):
                raise ValueError(
                    "Please specify a point, a vector or a length."
                )

            if atStart and atEnd:
                raise ValueError(
                    "Extending in both directions not available with point / vector."
                )

            return self.extendByPoint(
                point,
                atStart=atStart if atStart is not None else False,
                multipleKnots=multipleKnots,
                useSegment=useSegment
            )

        elif vector is not None:
            if (point is not None) or (length is not None):
                raise ValueError(
                    "Please specify a point, a vector or a length."
                )

            if atStart and atEnd:
                raise ValueError(
                    "Extending in both directions not available with point / vector."
                )

            return self.extendByVector(
                vector,
                atStart=atStart if atStart is not None else False,
                multipleKnots=multipleKnots,
                useSegment=useSegment
            )

        elif length is not None:
            if (point is not None) or (length is not None):
                raise ValueError(
                    "Please specify a point, a vector or a length."
                )

            if useSegment:
                raise ValueError(
                    "Option not available when extending by length: useSegment"
                )

            return self.extendByLength(
                vector,
                atStart=atStart,
                atEnd=atEnd,
                multipleKnots=multipleKnots
            )

        else:
            raise ValueError("Insufficient hints.")

    @copyToShape(editsHistory=True)
    @short(globalScale='gs', vector='v')
    def squashStretch(self,
                      squashy,
                      stretchy,
                      globalScale=None,
                      vector=None):
        """
        :param squashy: the user attribute to control how squashy the output
            should be
        :type squashy: :class:`str`, :class:`~paya.runtime.plugs.Math1D`
        :param stretchy: the user attribute to control how stretchy the output
            should be
        :type stretchy: :class:`str`, :class:`~paya.runtime.plugs.Math1D`
        :param globalScale/gs: (recommended) an attribute to use as a
            normalizing factor for length calculations; defaults to ``None``
        :type globalScale/gs: :class:`str`, :class:`~paya.runtime.plugs.Math1D`
        :param vector/v: (recommended) an extension vector to use when the
            curve is under-shot (e.g. an extracted animation control axis);
            defaults to ``None``
        :return: This curve output with added squash-stretch effects.
        :rtype: :class:`NurbsCurve`
        """
        nativeLen = self.length()

        if globalScale is not None:
            nativeLen *= globalScale

        liveLen = self.length(p=True)
        targetLen = liveLen.gatedClamp(nativeLen, squashy, stretchy)

        return self.setLength(targetLen, vector=vector)

    @copyToShape(editsHistory=True)
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
            matchCurve = _tm.asGeoPlug(matchCurve)

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

    @copyToShape(editsHistory=True)
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

    @copyToShape(editsHistory=True)
    def cageRebuild(self):
        """
        :return: A linear curve with the same CVs as this one.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        return self.rebuild(degree=1, keepControlPoints=True)

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    MISC
    #---------------------------------------------------------------|

    @copyToShape(editsHistory=True)
    def reverse(self):
        """
        :return: The reversed curve.
        :rtype: :class:`~paya.runtime.plugs.NurbsCurve`
        """
        node = r.nodes.ReverseCurve.createNode()
        self >> node.attr('inputCurve')
        return node.attr('outputCurve')

    @copyToShape(editsHistory=True)
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
        otherCurve = _tm.asGeoPlug(otherCurve)
        node = r.nodes.AvgCurves.createNode()
        node.attr('automaticWeight').set(False)
        node.attr('normalizeWeights').set(False)
        self >> node.attr('inputCurve1')
        otherCurve >> node.attr('inputCurve2')
        weight >> node.attr('weight2')
        (1-node.attr('weight2')) >> node.attr('weight1')

        return node.attr('outputCurve')

    @copyToShape(editsHistory=True)
    @short(insertBetween='ib')
    def insertKnot(self, *parameters, insertBetween=None):
        """
        :param \*parameters: the parameters at, or between, which to add
            knots
        :type \*parameters: :class:`float` |
            :class:`~paya.runtime.plugs.Math1D` |
            [:class:`float` | :class:`~paya.runtime.plugs.Math1D`]
        :param bool insertBetween/ib: if this is specified, cuts won't
            be performed at the specified parameters, but rather between
            them; this should be a scalar, or a list of scalars
            (one per internal segment, i.e. ``len(parameters)-1``),
            specifying the number(s) of cuts; defaults to ``None``
        :return: The edited curve.
        :rtype: :class:`~paya.runtime.nodes.NurbsCurve`
        """
        parameters = _pu.expandArgs(*parameters)
        numParams = len(parameters)

        if insertBetween:
            if numParams < 2:
                raise ValueError("Need two or more "+
                                 "parameters between which to insert.")

            cutsPerSegment = list(_pu.expandArgs(insertBetween))
            lnCutsPerSegment = len(cutsPerSegment)

            if lnCutsPerSegment is 1:
                cutsPerSegment *= (numParams-1)

            elif lnCutsPerSegment is not numParams-1:
                raise ValueError(
                    "Specify a single number of inbetweens, or one number "+
                    "per internal segment (i.e. len(parameters)-1).")

        node = r.nodes.InsertKnotCurve.createNode()
        self >> node.attr('inputCurve')

        for i, parameter in enumerate(parameters):
            parameter >> node.attr('parameter')[i]

        if insertBetween:
            node.attr('insertBetween').set(True)

            for i, numCuts in enumerate(cutsPerSegment):
                numCuts >> node.attr('numberOfKnots')[i]

        return node.attr('outputCurve')