from importlib import reload
import paya.lib.nurbsutil as _nu
import paya.lib.mathops as _mo
import pymel.core.nodetypes as _nt
from paya.util import short
import paya.runtime as r


class NurbsCurve:

    #-----------------------------------------------------|    Constructors

    @classmethod
    @short(
        degree='d',
        under='u',
        name='n',
        conformShapeNames='csn',
        intermediate='i',
        displayType='dt',
        bSpline='bsp'
    )
    def create(
            cls,
            *points,
            degree=3,
            name=None,
            bSpline=False,
            under=None,
            displayType=None,
            conformShapeNames=True,
            intermediate=False
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
        :param bool conformShapeNames/csn: ignored if *under* is ``None``;
            conform destination parent shapes after reparenting; defaults to
            True
        :param bool intermediate: set the shape to intermediate; defaults to
            False
        :param displayType/dt: if provided, an index or enum label:

            - 0: 'Normal'
            - 1: 'Template'
            - 2: 'Reference'

            If omitted, display overrides won't be activated at all.
        :type displayType/dt: None, int, str
        :type displayType/dt:
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

            if conformShapeNames:
                r.PyNode(under).conformShapeNames()

        # Modify
        if bSpline or hasPlugs:
            origShape = curveShape.getOrigInput(create=True).node()

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

        return curveShape

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

        p, dim, isplug = _mo.info(refPoint)

        if isplug:
            return self.attr('worldSpace').closestPoint(refPoint)

        return self.closestPoint(refPoint, space='world')

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
        if plug:
            return self.attr('worldSpace').pointAtParam(param)

        p, dim, isplug = _mo.info(param)

        if isplug:
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

        length, dim, isplug = _mo.info(length)

        if isplug:
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

        fraction, dim, isplug = _mo.info(fraction)

        if isplug:
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

        point, dim, isplug = _mo.info(point)

        if isplug:
            return self.attr('worldSpace').paramAtPoint(point)

        point = self.closestPoint_(point)
        param = self.getParamAtPoint(point, space='world')

        if asComponent:
            return self.comp('u')[param]

        return param

    closestParam = paramAtPoint

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

        fraction, dim, isplug = _mo.info(fraction)

        if isplug:
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

        length, dim, isplug = _mo.info(length)

        if isplug:
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

        fraction, dim, isplug = _mo.info(fraction)

        if isplug:
            return self.attr('worldSpace').lengthAtFraction()

        return self.length() * fraction

    @short(plug='p')
    def lengthAtParam(self, param, plug=False):
        """
        :param param: the parameter
        :type param: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: Tthe curve length at the given parameter.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.attr('worldSpace').lengthAtParam()

        param, dim, isplug = _mo.info(param)

        if isplug:
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

        point, dim, isplug = _mo.info(point)

        if isplug:
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

        length, dim, isplug = _mo.info(length)

        if isplug:
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
        if plug:
            return self.attr('worldSpace').fractionAtParam(param)

        param, dim, isplug = _mo.info(param)

        if isplug:
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

        point, dim, isplug = _mo.info(point)

        if isplug:
            return self.attr('worldSpace').fractionAtPoint(point)

        param = self.paramAtPoint(point)
        return self.fractionAtParam(param)

    #-----------------------------------------------------|    Up vector sampling

    @short(plug='p')
    def upVectorAtParam(self, param, plug=False):
        """
        :param param: the parameter at which to sample the up vector
        :rtype param: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        p, pdim, pisplug = _mo.info(param)

        plug = plug or pisplug

        if plug:
            return self.attr('worldSpace').upVectorAtParam(param)

        else:
            position, tangent, derivative = \
                self.getDerivativesAtParm(float(param), space='world')

            return tangent.cross(derivative).normal()

    @short(plug='p')
    def upVectorAtFraction(self, fraction, plug=False):
        """
        :param fraction: the length fraction at which to sample the up vector
        :rtype fraction: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtFraction(fraction)
        return self.upVectorAtParam(param, p=plug)

    @short(plug='p')
    def upVectorAtLength(self, fraction, plug=False):
        """
        :param length: the length at which to sample the up vector
        :rtype length: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtLength(length)
        return self.upVectorAtParam(param, p=plug)

    @short(plug='p')
    def upVectorAtPoint(self, point, plug=False):
        """
        :param point: the point at which to sample the up vector
        :rtype point: list, tuple, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A vector that's perpendicular to both the curve normal
            and tangent.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        param = self.paramAtPoint(point)
        return self.upVectorAtParam(param, p=plug)

    #-----------------------------------------------------|    Matrix sampling

    @short(
        tangentStretch='ts',
        upVector='upv',
        upObject='upo',
        upCurve='upc',
        fraction='fr',
        globalScale='gs',
        matchedCurve='mc',
        plug='p'
    )
    def _matrixAtParamOrFraction(
            self,
            paramOrFraction,
            tangentAxis,
            upAxis,
            tangentStretch=False, # ignored in soft impl
            upVector=None,
            upObject=None,
            upCurve=None,
            fraction=False,
            globalScale=None, # ignored in soft impl
            matchedCurve=False,
            plug=False
    ):
        if plug or any((
            _mo.isPlug(x) for x in [
                paramOrFraction, upVector, upCurve, globalScale]
        )):
            return self.attr('worldSpace')._matrixAtParamOrFraction(
                paramOrFraction,
                tangentAxis,
                upAxis,
                ts=tangentStretch,
                upv=upVector,
                upo=upObject,
                upc=upCurve,
                fr=fraction,
                gs=globalScale,
                mc=matchedCurve
            )

        if upVector:
            upVector = _mo.info(upVector)[0]

        if upObject:
            upObject = r.PyNode(upObject)

        if upCurve:
            upCurve = r.PyNode(upCurve)

        #------------------------------|    Soft implementation

        if fraction:
            param = self.paramAtFraction(paramOrFraction)

        else:
            param = float(paramOrFraction)


        position, tangent, derivative = \
            self.getDerivativesAtParm(param, space='world')

        # Resolve up vector

        if upVector:
            if upObject:
                upVector *= upObject.getMatrix(worldSpace=True)

        else:
            if upObject:
                upVector = upObject.getWorldPosition()-position

            else:
                if upCurve:
                    if matchedCurve:
                        interest = upCurve.pointAtParam(param)

                    else:
                        interest = upCurve.closestPoint_(position)

                    upVector = interest-position

                else:
                    upVector = self.normal(param, space='world')

        return r.createMatrix(tangentAxis, tangent,
            upAxis, upVector, t=position).pk(t=True, r=True)

    @short(
        tangentStretch='ts',
        upVector='upv',
        upObject='upo',
        upCurve='upc',
        globalScale='gs',
        matchedCurve='mc',
        plug='p'
    )
    def matrixAtParam(
            self,
            param,
            tangentAxis,
            upAxis,
            tangentStretch=False, # ignored in soft impl
            upVector=None,
            upObject=None,
            upCurve=None,
            globalScale=None, # ignored in soft impl
            matchedCurve=False,
            plug=False
    ):
        """
        :param param: the parameter at which to sample the matrix
        :type param: float, str, :class:`~paya.runtime.Math1D`
        :param str tangentAxis: the axis to align to the curve tangent
        :param str upAxis: the axis to align to the resolved up vector
        :param bool tangentStretch/ts: incorporate tangent stretching
            (dynamic only); defaults to False
        :param upVector/upv: used as an up vector on its own, or extracted from
            *upObject*; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param upCurve/upc: an up curve; defaults to None
        :type upCurve/upc: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param upObject/upo: used as an aiming interest on its own, or as a source
            for *upVector*; defaults to None
        :type upObject/upo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param globalScale/gs: used to drive scaling on dynamic matrices only;
            the scale will be normalised; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *upCurve* has the
            same U domain as this curve, to avoid unnecessary closest-point
            calculations; defaults to False
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A matrix at the specified parameter, constructed using the
            most efficient DG configuration for the given options.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        return self._matrixAtParamOrFraction(
            param,
            tangentAxis,
            upAxis,
            ts=tangentStretch,
            upv=upVector,
            upo=upObject,
            upc=upCurve,
            fr=False,
            gs=globalScale,
            mc=matchedCurve,
            p=plug
        )

    @short(
        tangentStretch='ts',
        upVector='upv',
        upObject='upo',
        upCurve='upc',
        globalScale='gs',
        matchedCurve='mc',
        plug='p'
    )
    def matrixAtFraction(
            self,
            fraction,
            tangentAxis,
            upAxis,
            tangentStretch=False, # ignored in soft impl
            upVector=None,
            upObject=None,
            upCurve=None,
            globalScale=None, # ignored in soft impl
            matchedCurve=False,
            plug=False
    ):
        """
        :param fraction: the fraction at which to sample the matrix
        :type fraction: float, str, :class:`~paya.runtime.Math1D`
        :param str tangentAxis: the axis to align to the curve tangent
        :param str upAxis: the axis to align to the resolved up vector
        :param bool tangentStretch/ts: incorporate tangent stretching
            (dynamic only); defaults to False
        :param upVector/upv: used as an up vector on its own, or extracted from
            *upObject*; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param upCurve/upc: an up curve; defaults to None
        :type upCurve/upc: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param upObject/upo: used as an aiming interest on its own, or as a source
            for *upVector*; defaults to None
        :type upObject/upo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param globalScale/gs: used to drive scaling on dynamic matrices only;
            the scale will be normalised; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *upCurve* has the
            same U domain as this curve, to avoid unnecessary closest-point
            calculations; defaults to False
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A matrix at the specified fraction, constructed using the
            most efficient DG configuration for the given options.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        return self._matrixAtParamOrFraction(
            fraction,
            tangentAxis,
            upAxis,
            ts=tangentStretch,
            upv=upVector,
            upo=upObject,
            upc=upCurve,
            fr=True,
            gs=globalScale,
            mc=matchedCurve,
            p=plug
        )

    @short(
        tangentStretch='ts',
        upVector='upv',
        upObject='upo',
        upCurve='upc',
        globalScale='gs',
        matchedCurve='mc',
        plug='p'
    )
    def matrixAtLength(
            self,
            length,
            tangentAxis,
            upAxis,
            tangentStretch=False, # ignored in soft impl
            upVector=None,
            upObject=None,
            upCurve=None,
            globalScale=None, # ignored in soft impl
            matchedCurve=False,
            plug=False
    ):
        """
        :param length: the length at which to sample the matrix
        :type length: float, str, :class:`~paya.runtime.Math1D`
        :param str tangentAxis: the axis to align to the curve tangent
        :param str upAxis: the axis to align to the resolved up vector
        :param bool tangentStretch/ts: incorporate tangent stretching
            (dynamic only); defaults to False
        :param upVector/upv: used as an up vector on its own, or extracted from
            *upObject*; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param upCurve/upc: an up curve; defaults to None
        :type upCurve/upc: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param upObject/upo: used as an aiming interest on its own, or as a source
            for *upVector*; defaults to None
        :type upObject/upo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param globalScale/gs: used to drive scaling on dynamic matrices only;
            the scale will be normalised; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *upCurve* has the
            same U domain as this curve, to avoid unnecessary closest-point
            calculations; defaults to False
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A matrix at the specified length, constructed using the
            most efficient DG configuration for the given options.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        return self._matrixAtParamOrFraction(
            self.paramAtLength(length),
            tangentAxis,
            upAxis,
            ts=tangentStretch,
            upv=upVector,
            upo=upObject,
            upc=upCurve,
            fr=False,
            gs=globalScale,
            mc=matchedCurve,
            p=plug
        )

    @short(
        tangentStretch='ts',
        upVector='upv',
        upObject='upo',
        upCurve='upc',
        fraction='fr',
        globalScale='gs',
        matchedCurve='mc',
        plug='p'
    )
    def matrixAtPoint(
            self,
            point,
            tangentAxis,
            upAxis,
            tangentStretch=False,
            upVector=None,
            upObject=None,
            upCurve=None,
            globalScale=None,
            matchedCurve=False,
            plug=False
    ):
        """
        :param point: the point at which to sample the matrix
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Point`
        :param str tangentAxis: the axis to align to the curve tangent
        :param str upAxis: the axis to align to the resolved up vector
        :param bool tangentStretch/ts: incorporate tangent stretching
            (dynamic only); defaults to False
        :param upVector/upv: used as an up vector on its own, or extracted from
            *upObject*; defaults to None
        :type upVector/upv: None, list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param upCurve/upc: an up curve; defaults to None
        :type upCurve/upc: str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param upObject/upo: used as an aiming interest on its own, or as a source
            for *upVector*; defaults to None
        :type upObject/upo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool fraction/fr: interpret *paramOrFraction* as a fraction;
            defaults to False
        :param globalScale/gs: used to drive scaling on dynamic matrices only;
            the scale will be normalised; defaults to None
        :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
        :param bool matchedCurve/mc: set this to True when *upCurve* has the
            same U domain as this curve, to avoid unnecessary closest-point
            calculations; defaults to False
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A matrix at the specified point, constructed using the
            most efficient DG configuration for the given options.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        return self._matrixAtParamOrFraction(
            self.paramAtPoint(point),
            tangentAxis,
            upAxis,
            ts=tangentStretch,
            upv=upVector,
            upo=upObject,
            upc=upCurve,
            gs=globalScale,
            mc=matchedCurve,
            fr=False,
            p=plug
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

    # @short(
    #     globalScale='gs',
    #     tangentStretch='ts',
    #     upVectors='upv',
    #     upCurve='upc',
    #     matchedCurve='mc',
    #     plug='p'
    # )
    # def distributeMatrices(
    #         self,
    #         numberOrFractions,
    #         tangentAxis,
    #         upAxis,
    #         upVectors=None,
    #         upCurve=None,
    #         globalScale=None,
    #         matchedCurve=False,
    #         tangentStretch=False,
    #         plug=False
    # ):
    #     """
    #     :param numberOrFractions: either a number of sample points, or an
    #         explicit list of 0.0 -> 1.0 length fractions
    #     :type numberOrFractions: int, [float],
    #         [:class:`~paya.runtime.plugs.Math1D`]
    #     :param str tangentAxis: the axis to align to the curve tangent
    #     :param str upAxis: the axis to align to the resolved up vector
    #     :param bool tangentStretch/ts: incorporate tangent stretching
    #         (dynamic only); defaults to False
    #     :param upVector/upv: used as an up vector on its own, or extracted from
    #         *upObject*; this can be provided as a single vector, or a list of
    #         vectors (one per sample point); defaults to None
    #     :type upVector/upv: None, list, tuple, str,
    #         :class:`~paya.runtime.data.Vector`,
    #         :class:`~paya.runtime.plugs.Vector`
    #         [list], [tuple], [str],
    #         [:class:`~paya.runtime.data.Vector`],
    #         [:class:`~paya.runtime.plugs.Vector`]
    #     :param upCurve/upc: an up curve; defaults to None
    #     :type upCurve/upc: str, :class:`~paya.runtime.nodes.Transform`,
    #         :class:`~paya.runtime.nodes.NurbsCurve`,
    #         :class:`~paya.runtime.plugs.NurbsCurve`
    #     :param bool fraction/fr: interpret *paramOrFraction* as a fraction;
    #         defaults to False
    #     :param globalScale/gs: used to drive scaling on dynamic matrices only;
    #         the scale will be normalised; defaults to None
    #     :type globalScale/gs: None, float, :class:`~paya.runtime.plugs.Math1D`
    #     :param bool matchedCurve/mc: set this to True when *upCurve* has the
    #         same U domain as this curve, to avoid unnecessary closest-point
    #         calculations; defaults to False
    #     :return: Matrices distributed uniformly along the curve.
    #     :rtype: [:class:`~paya.runtime.plugs.Matrix`],
    #         [:class:`~paya.runtime.data.Matrix`]
    #     """
    #     fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)
    #     num = len(fractions)
    #
    #     if upVectors:
    #         upVectors = _mo.resolveMultiVectorArg(num, upVectors)
    #
    #     out = []
    #
    #     for i, fraction in enumerate(fractions):
    #         with r.Name(i+1):
    #             matrix = self.matrixAtFraction(
    #                 fraction,
    #                 tangentAxis,
    #                 upAxis,
    #                 upv=upVectors[i] if upVectors else None,
    #                 upc=upCurve,
    #                 gs=globalScale,
    #                 mc=matchedCurve,
    #                 ts=tangentStretch,
    #                 p=plug
    #             )
    #
    #             out.append(matrix)
    #
    #     return out
    #
    # @short(
    #     globalScale='gs',
    #     tangentStretch='ts',
    #     upVectors='upv',
    #     upCurve='upc',
    #     matchedCurve='mc',
    #     plug='p'
    # )
    # def distributeAimingMatrices(
    #         self,
    #         numberOrFractions,
    #         downAxis,
    #         upAxis,
    #         upVectors=None,
    #         upCurve=None,
    #         globalScale=None,
    #         matchedCurve=False,
    #         tangentStretch=False,
    #         plug=False
    # ):
    #     """
    #     :param numberOrFractions: either a number of sample points, or an
    #         explicit list of 0.0 -> 1.0 length fractions
    #     :type numberOrFractions: int, [float],
    #         [:class:`~paya.runtime.plugs.Math1D`]
    #     :param str downAxis: the aiming axis for each matrix
    #     :param str upAxis: the axis to align to the resolved up vector
    #     :type upVector/upv: None, list, tuple, str,
    #         :class:`~paya.runtime.data.Vector`,
    #         :class:`~paya.runtime.plugs.Vector`
    #         [list], [tuple], [str],
    #         [:class:`~paya.runtime.data.Vector`],
    #         [:class:`~paya.runtime.plugs.Vector`]
    #     :param upCurve/upc: an up curve; defaults to None
    #     :param globalScale/gs: used to drive scaling on dynamic matrices only;
    #         the scale will be normalised; defaults to None
    #     :param matchedCurve:
    #     :param bool tangentStretch/ts: incorporate tangent stretching
    #         (dynamic only); defaults to False
    #     :param bool plug/p: force a dynamic output; defaults to False
    #     :return: Aiming matrices, uniformly distributed along the length of
    #         this curve.
    #     :rtype: [:class:`~paya.runtime.data.Matrix`]
    #         [:class:`~paya.runtime.plugs.Matrix`]
    #     """
    #     defer = False
    #
    #     if plug:
    #         defer = True
    #
    #     else:
    #         if upVectors is not None:
    #             if any((_mo.isPlug(x) for x in upVectors)):
    #                 defer = True
    #
    #             else:
    #                 if any((_mo.isPlug(x) for x in [
    #                     upCurve, globalScale, matchedCurve])):
    #                     defer = True
    #
    #     if defer:
    #         return self.attr('worldSpace')[0].distributeAimingMatrices(
    #             numberOrFractions,
    #             downAxis,
    #             upAxis,
    #             upv=upVectors,
    #             upc=upCurve,
    #             gs=globalScale,
    #             mc=matchedCurve,
    #             ts=tangentStretch
    #         )
    #
    #     #------------------------------------|    Soft implementation
    #
    #     fractions = _mo.resolveNumberOrFractionsArg(numberOrFractions)
    #     params = [self.paramAtFraction(fraction) for fraction in fractions]
    #     points = [self.pointAtParam(param) for param in params]
    #
    #     num = len(fractions)
    #
    #     if upVectors:
    #         upVectors = _mo.resolveMultiVectorArg(num, upVectors)
    #
    #     elif upCurve:
    #         upCurve = r.PyNode(upCurve)
    #
    #         if matchedCurve:
    #             interests = [upCurve.pointAtParam(
    #                 float(param)) for param in params]
    #
    #         else:
    #             interests = [upCurve.closestPoint_(point) for point in points]
    #
    #         upVectors = [interest-point for \
    #                 interest, point in zip(interests, points)]
    #
    #     else:
    #         upVectors = [self.normal(
    #             float(param), space='world') for param in params]
    #
    #     aimVectors = []
    #
    #     for i, thisPoint in enumerate(points[:-1]):
    #         nextPoint = points[i+1]
    #         aimVectors.append(nextPoint-thisPoint)
    #
    #     aimVectors.append(aimVectors[-1])
    #
    #     matrices = []
    #
    #     for point, aimVector, upVector in zip(
    #         points,
    #         aimVectors,
    #         upVectors
    #     ):
    #         matrix = r.createMatrix(
    #             downAxis, aimVector,
    #             upAxis, upVector,
    #             t=point
    #         ).pk(t=True, r=True)
    #
    #         matrices.append(matrix)
    #
    #     return matrices