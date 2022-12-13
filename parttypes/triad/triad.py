import paya.runtime as r
import paya.lib.mathops as _mo
from paya.util import short
from paya.config import takeUndefinedFromConfig, undefined


class Triad(r.parts.Part):

    #-------------------------------------------------------|
    #-------------------------------------------------------|    CONSTRUCTORS
    #-------------------------------------------------------|

    @r.partCreator
    @takeUndefinedFromConfig
    def create(self,
               points,
               upVector,
               numTopTwists=3,
               numBtmTwists=3,
               bevelLength=None,
               endIkCtMatrix=None,
               endRotCtMatrix=None,
               downAxis=undefined,
               upAxis=undefined,
               polePoint=None,
               poleLength=None
               ):
        """
        :param points:
        :param topTwist:
        :param bottomTwist:
        :return:
        """
        """
        Resolve points list against 'bevelLength'
        
        TMP
            Draw temp chain
        
        IK
            Derive chain
            Draw cts
            Hook up, with ss
        FK
            Derive chain
            Draw cts
            Drive chain, with ss
        
        BL
            Derive blend chain
            IK / FK blend
            
        TW
            Derive twist chain
        """
        #---------------------------------------------------|
        #---------------------------------------------------|    Init
        #---------------------------------------------------|

        points = self._resolvePoints(points, bevelLength=bevelLength)
        upVector = r.data.Vector(upVector)

        #-----------------------------------------------------------|
        #-----------------------------------------------------------|    TMP
        #-----------------------------------------------------------|

        with r.Name('tmp'):
            tmpChain = r.Chain.createFromPoints(
                points,
                upVector,
                downAxis=downAxis,
                upAxis=upAxis,
                parent=self.tree['joints'].node(inheritsTransform=False)
            )

        #-----------------------------------------------------------|
        #-----------------------------------------------------------|    IK
        #-----------------------------------------------------------|

        with r.Name('ik'):
            ikSystem = self._createIkSystem(
                tmpChain,
                downAxis,
                upAxis,
                endIkCtMatrix=endIkCtMatrix,
                upVector=upVector,
                polePoint=polePoint,
                poleLength=poleLength
            )

        #-----------------------------------------------------------|
        #-----------------------------------------------------------|    FK
        #-----------------------------------------------------------|

        with r.Name('fk'):
            fkSystem = self._createFkSystem(
                tmpChain,
                downAxis,
                upAxis,
                endRotCtMatrix=endRotCtMatrix,
                upVector=upVector
            )

        #-----------------------------------------------------------|
        #-----------------------------------------------------------|    BL
        #-----------------------------------------------------------|

        hasTwists = numTopTwists or numBtmTwists

        with r.Name('blend' if hasTwists else 'bind'):
            blSystem = self._createBlendSystem(
                fkSystem,
                ikSystem
            )

        #-----------------------------------------------------------|
        #-----------------------------------------------------------|    TW
        #-----------------------------------------------------------|

        if hasTwists:
            with r.Name('bind'):
                twSystem = self._createTwistSystem(blSystem)

        #-----------------------------------------------------------|
        #-----------------------------------------------------------|    Finish
        #-----------------------------------------------------------|

        """
        Tag bind joints
        """
        raise NotImplementedError('Finish')

    #-------------------------------------------------------|
    #-------------------------------------------------------|    PARTIAL
    #-------------------------------------------------------|

    def _resolvePoints(self, points, bevelLength=None):
        num = len(points)

        if num is 3:
            if bevelLength is not None:
                points = _mo.bevelTriadPoints(points, bevelLength)

        elif num is 4:
            if bevelLength is not None:
                raise ValueError("bevelLengthling needs three points.")

            points = [r.data.Point(x) for x in points]

        else:
            raise ValueError("Provide three or four points.")

        return points

