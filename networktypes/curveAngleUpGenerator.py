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
    @short(unwindSwitch='uws', interpolation='i')
    def create(cls, curve, paramNormalKeys,
               resolution, unwindSwitch=0, interpolation=3):
        """
        :param curve: the curve associated with this system
        :type curve: str, :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.plugs.NurbsCurve`
        :param paramNormalKeys: a zipped mapping of *parameter: normal*,
            defining normal 'keys' along the curve
        :type paramNormalKeys: [(
            float | :class:`~paya.runtime.plugs.Math1D`,
            tuple | list | :class:`~paya.runtime.data.Vector` | :class:`~paya.runtime.plugs.Vector`
            )]
        :param int resolution: the number of parallel-transport solution points
            along the curve; more solutions yields more accuracy at the cost
            of interaction speed (start with something like 16 and test)
        :param unwindSwitch/uws: an integer value or plug to define the
            unwinding mode:

            - 0 (shortest, the default)
            - 1 (positive)
            - 2 (negative)

            This can also be a list of values or attributes, in which case it
            should be of length paramNormalKeys-1
        :type unwindSwitch/uws: int, :class:`~paya.runtime.plugs.Math1D`,
            [int, :class:`~paya.runtime.plugs.Math1D`]
        :param interpolation/i: an integer plug or value defining which type
            of interpolation should be applied to any later sampled values;
            this tallies with the color interpolation enums on a
            :class:`remapValue <paya.runtime.nodes.RemapValue>` node, which
            are:

            - 0 ('None', you wouldn't usually want this)
            - 1 ('Linear')
            - 2 ('Smooth')
            - 3 ('Spline')

            The default is 3 ('Spline').
        :type interpolation/i: int, :class:`~paya.runtime.plugs.Math1D`
        :return: The network node.
        :rtype: :class:`~paya.runtime.nodes.Network`
        """
        #------------------------------------------------|    Prep

        paramNormalKeys = list(paramNormalKeys)
        numKeys = len(paramNormalKeys)

        if numKeys < 2:
            raise ValueError("Need at least two keys.")

        numSegments = numKeys-1

        # Wrangle args
        if isinstance(unwindSwitch, (tuple, list)):
            if len(unwindSwitch) is not numSegments:
                raise ValueError(
                    "If 'unwindSwitch' is a list, it "+
                    "should be of length "+
                    "paramUpVectorKeys-1.")

            unwindSwitches = [_mo.info(x)[0] for x in unwindSwitch]

        else:
            unwindSwitches = [unwindSwitch] * numSegments

        curve = _po.asGeoPlug(curve, worldSpace=True)

        # Create per-segment resolutions with corrected rounding
        segmentResolution = round(resolution / numSegments)
        segmentResolutions = [segmentResolution] * numSegments
        remulted = segmentResolution * numSegments

        if remulted < resolution:
            # Add one more sample to start
            segmentResolutions[0] += 1

        elif remulted > resolution:
            # Remove one sample from end
            segmentResolutions[-1] -= 1

        #------------------------------------------------|    Build

        with r.Name(curve.node().basename(sts=True), 'angleUpGen'):

            #--------------------------------------------|    Basics

            node = cls.createNode()
            node._addSamplesAttr()
            curve >> node.addAttr('curve', at='message')
            rv = r.nodes.RemapValue.createNode()
            rv.attr('message') >> node.addAttr('remapValue', at='message')

            #--------------------------------------------|    Solve

            params, normals = zip(*paramNormalKeys)

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

                    for x, tangentSampleParam in enumerate(tangentSampleParams):
                        with r.Name('tangent', x+1):
                            tangents.append(curve.tangentAtParam(tangentSampleParam))

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

        # Done. Return network
        return node

    def _sampleAt(self, parameter):
        rv = self.attr('remapValue').inputs()[0]
        return rv.sampleColor(parameter)