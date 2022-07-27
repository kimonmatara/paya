import paya.runtime as r


class ClusterHandle:

    #---------------------------------------------------------|    Navigation

    def getClusterNode(self):
        """
        :return: The associated cluster node.
        :rtype: :class:`~paya.runtime.nodes.Cluster`
        """
        return self.attr('clusterTransforms').outputs(type='cluster')[0]

    #---------------------------------------------------------|    Misc edits

    def resetVisualOrigin(self):
        """
        Edits the 'origin' so that it overlaps the weighted node's
        rotate pivot.

        :return: ``self``
        :rtype: :class:`ClusterHandle`
        """
        wn = self.getClusterNode().getHandle()
        realPosition = r.data.Point(
            r.xform(wn, q=True, rp=True, ws=True, a=True))
        wmtx = wn.getMatrix(worldSpace=True)
        rpmtx = realPosition.asTranslateMatrix()
        tmtx = wmtx.pick(t=True)
        posmtx = rpmtx * tmtx.inverse()
        rsmtx = wmtx.pick(t=False)
        mtx = rsmtx * posmtx

        point = r.data.Point() ^ mtx.inverse()
        self.attr('origin').set(-point)

        return self