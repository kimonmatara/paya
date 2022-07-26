import maya.OpenMaya as om

from paya.util import short
import paya.lib.mathops as _mo
import paya.runtime as r
import paya.lib.nurbsutil as _nu


class BezierCurve:

    #----------------------------------------------------|    Analysis

    def getShapeMFn(self):
        """
        Returns an API function set for the shape type associated with this
        plug, initialised around the MObject of the data block. Useful for
        performing spot inspections (like ``numCVs()`` on a curve output)
        without creating a shape.

        :return: The function set.
        :rtype: :class:`~maya.OpenMaya.MFnDagNode`
        """
        # This will crash if called on a root array mplug, so force an index

        if self.isArray():
            plug = self[0]

        else:
            plug = self

        plug.evaluate()
        mplug = plug.__apimplug__()
        handle = mplug.asMDataHandle()
        mobj = handle.data()

        return om.MFnNurbsCurve(mobj)

    def numAnchors(self):
        """
        :return: The number of anchors on this bezier curve.
        :rtype: int
        """
        mfn = self.getShapeMFn()
        numCVs = mfn.numCVs()
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

    @short(anchors='a')
    def getControlPoints(self, anchors=False):
        """
        Overloads :meth:`paya.runtime.plugs.NurbsCurve.getControlPoints` to
        add the *anchors* / *a* option.

        :param bool anchors/a: organise the return into bezier anchor groups;
            see :func:`paya.lib.nurbsutil.itemsAsBezierAnchors`; defaults to
            False
        :return: The control points.
        :rtype: [:class:`~paya.runtime.plugs.Vector`], [dict]
        """
        result = r.plugs.NurbsCurve.getControlPoints(self)

        if anchors:
            result = _nu.itemsAsBezierAnchors(result)

        return result

    @short(
        upVector='upv',
        aimCurve='aic',
        closestPoint='cp',
        globalScale='gs',
        squashStretch='ss'
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
            squashStretch=False
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
        :return: A matrix at the specified anchor.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        anchor = self.getControlPoints(anchors=True)[anchorIndex]
        points = list(anchor.values())
        tangent = points[-1]-points[0]
        point = anchor['root']

        if globalScale is None:
            globalScale = 1.0
            gsIsPlug = False

        else:
            globalScale, gsDim, gsIsPlug = _mo.info(globalScale)

            if gsIsPlug:
                _globalScale = globalScale.get()

                if _globalScale != 1.0:
                    globalScale /= _globalScale

            else: # discard
                globalScale = 1.0

        if upVector:
            upVector = _mo.info(upVector)[0]

        else:
            if aimCurve:
                aimCurve = _mo.asGeoPlug(aimCurve, worldSpace=True)

                if closestPoint:
                    interest = aimCurve.closestPoint(anchor['root'])

                else:
                    param = self.paramAtAnchor(anchorIndex)
                    interest = aimCurve.pointAtParam(param)

                upVector = interest-anchor['root']

            else:
                param = self.paramAtAnchor(anchorIndex)
                upVector = self.infoAtParam(param).attr('normal')

        matrix = r.createMatrix(
            tangentAxis, tangent,
            upAxis, upVector,
            t=anchor['root']
        ).pick(translate=True, rotate=True)

        if gsIsPlug or squashStretch:
            factors = [globalScale] * 3

            if squashStretch:
                tangentLength = tangent.length()
                _tangentLength = tangentLength.get()

                if _tangentLength != 1.0:
                    tangentLength /= _tangentLength

                tangentIndex = 'xyz'.index(tangentAxis.strip('-'))
                factors[tangentIndex] = tangentLength

                smtx = r.createScaleMatrix(*factors)
                matrix = smtx * matrix

        return matrix