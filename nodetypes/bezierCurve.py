import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r
import paya.lib.nurbsutil as _nu


class BezierCurve:

    #-----------------------------------------------------------------|    Constructor

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
            name=None,
            under=None,
            displayType=None,
            conformShapeName=True,
            intermediate=False,
            lineWidth=None
    ):
        """
        Bezier curve constructor. Points can be static or dynamic.

        :param \*points: if provided, the number of CV points must be 'legal'
            for a Bezier curve; namely, outer anchors must receive two CVs
            each, and inner anchors must each receive three CVs; if omitted,
            an empty Bezier curve shape node will be createds
        :param \*points: None, str, tuple, list,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param name/n: one or more name elements; defaults to None
        :type name/n: str, int, None, tuple, list
        :param under/u: an optional destination parent; no space conversion
            will take place; if the parent has transforms, the curve shape
            will be transformed as well; defaults to None
        :type under/u: None, str, :class:`~paya.runtime.nodes.Transform`
        :param displayType/dt: if provided, an index or enum label:

            - 0: 'Normal'
            - 1: 'Template'
            - 2: 'Reference'

            If omitted, display overrides won't be activated at all.
        :type displayType/dt: None, int, str
        :param bool conformShapeName/csn: if reparenting, rename the shape to
            match the destination parent; defaults to True
        :param bool intermediate: set the shape to intermediate; defaults to
            False
        :param lineWidth/lw: an override for the line width; defaults to None
        :type lineWidth/lw: None, float
        :return: The curve shape.
        :rtype: :class:`BezierCurve`
        """
        points = _mo.expandVectorArgs(points)

        if points:
            num = len(points)

            if _nu.legalNumCVsForBezier(num):
                infos = [_mo.info(point) for point in points]
                points = [info[0] for info in infos]
                hasPlugs = any((info[2] for info in infos))

                if hasPlugs:
                    _points = [_mo.asValue(point) for point in points]

                else:
                    _points = points

                knots = _nu.getKnotList(num, 3)

                name = cls.makeName(name)
                curveXf = r.curve(p=_points, k=knots, d=3, bezier=True, n=name)
                shape = curveXf.getShape()

                if under:
                    r.parent(shape, under, r=True, shape=True)
                    r.delete(curveXf)

                    if conformShapeName:
                        shape.conformName()

                if hasPlugs:
                    historyShape = shape.getHistoryPlug(create=True).node()

                    for i, point in enumerate(points):
                        point >> historyShape.attr('controlPoints')[i]

            else:
                raise RuntimeError(
                    "Invalid number of bezier CVs: {}".format(num)
                )

        else:
            shape = cls.createShape(n=name, u=under, csn=conformShapeName)

        # Post-config
        if displayType is not None:
            shape.attr('overrideEnabled').set(True)
            shape.attr('overrideDisplayType').set(displayType)

        if intermediate:
            shape.attr('intermediateObject').set(intermediate)

        return shape

    #-----------------------------------------------------------------|    Inspections

    def numAnchors(self):
        """
        :return: The number of anchors on this bezier curve.
        :rtype: int
        """
        numCVs = self.numCVs()
        out = (numCVs+2) / 3

        if not out.is_integer():
            raise RuntimeError("Invalid number of CVs for a bezier curve.")

        return int(out)

    def paramAtAnchor(self, anchorIndex):
        """
        This is a fixed calculation, since anchors always 'touch' the curve at
        same parameter.

        :param int anchorIndex: the anchor index
        :return: The U parameter.
        """
        umin, umax = self.getKnotDomain()
        numAnchors = self.numAnchors()
        grain = (umax-umin) / (numAnchors-1)
        return grain * anchorIndex

    #-----------------------------------------------------------------|    Sampling

    @short(
        asComponents='ac',
        asPoints='ap',
        asIndices='ai',
        plug='p'
    )
    def getCVsAtAnchor(
            self,
            anchorIndex,
            asComponents=False,
            asPoints=False,
            asIndices=False,
            plug=False
    ):
        """
        Note that, unlike Maya's standard
        :meth:`~pymel.core.nodetypes.NurbsCurve.getCVs`, this returns
        components, not points.

        :param int anchorIndex: the index of the anchor to inspect
        :param bool asComponents/ac: return instances of
            :class:`~paya.runtime.comps.NurbsCurveCV`; defaults to False
        :param bool asIndices/ai: return CV indices; defaults to False
        :param bool asPoints/ap: return world positions; defaults to True
        :param bool plug/p: if *asPoints* is requested, return attributes,
            not values; defaults to False
        :return: The control vertices at the given anchor.
        :rtype: [:class:`~paya.runtime.components.NurbsCurveCV`]
        """
        allIndices = range(self.numCVs())
        anchor = _nu.itemsAsBezierAnchors(allIndices)[anchorIndex]

        if asPoints or asComponents:
            for key, index in anchor.items():
                if asComponents:
                    value = self.comp('cv')[index]

                elif asPoints:
                    value = self.pointAtCV(index, p=plug)

                anchor[key] = value

        return list(anchor.values())

    @short(anchors='a', plug='p', worldSpace='ws')
    def getControlPoints(self, anchors=False, plug=False, worldSpace=False):
        """
        Overloads :meth:`paya.runtime.nodes.NurbsCurve.getControlPoints` to
        add the *anchors* / *a* option.

        :param bool anchors/a: organise the return into bezier anchor groups;
            see :func:`paya.lib.nurbsutil.itemsAsBezierAnchors`; defaults to
            False
        :param bool plug/p: force a dynamic output; defaults to False
        :param bool worldSpace/ws: return world-space points; defaults to
            False
        :return: The control points.
        :rtype: [:class:`~paya.runtime.plugs.Vector`],
            [:class:`~paya.runtime.data.Point`]
            [dict]
        """
        if plug:
            return self.attr('worldSpace' if \
                worldSpace else 'local').getControlPoints(a=anchors)

        controlPoints = r.nodes.NurbsCurve.getControlPoints(
            self, p=plug, ws=worldSpace
        )

        if anchors:
            controlPoints = _nu.itemsAsBezierAnchors(controlPoints)

        return controlPoints

    @short(
        upVector='upv',
        aimCurve='aic',
        closestPoint='cp',
        globalScale='gs',
        squashStretch='ss',
        plug='p'
    )
    def matrixAtAnchor(
            self,
            anchorIndex,
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
        :param int anchorIndex: the anchor index
        :param str tangentAxis: the axis to map to the anchor tangent,
            for example '-y'
        :param str upAxis: the axis to map to the resolve up vector,
            for example 'x'
        :param upVector/upv: an explicit up vector; defaults to None
        :type upVector/upv: None, tuple, list, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param aimCurve/aic: an aim curve to derive up vectors from;
            defaults to None
        :type aimCurve/aic: None, str, :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param bool closestPoint/cp: pull points from the aim curve based on
            proximity, not matched parameter; defaults to True
        :param globalScale/gs: ignored if not a plug; a baseline scalar;
            defaults to None
        :type globalScale/gs: None, str, float,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow squash-and-stretch on the tangent
            vector; defaults to False
        :param bool plug/p: force a dynamic output; defaults to False
        :return: A matrix at the specified anchor.
        :rtype: :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.data.Matrix`
        """
        if plug \
                or upVector and _mo.isPlug(upVector) \
                or aimCurve and _mo.isPlug(aimCurve) \
                or globalScale and _mo.isPlug(globalScale):
            return self.attr('worldSpace').matrixAtAnchor(
                anchorIndex, tangentAxis, upAxis,
                upv=upVector, aic=aimCurve, cp=closestPoint,
                gs=globalScale, ss=squashStretch
            )

        anchor = self.getControlPoints(
            worldSpace=True, anchors=True)[anchorIndex]

        points = list(anchor.values())
        tangent = points[-1]-points[0]
        point = anchor['root']

        if upVector:
            upVector = r.data.Vector(upVector)

        else:
            if aimCurve:
                aimCurve = r.PyNode(aimCurve)

                if closestPoint:
                    interest = aimCurve.closestPoint_(point)

                else:
                    param = self.paramAtAnchor(anchorIndex)
                    interest = aimCurve.pointAtParam(param)

                upVector = interest-point

            else:
                param = self.paramAtAnchor(anchorIndex)
                upVector = self.normal(param, space='world')

        return r.createMatrix(
            tangentAxis, tangent,
            upAxis, upVector,
            t=point
        ).pick(translate=True, rotate=True)

    #-----------------------------------------------------------------|    Clusters

    @short(tolerance='tol', merge='mer', anchors='a')
    def clusterAll(self, merge=False, tolerance=1e-6, anchors=False):
        """
        Overloads :meth:`~paya.runtime.nodes.NurbsCurve.clusterAll` to add the
        *anchors* / *a* option.

        :param bool anchors/a: group clusters by bezier anchor; defaults to
            False
        :param bool merge/mer: merge CVs if they overlap within the specified
            *tolerance*; defaults to False
        :param float tolerance/tol: the merging tolerance; defaults to 1e-6
        :return: The clusters.
        :rtype: [:class:`~paya.runtime.nodes.Cluster`]
        """
        if anchors:
            cvs = list(self.comp('cv'))
            anchors = _nu.itemsAsBezierAnchors(cvs)

            omitItems = []

            if merge:
                for i, refAnchor in enumerate(anchors):
                    if refAnchor in omitItems:
                        continue

                    refRootCV = refAnchor['root']
                    refRootPt = refRootCV.getWorldPosition()

                    for x, otherAnchor in enumerate(anchors):
                        if x is i or otherAnchor in omitItems:
                            continue

                        otherRootCV = otherAnchor['root']
                        otherRootPt = otherRootCV.getWorldPosition()

                        if refRootPt.isEquivalent(otherRootPt, tol=tolerance):
                            omitItems.append(otherAnchor)
                            pool = refAnchor.setdefault('additions', [])
                            pool += list(otherAnchor.values())

            anchors = [anchor for anchor in anchors if anchor not in omitItems]

            clusters = []

            for i, anchor in enumerate(anchors):
                allCVs = anchor.values()
                rootPt = anchor['root'].getWorldPosition()

                mtx = rootPt.asTranslateMatrix()

                with r.Name(i+1):
                    cluster = r.nodes.Cluster.create(allCVs, wm=mtx)
                    clusters.append(cluster)

        else:
            return r.nodes.NurbsCurve.clusterAll(
                self, merge=merge, tol=tolerance)