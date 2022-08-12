from paya.shapext import copyToShapeAsEditor, copyToShapeAsSampler, copyToShape
from paya.util import short
import paya.lib.nurbsutil as _nu
import maya.OpenMaya as om
import paya.runtime as r


class BezierCurve:

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    MFn
    #---------------------------------------------------------------|

    # Necessary otherwise will look up MFnBezierCurve, which doesn't exist

    def getShapeMFn(self):
        """
        Returns an API function set for the shape type associated with this
        plug, initialised around the MObject of the data block. Useful for
        performing spot inspections (like ``numCVs()`` on a curve output)
        without creating a shape.

        :return: The function set.
        :rtype: :class:`~maya.OpenMaya.MFnNurbsCurve`
        """
        try:
            return getattr(self, '_shapeMFn')

        except AttributeError:
            # This will crash if called on a root array mplug, so force an
            # index

            if self.isArray():
                plug = self[0]

            else:
                plug = self

            plug.evaluate()
            mplug = plug.__apimplug__()
            handle = mplug.asMDataHandle()
            mobj = handle.data()

            self._shapeMFn = out = om.MFnNurbsCurve(mobj)

            return out

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    SPOT INSPECTIONS
    #---------------------------------------------------------------|

    @copyToShape()
    def numAnchors(self):
        """
        :return: The number of anchors on this Bezier curve.
        :rtype: :class:`int`
        """
        numCVs = self.numCVs()
        out = (numCVs+2) / 3

        if not out.is_integer():
            raise RuntimeError("Invalid number of CVs for a bezier curve.")

        return int(out)

    @copyToShape()
    def paramAtAnchor(self, anchorIndex):
        """
        This is a fixed / static-only calculation, since anchors always
        'touch' the curve at the same parameter.

        :param int anchorIndex: the anchor index
        :return: The U parameter.
        """
        umin, umax = self.getKnotDomain(plug=False)
        numAnchors = self.numAnchors()
        grain = (umax-umin) / (numAnchors-1)
        return grain * anchorIndex

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    SAMPLING
    #---------------------------------------------------------------|

    #---------------------------------------------------|    Points

    @copyToShapeAsSampler()
    @short(asPoints='ap',
           asIndices='ai',
           plug='p')
    def getCVsAtAnchor(self,
                       anchorIndex,
                       asPoints=None,
                       asIndices=None,
                       plug=True):
        """
        :param int anchorIndex: the index of the anchor to inspect
        :param bool asPoints/ap: return CV point positions (the default)
        :param bool asIndices/ai: return CV indices; indices are always
            returned as values, not scalar outputs, even if *plug* is
            ``True``
        :param plug/p: if *asPoints* is requested, return point outputs, not
            just values; defaults to ``True``
        :return: The CV indices or positions.
        :rtype: [:class:`int`] | [:class:`paya.runtime.plugs.Vector`] |
            [:class:`paya.runtime.data.Point`]
        """
        if (asPoints is None) and (asIndices is None):
            asPoints, asIndices = True, False

        elif (asPoints is None) and (asIndices is not None):
            asPoints = not asIndices

        elif (asPoints is not None) and (asIndices is None):
            asIndices = not asPoints

        allIndices = range(self.numCVs())
        anchor = _nu.itemsAsBezierAnchors(allIndices)[anchorIndex]

        if asPoints:
            for key, index in anchor.items():
                value = self.pointAtCV(index, p=plug)
                anchor[key] = value

        return list(anchor.values())

    @copyToShapeAsSampler()
    @short(plug='p', anchors='a')
    def getCVs(self, plug=True, anchors=False):
        """
        :param bool plug/p: return plugs rather than values;
            defaults to ``True``
        :param bool anchors/a: organise the return into bezier anchor groups;
            see :func:`paya.lib.nurbsutil.itemsAsBezierAnchors`; defaults to
            ``False``
        :return: The members of the ``controlPoints`` info array for this
            curve.
        :rtype: [:class:`~paya.runtime.plugs.Vector`],
            [:class:`~paya.runtime.data.Point`]
        """
        out = super(r.plugs.BezierCurve, self).getCVs(p=plug)

        if anchors:
            out = _nu.itemsAsBezierAnchors(out)

        return out

    #---------------------------------------------------|    Matrices

    @copyToShapeAsSampler(worldSpaceOnly=True)
    @short(upVector='uvp',
           upObject='uo',
           aimCurve='aic',
           closestPoint='cp',
           upVectorSampler='ups',
           defaultToNormal='dtn',
           globalScale='gs',
           squashStretch='ss',
           plug='p')
    def matrixAtAnchor(self,
                      anchorIndex,

                      primaryAxis,
                      secondaryAxis,

                      upVector=None,
                      upObject=None,

                      aimCurve=None,
                      closestPoint=True,

                      upVectorSampler=None,
                      defaultToNormal=None,

                      globalScale=None,
                      squashStretch=False,

                      plug=True):
        """
        :param int anchorIndex: the index of the anchor at which to
            construct a matrix
        :param str primaryAxis: the primary (aim) matrix axis, for example
            '-y'
        :param str secondaryAxis: the secondary (up) matrix axis, for example
            'x'
        :param upVector/upv: if provided on its own, used directly; if combined
            with *upObject*, multiplied by the object's world matrix, similar
            to the 'Object Rotation Up' mode on :class:`motion path
            <paya.runtime.nodes.MotionPath>` nodes; defaults to ``None``
        :type upVector/upv: None, str, tuple, list,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param upObject/uo: similar to :class:`motion path
            <paya.runtime.nodes.MotionPath>` nodes, if provided on its own,
            used as an aiming interest ('Object Up' mode); if combined with
            *upVector*, the up vector is multiplied by the object's world
            matrix ('Object Rotation Up' mode); defaults to ``None``
        :type upObject/uo: None, str, :class:`~paya.runtime.nodes.Transform`
        :param aimCurve/aic: a curve from which to pull aiming interests,
            similar to the option on
            :class:`curveWarp <paya.runtime.nodes.CurveWarp>` nodes; defaults
            to ``None``
        :type aimCurve/aic: None, str,
            :class:`paya.runtime.plugs.NurbsCurve`,
            :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool closestPoint/cp: pull points from *aimCurve* by proximity,
            not matched parameters; defaults to ``True``
        :param upVectorSampler/ups: an up vector sampler created using
            :meth:`createUpVectorSampler`; defaults to ``None``
        :type upVectorSampler/ups: None, str, :class:`~paya.runtime.nodes.Network`,
            :class:`~paya.runtime.networks.CurveUpVectorSampler`
        :param bool defaultToNormal/dtn: when all other up vector options are
            exhausted, don't fall back to any 'default' up vector sampler
            previously created using
            :meth:`createUpVectorSampler(setAsDefault=True) <createUpVectorSampler>`;
            instead, use the curve normal (the curve normal will be used anyway
            if no default sampler is defined); defaults to ``False``
        :param globalScale/gs: a baseline scaling factor; note that scale will
            be normalized in all cases, so if this is value rather than a plug,
            it will have no practical effect; defaults to ``None``
        :type globalScale/gs: None, float, str, :class:`~paya.runtime.plugs.Math1D`
        :param bool squashStretch/ss: allow squashing and stretching of the
            *primaryAxis* on the output matrix; defaults to ``False``
        :param bool plug/p: return a plug rather than a value (note that, if this
            is ``False``, *globalScale* and *squashAndStretch* are ignored);
            defaults to ``True``
        :return: A matrix at the specified anchor.
        :rtype: :class:`paya.runtime.data.Matrix`, :class:`paya.runtime.plugs.Matrix`
        """
        return self.matrixAtParam(
            self.paramAtAnchor(anchorIndex),

            primaryAxis,
            secondaryAxis,

            upVector=upVector,
            upObject=upObject,

            aimCurve=aimCurve,
            closestPoint=closestPoint,

            upVectorSampler=upVectorSampler,
            defaultToNormal=defaultToNormal,

            globalScale=globalScale,
            squashStretch=squashStretch,

            plug=plug
        )