from importlib import reload

import pymel.util as _pu
import pymel.core.nodetypes as _nt

import paya.lib.nurbsutil as _nu
from paya.lib.loopback import Loopback
import paya.lib.nurbsutil as _nu
import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #-----------------------------------------------------|    Constructors

    @classmethod
    @short(
        degree='d',
        under='u',
        name='n',
        conformShapeName='csn',
        intermediate='i',
        displayType='dt',
        bSpline='bsp',
        lineWidth='lw'
    )
    def create(
            cls,
            *points,
            degree=3,
            name=None,
            bSpline=False,
            under=None,
            displayType=None,
            conformShapeName=True,
            intermediate=False,
            lineWidth=None
    ):
        """
        Draws static or dynamic curves.

        :param \*points: the input points; can be values or attributes
        :type \*points: list, tuple, str, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`, :class:`~paya.runtime.plugs.Vector`
        :param bool bSpline/bsp: only available if *degree* is 3; draw as a
            bSpline (similar to drawing by EP); defaults to False
        :param int degree/d: the curve degree; defaults to 3
        :param under/u: an optional destination parent; no space conversion
            will take place; if the parent has transforms, the curve shape
            will be transformed as well; defaults to None
        :type under/u: None, str, :class:`~paya.runtime.nodes.Transform`
        :param name/n: one or more name elements; defaults to None
        :type name/n: str, int, None, tuple, list
        :param bool conformShapeName/csn: if reparenting, rename the shape to match
            the destination parent; defaults to True
        :param bool intermediate: set the shape to intermediate; defaults to
            False
        :param displayType/dt: if provided, an index or enum label:

            - 0: 'Normal'
            - 1: 'Template'
            - 2: 'Reference'

            If omitted, display overrides won't be activated at all.
        :type displayType/dt: None, int, str
        :param lineWidth/lw: an override for the line width; defaults to None
        :type lineWidth/lw: None, float
        :return: The curve shape.
        :rtype: :class:`NurbsCurve`
        """
        points = _mo.expandVectorArgs(points)
        num = len(points)

        if bSpline:
            if degree is not 3:
                raise RuntimeError(
                   "bSpline drawing is only available for degree 3."
                )

            drawDegree = 1

        else:
            drawDegree = degree

        minNum = drawDegree+1

        if num < minNum:
            raise RuntimeError(
                "At least {} CVs needed for degree {}.".format(
                    minNum,
                    degree
                )
            )

        infos = [_mo.info(point) for point in points]
        points = [info[0] for info in infos]
        hasPlugs = any([info[2] for info in infos])

        if hasPlugs:
            _points = [info[0].get() if info[2]
                else info[0] for info in infos]

        else:
            _points = points

        # Soft-draw
        curveXf = r.curve(
            name=cls.makeName(n=name),
            knot=_nu.getKnotList(num, drawDegree),
            point=_points,
            degree=drawDegree
        )

        # Reparent
        curveShape = curveXf.getShape()

        if under:
            r.parent(curveShape, under, r=True, shape=True)
            r.delete(curveXf)

            if conformShapeName:
                curveShape.conformName()

        # Modify
        if bSpline or hasPlugs:
            origShape = curveShape.getOrigPlug(create=True).node()

            if hasPlugs:
                for i, point in enumerate(points):
                    point >> origShape.attr('controlPoints')[i]

            if bSpline:
                origShape.attr('worldSpace'
                    ).bSpline() >> curveShape.attr('create')

            if not hasPlugs:
                curveShape.deleteHistory()

        # Configure
        if intermediate:
            curveShape.attr('intermediateObject').set(True)

        if displayType is not None:
            curveShape.attr('overrideEnabled').set(True)
            curveShape.attr('overrideDisplayType').set(displayType)

        if lineWidth is not None:
            curveShape.attr('lineWidth').set(lineWidth)

        return curveShape

    @classmethod
    @short(
        radius='r',
        directionVector='dv',
        toggleArc='tac',
        sections='s',
        degree='d',
        name='n',
        lineWidth='lw'
    )
    def createArc(
            cls,
            *points,
            directionVector=None,
            radius=1.0,
            toggleArc=False,
            sections=8,
            degree=3,
            guard=None,
            name=None,
            lineWidth=None
    ):
        """
        Constructs a circular arc. The arc will be live if any of the
        arguments are plugs.

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
        :param lineWidth/lw: an override for the line width; defaults to None
        :type lineWidth/lw: None, float
        :param name/n: one or more name elements; defaults to None
        :type name/n: str, int, None, tuple, list
        :return: The curve shape.
        :rtype: :class:`~paya.runtime.nodes.NurbsCurve`
        """
        points = _mo.expandVectorArgs(*points)

        live = any((_mo.isPlug(point) for point in points)) \
            or (directionVector and _mo.isPlug(directionVector)) \
            or _mo.isPlug(radius)

        output = r.plugs.NurbsCurve.createArc(
            points,
            directionVector=directionVector,
            radius=radius,
            toggleArc=toggleArc,
            sections=sections,
            degree=degree,
            guard=guard
        )

        shape = output.createShape(n=name)

        if not live:
            shape.deleteHistory()

        if lineWidth is not None:
            shape.attr('lineWidth').set(lineWidth)

        return shape

    @classmethod
    def createFromMacro(cls, macro, **overrides):
        """
        :param dict macro: the type of macro returned by :meth:`macro`
        :param \*\*overrides: overrides passed-in as keyword arguments
        :return: A curve constructed using the macro.
        :rtype: :class:`NurbsCurve`.
        """
        macro = macro.copy()
        macro.update(overrides)

        kwargs = {
            'point': macro['point'],
            'knot': macro['knot'],
            'periodic': macro['form'] is 2,
            'degree': macro['degree']
        }

        xf = r.curve(**kwargs)

        if macro['knotDomain'][1] == 1.0 and curve.getKnotDomain()[1] != 1.0:
            xf = r.rebuildCurve(
                xf,
                ch=False,
                d=macro['degree'],
                kcp=True,
                kep=True,
                kt=True,
                rt=0,
                rpo=True,
                kr=0
            )[0]

        shape = xf.getShape()
        shape.rename(macro['name'])

        if macro['form'] is 1:
            shape.attr('f').set(1)

        return shape

    #-----------------------------------------------------|    Loopbacks

    subCurve = Loopback()
    detach = Loopback()
    extend = Loopback()
    extendByVector = Loopback()
    extendToPoint = Loopback()
    retract = Loopback()
    setLength = Loopback()
    reverse = Loopback()
    toBezier = Loopback()
    toNurbs = Loopback()
    bSpline = Loopback()
    cvRebuild  = Loopback()
    rebuild = Loopback()
    cageRebuild = Loopback()
    blend = Loopback()

    #-----------------------------------------------------|    Macro

    def macro(self):
        """
        :return: A simplified representation of this curve that can be used
            by :meth:`createFromMacro` to reconstruct it.
        :rtype: dict
        """
        macro = r.nodes.DependNode.macro(self)

        macro['knot'] = self.getKnots()
        macro['degree'] = self.degree()
        macro['form'] = self.attr('f').get()
        macro['point'] = list(map(list, self.getCVs()))
        macro['knotDomain'] = self.getKnotDomain()

        return macro

    @classmethod
    def normalizeMacro(cls, macro):
        """
        Used by the shapes library to fit control points inside a unit cube.
        This is an in-place operation; the method has no return value.

        :param dict macro: the macro to edit
        """
        points = macro['point']
        points = _mo.pointsIntoUnitCube(points)
        macro['point'] = [list(point) for point in points]

    #-----------------------------------------------------|    Abstract I/O

    @property
    def geoInput(self):
        return self.attr('create')

    @property
    def worldGeoOutput(self):
        return self.attr('worldSpace')

    @property
    def localGeoOutput(self):
        return self.attr('local')

    #-----------------------------------------------------|    Curve-level info

    @short(reuse='re')
    def initCurveInfo(self, reuse=True):
        """
        Initialises, or retrieves, a ``curveInfo`` node connected to this
        curve.

        :param bool reuse/re: look for existing nodes
        :return: The ``curveInfo`` node.
        :rtype: :class:`~paya.runtime.nodes.CurveInfo`
        """
        if reuse:
            outputs = self.attr('worldSpace').outputs(type='curveInfo')

            if outputs:
                return outputs[0]

        node = r.nodes.CurveInfo.createNode()
        self.attr('worldSpace') >> node.attr('inputCurve')
        return node

    @short(plug='p', tolerance='tol')
    def length(self, plug=False, tolerance=0.001):
        """
        Overload of :meth:`pymel.core.nodetypes.NurbsCurve.length`.

        :param bool plug/p: return an attribute, not just a value;
            defaults to False
        :param float tolerance/tol: ignored for the plug implementation;
            defaults to 0.001
        :return: The length of this curve.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            info = self.initCurveInfo()
            return info.attr('arcLength')

        return r.nodetypes.NurbsCurve.length(self, tolerance=tolerance)

    #-----------------------------------------------------|    Point sampling

    @short(plug='p', worldSpace='ws')
    def getControlPoints(self, plug=False, worldSpace=False):
        """
        Similar to :meth:`~pymel.core.nodetypes.NurbsCurve.getCVs`, with some
        modifications.

        :param bool plug/p: force a dynamic output; defaults to False
        :param bool worldSpace/ws: return world-space points; defaults to
            False
        :return: One point per CV on this curve, as a value or attribute.
        :rtype: [:class:`~paya.runtime.data.Point`],
            [:class:`~paya.runtime.plugs.Vector`]
        """
        if plug:
            return self.attr(
                'worldSpace' if worldSpace else 'local').getControlPoints()

        return self.getCVs(space='world' if worldSpace else 'object')

    @short(plug='p')
    def closestPoint_(self, refPoint, plug=False):
        """
        :param refPoint: the reference point
        :type refPoint: list, tuple, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The closest world-space point along this curve to the given
            reference point.
        :rtype: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.attr('worldSpace').closestPoint(refPoint)

        p, dim, pisplug = _mo.info(refPoint)

        if pisplug:
            return self.attr('worldSpace').closestPoint(refPoint)

        return self.closestPoint(refPoint, space='world')

    @short(plug='p')
    def pointAtCV(self, cv, plug=False):
        """
        :param cv: the CV to sample
        :type cv: int, :class:`~paya.runtime.comps.NurbsCurveCV`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The world-space point position of the specified CV.
        """
        if plug:
            return self.attr('worldSpace').pointAtCV(cv)

        if isinstance(cv, int):
            cv = self.comp('cv')[cv]

        return r.pointPosition(cv, world=True)

    @short(plug='p')
    def pointAtParam(self, param, plug=False):
        """
        :param param: the parameter at which to sample
        :type param: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A world-space point at the specified parameter.
        :type: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        param = _nu.conformUParamArg(param)

        if plug:
            return self.attr('worldSpace').pointAtParam(param)

        p, dim, pisplug = _mo.info(param)

        if pisplug:
            return self.attr('worldSpace').pointAtParam(param)

        return self.getPointAtParam(float(param), space='world')

    @short(plug='p')
    def pointAtLength(self, length, plug=False):
        """
        :param length: the length at which to sample
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A world-space point at the specified length.
        :type: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.attr('worldSpace').pointAtLength(length)

        length, dim, lisplug = _mo.info(length)

        if lisplug:
            return self.attr('worldSpace').pointAtLength(length)

        param = self.findParamFromLength(length)
        return self.pointAtParam(param)

    @short(plug='p')
    def pointAtFraction(self, fraction, plug=False):
        """
        :param fraction: the length fraction at which to sample
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A world-space point at the specified length fraction.
        :type: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.attr('worldSpace').pointAtFraction(fraction)

        fraction, dim, fisplug = _mo.info(fraction)

        if fisplug:
            return self.attr('worldSpace').pointAtFraction(fraction)

        length = self.length() * fraction
        return self.pointAtLength(length)

    #-----------------------------------------------------|    Param sampling

    @short(asComponent='ac', plug='p')
    def paramAtPoint(self, point, asComponent=True, plug=False):
        """
        Returns the parameter at the given point. This is a 'forgiving'
        implementation; a closest param will still be returned if the
        point is not on the curve.

        :alias: ``closestParam``
        :param point: the reference point
        :type point: list, tuple, :class:`~paya.runtime.data.Point`
            :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output; defaults to False
        :param bool asComponent/ac: return an instance of
            :class:`~paya.runtime.comps.NurbsCurveParameter` rather than
            a float; defaults to True
        :return: The sampled parameter.
        :rtype: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.attr('worldSpace').paramAtPoint(point)

        point, dim, pisplug = _mo.info(point)

        if pisplug:
            return self.attr('worldSpace').paramAtPoint(point)

        point = self.closestPoint_(point)
        param = self.getParamAtPoint(point, space='world')

        if asComponent:
            return self.comp('u')[param]

        return param

    closestParam = paramAtPoint

    @short(plug='p')
    def closestFraction(self, point, plug=False):
        """
        :param point: the reference point
        :type point: tuple, list, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The closest length fraction to the given point.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        param = self.closestParam(point, p=plug)
        return self.fractionAtParam(param, p=plug)

    @short(asComponent='ac', plug='p')
    def paramAtFraction(self, fraction, asComponent=True, plug=False):
        """
        :param fraction: the length fraction at which to sample
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :param bool asComponent/ac: return an instance of
            :class:`~paya.runtime.comps.NurbsCurveParameter` rather than
            a float; defaults to True
        :return: The parameter at the given length fraction.
        :rtype: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.attr('worldSpace').paramAtFraction(fraction)

        fraction, dim, fisplug = _mo.info(fraction)

        if fisplug:
            return self.attr('worldSpace').paramAtFraction(fraction)

        length = self.length() * fraction
        param = self.findParamFromLength(length)

        if asComponent:
            return self.comp('u')[param]

        return param

    @short(asComponent='ac', plug='p')
    def paramAtLength(self, length, asComponent=True, plug=False):
        """
        :param length: the length at which to sample
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :param bool asComponent/ac: return an instance of
            :class:`~paya.runtime.comps.NurbsCurveParameter` rather than
            a float; defaults to True
        :return: The parameter at the given length.
        :rtype: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.attr('worldSpace').paramAtLength(length)

        length, dim, lisplug = _mo.info(length)

        if lisplug:
            return self.attr('worldSpace').paramAtLength(length)

        param = self.findParamFromLength(length)

        if asComponent:
            return self.comp('u')[param]

        return param

    #-----------------------------------------------------|    Length sampling

    @short(plug='p')
    def lengthAtFraction(self, fraction, plug=False):
        """
        :param fraction: the length fraction
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The curve length at the given fraction.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.attr('worldSpace').lengthAtFraction()

        fraction, dim, fisplug = _mo.info(fraction)

        if fisplug:
            return self.attr('worldSpace').lengthAtFraction()

        return self.length() * fraction

    @short(plug='p')
    def lengthAtParam(self, param, plug=False):
        """
        :param param: the parameter
        :type param: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The curve length at the given parameter.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        param = _nu.conformUParamArg(param)

        if plug:
            return self.attr('worldSpace').lengthAtParam()

        param, dim, pisplug = _mo.info(param)

        if pisplug:
            return self.attr('worldSpace').lengthAtParam()

        return self.findLengthFromParam(float(param))

    @short(plug='p')
    def lengthAtPoint(self, point, plug=False):
        """
        Returns the curve length at the given point. This is a 'forgiving'
        implementation; a closest point will be used if *point* is not on the
        curve.

        :param point: the point
        :type point: list, tuple, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The curve length.
        :rtype: :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.attr('worldSpace').lengthAtPoint(point)

        point, dim, pisplug = _mo.info(point)

        if pisplug:
            return self.attr('worldSpace').lengthAtPoint(point)

        param = self.paramAtPoint(point)
        return self.findLengthFromParam(param)

    #-----------------------------------------------------|    Fraction sampling

    @short(plug='p')
    def fractionAtLength(self, length, plug=False):
        """
        :param length: the length at which to sample a fraction
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The length fraction at the given length.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.attr('worldSpace').fractionAtLength(length)

        length, dim, lisplug = _mo.info(length)

        if lisplug:
            return self.attr('worldSpace').fractionAtLength(length)

        return length / self.length()

    @short(plug='p')
    def fractionAtParam(self, param, plug=False):
        """
        :param param: the parameter at which to sample a fraction
        :type param: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The length fraction at the given parameter
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        param = _nu.conformUParamArg(param)

        if plug:
            return self.attr('worldSpace').fractionAtParam(param)

        param, dim, pisplug = _mo.info(param)

        if pisplug:
            return self.attr('worldSpace').fractionAtParam(param)

        return self.lengthAtParam(param) / self.length()

    @short(plug='p')
    def fractionAtPoint(self, point, plug=False):
        """
        :param point: the point at which to sample a fraction
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The length fraction at the given point.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.attr('worldSpace').fractionAtPoint(point)

        point, dim, pisplug = _mo.info(point)

        if pisplug:
            return self.attr('worldSpace').fractionAtPoint(point)

        param = self.paramAtPoint(point)
        return self.fractionAtParam(param)

    #-----------------------------------------------------|    Tangent sampling

    @short(normalize='nr', plug='p')
    def tangentAtParam(self, param, normalize=False, plug=False):
        """
        :param param: The parameter at which to sample the tangent.
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :param bool normalize/nr: Normalize the tangent; defaults to False
        :return: The curve tangent at the given parameter.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.attr('worldSpace').tangentAtParam(param, nr=normalize)

        param, pdim, pisplug = _mo.info(param)

        if pisplug:
            return self.attr('worldSpace').tangentAtParam(param, nr=normalize)

        tangent = self.getDerivativesAtParm(float(param), space='world')[1]

        if normalize:
            tangent = tangent.normal()

        return tangent

    #-----------------------------------------------------|    Up vector sampling

    @short(plug='p')
    def binormalAtParam(self, param, plug=False):
        """
        :param param: the parameter at which to sample the binormal
        :rtype param: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = _nu.conformUParamArg(param)
        p, pdim, pisplug = _mo.info(param)

        plug = plug or pisplug

        if plug:
            return self.attr('worldSpace').binormalAtParam(param)

        else:
            position, tangent, derivative = \
                self.getDerivativesAtParm(float(param), space='world')

            return tangent.cross(derivative).normal()

    @short(plug='p')
    def binormalAtFraction(self, fraction, plug=False):
        """
        :param fraction: the length fraction at which to sample the binormal
        :rtype fraction: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtFraction(fraction)
        return self.binormalAtParam(param, p=plug)

    @short(plug='p')
    def binormalAtLength(self, fraction, plug=False):
        """
        :param length: the length at which to sample the binormal
        :rtype length: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtLength(length)
        return self.binormalAtParam(param, p=plug)

    @short(plug='p')
    def binormalAtPoint(self, point, plug=False):
        """
        :param point: the point at which to sample the binormal
        :rtype point: list, tuple, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtPoint(point)
        return self.binormalAtParam(param, p=plug)

    #-----------------------------------------------------|    Matrix sampling

    @short(
        squashStretch='ss',
        upVector='upv',
        aimCurve='aic',
        fraction='fr',
        globalScale='gs',
        closestPoint='cp',
        plug='p'
    )
    def matrixAtParamOrFraction(
            self,
            paramOrFraction,
            tangentAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            closestPoint=True,
            globalScale=None,
            squashStretch=False,
            fraction=False,
            plug=False
            ):
        """
        Base curve framing implementation. Uses ``motionPath`` and / or
        ``pointOnCurveInfo`` nodes.

        :param paramOrFraction: a parameter of length fraction at which
            to sample the matrix
        :type paramOrFraction:
            float, str,
            :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :param str tangentAxis: the axis to map to the curve tangent,
            e.g. '-y'
        :param str upAxis: the axis to map to the resolved up vector, e.g. 'x'
        :param upVector/upv: an explicit up vector; defaults to None
        :type upVector/upv: None, str, tuple, list,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an 'aim' curve for the up vector, similar to
            the ``curveWarp`` deformer; defaults to False
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: sample points on the aim-curve by
            proximity rather than matched parameter; defaults to True
        :param globalScale/gs: ignored if not a plug; a baseline scale (will
            be normalized); defaults to None
        :type globalScale/gs: None, float, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow the tangent vector to squash and
            stretch; defaults to False
        :param bool fraction/fr: interpret *paramOrFraction* as a length
            fraction rather than a parameter; defaults to False
        :return: The constructed matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        if plug \
                or _mo.isPlug(paramOrFraction) \
                or upVector and _mo.isPlug(upVector) \
                or aimCurve and _mo.isPlug(aimCurve) \
                or globalScale and _mo.isPlug(globalScale):
            return self.attr('worldSpace').matrixAtParamOrFraction(
                paramOrFraction, tangentAxis, upAxis,
                upv=upVector, aic=aimCurve, cp=closestPoint,
                gs=globalScale, ss=squashStretch, fr=fraction
            )

        # Soft implementation
        if fraction:
            param = self.paramAtFraction(paramOrFraction)

        else:
            param = paramOrFraction

        point, tangent, derivative = \
            self.getDerivativesAtParm(float(param), space='world')

        if not upVector:
            if aimCurve:
                aimCurve = r.PyNode(aimCurve)

                if closestPoint:
                    interest = aimCurve.closestPoint_(point)

                else:
                    interest = aimCurve.pointAtParam(param)

                upVector = interest-point

            else:
                upVector = self.normal(param, space='world')

        return r.createMatrix(
            tangentAxis, tangent,
            upAxis, upVector,
            translate=point
        ).pick(translate=True, rotate=True)

    @short(
        squashStretch='ss',
        upVector='upv',
        aimCurve='aic',
        globalScale='gs',
        closestPoint='cp',
        plug='p'
    )
    def matrixAtParam(
            self,
            param,
            tangentAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            closestPoint=True,
            globalScale=None,
            squashStretch=False,
            plug=False
            ):
        """
        :param param: the parameter at which to sample the matrix
        :type param: float, str,
            :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :param str tangentAxis: the axis to map to the curve tangent,
            e.g. '-y'
        :param str upAxis: the axis to map to the resolved up vector, e.g. 'x'
        :param upVector/upv: an explicit up vector; defaults to None
        :type upVector/upv: None, str, tuple, list,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an 'aim' curve for the up vector, similar to
            the ``curveWarp`` deformer; defaults to False
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: sample points on the aim-curve by
            proximity rather than matched parameter; defaults to True
        :param globalScale/gs: ignored if not a plug; a baseline scale (will
            be normalized); defaults to None
        :type globalScale/gs: None, float, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow the tangent vector to squash and
            stretch; defaults to False
        :return: The constructed matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        return self.matrixAtParamOrFraction(
            param, tangentAxis, upAxis,
            upv=upVector, aic=aimCurve,
            cp=closestPoint, gs=globalScale,
            ss=squashStretch, p=plug,
            fr=False
        )

    @short(
        squashStretch='ss',
        upVector='upv',
        aimCurve='aic',
        globalScale='gs',
        closestPoint='cp',
        plug='p'
    )
    def matrixAtFraction(
            self,
            fraction,
            tangentAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            closestPoint=True,
            globalScale=None,
            squashStretch=False,
            plug=False
            ):
        """
        :param fraction: the fraction at which to sample the matrix
        :type fraction: float, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :param str tangentAxis: the axis to map to the curve tangent,
            e.g. '-y'
        :param str upAxis: the axis to map to the resolved up vector, e.g. 'x'
        :param upVector/upv: an explicit up vector; defaults to None
        :type upVector/upv: None, str, tuple, list,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an 'aim' curve for the up vector, similar to
            the ``curveWarp`` deformer; defaults to False
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: sample points on the aim-curve by
            proximity rather than matched parameter; defaults to True
        :param globalScale/gs: ignored if not a plug; a baseline scale (will
            be normalized); defaults to None
        :type globalScale/gs: None, float, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow the tangent vector to squash and
            stretch; defaults to False
        :return: The constructed matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        return self.matrixAtParamOrFraction(
            fraction, tangentAxis, upAxis,
            upv=upVector, aic=aimCurve,
            cp=closestPoint, gs=globalScale,
            ss=squashStretch, p=plug,
            fr=True
        )

    @short(
        squashStretch='ss',
        upVector='upv',
        aimCurve='aic',
        globalScale='gs',
        closestPoint='cp',
        plug='p'
    )
    def matrixAtLength(
            self,
            length,
            tangentAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            closestPoint=True,
            globalScale=None,
            squashStretch=False,
            plug=False
            ):
        """
        :param length: the length at which to sample the matrix
        :type length: float, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :param str tangentAxis: the axis to map to the curve tangent,
            e.g. '-y'
        :param str upAxis: the axis to map to the resolved up vector, e.g. 'x'
        :param upVector/upv: an explicit up vector; defaults to None
        :type upVector/upv: None, str, tuple, list,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an 'aim' curve for the up vector, similar to
            the ``curveWarp`` deformer; defaults to False
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: sample points on the aim-curve by
            proximity rather than matched parameter; defaults to True
        :param globalScale/gs: ignored if not a plug; a baseline scale (will
            be normalized); defaults to None
        :type globalScale/gs: None, float, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow the tangent vector to squash and
            stretch; defaults to False
        :return: The constructed matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        fraction = self.fractionAtLength(length)

        return self.matrixAtParamOrFraction(
            fraction, tangentAxis, upAxis,
            upv=upVector, aic=aimCurve,
            cp=closestPoint, gs=globalScale,
            ss=squashStretch, p=plug,
            fr=True
        )

    @short(
        squashStretch='ss',
        upVector='upv',
        aimCurve='aic',
        globalScale='gs',
        closestPoint='cp',
        plug='p'
    )
    def matrixAtPoint(
            self,
            point,
            tangentAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            closestPoint=True,
            globalScale=None,
            squashStretch=False,
            plug=False
            ):
        """
        :param point: the point at which to sample the matrix
        :type point: float, str, tuple, list,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output; defaults to False
        :param str tangentAxis: the axis to map to the curve tangent,
            e.g. '-y'
        :param str upAxis: the axis to map to the resolved up vector, e.g. 'x'
        :param upVector/upv: an explicit up vector; defaults to None
        :type upVector/upv: None, str, tuple, list,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an 'aim' curve for the up vector, similar to
            the ``curveWarp`` deformer; defaults to False
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: sample points on the aim-curve by
            proximity rather than matched parameter; defaults to True
        :param globalScale/gs: ignored if not a plug; a baseline scale (will
            be normalized); defaults to None
        :type globalScale/gs: None, float, str,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow the tangent vector to squash and
            stretch; defaults to False
        :return: The constructed matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        param = self.paramAtPoint(point)

        return self.matrixAtParamOrFraction(
            param, tangentAxis, upAxis,
            upv=upVector, aic=aimCurve,
            cp=closestPoint, gs=globalScale,
            ss=squashStretch, p=plug,
            fr=False
        )

    #-----------------------------------------------------|    Distributions

    @short(plug='p')
    def distributePoints(self, numberOrFractions, plug=False):
        """
        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :type numberOrFractions: tuple, list or int
        :param bool plug/p: force a dynamic output; defaults to False
        :return: World-space points distributed along the length of the curve.
        :rtype: [:class:`~paya.runtime.data.Point`],
            [:class:`~paya.runtime.plug.Vector`]
        """
        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)

        return [self.pointAtFraction(
            fraction, p=plug) for fraction in fractions]

    @short(
        plug='p',
        asComponents='ac'
    )
    def distributeParams(
            self,
            numberOrFractions,
            plug=False,
            asComponent=True
    ):
        """
        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :type numberOrFractions: tuple, list or int
        :param bool asComponent/ac: if parameter values are returned, use
            :class:`~paya.runtime.comps.NurbsCurveParameter` instances instead
            of floats; defaults to True
        :param bool plug/p: force a dynamic output; defaults to False
        :return: Parameters distributed along the length of the curve.
        :rtype: [float], [:class:`~paya.runtime.comps.NurbsCurveParameter`],
            [:class:`~paya.runtime.plugs.Math1D`]
        """
        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)

        return [self.paramAtFraction(
            fraction,
            p=plug,
            ac=asComponent
        ) for fraction in fractions]

    @short(plug='p')
    def distributeLengths(self, numberOrFractions, plug=False):
        """
        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :type numberOrFractions: tuple, list or int
        :param bool plug/p: force a dynamic output; defaults to False
        :return: Lengths distributed along the curve.
        :rtype: [float], [:class:`~paya.runtime.plugs.Math1D`]
        """
        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)

        return [self.lengthAtFraction(
            fraction, p=plug) for fraction in fractions]

    @short(
        upVector='upv',
        aimCurve='aic',
        squashStretch='ss',
        closestPoint='cp',
        globalScale='gs',
        plug='p'
    )
    def distributeMatrices(
            self,
            numberOrFractions,
            tangentAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            squashStretch=None,
            closestPoint=True,
            globalScale=None,
            plug=False
    ):
        """
        :param numberOrFractions: this can either be a number of uniform
            fractions to generate, or an explicit list of fractions
        :type numberOrFractions: float, [float],
            :class:`~paya.runtime.plugs.Math1D`,
            [:class:`~paya.runtime.plugs.Math1D`]
        :param str tangentAxis: the matrix axis to map to the curve tangent,
            for example '-y'
        :param str upAxis: the matrix axis to align to the resolved up vector, for
            example 'x'
        :param upVector/upv: if provided, should be either a single up vector or a
            a list of up vectors (one per fraction); defaults to None
        :type upVector/upv:
            None,
            list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`,
            [list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`]
        :param aimCurve/aic: an 'up' curve, as seen for example on Maya's
            ``curveWarp``; defaults to None
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from the aim curve by
            proximity rather than matched parameter; defaults to True
        :param bool squashStretch/ss: allow squash and stretch on the tangent
            vectors; defaults to False
        :param globalScale/gs: ignored if not a plug; a baseline scaling
            factor (will be normalized); defaults to None
        :param bool plug/p: force a dynamic output; defaults to False
        :return: Matrices, distributed uniformly (by length) along this curve.
        :rtype: [:class:`~paya.runtime.plugs.Matrix`],
            [:class:`~paya.runtime.data.Matrix`]
        """
        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)
        number = len(fractions)

        if upVector:
            upVectors = _mo.conformVectorArg(upVector, ll=number)
        else:
            upVectors = [None] * number

        out = []

        for i, fraction in enumerate(fractions):
            with r.Name(i+1):
                matrix = self.matrixAtFraction(
                    fraction,
                    tangentAxis, upAxis,
                    upv=upVectors[i], aic=aimCurve,
                    ss=squashStretch, cp=closestPoint,
                    gs=globalScale, p=plug
                )

                out.append(matrix)

        return out

    @short(
        upVector='upv',
        aimCurve='aic',
        squashStretch='ss',
        closestPoint='cp',
        globalScale='gs',
        plug='p'
    )
    def distributeAimingMatrices(
            self,
            numberOrFractions,
            aimAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            squashStretch=None,
            closestPoint=True,
            globalScale=None,
            plug=False
    ):
        """
        Similar to :meth:`distributeMatrices`, but here the matrices aim at
        each other for a 'chained' effect.

        :param numberOrFractions: this can either be a number of uniform
            fractions to generate, or an explicit list of fractions
        :type numberOrFractions: float, [float],
            :class:`~paya.runtime.plugs.Math1D`,
            [:class:`~paya.runtime.plugs.Math1D`]
        :param str aimAxis: the matrix axis to map to the aim vectors,
            for example '-y'
        :param str upAxis: the matrix axis to align to the resolved up vector, for
            example 'x'
        :param upVector/upv: if provided, should be either a single up vector or a
            a list of up vectors (one per fraction); defaults to None
        :type upVector/upv:
            None,
            list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`,
            [list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`]
        :param aimCurve/aic: an 'up' curve, as seen for example on Maya's
            ``curveWarp``; defaults to None
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from the aim curve by
            proximity rather than matched parameter; defaults to True
        :param bool squashStretch/ss: allow squash and stretch on the aim
            vectors; defaults to False
        :param bool plug/p: force a dynamic output; defaults to False
        :param globalScale/gs: ignored if not a plug; a baseline scaling
            factor (will be normalized); defaults to None
        :return: Matrices, distributed uniformly (by length) along this curve.
        :rtype: [:class:`~paya.runtime.plugs.Matrix`],
            [:class:`~paya.runtime.data.Matrix`]
        """
        if plug:
            return self.attr('worldSpace').distributeAimingMatrices(
                numberOrFractions, aimAxis, upAxis,
                upv=upVector, aic=aimCurve, ss=squashStretch,
                cp=closestPoint, gs=globalScale
            )

        fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)
        number = len(fractions)

        if upVector:
            upVector = _mo.conformVectorArg(upVector, ll=number)

        if any((_mo.isPlug(fraction) for fraction in fractions)) \
                or upVector and any((_mo.isPlug(member) for member in upVector)) \
                or aimCurve and _mo.isPlug(aimCurve) \
                or globalScale and _mo.isPlug(globalScale):
            return self.attr('worldSpace').distributeAimingMatrices(
                numberOrFractions, aimAxis, upAxis,
                upv=upVector, aic=aimCurve, ss=squashStretch,
                cp=closestPoint, gs=globalScale
            )

        #---------------------------------------|    Soft implementation

        points = [self.pointAtFraction(fraction) for fraction in fractions]
        aimVectors = _mo.getAimVectors(points)
        aimVectors.append(aimVectors[-1])

        if upVector:
            upVectors = upVector

        else:
            upVectors = []

            if aimCurve:
                aimCurve = r.PyNode(aimCurve)

                for i, point in enumerate(points):
                    if closestPoint:
                        interest = aimCurve.closestPoint_(point)

                    else:
                        param = self.paramAtPoint(point)
                        interest = aimCurve.pointAtParam(param)

                    upVector = interest-point
                    upVectors.append(upVector)

            else:
                params = [self.paramAtPoint(point) for point in points]
                upVectors = [self.normal(
                    param, space='world') for param in params]

        out = []

        for point, aimVector, upVector in zip(
            points, aimVectors, upVectors
        ):
            matrix = r.createMatrix(
                aimAxis, aimVector,
                upAxis, upVector,
                translate=point
            ).pick(translate=True, rotate=True)

            out.append(matrix)

        return out

    @short(
        upVector='upv',
        aimCurve='aic',
        squashStretch='ss',
        closestPoint='cp',
        globalScale='gs',
        plug='p',
        under='u'
    )
    def distributeJoints(
            self,
            numberOrFractions,
            tangentAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            squashStretch=None,
            closestPoint=True,
            globalScale=None,
            under=None,
            plug=False
    ):
        """
        :param numberOrFractions: this can either be a number of uniform
            fractions to generate, or an explicit list of fractions
        :type numberOrFractions: float, [float],
            :class:`~paya.runtime.plugs.Math1D`,
            [:class:`~paya.runtime.plugs.Math1D`]
        :param str tangentAxis: the matrix axis to map to the curve tangent,
            for example '-y'
        :param str upAxis: the matrix axis to align to the resolved up vector, for
            example 'x'
        :param upVector/upv: if provided, should be either a single up vector or a
            a list of up vectors (one per fraction); defaults to None
        :type upVector/upv:
            None,
            list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`,
            [list, tuple, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`]
        :param aimCurve/aic: an 'up' curve, as seen for example on Maya's
            ``curveWarp``; defaults to None
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from the aim curve by
            proximity rather than matched parameter; defaults to True
        :param bool squashStretch/ss: allow squash and stretch on the tangent
            vectors; defaults to False
        :param globalScale/gs: ignored if not a plug; a baseline scaling
            factor (will be normalized); defaults to None
        :param bool plug/p: force a dynamic output; defaults to False
        :param under/u: an optional destination parent for the joints;
            defaults to None
        :type under/u: str, :class:`~paya.runtime.nodes.Transform`
        :return: Joints, distributed uniformly (by length) along this curve.
        :rtype: [:class:`~paya.runtime.nodes.Joint`]
        """
        matrices = self.distributeMatrices(
            numberOrFractions,
            tangentAxis, upAxis,
            upv=upVector, aic=aimCurve,
            ss=squashStretch, cp=closestPoint,
            gs=globalScale, p=plug
        )

        if plug:
            _matrices = [matrix.get() for matrix in matrices]

        else:
            _matrices = matrices

        out = []

        for i, _matrix in enumerate(_matrices):
            with r.Name(i+1):
                joint = r.nodes.Joint.create(
                    displayLocalAxis=True,
                    under=under,
                    worldMatrix=_matrix
                )

                out.append(joint)

        if plug:
            for i, matrix, joint in zip(
                range(len(matrices)),
                matrices,
                out
            ):
                with r.Name(i+1):
                    matrix.applyViaOpm(joint, worldSpace=True)

        return out

    @short(
        upVector='upv',
        closestPoint='cp',
        globalScale='gs',
        squashStretch='ss',
        aimCurve='aic',
        plug='p',
        under='u'
    )
    def fitChain(
            self,
            numberOrFractions,
            aimAxis,
            upAxis,
            upVector=None,
            aimCurve=None,
            closestPoint=True,
            globalScale=None,
            squashStretch=False,
            plug=False,
            under=None
    ):
        matrices = self.distributeAimingMatrices(
            numberOrFractions,
            aimAxis, upAxis,
            upv=upVector, aic=aimCurve,
            cp=closestPoint, gs=globalScale,
            ss=squashStretch, p=plug
        )

        if plug:
            _matrices = [matrix.get() for matrix in matrices]

        else:
            _matrices = matrices

        chain = r.Chain.createFromMatrices(_matrices, under=under)

        if plug:
            for i, matrix, joint in zip(
                range(len(matrices)),
                matrices,
                chain
            ):
                matrix.applyViaOpm(joint, worldSpace=True)

        return chain

    #-----------------------------------------------------|    Clusters

    @short(tolerance='tol')
    def getCollocatedCVGroups(self, tolerance=1e-6):
        """
        :param float tolerance/tol: the collocation tolerance;
            defaults to 1e-7
        :return: A list of lists, where each sub-list comprises CVs which
            are collocated.
        :rtype: [[:class:`~paya.runtime.comps.NurbsCurveCV`]]
        """
        cvs = list(self.comp('cv'))
        num = len(cvs)
        indices = range(num)
        points = [r.pointPosition(cv, world=True) for cv in cvs]

        groups = []
        usedIndices = []

        for i, startCV, startPoint in zip(indices, cvs, points):
            if i in usedIndices:
                continue

            group = [startCV]
            usedIndices.append(i)

            for x, cv, point in zip(indices, cvs, points):
                if x in usedIndices:
                    continue

                if point.isEquivalent(startPoint, tol=1e-6):
                    group.append(cv)
                    usedIndices.append(x)

            groups.append(group)

        return groups

    @short(tolerance='tol', merge='mer')
    def clusterAll(self, merge=False, tolerance=1e-6):
        """
        Clusters-up the CVs on this curve.

        :param bool merge/mer: merge CVs if they overlap within the specified
            *tolerance*; defaults to False
        :param float tolerance/tol: the merging tolerance; defaults to 1e-6
        :return: The clusters.
        :rtype: [:class:`~paya.runtime.nodes.Cluster`]
        """
        if merge:
            items = self.getCollocatedCVGroups(tol=tolerance)

        else:
            items = self.comp('cv')

        clusters = []

        for i, item in enumerate(items):
            with r.Name(i+1):
                cluster = r.nodes.Cluster.create(item)

            clusters.append(cluster)

        return clusters