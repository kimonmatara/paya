import paya.runtime as r


class PointOnCurveInfo:

    #------------------------------------------------------|    Sampling

    def getBinormal(self):
        """
        Getter for the ``.binormal`` property.

        :return: The binormal.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """

        if self.hasAttr('upVector'):
            plug = self.attr('upVector')

            if plug.inputs():
                return plug

        else:
            plug = self.addVectorAttr('upVector')

        plug.unlock(recursive=True)

        tangent = self.attr('tangent')
        normal = self.attr('normal')

        tangent.cross(normal).normal() >> plug
        plug.lock()

        return plug

    binormal = property(fget=getBinormal)