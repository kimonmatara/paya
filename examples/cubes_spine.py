import pymel.util as _pu
import paya.lib.mathops as _mo
import paya.runtime as r

def makeSpineLevels(numLevels, numJoints):
    """
    Create two anchor-bezier
    Draw controls at the anchors
    Drive the bezier with the controls; use the controls to add up vector information



    Subdivide previous to get three-point bezier. This is the 'platform'
    Draw inner controls
    For each control:
        Get a matrix at the matching inner platform anchor, use it to drive the control
        (including tangent stretch)

    Create an offset curve
    Cluster internal anchors to the inner controls
    For the outer anchors:
        Get tangent from platform curve
        Get up vector and position from root bounds controls
        Drive with matrices
    """
    #--------------------------------------------------|    Prep

    startPt = r.PyNode('start_guide').getWorldPosition()
    endPt = r.PyNode('end_guide').getWorldPosition()

    #--------------------------------------------------|    Create group structures

    mainGp = r.nodes.Transform.create()
    globalScale = mainGp.attr('wm').y.length()

    #--------------------------------------------------|    Iterate

    bundles = []

    for i in range(numLevels):
        bundle = {}
        first = i == 0

        with r.Name('level', i+1):

            levelGp = r.nodes.Transform.create(p=mainGp)

            #------------------------------------------|    Get starting points

            if first:
                innerWeights = _mo.floatRange(0, 1, 4)[1:-1]
                innerPts = [_pu.blend(startPt, endPt, weight=weight
                                      ) for weight in innerWeights]
                _prevOutputPtDicts = [
                    {'root': startPt, 'out': innerPts[0]},
                    {'in': innerPts[1], 'root': endPt}
                ]

            else:
                prevOutput = bundles[i-1]['output'].attr('worldSpace')
                prevSubOutput = prevOutput.subdivideAnchors()
                prevOutputPtDicts = prevSubOutput.getControlVerts(anchors=True,
                                                               p=True)

                _prevOutputPtDicts = [{k: v.get() for k, v \
                                    in dct.items()} for dct in prevOutputPtDicts]

            #------------------------------------------|    Draw controls

            if first:
                drawMatrices = [pt.asTranslateMatrix() for pt in (startPt, endPt)]

            else:
                # Skip the external controls; will reuse the base controls
                drawMatrices = [None] * (len(_prevOutputPtDicts)-2)

            ctGp = r.nodes.Transform.create(n='controls', u=levelGp)

            bundle['controls'] = controls = [
                r.createControl(
                    wm=drawMatrix,
                    k=['t','r','sz'],
                    size=3 * (0.8 ** i),
                    n=x+1,
                    col=14,
                    u=ctGp
                ) for x, drawMatrix in enumerate(drawMatrices)
            ]

            #------------------------------------------|    Drive controls

            if not first:
                # Get tangents from previous output curve anchors
                tangents = [prevOutputPtDict.get('out', prevOutputPtDict['root']) \
                            -prevOutputPtDict.get('in', prevOutputPtDict['root']) \
                            for prevOutputPtDict in prevOutputPtDicts]

                # Get points from previous output curve anchors
                points = [prevOutputPtDict['root'] \
                          for prevOutputPtDict in prevOutputPtDicts]

                upVecParams = [prevOutput.nearestParam(point.get()
                                                       ) for point in points]
                upVecs = [prevOutput.upVectorAtParam(
                    param, p=True) for param in upVecParams]

                # Only drive inner controls
                ctDriverMatrices = [r.createMatrix(
                    'z', tangent,
                    'y', upVec,
                    t=point
                ).pick(t=True,
                       r=True) for tangent, upVec, point \
                                    in zip(tangents[1:-1], upVecs[1:-1], points[1:-1])]

                for ct, ctDriverMatrix in zip(
                    controls, ctDriverMatrices
                ):
                    ctDriverMatrix.applyViaOpm(ct.getParent(), ws=True)

            #------------------------------------------|    Transform points

            driverMatrices = [ct.attr('wm') for ct in controls]

            if not first:
                # Insert driver matrices from level 0 bounds controls
                driverMatrices.insert(0, bundles[0]['controls'][0].attr('wm').pick(t=1, r=1))
                driverMatrices.append(bundles[0]['controls'][-1].attr('wm').pick(t=1,r=1))

                # Incorporate tangent stretch from previous output curve
                tangentStretchMatrices = [
                    r.createScaleMatrix(globalScale,
                                        globalScale,
                                        tangent.length().normal()) \
                    for tangent in tangents]

                driverMatrices = [tangentStretchMatrix * driverMatrix \
                                  for tangentStretchMatrix, driverMatrix \
                                  in zip(tangentStretchMatrices,
                                         driverMatrices)]

            bezPoints = []

            for driverMatrix, _startPtDict in zip(
                driverMatrices, _prevOutputPtDicts
            ):
                bezPoints += [point ^ driverMatrix.asOffset() \
                              for point in _startPtDict.values()]

            #------------------------------------------|    Generate output curve

            bundle['output'] = outputCurve = \
                r.nodes.BezierCurve.create(bezPoints, n='output')

            levelGp | outputCurve.getParent()

            refPoints = [driverMatrix.get().t for driverMatrix in driverMatrices]
            refParams = [outputCurve.nearestParam(refPoint) for refPoint in refPoints]
            refUpVecs = [ct.attr('wm').y for ct in controls]

            if first:
                startUpVec, endUpVec = refUpVecs

            else:
                refUpVecs.insert(0, startUpVec)
                refUpVecs.append(endUpVec)

            upVecMap = list(zip(refParams, refUpVecs))
            sampler = outputCurve.createUpVectorSampler(upv=upVecMap,
                                                        parallelTransport=1,
                                                        uws=0)

        bundles.append(bundle)

    jointsGp = r.nodes.Transform.create(p=mainGp, n='joints')
    bundles[-1]['output'].distributeJoints(
        numJoints, 'z', 'y', p=True, gs=globalScale)

def test():
    r.openFile('C:/Users/user/Documents/paya_showcases/scenes/multi_spine/multi_v001.mb', f=1)
    makeSpineLevels(1, 24)