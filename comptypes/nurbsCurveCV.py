from paya.util import short
import paya.runtime as r


class NurbsCurveCV:

    #-----------------------------------------------------|    Component management

    def isRange(self):
        """
        :return: True if this component represents a range.
        :rtype: bool
        """
        return len(self.indices()) > 1

    def __int__(self):
        """
        :raises ValueError: Can't return an integer because this instance
            represents a range of CVS.
        :return: The CV index.
        :rtype: int
        """
        if self.isRange():
            raise ValueError("CV is a range.")

        return self.indices()[0]

    #-----------------------------------------------------|    Sampling

    @short(plug='p')
    def getWorldPosition(self, plug=False):
        """
        :alias: ``gwp``
        :param bool plug/p: force a dynamic output; defaults to False
        :return: The world-space point position of the specified CV.
        """
        if self.isRange():
            raise ValueError("CV is a range.")

        return self.node().pointAtCV(self, p=plug)

    gwp = getWorldPosition

    #-----------------------------------------------------|    Clusters

    def cluster(self, **createFlags):
        """
        Clusters this CV.

        :param \*\*createFlags: forwarded to
            :meth:`paya.runtime.nodes.Cluster.create`.
        :return: The cluster node.
        :rtype: :class:`~paya.runtime.nodes.Cluster`
        """
        return r.nodes.Cluster.create(self, **createFlags)