
import paya.lib.mathops as _mo
import pymel.util as _pu
import paya.runtime as r

@r.nativeUnits
def test():
    r.openFile('C:/Users/user/Desktop/interp.mb', f=1)

    curve = r.pn('curve1')
    startLoc = r.pn('start')
    endLoc = r.pn('end')

    startVec = startLoc.wm.y
    endVec = endLoc.wm.y

    num = 20
    umin, umax = curve.getKnotDomain()
    sampleParams = _mo.floatRange(umin, umax, num)

    points = [curve.pointAtParam(par, ws=1, p=1) for par in sampleParams]
    tangents = [curve.tangentAtParam(par, ws=1, p=1) for par in sampleParams]

    startVec = startVec.rejectFrom(tangents[0])
    endVec = endVec.rejectFrom(tangents[-1])

    fwdUpVecs = _mo.parallelTransport(startVec, tangents)
    bwdUpVecs = _mo.parallelTransport(endVec, tangents[::-1])[::-1]

    blendedVecs = []

    ratios = _mo.floatRange(0, 1, num)

    for i, fwdUpVec, bwdUpVec, tangent, ratio, point in zip(
        range(num),
        fwdUpVecs,
        bwdUpVecs,
        tangents,
        ratios,
        points
    ):
        with r.Name(i+1, padding=3):

            loc = r.spaceLocator()
            loc.addAttr('primaryDot', k=True)
            loc.addAttr('secondaryDot', k=True)
            fwdUpVec.dot(tangent,nr=1) >> loc.primaryDot
            bwdUpVec.dot(tangent,nr=1) >> loc.secondaryDot

            fwdUpVec = fwdUpVec.rejectFrom(tangent)
            bwdUpVec = bwdUpVec.rejectFrom(tangent)

            angle = fwdUpVec.angle(bwdUpVec, cn=tangent)

            over180 = angle.gt(_pu.radians(180))

            """
            angle = over180.ifElse(
                angle-_pu.radians(360),
                angle
            ).setClass(r.plugs.Angle)
            """

            angle *= ratio

            vec = fwdUpVec.rotateByAxisAngle(tangent, angle)

            mtx = r.createMatrix(
                'z', tangent,
                'y', vec,
                t=point
            ).pk(t=1,r=1)

            mtx.applyViaOpm(loc, ws=True)












    # with r.Name('foward'):
    #     for i in range(num):
    #         with r.Name(i+1, padding=3):
    #             pt = points[i]
    #             tan = tangents[i]
    #             up = fwdUpVecs[i]
    #
    #             mtx = r.createMatrix('z', tan, 'y', up, t=pt).pk(t=1, r=1)
    #             mtx.cl()
    #
    # with r.Name('backward'):
    #     for i in range(num):
    #         with r.Name(i+1, padding=3):
    #             pt = points[i]
    #             tan = tangents[i]
    #             up = bwdUpVecs[i]
    #
    #             mtx = r.createMatrix('z', tan, 'y', up, t=pt).pk(t=1, r=1)
    #             mtx.cl()