import paya.runtime as r


class PointOnCurveInfo:

    #------------------------------------------------------|    Sampling

    def getUpVectorOutput(self):
        """
        Getter for the ``.upVector`` / ``.upv`` property.

        Initialises, or retrieves, a vector that's perpendicular to the
        normal, and closer to what it intuitively meant as an 'up' vector
        on curves.

        :return: The up vector.
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

    upVector = property(fget=getUpVectorOutput)