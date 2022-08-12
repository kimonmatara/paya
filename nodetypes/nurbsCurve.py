import maya.OpenMaya as om
import pymel.util as _pu
import pymel.core.nodetypes as _nt

from paya.shapext import ShapeExtensionMeta
import paya.lib.nurbsutil as _nu
from paya.lib.loopback import Loopback
import paya.lib.nurbsutil as _nu
import paya.lib.mathops as _mo
import paya.lib.plugops as _po
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
        under='u',
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
                         under=None,
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
        :param under/u: an optional destination parent for the joints
        :type under/u: None, str, :class:`~paya.runtime.nodes.Transform`
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

        joints = [r.nodes.Joint.create(wm=matrix, n=i+1,
                                       u=under, ro=rotateOrder,
                                       dla=displayLocalAxis,
                                       fr=freeze, dec=decompose)\
                  for i, matrix in enumerate(matrices)]

        if chain:
            for thisJoint, nextJoint in zip(joints, joints[1:]):
                nextJoint.setParent(thisJoint)

            return r.Chain(joints)

        return joints

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

