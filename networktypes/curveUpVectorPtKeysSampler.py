import paya.lib.typeman as _tm
import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r


class CurveUpVectorPtKeysSampler(r.networks.CurveUpVectorRemapSampler):
    """
    Solves for parallel transport in both directions for each key segment,
    and blends between the solutions by angle, with unwinding options.

    Works similarly to
    :class:`~paya.runtime.networks.CurveUpVectorIkSplineStyleSampler`, but
    with properly-localised twist.
    """

    #-------------------------------------------------------|    Constructor

    @classmethod
    @short(interpolation='i',
           resolution='res',
           unwindSwitch='uws')
    def create(cls,
               curve,
               paramVectorKeys,
               interpolation='Linear',
               resolution=9,
               unwindSwitch=0):
        """
        :param curve: the curve on which to create the sampler
        :type curve: str, :class:`paya.runtime.nodes.NurbsCurve`,
            :class:`paya.runtime.nodes.Transform`,
            :class:`paya.runtime.plugs.NurbsCurve`
        :param paramVectorKeys: zipped *parameter, vector* pairs, indicating
            known up vectors along the curve; at least two such keys are
            needed
        :type paramVectorKeys:
            [[:class:`float` | :class:`str` | :class:`~paya.runtime.plugs.Math1D`],
            [:class:`tuple` | :class:`list`,
            :class:`paya.runtime.data.Vector`,
            :class:`paya.runtime.plugs.Vector`]]
        :param interpolation/i: a string label or integer value or plug
            specifying how to interpolate between the keyed pairs, namely:

            -   ``0`` (``'None'``) (you wouldn't normally want this)
            -   ``1`` (``'Linear'``) (the default)
            -   ``2`` (``'Smooth'``)
            -   ``3`` (``'Spline'``)

        :type interpolation/i: int, str, :class:`~paya.runtime.plugs.Math1D`
        :param int resolution/res: the number of parallel-transport solutions to
            generate along the curve; higher numbers improve accuracy at the
            expense of performance; defaults to 9
        :param unwindSwitch/uws: an integer value or plug, or a list of integer
            values or plugs (one per segment, i.e.
            ``len(paramVectorKeys)-1``) specifying how to resolve angle-
            blending edge cases:

            -   ``0`` (shortest, the default)
            -   ``1`` (positive)
            -   ``2`` (negative)

        :type unwindSwitch/uws: :class:`int`, :class:`str`,
            :class:`~paya.runtime.plugs.Math1D`,
        [:class:`int` | :class:`str` | :class:`~paya.runtime.plugs.Math1D`]
        :return: The network system.
        :rtype: :class:`CurveUpVectorPtKeysSampler`
        """
        with r.NodeTracker() as track:
            node = cls._create(curve, paramVectorKeys,
                               interpolation=interpolation,
                               resolution=resolution,
                               unwindSwitch=unwindSwitch)

        node._tagDependencies(track.getNodes())
        return node

    @classmethod
    def _create(cls,
               curve,
               paramVectorKeys,
               interpolation='Linear',
               resolution=9,
               unwindSwitch=0):

        #-----------------------------------------|    Prep

        paramVectorKeys = list(paramVectorKeys)
        numKeys = len(paramVectorKeys)

        if numKeys < 2:
            raise ValueError("Need at least two vector keys.")

        numSegments = numKeys-1

        if isinstance(unwindSwitch, (tuple, list)):
            if len(unwindSwitch) is not numSegments:
                raise ValueError(
                    "If 'unwindSwitch' is a list, it "+
                    "should be of length "+
                    "paramUpVectorKeys-1.")

            unwindSwitches = [_tm.mathInfo(x)[0] for x in unwindSwitch]

        else:
            unwindSwitches = [unwindSwitch] * numSegments

        curve = _tm.asGeoPlug(curve)
        segmentResolutions = cls._resolvePerSegmentResolutions(
            numSegments, resolution
        )

        #-----------------------------------------|    Solve

        params, normals = zip(*paramVectorKeys)

        # Init per-segment info bundles
        infoPacks = []

        for i, param, normal, segmentResolution in zip(
            range(numSegments),
            params[:-1],
            normals[:-1],
            segmentResolutions):

            tangentSampleParams = _mo.floatRange(
                param, params[i+1], segmentResolution)

            infoPack = {
                'startParam': param,
                'nextParam': params[i+1],
                'startNormal': normals[i],
                'endNormal': normals[i+1],
                'unwindSwitch': unwindSwitches[i],
                'tangentSampleParams': tangentSampleParams
            }

            infoPacks.append(infoPack)

        # Add tangent samples to each bundle, taking care not to
        # replicate overlapping samples
        for i, infoPack in enumerate(infoPacks):
            with r.Name('segment', i+1, padding=2):
                inner = i > 0
                tangentSampleParams = infoPack['tangentSampleParams'][:]

                if inner:
                    del(tangentSampleParams[0])

                infoPack['tangents'] = tangents = []

                for x, tangentSampleParam in enumerate(
                        tangentSampleParams):
                    with r.Name('tangent', x+1):
                        tangents.append(
                            curve.tangentAtParam(tangentSampleParam, p=True)
                        )

                if inner:
                    tangents.insert(0, infoPacks[i-1]['tangents'][-1])


        # Run the parallel transport per-segment
        for i, infoPack in enumerate(infoPacks):
            with r.Name('segment', i+1, padding=2):
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

        #-----------------------------------------|    Create interpolator system

        keymap = list(zip(outParams, outNormals))

        return super(r.networks.CurveUpVectorPtKeysSampler, cls)._create(
            curve, keymap, interpolation=interpolation
        )


    @classmethod
    def _resolvePerSegmentResolutions(cls, numSegments, resolution):
        # Formula is:
        # resolution = (resPerSegment * numSegments) - (numSegments-1)
        # hence:
        # resPerSegment = (resolution + (numSegments-1)) / numSegments

        # Assume that a minimum 'good' total resolution for any kind of
        # curve is 9, and a minimum functioning value for 'resPerSegment'
        # is 3

        minimumPerSegmentResolution = 3
        minimumTotalResolution = 9
        minimumResolutionForThisCurve = max([
            (minimumPerSegmentResolution * numSegments) - (numSegments-1),
            minimumTotalResolution
        ])

        if resolution is None:
            resolution = 3 * numSegments

        elif resolution < minimumResolutionForThisCurve:
            r.warning(("Requested resolution ({}) is too low for this"+
                " curve; raising to {}.").format(resolution,
                minimumResolutionForThisCurve))

            resolution = minimumResolutionForThisCurve

        # Derive per-segment resolution
        perSegmentResolution = (resolution + (numSegments-1)) / numSegments
        perSegmentResolution = int(round(perSegmentResolution))

        resolutions = [perSegmentResolution] * numSegments
        retotalled = (perSegmentResolution * numSegments) - (numSegments-1)

        # Correct rounding errors
        if retotalled < resolution:
            resolutions[0] += 1

        elif retotalled > resolution:
            resolutions[-1] -= 1

        return resolutions