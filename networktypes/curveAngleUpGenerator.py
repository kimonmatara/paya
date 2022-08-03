from paya.util import short
import paya.lib.plugops as _po
import paya.lib.mathops as _mo
import paya.runtime as r


class CurveAngleUpGenerator(r.networks.CurveUpGenerator):
    """
    Curve up vector generator with per-segment parallel transport solving.
    If more than one vector key is defined, the blending can be governed by
    per-segment user-switchable unwinding modes.
    """
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

    @classmethod
    @short(unwindSwitch='uws', interpolation='i', resolution='res')
    def create(cls, curve, paramVectorKeys,
               resolution=None, unwindSwitch=0, interpolation=1):
        """
        :param curve: the curve associated with this system
        :type curve: str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param paramVectorKeys:
            zipped *parameter, vector* pairs defining known up vectors between
            which to blend; this should include entries for the minimum and
            maximum parameters in the curve U domain, otherwise you may get
            unexpected results; defaults to None
        :type paramVectorKeys/pvk:
            [(float | :class:`~paya.runtime.plugs.Math1D`,
                list | tuple | :class:`~paya.runtime.data.Vector` |
                :class:`~paya.runtime.plugs.Vector`)]
        :param int resolution/res: the number of parallel-transport solution
            points along the curve; more solutions yield more accuracy at the
            cost of interaction speed; if omitted, defaults to
            ``3 * (len(paramVectorKeys)-1)``, i.e. three samples per key
            segment
        :param unwindSwitch/uws: an integer value or plug to define the
            unwinding mode:

            - 0 (shortest, the default)
            - 1 (positive)
            - 2 (negative)

            This can also be a list of values or attributes, in which case it
            should be of length paramVectorKeys-1
        :type unwindSwitch/uws: int, :class:`~paya.runtime.plugs.Math1D`,
            [int, :class:`~paya.runtime.plugs.Math1D`]
        :param interpolation/i: an integer plug or value defining which type
            of interpolation should be applied to any subsequently sampled
            values; this tallies with the color interpolation enums on a
            :class:`remapValue <paya.runtime.nodes.RemapValue>` node, which
            are:

            - 0 ('None', you wouldn't usually want this)
            - 1 ('Linear') (the default)
            - 2 ('Smooth')
            - 3 ('Spline')

        :type interpolation/i: int, :class:`~paya.runtime.plugs.Math1D`
        :return: The network node.
        :rtype: :class:`~paya.runtime.networks.CurveAngleUpGenerator`
        """

        #------------------------------------------------|    Prep

        paramVectorKeys = list(paramVectorKeys)
        numKeys = len(paramVectorKeys)

        if numKeys < 2:
            raise ValueError("Need at least two vector keys.")

        numSegments = numKeys-1

        # Wrangle args
        if interpolation is None:
            interpolation = 1

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

        curve = _po.asGeoPlug(curve)
        segmentResolutions = cls._resolvePerSegmentResolutions(
            numSegments, resolution
        )

        #------------------------------------------------|    Build

        with r.Name(curve.node().basename(sts=True), 'angleUpGen'):

            #--------------------------------------------|    Basics

            node = cls.createNode()
            node._addSamplesAttr()
            curve >> node.addAttr('curve', at='message')
            rv = r.nodes.RemapValue.createNode()
            rv.attr('message') >> node.addAttr('remapValue', at='message')

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
                infoPack = {
                    'startParam': param,
                    'nextParam': params[i+1],
                    'startNormal': normals[i],
                    'endNormal': normals[i+1],
                    'unwindSwitch': unwindSwitches[i],
                    'tangentSampleParams': _mo.floatRange(
                        param, params[i+1],
                        segmentResolution)
                }

                infoPacks.append(infoPack)

            # Add tangent samples to each bundle, taking care not to
            # replicate overlapping samples
            for i, infoPack in enumerate(infoPacks):
                with r.Name('segment', i+1, padding=2):
                    inner = i > 0
                    tangentSampleParams = infoPack['tangentSampleParams'][:]

                    if inner:
                        del(tangentSampleParams[i])

                    infoPack['tangents'] = tangents = []

                    for x, tangentSampleParam in enumerate(
                            tangentSampleParams):
                        with r.Name('tangent', x+1):
                            tangents.append(
                                curve.tangentAtParam(tangentSampleParam)
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

            # Use them to set keys on the remap value node
            rv.setColors(zip(outParams, outNormals), i=interpolation)

        return node

    def _sampleAt(self, parameter):
        rv = self.attr('remapValue').inputs()[0]
        return rv.sampleColor(parameter)