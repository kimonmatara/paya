import re
from paya.geoshapext import ShapeExtensionMeta
import paya.lib.typeman as _tm
import paya.lib.mathops as _mo
from paya.util import short
import paya.lib.nurbsutil as _nu
import paya.runtime as r



class BezierCurve(metaclass=ShapeExtensionMeta):

    #-----------------------------------------------------------------|
    #-----------------------------------------------------------------|    Constructor
    #-----------------------------------------------------------------|

    @classmethod
    @short(name='n',
           parent='p',
           displayType='dt',
           conformShapeName='csn',
           intermediate='i',
           lineWidth='lw',
           dispCV='dcv')
    def create(cls,
               *points,
               name=None, # shape name
               parent=None,
               displayType=None,
               conformShapeName=None,
               intermediate=False,
               lineWidth=None,
               dispCV=True):
        """
        Bezier curve constructor. Points can be static or dynamic.

        :param \*points: if provided, the number of CV points must be 'legal'
            for a Bezier curve; namely, outer anchors must receive two CVs
            each, and inner anchors must each receive three CVs; if omitted,
            an empty Bezier curve shape node will be createds
        :param \*points: None, str, tuple, list,
            :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param str name/n: a name for the curve *shape* node; defaults to a
            contextual name
        :param parent/p: an optional destination parent; no space conversion
            will take place; if the parent has transforms, the curve shape
            will be transformed as well; defaults to None
        :typeparent/p: None, str, :class:`~paya.runtime.nodes.Transform`
        :param displayType/dt: if provided, an index or enum label:

            - 0: 'Normal'
            - 1: 'Template'
            - 2: 'Reference'

            If omitted, display overrides won't be activated at all.
        :type displayType/dt: None, int, str
        :param bool conformShapeName/csn: if reparenting, rename the shape to
            match the destination parent; defaults to ``True`` if *parent* has
            been specified, otherwise ``False``
        :param bool intermediate/i: set the shape to intermediate; defaults to
            ``False``
        :param lineWidth/lw: an override for the line width; defaults to
            ``None``
        :type lineWidth/lw: ``None``, :class:`float`
        :param bool dispCV/dcv: display CVs on the curve; defaults to ``True``
        :return: The curve shape.
        :rtype: :class:`BezierCurve`
        """

        if conformShapeName is None:
            conformShapeName = True if parent else False

        if name is None:
            name = cls.makeName()

        points = _tm.expandVectorArgs(points)

        if points:
            num = len(points)

            if _nu.legalNumCVsForBezier(num):
                infos = [_mo.info(point) for point in points]
                points = [info['item'] for info in infos]
                hasPlugs = any((info['isPlug'] for info in infos))

                if hasPlugs:
                    _points = [_tm.asValue(point) for point in points]

                else:
                    _points = points

                knots = _nu.getKnotList(num, 3, bezier=True)

                kwargs = {}

                if not (parent and conformShapeName):
                    mt = re.match(r"^(.*?)Shape$", name)

                    if mt:
                        kwargs['name'] = mt.groups()[0]

                curveXf = r.curve(p=_points, k=knots, d=3, bezier=True, **kwargs)
                shape = curveXf.getShape()

                if parent:
                    r.parent(shape, parent, r=True, shape=True)
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
            shape = cls.createShape(n=name, p=parent, csn=conformShapeName)

        # Post-config
        if displayType is not None:
            shape.attr('overrideEnabled').set(True)
            shape.attr('overrideDisplayType').set(displayType)

        if intermediate:
            shape.attr('intermediateObject').set(intermediate)

        shape.attr('dispCV').set(dispCV)

        return shape

    @classmethod
    @short(numAnchors='na')
    def createLine(cls, startPt, endPt, numAnchors=2, **kwargs):
        """
        Convenience wrapper for :meth:`create` to quickly draw a straight
        bezier line.

        :param startPt: the start point
        :type startPt: :class:`tuple`, :class:`list`,
            :class:`str`, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param endPt: the end point
        :type endPt: :class:`tuple`, :class:`list`,
            :class:`str`, :class:`~paya.runtime.data.Point`,
            :class:`~paya.runtime.plugs.Vector`
        :param int numAnchors/na: the number of anchors; defaults to 2
        :param \*\*kwargs: forwarded to :meth:`create`
        :return: The bezier curve shape.
        :rtype: :class:`BezierCurve`
        """
        if numAnchors < 2:
            raise ValueError("Need at least two anchors.")

        startPt = _tm.conformVectorArg(startPt)
        endPt = _tm.conformVectorArg(endPt)
        numPoints = 4 + ((numAnchors-2) * 3)

        internalWeights = _mo.floatRange(0, 1, numPoints)[1:-1]
        allPoints = [startPt] + [startPt.blend(endPt,
                w=weight) for weight in internalWeights] + [endPt]

        return cls.create(allPoints, **kwargs)

    #-----------------------------------------------------------------|
    #-----------------------------------------------------------------|    Deformers
    #-----------------------------------------------------------------|

    def clusterAnchor(self, anchorIndex, **kwargs):
        """
        :param int anchorIndex: the index of the anchor to cluster
        :param \*\*kwargs:
            forwarded to :meth:`paya.runtimes.nodes.Cluster.create`
        :return: A cluster for the specified anchor.
        :rtype: :class:`~paya.runtime.nodes.Cluster`
        """
        indices = self.getCVsAtAnchor(
            anchorIndex, asDict=True, asIndex=True)
        cvs = [self.comp('cv')[i] for i in indices]

        return r.nodes.Cluster.create(cvs, **kwargs)

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