import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r
import paya.lib.nurbsutil as _nu


class BezierCurve:

    #----------------------------------------------------|    Inspections

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

    #----------------------------------------------------|    Sampling

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