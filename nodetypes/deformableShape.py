from paya.util import short
import paya.runtime as r


class DeformableShape:

    #--------------------------------------------------------|    History management

    def hasHistory(self):
        """
        :return: True if this shape has history, otherwise False.
        :rtype: bool
        """
        return bool(self.geoInput.inputs())

    @short(create='c')
    def getOriginalGeometry(self, create=False):
        """
        :param bool create/c: create the original geometry if it doesn't
            already exist
        :return: The output of the best candidate for an 'original geometry'
            in this shape's history.
        :rtype: :class:`~paya.runtime.plugs.Geometry`
        """
        result = r.deformableShape(self, og=True)[0]

        if result:
            return r.Attribute(result)

        if create:
            result = r.deformableShape(self, cog=True)
            return r.Attribute(result[0])