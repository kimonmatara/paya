from paya.shapext import ShapeExtensionMeta
import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r
import paya.lib.nurbsutil as _nu


class BezierCurve(metaclass=ShapeExtensionMeta):

    #-----------------------------------------------------------------|
    #-----------------------------------------------------------------|    Constructor
    #-----------------------------------------------------------------|

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

    #-----------------------------------------------------------------|
    #-----------------------------------------------------------------|    Deformers
    #-----------------------------------------------------------------|


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

            anchors = [anchor for anchor \
                       in anchors if anchor not in omitItems]

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