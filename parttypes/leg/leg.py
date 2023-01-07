import paya.runtime as r
from paya.util import short
from paya.config import takeUndefinedFromConfig, undefined
from paya.lib.mathops import flipAxis


class Leg(r.parts.Triad):

    @classmethod
    @takeUndefinedFromConfig
    def createChain(cls,
                    points,
                    upVector,
                    downAxis=undefined,
                    upAxis=undefined,
                    parent=None,
                    ikJitter=False,
                    opposite=False):
        """
        Creates a skeletal chain for a leg. The chain will comprise joints
        for the following:

            [0] hip
            [1] knee
            [2] ankle
            [3] ball of foot
            [4] toe tip

        :param points: five points (one for each joint); excess points will be
            discarded
        :type points: :class:`list` [:class:`list` [:class:`float`] |
            :class:`~paya.runtime.data.Point` |
            :class:`~paya.runtime.data.Vector`]
        :param upVector: the main up vector hint for the chain; this will
            guide cross product calculations to resolve orientations for
            the main bend axis
        :param str downAxis: the 'bone' axis; defaults to
            ``paya.config.downAxis``
        :param str upAxis: the axis to map to the up vector; defaults to
            ``paya.config.upAxis``
        :param parent: an optional destination parent for the chain;
            defaults to ``None``
        :type parent: ``None``, :class:`str`,
            :class:`~paya.runtime.nodes.Transform`
        :param bool opposite: flips the (resolved) down axis; defaults to
            ``False``
        :return: The generated chain.
        :rtype: :class:`Chain`
        """
        #--------------------------------------|    Init

        if len(points) < 5:
            raise ValueError("Need five points.")

        points = list(points)[:5]
        upVector = r.data.Vector(upVector)

        if opposite:
            downAxis = flipAxis(downAxis)

        #--------------------------------------|    Build triad

        triad = r.Chain.createFromPoints(
            points[:3],
            upVector,
            downAxis=downAxis,
            upAxis=upAxis,
            parent=parent
        )

        if ikJitter:
            triad.autoPreferredAngle(upVector)

        #--------------------------------------|    Build foot

        foot = r.Chain.createFromPoints(
            points[2:5],
            upVector,
            downAxis=downAxis,
            upAxis=upAxis,
            parent=parent
        )

        #--------------------------------------|    Overlap them

        out = triad.copy()
        out.appendChain(foot)
        out.rename()

        return out