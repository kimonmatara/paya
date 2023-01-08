from paya.lib.mathops import flipAxis
import paya.runtime as r
from paya.util import short
from paya.config import takeUndefinedFromConfig, undefined


class Triad(r.parts.Part):

    #-------------------------------------------------------|
    #-------------------------------------------------------|    CONSTRUCTORS
    #-------------------------------------------------------|

    @classmethod
    @takeUndefinedFromConfig
    def createChain(cls,
                    points,
                    upVector,
                    tipMatrix=None,
                    downAxis=undefined,
                    upAxis=undefined,
                    numTopTwists=0,
                    numBtmTwists=0,
                    parent=None,
                    ikJitter=False,
                    opposite=False):
        """
        Creates a three-point skeletal chain.

        :param points: a world position for each joint; three points
            are required; excess points will be discarded
        :type points: :class:`list` [:class:`list` [:class:`float`] |
            :class:`~paya.runtime.data.Point` |
            :class:`~paya.runtime.data.Vector`]
        :param upVector: the main up vector hint for the chain; this will
            guide cross product calculations to resolve orientations for
            the main bend axis
        :param tipMatrix: an optional rotation matrix override for the tip
            (end) joint; if provided, only orientation information will be
            used; defaults to ``None``
        :type tipMatrix: ``None``, :class:`list` [:class:`float`],
            :class:`~paya.runtime.data.Matrix`
        :param int numTopTwists: the number of twist joints to insert on the
            top (bicep / thigh) bone; defaults to ``0``
        :param int numBtmTwists: the number of twist joints to insert on the
            btm (forearm / shin) bone; defaults to ``0``
        :param str downAxis: the 'bone' axis; defaults to
            ``paya.config.downAxis``
        :param str upAxis: the axis to map to the up vector; defaults to
            ``paya.config.upAxis``
        :param parent: an optional destination parent for the chain;
            defaults to ``None``
        :type parent: ``None``, :class:`str`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool ikJitter: ignored if twist joints are involved; if this
            chain is in-line, auto-configures preferred angles to prevent
            lockout; defaults to ``False``
        :param bool opposite: flips the (resolved) down axis; defaults to
            ``False``
        :return: The generated chain.
        :rtype: :class:`Chain`
        """
        #--------------------------------------|    Init

        if len(points) < 3:
            raise ValueError("Need three points.")

        points = list(points)[:3]
        upVector = r.data.Vector(upVector)

        if opposite:
            downAxis = flipAxis(downAxis)

        #--------------------------------------|    Build

        chain = r.Chain.createFromPoints(
            points,
            upVector,
            downAxis=downAxis,
            upAxis=upAxis,
            parent=parent,
            tipMatrix=tipMatrix
        )

        #--------------------------------------|    Twists / jitter

        if numTopTwists or numBtmTwists:
            if numTopTwists:
                topSegment = chain[:2]
                topSegment.insertJoints(numTopTwists)

            if numBtmTwists:
                btmSegment = chain[1:]
                btmSegment.insertJoints(numBtmTwists)

            # Rescan
            chain = chain[0].chainFromHere()
            chain.rename()

        elif ikJitter:
            chain.autoPreferredAngle(upVector)

        return chain

    # @r.partCreator
    # @takeUndefinedFromConfig
    # def create(
    #         self,
    #         points,
    #         upVector,
    #         endIkCtMatrix=None,
    #         endRotCtMatrix=None,
    #         downAxis=undefined,
    #         upAxis=undefined,
    #         poleCtMatrix=None,
    #         createIkLine=True,
    #         polePoint=None, # ignored if poleCtMatrix
    #         poleLength=1.0 # ignored if polePoint or poleCtMatrix
    # ):
    #     #--------------------------------------|    Init
    #
    #     if len(points) is not 3:
    #         raise ValueError("Need three points.")
    #
    #     points = [r.data.Point(point) for point in points]
    #     upVector = r.data.Vector(upVector)
    #
    #     #--------------------------------------|    Tmp
    #
    #     with r.Name('tmp', padding=2):
    #         tmpChain = r.Chain.createFromPoints(
    #             points,
    #             upVector,
    #             downAxis=downAxis,
    #             upAxis=upAxis,
    #             parent=self.tree['joints'].node()
    #         )
    #
    #     #--------------------------------------|    IK
    #
    #     with r.Name('ik'):
    #         ikResult = self._createIkSystem(tmpChain,
    #                                         downAxis,
    #                                         upAxis,
    #                                         upVector,
    #                                         endIkCtMatrix=endIkCtMatrix,
    #                                         poleCtMatrix=poleCtMatrix,
    #                                         polePoint=polePoint,
    #                                         poleLength=poleLength,
    #                                         createIkLine=createIkLine)
    #
    #     #--------------------------------------|    FK
    #
    #     with r.Name('fk'):
    #         fkResult = self._createFkSystem(tmpChain,
    #                                         downAxis,
    #                                         upAxis,
    #                                         upVector)
    #
    #     #--------------------------------------|    Blend
    #
    #     with r.Name('blend'):
    #         self._createBlendSystem(tmpChain, fkResult, ikResult)
    #
    # #-------------------------------------------------------|
    # #-------------------------------------------------------|    PARTIALS
    # #-------------------------------------------------------|
    #
    # def _createIkSystem(self,
    #                     tmpChain,
    #                     downAxis,
    #                     upAxis,
    #                     upVector,
    #                     poleCtMatrix=None,
    #                     polePoint=None,
    #                     endIkCtMatrix=None,
    #                     poleLength=1.0,
    #                     createIkLine=True):
    #
    #     #--------------------------------------|    Derive chain
    #
    #     with r.Name(padding=2):
    #         chain = tmpChain[:3].duplicate()
    #
    #     #--------------------------------------|    Draw pole controls
    #
    #     if poleCtMatrix is not None:
    #         poleCtMatrix = r.data.Matrix(poleCtMatrix)
    #     else:
    #         if polePoint is not None:
    #             polePoint = r.data.Point(polePoint)
    #         else:
    #             inline = chain.isInline()
    #
    #             if inline:
    #                 chordVec = tmpChain[2].gwp()-tmpChain[0].gwp()
    #                 kneeVec = chordVec.cross(upVector)
    #             else:
    #                 v1, v2 = tmpChain.vectors()
    #                 kneeVec = v1.normal()-v2.normal()
    #
    #             polePoint = tmpChain[1].gwp() + (kneeVec.normal() * poleLength)
    #
    #         poleCtMatrix = r.data.Matrix()
    #         poleCtMatrix.t = polePoint
    #
    #     # Draw
    #     with r.Name('pole'):
    #         poleCts = r.createControls(
    #             worldMatrix=poleCtMatrix,
    #             parent=self.tree['controls']['ik'].node(),
    #             keyable=['t'],
    #             shape='sphere'
    #         )
    #
    #     #--------------------------------------|    Draw end controls
    #
    #     if endIkCtMatrix:
    #         drawMatrix = r.data.Matrix(endIkCtMatrix)
    #     else:
    #         drawMatrix = r.data.Matrix()
    #         drawMatrix.t = chain[2].getWorldPosition()
    #
    #     with r.Name('end'):
    #         endCts = r.createControls(
    #             numControls=2,
    #             worldMatrix=drawMatrix,
    #             keyable=['t', 'r', 'ro'],
    #             parent=self.tree['controls']['ik'].node(),
    #             pickWalkParent=poleCts[0],
    #             pickWalkInsets=False
    #         )
    #
    #     #--------------------------------------|    Create IK handle
    #
    #     with r.Name('end'):
    #         endIkh = chain.createIkHandle(jitter=True,
    #                                       upVector=upVector)
    #
    #         endIkh.setParent(self.tree['util'].node(it=False))
    #         endIkh.hide()
    #         endCts[1].attr('wm').drive(endIkh, ws=True, mo=True)
    #
    #     #--------------------------------------|    Assign pole point
    #
    #     livePolePoint = poleCts[1].getWorldPosition(plug=True)
    #
    #     endIkh.setPolePoint(livePolePoint,
    #                         maintainOffset=True)
    #
    #     #--------------------------------------|    Add auto-follow for pole
    #
    #     chordStart = chain[0].getWorldPosition() \
    #         ^ self.node().getWorldMatrix(plug=True, asOffset=True)
    #
    #     chordEnd = endCts[1].getWorldPosition(plug=True)
    #     chordVec = chordEnd-chordStart
    #     chordLen = chordVec.length()
    #     nativeChainLen = chain.length() * self.getPartScale(plug=True)
    #     chordLen = chordLen.maxClamp(nativeChainLen)
    #     targetLen = chordLen * 0.5
    #
    #     mtx = r.createMatrix(
    #         downAxis,
    #         chordVec,
    #         upAxis,
    #         upVector*self.node().getWorldMatrix(plug=True, asOffset=True),
    #         t=chordStart+(chordVec.normal() * targetLen)
    #     ).pk(t=True, r=True)
    #
    #     mtx = self.getPartScaleMatrix(plug=True) * mtx
    #
    #     poleCts[0].createAnimSpace(['auto'], [mtx],
    #                                translate=True, rotate=True)
    #
    #     #-------------------------------------------|    Create feedback line
    #
    #     chordEnd = chordStart + (chordVec.normal() * chordLen)
    #
    #     if createIkLine:
    #         with r.Name('feedback'):
    #             curve = r.nodes.NurbsCurve.create(
    #                 [chordStart, livePolePoint, chordEnd],
    #                 displayType='Template',
    #                 degree=1
    #             ).toTransform()
    #
    #             curve.setParent(self.tree['util'].node(it=False))
    #
    #     out = {'chain': chain}
    #
    #     if createIkLine:
    #         out['curve'] = curve
    #
    #     return out
    #
    # def _createFkSystem(self, tmpChain, downAxis, upAxis, upVector):
    #
    #     #-------------------------------------------|    Derive chain
    #
    #     with r.Name(padding=2):
    #         chain = tmpChain.duplicate()
    #
    #     #-------------------------------------------|    Draw controls
    #
    #     controls = []
    #     rotateOrder = _mo.inventRotateOrder(downAxis, upAxis)
    #
    #     for i, joint in enumerate(chain[:2]):
    #         keyable = ['ro']
    #
    #         if i is 1:
    #             keyable.append('r'+_mo.absAxis(upAxis))
    #         else:
    #             keyable.append('r')
    #
    #         control = r.createControl(
    #             worldMatrix=joint.getWorldMatrix(),
    #             rotateOrder=rotateOrder,
    #             keyable=keyable,
    #             parent=controls[-1] if controls \
    #                 else self.tree['controls']['fk'].node(),
    #             pickWalkParent=controls[-1] if controls else None,
    #             shape='diamond'
    #         )
    #
    #         control.attr('wm').decomposeAndApply(joint, ws=True, r=True)
    #         controls.append(control)
    #
    #     return {'chain': chain}
    #
    # def _createBlendSystem(self, tmpChain, fkResult, ikResult):
    #     node = self.node()
    #     ikOn = node.addAttr('ikOn', k=True, min=0, max=1, dv=1)
    #     ikOff = node.addAttr('ikOff', min=0, max=1, dv=0)
    #     (1-ikOn) >> ikOff
    #     ikOff.lock()
    #
    #     ikOn >> self.tree['controls']['ik'].node().attr('v')
    #     ikOff >> self.tree['controls']['fk'].node().attr('v')
    #
    #     try:
    #         ikOn >> ikResult['curve'].attr('v')
    #     except KeyError:
    #         pass
    #
    #     fkChain = fkResult['chain']
    #     ikChain = ikResult['chain']
    #
    #     with r.Name(padding=2):
    #         blChain = tmpChain.duplicate()
    #
    #     for fkJt, ikJt, blJt in zip(fkChain, ikChain, blChain):
    #         mtx = fkJt.wm.blend(ikJt.wm, weight=ikOn)
    #         mtx.drive(blJt, ws=True, uop=False)