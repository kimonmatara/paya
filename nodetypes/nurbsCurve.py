import re

from paya.geoshapext import ShapeExtensionMeta
import paya.lib.nurbsutil as _nu
import paya.lib.mathops as _mo
import paya.lib.typeman as _tm
from paya.util import short
import paya.runtime as r



class NurbsCurve(metaclass=ShapeExtensionMeta):

    #--------------------------------------------------------------------|
    #--------------------------------------------------------------------|    Abstract I/O
    #--------------------------------------------------------------------|

    @property
    def localGeoOutput(self):
        return self.attr('local')

    @property
    def worldGeoOutput(self):
        return self.attr('worldSpace')[0]

    @property
    def geoInput(self):
        return self.attr('create')

    #--------------------------------------------------------------------|
    #--------------------------------------------------------------------|    Constructors
    #--------------------------------------------------------------------|

    @classmethod
    @short(
        degree='d',
        parent='p',
        name='n',
        conformShapeName='csn',
        intermediate='i',
        displayType='dt',
        bSpline='bsp',
        lineWidth='lw',
        dispCV='dcv'
    )
    def create(
            cls,
            *points,
            degree=3,
            name=None,
            bSpline=False,
            parent=None,
            displayType=None,
            conformShapeName=None,
            intermediate=False,
            lineWidth=None,
            dispCV=True
    ):
        """
        Draws static or dynamic curves.

        :param \*points: the input points; can be values or attributes
        :type \*points: list, tuple, str, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`, :class:`~paya.runtime.plugs.Vector`
        :param bool bSpline/bsp: only available if *degree* is 3; draw as a
            bSpline (similar to drawing by EP); defaults to False
        :param int degree/d: the curve degree; defaults to 3
        :param parent/p: an optional destination parent; no space conversion
            will take place; if the parent has transforms, the curve shape
            will be transformed as well; defaults to None
        :type parent/p: None, str, :class:`~paya.runtime.nodes.Transform`
        :param str name/n: the shape name; defaults to ``None``
        :param bool conformShapeName/csn: ignored if *parent* was omitted;
            rename the shape after it is reparented; defaults to True if
            *parent* was provided, otherwise False
        :param bool intermediate: set the shape to intermediate; defaults to
            False
        :param displayType/dt: if provided, an index or enum label:

            - 0: 'Normal'
            - 1: 'Template'
            - 2: 'Reference'

            If omitted, display overrides won't be activated at all.
        :type displayType/dt: None, int, str
        :param bool dispCV/dcv: display CVs on the curve; defaults to True
        :param lineWidth/lw: an override for the line width; defaults to None
        :type lineWidth/lw: None, float
        :return: The curve shape.
        :rtype: :class:`NurbsCurve`
        """
        if conformShapeName is None:
            conformShapeName = True if parent else False

        points = _tm.expandVectorArgs(points)
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

        infos = [_tm.mathInfo(point) for point in points]
        points = [info[0] for info in infos]
        hasPlugs = any([info[2] for info in infos])

        if hasPlugs:
            _points = [info[0].get() if info[2]
                else info[0] for info in infos]

        else:
            _points = points

        # Soft-draw

        kwargs = {}

        if not (parent and conformShapeName):
            mt = re.match(r"^(.*?)Shape$", name)

            if mt:
                kwargs['name'] = mt.groups()[0]

        curveXf = r.curve(
            knot=_nu.getKnotList(num, drawDegree),
            point=_points,
            degree=drawDegree,
            **kwargs
        )

        # Reparent
        curveShape = curveXf.getShape()

        if parent:
            r.parent(curveShape, parent, r=True, shape=True)
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
        conformShapeName='csn',
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
            conformShapeName=None,
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
        :param str name/n: the shape name; defaults to ``None``
        :param bool conformShapeName/csn: ignored if *parent* was omitted;
            rename the shape after it is reparented; defaults to True if
            *parent* was provided, otherwise False
        :return: The curve shape.
        :rtype: :class:`~paya.runtime.nodes.NurbsCurve`
        """
        points = _tm.expandVectorArgs(*points)

        live = any((_tm.isPlug(point) for point in points)) \
            or (directionVector and _tm.isPlug(directionVector)) \
            or _tm.isPlug(radius)

        output = r.plugs.NurbsCurve.createArc(
            points,
            directionVector=directionVector,
            radius=radius,
            toggleArc=toggleArc,
            sections=sections,
            degree=degree,
            guard=guard
        )

        shape = output.createShape(name=name,
                                   conformShapeName=conformShapeName)

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

    #--------------------------------------------------------------------|
    #--------------------------------------------------------------------|    Macro
    #--------------------------------------------------------------------|

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

    #--------------------------------------------------------------------|
    #--------------------------------------------------------------------|    SAMPLING
    #--------------------------------------------------------------------|

    @short(worldSpace='ws', plug='p')
    def length(self, worldSpace=False, plug=False):
        """
        Overloads the base PyMEL method to implement *worldSpace* and *plug*.

        :param bool worldSpace/ws: return the world-space length; defaults to
            ``False``
        :param bool plug/p: return the length as a plug, not a value; defaults to
            ``False``
        :return: The local- or world-space length of this curve.
        :rtype: :class:`float` | :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            output = self.getGeoOutput(ws=worldSpace)
            return output.length()

        if worldSpace:
            return self.attr('worldSpace')[0].length(p=False)

        # If not worldSpace, revert to PyMEL method
        return r.nodetypes.NurbsCurve.length(self)

    #--------------------------------------------------------------------|
    #--------------------------------------------------------------------|    DEFORMERS
    #--------------------------------------------------------------------|

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

