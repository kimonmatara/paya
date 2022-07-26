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
    Worm rig example with per-point twist, pick-walk Bezier controls and
    driven blend shapes. Navigate to ``paya/examples/worm_rig_layout.ma``
    and run this:

    .. code-block:: python

        import paya.examples.worm_rig as wr
        wr.createWormRig('locator1', 'locator2', 16, 'base', 'squashed', 'stretched')

    :param startLoc: a locator to mark the root of the worm spine
    :param endLoc:  a locator to mark the tip of the worm spine
    :param numJoints: the number of spine joints to generate
    :param baseMesh: the main worm body
    :param squashMesh: a blend shape target for the 'squashed' state
    :param stretchMesh: a blend shape target for the 'stretched' state
    """
    # Get layout information
    startPoint = r.PyNode(startLoc).getWorldPosition()
    endPoint = r.PyNode(endLoc).getWorldPosition()
    spineVector = (endPoint-startPoint)

    # Draw the curves
    points = [startPoint+(spineVector * (1/3 * i)) for i in range(4)]

    spineCurve = r.nodes.BezierCurve.create(points, name='main').getParent()
    aimCurve = spineCurve.duplicate(name='aim', managedNames=True)[0]
    aimCurve.attr('translateY').set(1.5)
    aimCurve.makeIdentity(apply=True)

    # Draw controls, drive the curves
    controls = []

    for anchorIndex in (0, 1):
        matrix = spineCurve.matrixAtAnchor(anchorIndex, 'z', 'x', upv=[0,1,0])

        with r.Name(anchorIndex+1):
            control = r.createControl(
                worldMatrix=matrix,
                pickWalkParent=controls[-1] if controls else None,
                keyable=['translate', 'rotate', 'scaleZ'],
                color=6,
                size=1.25,
                lineWidth=2.0,
                rotateOrder='zxy' # for easier twist control
            )

            cvs = spineCurve.getCVsAtAnchor(anchorIndex, asComponents=True)
            cvs += aimCurve.getCVsAtAnchor(anchorIndex, asComponents=True)
            r.nodes.Cluster.create(cvs, handle=control, maintainOffset=True)

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
        closestPoint=True,
        plug=True
    )

    skin = r.nodes.SkinCluster.create(joints, baseMesh, dropoffRate=2)

    # Cleanup
    r.hide(squashMesh, stretchMesh,
           spineCurve, aimCurve, startLoc, endLoc)