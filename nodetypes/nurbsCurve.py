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

    #-----------------------------------------------------|    Sampling

    def takeClosestPoint(self, refPoint):
        """
        :param refPoint: the reference point
        :return: The closest point along the curve to 'refPoint`.
        :rtype: :class:`~paya.runtime.data.Point`
        """
        return self.closestPoint(refPoint, space='world')

    def takePointAtParam(self, param):
        """
        :param param: the parameter to sample
        :type param: float, int,
            :class:`~paya.runtime.comps.NurbsCurveParameter`
        :return: A world-space point at the specified parameter.
        :rtype: :class:`~paya.runtime.data.Point`
        """
        param = float(param)
        point = self.getPointAtParam(param, space='world')
        return point

    def takeParamAtFraction(self, fraction):
        """
        :param float fraction: the length fraction to sample
        :return: A parameter at the given length fraction.
        :rtype:
            :class:`~paya.runtime.comps.NurbsCurveParameter`
        """
        length = self.length() * float(fraction)
        param = self.findParamFromLength(length)
        return self.comp('u')[param]

    def takePointAtFraction(self, fraction):
        """
        :param fraction: the length fraction to sample
        :return: A world-space point at the given length fraction.
        :rtype: :class:`~paya.runtime.data.Point`
        """
        param = self.takeParamAtFraction(fraction)
        return self.takePointAtParam(param)

    def distributePoints(self, numberOrFractions):
        """
        Return world-space points distributed along the length of the curve.

        :param numberOrFractions: this can either be a list of length
            fractions, or a number
        :type numberOrFractions: tuple, list or int
        :return: The distributed points.
        :rtype: :class:`list` of :class:`~paya.runtime.data.Point`
        """
        if isinstance(numberOrFractions, int):
            fractions = _mo.floatRange(0, 1, numberOrFractions)

        else:
            fractions = numberOrFractions

        return [self.takePointAtFraction(
            fraction) for fraction in fractions]