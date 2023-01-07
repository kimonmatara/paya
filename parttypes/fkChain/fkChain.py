import paya.runtime as r
from paya.lib.mathops import flipAxis
from paya.config import takeUndefinedFromConfig, undefined


class FkChain(r.parts.Part):
    """
    Stub. Right now, it only implements :meth:`createChain`.
    """

    @classmethod
    @takeUndefinedFromConfig
    def createChain(cls,
                    points,
                    upVector,
                    downAxis=undefined,
                    upAxis=undefined,
                    tipMatrix=None,
                    opposite=False,
                    parent=None):
        """
        Thin wrapper for :meth:`paya.lib.skel.Chain.createFromPoints`.

        :param points: a world position for each joint; at least two points
            are required
        :type points: :class:`list` [:class:`list` [:class:`float`] |
            :class:`~paya.runtime.data.Point` |
            :class:`~paya.runtime.data.Vector`]
        :param str downAxis: the 'bone' axis; defaults to
            ``paya.config.downAxis``
        :param str upAxis: the axis to map to the up vector; defaults to
            ``paya.config.upAxis``
        :param tipMatrix/tm: an optional rotation matrix override for the tip
            (end) joint; if provided, only orientation information will be
            used; defaults to ``None``
        :param bool opposite: flips the (resolved) down axis; defaults to
            ``False``
        :param parent: an optional destination parent for the chain;
            defaults to ``None``
        :type parent: ``None``, :class:`str`,
            :class:`~paya.runtime.nodes.Transform`
        :return: The generated chain.
        :rtype: :class:`Chain`
        """
        #--------------------------------------|    Init

        if len(points) < 2:
            raise ValueError("Need at least two points.")

        if opposite:
            downAxis = flipAxis(downAxis)

        #--------------------------------------|    Build

        return r.Chain.createFromPoints(
            points,
            upVector,
            downAxis=downAxis,
            upAxis=upAxis,
            parent=parent,
            tipMatrix=tipMatrix
        )