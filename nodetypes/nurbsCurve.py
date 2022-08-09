import maya.OpenMaya as om
import pymel.util as _pu
import pymel.core.nodetypes as _nt

import paya.lib.nurbsutil as _nu
from paya.lib.loopback import Loopback
import paya.lib.nurbsutil as _nu
import paya.lib.mathops as _mo
import paya.lib.plugops as _po
from paya.util import short
import paya.runtime as r



class NurbsCurve:

    #----------------------------------------------------------------|
    #----------------------------------------------------------------|    Abstract I/O
    #----------------------------------------------------------------|

    @property
    def geoInput(self):
        return self.attr('create')

    @property
    def worldGeoOutput(self):
        return self.attr('worldSpace')[0]

    @property
    def localGeoOutput(self):
        return self.attr('local')

    #----------------------------------------------------------------|
    #----------------------------------------------------------------|    Constructors
    #----------------------------------------------------------------|

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

    #----------------------------------------------------------------|
    #----------------------------------------------------------------|    Macro
    #----------------------------------------------------------------|

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

    #----------------------------------------------------------------|
    #----------------------------------------------------------------|    Sampling
    #----------------------------------------------------------------|

    @short(parametric='par', uniform='uni')
    def _resolveNumberOrValues(self,
                               numberOrValues, parametric=False,
                               uniform=False):
        if parametric:
            if uniform:
                fractions = _mo.floatRange(0, 1, numberOrValues)
                length = self.length()

                values = [self.paramAtLength(
                    length * f) for f in fractions]

            else:
                umin, umax = self.getKnotDomain()
                values = _mo.floatRange(umin, umax, numberOrValues)

        else:
            values = _mo.floatRange(0, 1, numberOrValues)

        return values

    #------------------------------------------|    Curve-level

    @short(reuse='re', worldSpace='ws')
    def initCurveInfo(self, reuse=True, worldSpace=False):
        """
        Initialises, or retrieves, a ``curveInfo`` node connected to this
        curve.

        :param bool reuse/re: look for existing nodes
        :param bool worldSpace/ws: pull info off the world-space curve
            output; defaults to False
        :return: The ``curveInfo`` node.
        :rtype: :class:`~paya.runtime.nodes.CurveInfo`
        """
        return self.getGeoOutput(ws=worldSpace).info(re=reuse)

    @short(plug='p', tolerance='tol', worldSpace='ws')
    def length(self, plug=False, tolerance=0.001, worldSpace=False):
        """
        Overload of :meth:`pymel.core.nodetypes.NurbsCurve.length`.

        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :param bool worldSpace/ws: return the world-space length; defaults
            to False
        :param float tolerance/tol: ignored if *plug* or *worldSpace*;
            defaults to 0.001
        :return: The length of this curve.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            info = self.initCurveInfo(ws=worldSpace)
            return info.attr('arcLength')

        if worldSpace:
            # There's no API method to get a world-space length, annoyingly
            sampler = self.worldGeoOutput.info(re=False)
            out = sampler.attr('arcLength').get()
            return out

        return r.nodetypes.NurbsCurve.length(self, tolerance=tolerance)

    #------------------------------------------|    Get points

    @short(plug='p', worldSpace='ws')
    def getCVs(self, space=None, worldSpace=None, plug=False):
        """
        Overloads :meth:`pymel.core.nodetypes.NurbsCurve.getCVs`.

        :param str space: the API enumerator option for the sampling space;
            one of:

            -   'transform' (not supported for *plug*;
                set to 'object' or 'preTransform' instead)

            -   'preTransform' (the default)
            -   'postTransform' (not supported for *plug*;
                set to 'object' or 'preTransform' instead)

            -   'world'
            -   'object' (same as 'preTransform')

        :param bool worldSpace/ws: if this is specified then it will
            override *space* to 'preTransform' if False and 'world' if
            True; defaults to None
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: A list of control vertex positions, or the ``controlPoints``
            array attribute of a ``curveInfo`` node.
        :rtype: [:class:`~paya.runtime.data.Point`
            ], :class:`~paya.runtime.plugs.Vector`
        """
        if worldSpace is not None:
            space = 'world' if worldSpace else 'preTransform'

        elif space is None:
            space = 'preTransform'

        if plug:
            if space in ['preTransform', 'object', 'world']:
                return self.getGeoOutput(ws=space=='world').getCVs()
            else:
                raise NotImplementedError(
                    "Sampling space not supported for plug output: "+space
                )

        return r.nodetypes.NurbsCurve.getCVs(self, space=space)

    @short(worldSpace='ws', plug='p')
    def closestPoint(self, toThisPoint, param=None,
                     tolerance=0.001, space='preTransform',
                     worldSpace=None, plug=False):
        """
        Overloads :meth:`pymel.core.nodetypes.NurbsCurve.closestPoint`.

        :param toThisPoint: the reference point
        :type toThisPoint: tuple, list, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Point`
        :param param: this is passed along to the PyMEL method, and entirely
            ignored for the *plug* implementation; to get a parameter, use
            :meth:`closestParam` instead; defaults to None
        :param float tolerance/tol: ignored for the *plug* implementation;
            defaults to 0.001
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to 'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to 'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: if this is specified then it will
            override *space* to 'preTransform' if False and 'world' if
            True; defaults to None
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: :class:`~paya.runtime.data.Point` |
            :class:`~paya.runtime.plugs.Vector`
        """
        toThisPoint = _mo.conformVectorArg(toThisPoint)

        if worldSpace is not None:
            space = 'world' if worldSpace else 'preTransform'

        if plug:
            if space in ('world', 'preTransform', 'object'):
                output = self.getGeoOutput(ws=space == 'world')
                return output.closestPoint(toThisPoint)

            else:
                raise NotImplementedError(
                    "Space not implemented for plug output: {}".format(space))

        return r.nodetypes.NurbsCurve.closestPoint(self,
            toThisPoint, tolerance=tolerance, space=space)

    @short(plug='p', worldSpace='ws')
    def pointAtCV(self, cv, plug=False, worldSpace=False):
        """
        :param index cv: the index of the CV to sample
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :param bool worldSpace/ws: return the world-space position;
            defaults to False
        :return: The point position of the specified CV.
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).pointAtCV(cv)

        cv = self.comp('cv')[cv]

        kw = {}

        if world:
            kw['world'] = True

        else:
            kw['local'] = True

        return r.pointPosition(cv, **kw)

    @short(plug='p', worldSpace='ws')
    def pointAtParam(self, param,
            space='preTransform', plug=False, worldSpace=None):
        """
        Overloads :meth:`pymel.core.nodetypes.NurbsCurve.getPointAtParam`.

        :alias: ``getPointAtParam``
        :param param: the parameter at which to sample a point
        :type param: float, :class:`~paya.runtime.plugs.Math1D
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: if this is specified then it will
            override *space* to 'preTransform' if False and 'world' if
            True; defaults to None
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The point at the specified parameter.
        :rtype: :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if worldSpace is not None:
            if worldSpace:
                space = 'world'

            else:
                space = 'preTransform'

        if plug:
            if space in ['preTransform', 'object', 'world']:
                output = self.getGeoOutput(ws=space=='world')
                return output.pointAtParam(param)

            else:
                raise NotImplementedError(
                    "Space not implemented for plug output: {}".format(space))

        return r.nodetypes.NurbsCurve.getPointAtParam(
            self, param, space=space
        )

    getPointAtParam = pointAtParam

    @short(plug='p', worldSpace='ws')
    def pointAtFraction(self, fraction, plug=False, worldSpace=False):
        """
        :param param: the fraction at which to sample a point
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :param bool worldSpace/ws: return a world-space point; defaults to
            False
        :return: A point at the specified fraction.
        :rtype: :class:`~paya.runtime.plugs.Vector`,
            :class:`~paya.runtime.data.Point`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).pointAtFraction(fraction)

        fullLength = self.length()  # doesn't matter whether world
                                    # space or local for this

        param = r.nodes.NurbsCurve.findParamFromLength(
            self, fullLength * fraction
        )

        return self.pointAtParam(param, ws=worldSpace)

    @short(plug='p', worldSpace='ws')
    def pointAtLength(self, length, plug=False, worldSpace=False):
        """
        :param param: the length at which to sample a point
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: force a dynamic output; defaults to False
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: A point at the specified length.
        :rtype: :class:`~paya.runtime.plugs.Vector`,
            :class:`~paya.runtime.data.Point`
        """
        if plug:
            return (self.worldGeoOutput if worldSpace \
                else self.localGeoOutput).pointAtLength(length)

        if worldSpace:
            # Will have to perform some conversions, since API method doesn't
            # support world-space
            fullLength = self.length(ws=True)
            fraction = length / fullLength
            length = self.length() * fraction # local space

        param = r.nodes.NurbsCurve.findParamFromLength(self, length)
        return self.pointAtParam(param, ws=worldSpace)

    @short(parametric='par',
           uniform='uni',
           plug=False,
           worldSpace='ws')
    def distributePoints(self,
                         numberOrValues,
                         parametric=False,
                         uniform=False,
                         plug=False,
                         worldSpace=False):
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
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :param bool worldSpace/ws: generate world-space points; defaults to
            False
        :return: Points, distributed along this curve.
        :rtype: [:class:`~paya.runtime.plugs.Vector`]
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).distributePoints(
                numberOrValues, par=parametric, uni=uniform
            )

        values = self._resolveNumberOrValues(numberOrValues,
                                             parametric=parametric,
                                             uniform=uniform)

        if parametric:
            meth = self.pointAtParam

        else:
            meth = self.pointAtFraction

        return [meth(value, ws=worldSpace) for value in values]

    #------------------------------------------|    Get params

    @short(plug='p')
    def getKnotDomain(self, plug=False):
        """
        Overloads :meth:`pymel.core.nodetypes.NurbsCurve.getKnotDomain`.

        :param bool plug/p: return plugs, not values; defaults to False
        :return: The min and max U parameters on this curve.
        :rtype: (:class:`float` | :class:`~paya.runtime.plugs.Math1D`,
            :class:`float` | :class:`~paya.runtime.plugs.Math1D`)
        """
        if plug:
            return self.getGeoOutput().getKnotDomain()

        return r.nodetypes.NurbsCurve.getKnotDomain(self)

    @short(plug='p')
    def paramAtStart(self, plug=True):
        """
        :param bool plug/p: return plugs, not values; defaults to True
        :return: The parameter at the start of this curve.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.paramAtLength(0.0, p=True)

        return self.getKnotDomain(p=False)[0]

    @short(plug='p')
    def paramAtEnd(self, plug=True):
        """
        :param bool plug/p: return plugs, not values; defaults to True
        :return: The parameter at the end of this curve.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.paramAtFraction(1.0, p=True)

        return self.getKnotDomain(p=False)[1]

    @short(worldSpace='ws', plug='p')
    def getParamAtPoint(self, point,
            space='preTransform', worldSpace=False, plug=False):
        """
        Overloads :meth:`pymel.core.nodetypes.NurbsCurve.getParamAtPoint`.
        If a dynamic output is requested, it will be solved by closest point.

        :param point: the reference point
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :return: The parameter at, or closest to, the given point.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if worldSpace is not None:
            space = 'world' if worldSpace else 'preTransform'

        elif space is None:
            space = 'preTransform'

        if plug:
            if space in ['preTransform', 'object', 'world']:
                output = self.getGeoOutput(ws=space=='world')
                return output.paramAtPoint(point)

            else:
                raise NotImplementedError(
                    "Sampling space not supported for plug output: "+space
                )

        return r.nodetypes.NurbsCurve.getParamAtPoint(self, point, space=space)

    @short(tolerance='tol', worldSpace='ws', plug='p')
    def closestParam(self, point, space='preTransform',
            tolerance=0.001, worldSpace=False, plug=False):
        """
        Overloads :meth:`pymel.core.nodetypes.NurbsCurve.closestParam`.

        :alias: ``paramAtPoint``
        :param point: the reference point
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: if this is specified then it will
            override *space* to 'preTransform' if False and 'world' if
            True; defaults to None
        :param tolerance/tol: ignored for the dynamic implementation;
            passed along to
            :meth:`pymel.core.nodetypes.NurbsCurve.closestParam`; defaults to
            0.001
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The param closest to the given reference point.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if worldSpace is not None:
            space = 'world' if worldSpace else 'preTransform'

        elif space is None:
            space = 'preTransform'

        if plug:
            if space in ['preTransform', 'object', 'world']:
                output = self.getGeoOutput(ws=space=='world')
                return output.closestParam(point)

            else:
                raise NotImplementedError(
                    "Sampling space not supported for plug output: "+space
                )

        else:
            thisPoint = self.closestPoint(point, space=space)

            return r.nodetypes.NurbsCurve.getParamAtPoint(
                self, thisPoint, space=space
            )

    paramAtPoint = closestParam

    @short(plug='p')
    def paramAtFraction(self, fraction, plug=False):
        """
        :param fraction: the fraction at which to sample a parameter
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: A parameter at the given length fraction.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.localGeoOutput.paramAtFraction(fraction)

        length = self.length() * fraction
        return r.nodetypes.NurbsCurve.findParamFromLength(self, length)

    @short(plug='p', worldSpace='ws')
    def paramAtLength(self, length, plug=False, worldSpace=False):
        """
        :alias: ``findParamFromLength``
        :param length: the length at which to sample a parameter
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :param bool worldSpace/ws: indicate that *length* is a world-space
            length; defaults to False
        :return: A parameter at the given length.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).paramAtLength(length)

        fraction = length / self.length(ws=worldSpace)
        return self.paramAtFraction(fraction)

    findParamFromLength = paramAtLength

    @short(parametric='par', uniform='uni', plug='p')
    def distributeParams(self, numberOrValues,
                         parametric=False, uniform=False,
                         plug=False):
        """
        If *parametric* is True, the return will, in every case, be values,
        not plugs.

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
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: Parameters, distributed along this curve.
        :rtype: [float], [:class:`~paya.runtime.plugs.Math1D`]
        """
        if plug:
            return self.localGeoOutput.distributeParams(
                numberOrValues, par=parametric, uni=uniform
            )

        values = self._resolveNumberOrValues(numberOrValues,
                                             parametric=parametric,
                                             uniform=uniform)

        if parametric:
            return values

        return [self.paramAtFraction(value) for value in values]

    #------------------------------------------|    Get lengths

    @short(worldSpace='ws', plug='p')
    def lengthAtFraction(self, fraction, worldSpace=False, plug=False):
        """
        :param fraction: the fraction to inspect
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool worldSpace/ws: return a world-space length;
            defaults to False
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The curve length at the specified fraction.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.getGeoOutput(
                ws=worldSpace).lengthAtFraction(fraction)

        length = self.length(ws=worldSpace)
        return length * fraction

    @short(worldSpace='ws', plug='p')
    def lengthAtParam(self, param, worldSpace=False, plug=False):
        """
        :alias: ``lengthAtParam``
        :param param: the parameter to inspect
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool worldSpace/ws: return a world-space length; defaults to
            False
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The curve length at the specified parameter.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            output = self.getGeoOutput(ws=worldSpace)
            return output.lengthAtFraction(fraction)

        # The API answer will always be in local space
        partLength = r.nodetypes.NurbsCurve.findLengthFromParam(self, param)

        if worldSpace:
            # Convert by fraction
            localFullLength = self.length()
            fraction = partLength / localFullLength
            worldFullLength = self.length(ws=True)
            partLength = worldFullLength * fraction

        return partLength

    findLengthFromParam = lengthAtParam

    @short(worldSpace='ws', plug='p')
    def lengthAtPoint(self, point, worldSpace=False, plug=False):
        """
        This is a 'forgiving' implementation, and uses the closest point.

        :param point: the point to inspect
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool worldSpace/ws: indicate that *point* is in world space,
            and return a world-space length; defaults to False
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The curve length at the specified point.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).lengthAtPoint(point)

        param = self.paramAtPoint(point, ws=worldSpace)
        return self.lengthAtParam(param, ws=worldSpace)

    #------------------------------------------|    Get fractions

    def distributeFractions(self, number):
        """
        Convenience method. Equivalent to
        :meth:`floatRange(0, 1, number) <paya.lib.mathops.floatRange>`.

        :param int number: the number of fractions to generate
        :return: A uniform list of fractions.
        :rtype: [float]
        """
        return _mo.floatRange(0, 1, number)

    @short(worldSpace='ws', plug='p')
    def fractionAtPoint(self, point, worldSpace=False, plug=False):
        """
        This is a 'forgiving' implementation, and uses the closest point.

        :param point: the point at which to sample a fraction
        :type point: tuple, list, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool worldSpace/ws: indicate that *point* is in world space;
            defaults to False
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The length fraction at the specified point.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).fractionAtPoint(
                point
            )

        return self.lengthAtPoint(
            point, ws=worldSpace) / self.length(ws=worldSpace)

    @short(plug='p')
    def fractionAtParam(self, param, plug=False):
        """
        :param param: the parameter at which to sample a fraction
        :type param: float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The length fraction at the specified parameter.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        # world / local distinction doesn't matter for this

        if plug:
            return self.getGeoOutput().fractionAtParam(param)

        return self.lengthAtParam(param) / self.length()

    @short(worldSpace='ws', plug='p')
    def fractionAtLength(self, length, worldSpace=False, plug=False):
        """
        :param length: the length at which to sample a fraction
        :type length: float, str, :class:`~paya.runtime.plugs.Math1D`
        param bool worldSpace/ws: indicate that *length* is in world space;
            defaults to False
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The length fraction at the specified length.
        :rtype: float, :class:`~paya.runtime.plugs.Math1D`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).fractionAtLength(length)

        fullLength = self.length(ws=worldSpace)
        return length / fullLength

    #------------------------------------------|    Get normals

    @short(normalize='nr', worldSpace='ws', plug='p')
    def normal(self, param, space='preTransform',
               normalize=None, worldSpace=None, plug=False):
        """
        Overloads :meth:`pymel.core.nodetypes.NurbsCurve.normal`.

        .. note::

            Even though the Maya docs for the API method state that the vector
            is normalized, in practice this is only the case when *space* is
            'world'. For this reason, to defer to the API behaviour, the
            *normalize* argument here defaults to None. Pass a boolean to
            force a normalization state regardless of space.

        :param param: the parameter at which to sample the normal
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: if this is specified then it will
            override *space* to 'preTransform' if False and 'world' if
            True; defaults to None
        :param normalize/nr: whether to normalize the vector or not; see note;
            defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if worldSpace is not None:
            space = 'world' if worldSpace else 'preTransform'

        elif space is None:
            space = 'preTransform'

        if normalize is None:
            normalize = space == 'world'

        if plug:
            if space in ['preTransform', 'object', 'world']:
                return self.getGeoOutput(ws=space=='world').normal(
                    param, normalize=normalize
                )
            else:
                raise NotImplementedError(
                    "Sampling space not supported for plug output: "+space
                )

        if normalize and space == 'world' \
                or ((not normalize) and space != 'world'):
            return r.nodetypes.NurbsCurve.normal(self, param, space=space)

        info = self.getGeoOutput(ws=worldSpace).infoAtParam(param, re=False)
        normal = info.attr('normalizedNormal' \
                               if normalize else 'normal').get()
        r.delete(info)
        return normal

    @short(plug='p', worldSpace='ws', normalize='nr')
    def normalAtParam(self, param,
                      worldSpace=False, normalize=None, plug=False):
        """
        :param param: the parameter at which to sample the normal
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: overrides *space* to 'preTransform' if
            False and 'world' if True; defaults to False
        :param normalize/nr: set this to True to return a normalized vector,
            False to return a non-normalized vector or omit to use whichever
            if fastest; defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).normalAtParam(
                param, nr=normalize
            )

        return self.normal(param, ws=worldSpace, nr=normalize)

    @short(plug='p', worldSpace='ws', normalize='nr')
    def normalAtFraction(self, fraction,
                      worldSpace=False, normalize=None, plug=False):
        """
        :param fraction: the fraction at which to sample the normal
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: overrides *space* to 'preTransform' if
            False and 'world' if True; defaults to False
        :param normalize/nr: set this to True to return a normalized vector,
            False to return a non-normalized vector or omit to use whichever
            if fastest; defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).normalAtFraction(
                fraction, nr=normalize
            )

        param = self.paramAtFraction(fraction)
        return self.normalAtParam(param, nr=normalize, ws=worldSpace)

    @short(plug='p', worldSpace='ws', normalize='nr')
    def normalAtLength(self, length,
                      worldSpace=False, normalize=None, plug=False):
        """
        :param length: the length at which to sample the normal
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: overrides *space* to 'preTransform' if
            False and 'world' if True; defaults to False
        :param normalize/nr: set this to True to return a normalized vector,
            False to return a non-normalized vector or omit to use whichever
            if fastest; defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).normalAtLength(
                length, nr=normalize
            )

        param = self.paramAtLength(length, ws=worldSpace)
        return self.normalAtParam(param, nr=normalize, ws=worldSpace)

    @short(plug='p', worldSpace='ws', normalize='nr')
    def normalAtPoint(self, point,
                      worldSpace=False, normalize=None, plug=False):
        """
        :param point: the point at which to sample the normal
        :type point: tuple, list, str,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: overrides *space* to 'preTransform' if
            False and 'world' if True; defaults to False
        :param normalize/nr: set this to True to return a normalized vector,
            False to return a non-normalized vector or omit to use whichever
            if fastest; defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).normalAtPoint(
                length, nr=normalize
            )

        param = self.paramAtPoint(point, ws=worldSpace)
        return self.normalAtParam(param, nr=normalize, ws=worldSpace)

    #------------------------------------------|    Get tangents

    @short(normalize='nr', worldSpace='ws', plug='p')
    def tangent(self, param, space='preTransform',
               normalize=None, worldSpace=None, plug=False):
        """
        Overloads :meth:`pymel.core.nodetypes.NurbsCurve.tangent`.

        .. note::

            Even though the Maya docs for the API method state that the vector
            is normalized, in practice this is only the case when *space* is
            'world'. For this reason, to defer to the API behaviour, the
            *normalize* argument here defaults to None. Pass a boolean to
            force a normalization state regardless of space.

        :param param: the parameter at which to sample the tangent
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: if this is specified then it will
            override *space* to 'preTransform' if False and 'world' if
            True; defaults to None
        :param normalize/nr: whether to normalize the vector or not; see note;
            defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if worldSpace is not None:
            space = 'world' if worldSpace else 'preTransform'

        elif space is None:
            space = 'preTransform'

        if normalize is None:
            normalize = space == 'world'

        if plug:
            if space in ['preTransform', 'object', 'world']:
                return self.getGeoOutput(ws=space=='world').tangent(
                    param, normalize=normalize
                )
            else:
                raise NotImplementedError(
                    "Sampling space not supported for plug output: "+space
                )

        if normalize and space == 'world' \
                or ((not normalize) and space != 'world'):
            return r.nodetypes.NurbsCurve.tangent(self, param, space=space)

        tangent = self.getDerivativesAtParm(param, space=space)[1]

        if normalize:
            tangent = tangent.normal()

        return tangent

    @short(normalize='nr', plug='p', worldSpace='ws')
    def tangentAtParam(self, param,
                worldSpace=False, plug=False, normalize=None):
        """
        :param param: the parameter at which to sample the tangent
        :type param: float, :class:`~paya.runtime.plugs.Math1D`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: overrides *space* to 'preTransform' if
            False and 'world' if True; defaults to False
        :param normalize/nr: set this to True to return a normalized vector,
            False to return a non-normalized vector or omit to use whichever
            if fastest; defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).tangentAtParam(
                param, nr=normalize
            )

        return self.tangent(param, ws=worldSpace, nr=normalize)

    @short(plug='p', worldSpace='ws', normalize='nr')
    def tangentAtFraction(self, fraction,
                      worldSpace=False, normalize=None, plug=False):
        """
        :param fraction: the fraction at which to sample the tangent
        :type fraction: float, :class:`~paya.runtime.plugs.Math1D`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: overrides *space* to 'preTransform' if
            False and 'world' if True; defaults to False
        :param normalize/nr: set this to True to return a normalized vector,
            False to return a non-normalized vector or omit to use whichever
            if fastest; defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).tangentAtFraction(
                fraction, nr=normalize
            )

        param = self.paramAtFraction(fraction)
        return self.tangentAtParam(param, nr=normalize, ws=worldSpace)

    @short(plug='p', worldSpace='ws', normalize='nr')
    def tangentAtLength(self, length,
                      worldSpace=False, normalize=None, plug=False):
        """
        :param length: the length at which to sample the tangent
        :type length: float, :class:`~paya.runtime.plugs.Math1D`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: overrides *space* to 'preTransform' if
            False and 'world' if True; defaults to False
        :param normalize/nr: set this to True to return a normalized vector,
            False to return a non-normalized vector or omit to use whichever
            if fastest; defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).tangentAtLength(
                length, nr=normalize
            )

        param = self.paramAtLength(length, ws=worldSpace)
        return self.tangentAtParam(param, nr=normalize, ws=worldSpace)

    @short(plug='p', worldSpace='ws', normalize='nr')
    def tangentAtPoint(self, point,
                      worldSpace=False, normalize=None, plug=False):
        """
        :param point: the point at which to sample the tangent
        :type point: tuple, list, str,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param str space: the API enumerator option for the sampling space;
            one of:

            - 'transform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'preTransform' (the default)
            - 'postTransform' (not supported for *plug*; set to
                'object' or 'preTransform' instead)
            - 'world'
            - 'object' (same as 'preTransform')

        :param bool worldSpace/ws: overrides *space* to 'preTransform' if
            False and 'world' if True; defaults to False
        :param normalize/nr: set this to True to return a normalized vector,
            False to return a non-normalized vector or omit to use whichever
            if fastest; defaults to None
        :type normalize/nr: None, bool
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: The sampled vector.
        :rtype: :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        """
        if plug:
            return self.getGeoOutput(ws=worldSpace).tangentAtPoint(
                length, nr=normalize
            )

        param = self.paramAtPoint(point, ws=worldSpace)
        return self.tangentAtParam(param, nr=normalize, ws=worldSpace)

    #--------------------------------------------------|    Get up vectors

    @short(
        resolution='res',
        fromEnd='fe',
        plug='p',
        worldSpace='ws'
    )
    def getInterpKeysForParallelTransport(
            self,
            normal,
            resolution=9,
            fromEnd=False,
            worldSpace=False,
            plug=False
    ):
        if plug:
            output = self.getGeoOutput(ws=worldSpace)

            return output.getInterpKeysForParallelTransport(
                normal,
                res=resolution,
                fe=fromEnd
            )

        # Init some parameters, but uniformly
        fractions = _mo.floatRange(0,1, resolution)
        params = [self.paramAtFraction(f) for f in fractions]

        tangents = [self.tangentAtParam(
            param, ws=worldSpace) for param in params]

        if fromEnd:
            tangents = tangents[::-1]

        normals = _mo.parallelTransport(normal, tangents)

        if fromEnd:
            normals = normals[::-1]

        return list(zip(params, normals))

    @short(
        resolution='res',
        plug='p',
        worldSpace='ws',
        unwindSwitch='uws'
    )
    def getInterpKeysForAngleUpVectors(self,
                                       paramVectorKeys,
                                       resolution=9,
                                       plug=False,
                                       worldSpace=False,
                                       unwindSwitch=0):
        """
        :param paramVectorKeys: A list of lists, where each sublist comprises
            *parameter: known up vector*; this will define 'key points' around
            which to blend
        :type paramVectorKeys: [[:class:`float` |
            :class:`~paya.runtime.plugs.Math1D`,
            :class:`~paya.runtime.data.Vector` |
            :class:`~paya.runtime.plugs.Vector`]]
        :param int resolution/res: the number of solutions to generate across the
            curve; higher numbers improve accuracy but impact performance;
            defaults to 9
        :param unwindSwitch/uws: an integer value or plug to choose between three
            unwinding modes for the vector blending:

            -   0 (Shortest) (the default)
            -   1 (Positive)
            -   2 (Negative)

            This can also be a list of integers, in which case it should be of
            length paramVectorKeys-1 (i.e. same as the number of segments).
        :type unwindSwitch/uws: int, :class:`~paya.runtime.Math1D`,
            [int, :class:`~paya.runtime.Math1D`]
        :param bool worldSpace/ws: solve in world-space; defaults to False
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :return: A list of two-member lists, where each sublist comprises
            *parameter, up vector*.
        :rtype: [[:class:`float` | :class:`~paya.runtime.plugs.Math1D`,
            :class:`~paya.runtime.data.Vector` |
            :class:`~paya.runtime.plugs.Vector`]]
        """
        if plug:
            output = self.getGeoOutput(ws=worldSpace)

            return output.getInterpKeysForAngleUpVectors(
                paramVectorKeys,
                res=resolution,
                uws=unwindSwitch
            )

        #------------------------------------------------|    Prep

        paramVectorKeys = list(paramVectorKeys)
        numKeys = len(paramVectorKeys)

        if numKeys < 2:
            raise ValueError("Need at least two vector keys.")

        numSegments = numKeys-1

        if unwindSwitch is None:
            unwindSwitch = 0

        if isinstance(unwindSwitch, (tuple, list)):
            if len(unwindSwitch) is not numSegments:
                raise ValueError(
                    "If 'unwindSwitch' is a list, it "+
                    "should be of length "+
                    "paramUpVectorKeys-1.")

            unwindSwitches = [_mo.info(x)[0] for x in unwindSwitch]

        else:
            unwindSwitches = [unwindSwitch] * numSegments

        segmentResolutions = _nu._resolvePerSegResForBlendedParallelTransport(
            numSegments, resolution
        )

        #--------------------------------------------|    Solve

        params, normals = zip(*paramVectorKeys)

        # Init per-segment info bundles
        infoPacks = []

        for i, param, normal, segmentResolution in zip(
            range(numSegments),
            params[:-1],
            normals[:-1],
            segmentResolutions
        ):
            startParam = param
            endParam = params[i+1]

            infoPack = {
                'startParam': startParam,
                'nextParam': endParam,
                'startNormal': normals[i],
                'endNormal': normals[i+1],
                'unwindSwitch': unwindSwitches[i]
            }

            infoPack['tangentSampleParams'] = \
                _mo.floatRange(startParam, endParam, segmentResolution)

            infoPacks.append(infoPack)

        # Add tangent samples to each bundle, taking care not to
        # replicate overlapping samples
        for i, infoPack in enumerate(infoPacks):
            inner = i > 0
            tangentSampleParams = infoPack['tangentSampleParams'][:]

            if inner:
                del(tangentSampleParams[i])

            infoPack['tangents'] = tangents = []

            for x, tangentSampleParam in enumerate(
                    tangentSampleParams):
                tangents.append(
                    self.tangentAtParam(tangentSampleParam, ws=worldSpace)
                )

            if inner:
                tangents.insert(0, infoPacks[i-1]['tangents'][-1])

        # Run the parallel transport per-segment
        for i, infoPack in enumerate(infoPacks):
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

        return list(zip(outParams, outNormals))

    #--------------------------------------------------|    Sample matrices

    @short(upVector='upv',
           upObject='uo',
           aimCurve='aic',
           closestPoint='cp',
           globalScale='gs',
           squashStretch='ss',
           plug='p'
           )
    def matrixAtParam(self,
                      param,
                      primaryAxis,
                      secondaryAxis,

                      upVector=None,
                      upObject=None,
                      aimCurve=None,
                      closestPoint=True,

                      globalScale=None,
                      squashStretch=False,

                      plug=False
                      ):
        """
        Returns a world-space matrix at the specified parameter.s If no up
        vector information is provided, the curve normal will be used (not
        usually advisable).

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
        :param bool plug/p: set this to True to indicate that one or
            more arguments are plugs, and that therefore a dynamic result
            is required, or to force a dynamic result even if no arguments
            are plugs; defaults to False
        :param bool worldSpace/ws: construct matrices, and sample information,
            in world-space; defaults to False
        :raises ValueError: misconfigured argument(s)
        :return: A matrix at the specified parameter.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        if plug:
            return self.getGeoOutput(
                ws=True).matrixAtParam(param, primaryAxis,
                                       secondaryAxis, upv=upVector,
                                       uo=upObject, aic=aimCurve,
                                       cp=closestPoint, gs=globalScale,
                                       ss=squashStretch)

        #---------------------------------------|    Wrangle args

        if upVector and aimCurve:
            raise ValueError("Unsupported combo: up vector and aim curve")

        if upObject and aimCurve:
            raise ValueError("Unsupported combo: up object and aim curve")

        if upVector:
            upVector = _mo.conformVectorArg(upVector)

        if upObject:
            upObject = r.PyNode(upObject)

        if aimCurve:
            aimCurve = r.PyNode(aimCurve)

        #---------------------------------------|    Prep

        position = self.pointAtParam(param, ws=True)
        tangent = self.tangentAtParam(param, ws=True)

        if upVector:
            if upObject:
                upVector *= upObject.getMatrix(worldSpace=True)

        elif aimCurve:
            if closestPoint:
                interest = aimCurve.closestPoint(
                    position, ws=worldSpace)

            else:
                interest = aimCurve.pointAtParam(param, ws=True)

            upVector = interest-position

        elif upObject:
            upVector = upObject.getWorldPosition() - position

        else:
            upVector = self.normalAtParam(param)

        #---------------------------------------|    Build matrix

        return r.createMatrix(primaryAxis,
                              tangent,
                              secondaryAxis,
                              upVector,
                              t=position).pk(t=True, r=True)

    @short(plug='p')
    def matrixAtFraction(self, fraction, *args, plug=False, **kwargs):
        """
        If *plug* is ``True``, defers to
        :class:`~paya.runtime.plugs.NurbsCurve.matrixAtFraction` on the world
        geometry output; otherwise, converts *fraction* to a parameter and
        defers to :meth:`matrixAtParam`. See those methods for full
        documentation.

        :param fraction: the fraction at which to sample a matrix
        :type fraction: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param \*args: forwarded
        :param bool plug/p: return matrix plugs rather than values; defaults
            to Falses
        :return: The generated matrices.
        """
        if plug:
            return self.getGeoOutput(ws=True
                ).matrixAtFraction(fraction, *args, **kwargs)

        param = self.paramAtFraction(fraction)
        return self.matrixAtParam(param, *args, **kwargs)

    def matrixAtLength(self, length, *args, plug=False, **kwargs):
        """
        If *plug* is ``True``, defers to
        :class:`~paya.runtime.plugs.NurbsCurve.matrixAtLength` on the world
        geometry output; otherwise, converts *length* to a parameter and
        defers to :meth:`matrixAtParam`. See those methods for full
        documentation.

        :param length: the length at which to sample a matrix
        :type length: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param \*args: forwarded
        :param bool plug/p: return matrix plugs rather than values; defaults
            to Falses
        :return: The generated matrices.
        """
        if plug:
            return self.getGeoOutput(ws=True
                ).matrixAtLength(length, *args, **kwargs)

        param = self.paramAtLength(length, ws=True)
        return self.matrixAtParam(param, *args, **kwargs)

    def matrixAtPoint(self, point, *args, plug=False, **kwargs):
        """
        If *plug* is ``True``, defers to
        :class:`~paya.runtime.plugs.NurbsCurve.matrixAtPoint` on the world
        geometry output; otherwise, finds the parameter at *point* and
        defers to :meth:`matrixAtParam`. See those methods for full
        documentation.

        :param point: the point at which to sample a matrix
        :type point: list, tuple, str, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param \*args: forwarded
        :param bool plug/p: return matrix plugs rather than values; defaults
            to Falses
        :return: The generated matrices.
        """
        if plug:
            return self.getGeoOutput(ws=True
                ).matrixAtLength(length, *args, **kwargs)

        param = self.paramAtPoint(point, ws=True)
        return self.matrixAtParam(param, *args, **kwargs)

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
        resolution='res',

        plug='p'
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
                           resolution=9,

                           plug=False
                           ):

        if plug:
            output = self.getGeoOutput(worldSpace=True)

            return output.distributeMatrices(
                numberOrValues, primaryAxis, secondaryAxis,
                par=parametric, uni=uniform, upv=upVector,
                upo=upObject, aic=aimCurve, cp=closestPoint,
                gs=globalScale, ss=squashStretch,
                i=interpolation, pt=parallelTransport,
                uws=unwindSwitch, res=resolution)

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

        #-------------------------------------|    Build matrices

        if parametric:
            params = vals

        else:
            params = [self.paramAtFraction(f) for f in fractions]

        # Basics
        points = [self.pointAtParam(param, ws=True) for param in params]
        tangents = [self.tangentAtParam(param, ws=True) for param in params]

        # Resolve up vectors

        # if upVector:
        #     if aimCurve:
        #         raise ValueError("Unsupported combo: up vector and aim curve")
        #
        #     if singleUpVector:
        #         if upObject:
        #             if singleUpObject:
        #                 upVector *= upObject.getMatrix(worldSpace=True)
        #                 upVectors = [upVector] * number
        #
        #             else:
        #                 upObjects = upObject
        #                 if len(upObjects) != number:
        #                     raise ValueError(
        #                         "Mismatched number of up vectors "+
        #                         "and up objects."
        #                     )
        #
        #                 upVectors = [upVector * \
        #                              upObject.getMatrix(worldSpace=True
        #                                     ) for upObject in upObjects]
        #
        #         else:
        #             if parallelTransport:
        #
        #
        #
        #     if multiUpVectors:
        #         upVectors = upVector
        #
        #         if upObject:
        #             if multiUpObjects:
        #                 upObjects = upObject
        #                 upVectors = [upVector * upObject.getMatrix(
        #                     worldSpace=True) for upObject in upObjects]
        #
        #             else:
        #                 upObjectMtx = upObject.getMatrix(worldSpace=True)
        #                 upVectors = [upVector * upObjectMtx]




            

    #----------------------------------------------------------------|
    #----------------------------------------------------------------|    Loopbacks
    #----------------------------------------------------------------|

    toBezier = Loopback()
    toNurbs = Loopback()
    bSpline = Loopback()
    rebuild = Loopback()
    cvRebuild = Loopback()
    cageRebuild = Loopback()
    reverse = Loopback()
    subCurve = Loopback()
    detach = Loopback()
    retract = Loopback()
    attach = Loopback()
    extendByVector = Loopback()
    extendToPoint = Loopback()
    extendByLength = Loopback()
    extend = Loopback()
    blend = Loopback()
    setLength = Loopback()
