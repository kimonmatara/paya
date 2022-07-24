import paya.runtime as r

def createWormRig(
        startLoc,
        endLoc,
        numJoints,
        baseMesh,
        squashMesh,
        stretchMesh
):
    """
    Worm rig example with per-point twist, pick-walk controls and driven blend
    shapes. Navigate to ``paya/examples/worm_rig_layout.ma`` and run this:

    .. code-block:: python

        import paya.examples.worm_rig as wr
        wr.createWormRig('locator1', 'locator2', 12, 'base', 'squashed', 'stretched')

    :param startLoc: a locator to mark the root of the worm spine
    :param endLoc:  a locator to mark the tip of the worm spine
    :param numJoints: the number of spine joints to generate
    :param baseMesh: the main worm body
    :param squashMesh: a blend shape target for the 'squashed' state
    :param stretchMesh: a blend shape target for the 'stretched' state
    """

    with r.Name('worm', padding=2):
        # Get layout information
        startPoint = r.PyNode(startLoc).getWorldPosition()
        endPoint = r.PyNode(endLoc).getWorldPosition()
        spineVector = (endPoint-startPoint)

        # Build the driver curves
        spineCurve = r.nodes.NurbsCurve.create(startPoint, endPoint, degree=1)
        spineCurve.cvRebuild(4, degree=3).deleteHistory()

        aimCurve = spineCurve.duplicate()[0]
        aimCurve.attr('translateY').set(1.5)

        # Clusters and controls
        controls = []

        for i in range(4):
            with r.Name(i+1):
                thisRatio = 1/3 * i
                point = startPoint + (spineVector * thisRatio)

                control = r.createControl(
                    worldMatrix=point.asTranslateMatrix(),
                    pickWalkParent=controls[-1] if controls else None,
                    keyable=['translate', 'rotate'],
                    color=6,
                    size=1.25,
                    lineWidth=2.0
                )

                cvs = [spineCurve.cv[i], aimCurve.cv[i]]
                cluster = r.nodes.Cluster.create(
                    cvs, weightedNode=control, bindState=True)

                controls.append(control)

        # Driven blend shapes
        blend = r.nodes.BlendShape.create(baseMesh, pre=True)
        squashed = blend.targets.add(squashMesh)
        stretched = blend.targets.add(stretchMesh)

        squashStretchRatio = spineCurve.length(
            plug=True) / spineCurve.length()

        squashDriver = squashStretchRatio.remap(1.0, 0.75, 0.0, 1.0)
        squashDriver >> squashed.weight

        stretchDriver = squashStretchRatio.remap(1.0, 1.25, 0.0, 1.0)
        stretchDriver >> stretched.weight

        # Drive the bump map too
        bumpDriver = squashStretchRatio.remap(0.5, 1.25, 0.32, 0.0)
        bumpDriver >> r.PyNode('fractal2').attr('amplitude')

        # Skinning
        joints = spineCurve.distributeJoints(
            numJoints, 'y', 'x',
            aimCurve=aimCurve,
            matchedCurve=True,
            plug=True
        )

        skin = r.nodes.SkinCluster.create(joints, baseMesh, dropoffRate=2)

        # Cleanup
        r.hide(squashMesh, stretchMesh,
               spineCurve, aimCurve, startLoc, endLoc)