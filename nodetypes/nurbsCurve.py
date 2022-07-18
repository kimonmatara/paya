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
            origShape = curveShape.getOriginalGeometry(create=True).node()

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
        return self.attr('worldSpace')[0]

    @property
    def localGeoOutput(self):
        return self.attr('local')

    #-----------------------------------------------------|    Point sampling

    def closestPoint_(self, refPoint):
        """
        Returns the closest world-space point along this curve to the given
        reference point. If the reference point is a plug, the return will
        also be a plug.

        For persistent sampling against a reference value, call
        :meth:`~paya.runtime.plugs.NurbsCurve.closestPoint` on
        ``.worldSpace[0]``.

        :param refPoint: the reference point
        :type refPoint: list, tuple, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The closest point along the curve to *refPoint*.
        :rtype: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        p, dim, isplug = _mo.info(refPoint)

        if isplug:
            return self.attr('worldSpace')[0].closestPoint(refPoint)

        return self.closestPoint(refPoint, space='world')

    def pointAtParam(self, param):
        """
        Returns a world-space point at the specified parameter. If the
        parameter is a plug, the return will also be a plug.

        For persistent sampling against a reference value, call
        :meth:`~paya.runtime.plugs.NurbsCurve.pointAtParam` on
        ``.worldSpace[0]``.

        :param param: the parameter at which to sample
        :type param: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        :return: The sampled point.
        :type: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        p, dim, isplug = _mo.info(param)

        if isplug:
            return self.attr('worldSpace')[0].pointAtParam(param)

        return self.getPointAtParam(float(param), space='world')

    def pointAtLength(self, length):
        """
        Returns a world-space point at the specified length. If the
        length is a plug, the return will also be a plug.

        For persistent sampling against a reference value, call
        :meth:`~paya.runtime.plugs.NurbsCurve.pointAtLength` on
        ``.worldSpace[0]``.

        :param length: the length at which to sample
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The sampled point.
        :type: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        length, dim, isplug = _mo.info(length)

        if isplug:
            return self.attr('worldSpace')[0].pointAtLength(length)

        param = self.findParamFromLength(length)
        return self.pointAtParam(param)

    def pointAtFraction(self, fraction):
        """
        Returns a world-space point at the specified length fraction.
        If the fraction is a plug, the return will also be a plug.

        For persistent sampling against a reference value, call
        :meth:`~paya.runtime.plugs.NurbsCurve.pointAtFraction` on
        ``.worldSpace[0]``.

        :param fraction: the length fraction at which to sample
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :return: The sampled point.
        :type: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        fraction, dim, isplug = _mo.info(fraction)

        if isplug:
            return self.attr('worldSpace')[0].pointAtFraction(fraction)

        length = self.length() * fraction
        return self.pointAtLength(length)

    def distributePoints(self, numberOrFractions):
        """
        Returns world-space points distributed along the length of the curve.

        For a dynamic version, call
        :meth:`~paya.runtime.plugs.NurbsCurve.distributePoints` on
        ``.worldSpace[0]``.

        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :type numberOrFractions: tuple, list or int
        :return: The distributed points.
        :rtype: [:class:`~paya.runtime.data.Point`]
        """
        if isinstance(numberOrFractions, int):
            fractions = _mo.floatRange(0, 1, numberOrFractions)

        else:
            fractions = numberOrFractions

        return [self.pointAtFraction(fraction) for fraction in fractions]

    #-----------------------------------------------------|    Param sampling

    @short(asComponent='ac')
    def paramAtPoint(self, point, asComponent=True):
        """
        Returns the parameter at the given point. If the point is
        a plug, the return will also be a plug. This is a 'forgiving'
        implementation; a closest param will still be returned if the
        point is not on the curve.

        To sample dynamically against a reference value, call
        :meth:`~paya.runtime.plugs.NurbsCurve.paramAtPoint` on
        ``.worldSpace[0]``.

        :alias: ``closestParam``
        :param point: the reference point
        :type point: list, tuple, :class:`~paya.runtime.data.Point`
            :class:`~paya.runtime.plugs.Vector`
        :param bool asComponent/ac: return an instance of
            :class:`~paya.runtime.comps.NurbsCurveParameter` rather than
            a float; defaults to True
        :return: The sampled parameter.
        :rtype: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        """
        point, dim, isplug = _mo.info(point)

        if isplug:
            return self.attr('worldSpace')[0].paramAtPoint(point)

        point = self.closestPoint_(point)
        param = self.getParamAtPoint(point, space='world')

        if asComponent:
            return self.comp('u')[param]

        return param

    closestParam = paramAtPoint

    @short(asComponent='ac')
    def paramAtFraction(self, fraction, asComponent=True):
        """
        Returns the parameter at the given length fraction. If the fraction
        is a plug, the return will also be a plug.

        To sample dynamically against a reference value, call
        :meth:`~paya.runtime.plugs.NurbsCurve.paramAtFraction` on
        ``.worldSpace[0]``.

        :param fraction: the length fraction at which to sample
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool asComponent/ac: return an instance of
            :class:`~paya.runtime.comps.NurbsCurveParameter` rather than
            a float; defaults to True
        :return: The sampled parameter.
        :rtype: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        """
        fraction, dim, isplug = _mo.info(fraction)

        if isplug:
            return self.attr('worldSpace')[0].paramAtFraction(fraction)

        length = self.length() * fraction
        param = self.findParamFromLength(length)

        if asComponent:
            return self.comp('u')[param]

        return param

    @short(asComponent='ac')
    def paramAtLength(self, length, asComponent=True):
        """
        Returns the parameter at the given length. If the length
        is a plug, the return will also be a plug.

        To sample dynamically against a reference value, call
        :meth:`~paya.runtime.plugs.NurbsCurve.paramAtLength` on
        ``.worldSpace[0]``.

        :param length: the length at which to sample
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool asComponent/ac: return an instance of
            :class:`~paya.runtime.comps.NurbsCurveParameter` rather than
            a float; defaults to True
        :return: The sampled parameter.
        :rtype: float, :class:`~paya.runtime.comps.NurbsCurveParameter`,
            :class:`~paya.runtime.plugs.Math1D`
        """
        length, dim, isplug = _mo.info(length)

        if isplug:
            return self.attr('worldSpace')[0].paramAtLength(length)

        param = self.findParamFromLength(length)

        if asComponent:
            return self.comp('u')[param]

        return param

    #
    # def pointAtLength(self, length):
    #     """
    #     Returns a world-space point at the given length. For a dynamic version,
    #     call :meth:`~paya.runtime.plugs.NurbsCurve.pointAtLength` on an output
    #     plug.
    #
    #     :param float length: the length at which to sample
    #     :return: The sampled point.
    #     :rtype: :class:`~paya.runtime.data.Point`
    #     """
    #     param = self.paramAtLength(length)
    #     return self.pointAtParam(param)
    #
    # def pointAtFraction(self, fraction):
    #     """
    #     Returns a world-space point at the given length fraction. For a
    #     dynamic version, call
    #     :meth:`~paya.runtime.plugs.NurbsCurve.pointAtFraction` on an output
    #     plug.
    #
    #     :param float fraction: the length fraction at which to sample
    #     :return: The sampled point.
    #     :rtype: :class:`~paya.runtime.data.Point`
    #     """
    #     param = self.paramAtFraction(fraction)
    #     return self.pointAtParam(param)
    #
    # #-----------------------------------------------------|    Param sampling
    #
    # @short(asComponent='ac')
    # def paramAtLength(self, length, asComponent=True):
    #     """
    #     Returns the parameter at the given length fraction. For a dynamic
    #     version, call
    #     :meth:`~paya.runtime.plugs.NurbsCurve.paramAtLength` on an output
    #     plug.
    #
    #     :param float length: the length at which to sample
    #     :param bool asComponent/ac: return an instance of
    #         :class:`~paya.runtime.comps.NurbsCurveParameter` instead of
    #         a float; defaults to True
    #     :return: The sampled parameter.
    #     :rtype: :class:`~paya.runtime.comps.NurbsCurveParameter`, float
    #     """
    #     param = self.findParamFromLength(length)
    #
    #     if asComponent:
    #         return self.comp('u')[param]
    #
    #     return param
    #
    # @short(asComponent='ac')
    # def paramAtFraction(self, fraction, asComponent=True):
    #     """
    #     Returns the parameter at the given length fraction. For a dynamic
    #     version, call
    #     :meth:`~paya.runtime.plugs.NurbsCurve.paramAtFraction` on an output
    #     plug.
    #
    #     :param float fraction: length fraction at which to sample
    #     :param bool asComponent/ac: return an instance of
    #         :class:`~paya.runtime.comps.NurbsCurveParameter` instead of
    #         a float; defaults to True
    #     :return: The sampled parameter.
    #     :rtype: :class:`~paya.runtime.comps.NurbsCurveParameter`, float
    #     """
    #     length = self.length() * fration
    #     param = self.findParamFromLength(length)
    #
    #     if asComponent:
    #         return self.comp('u')[param]
    #
    #     return param