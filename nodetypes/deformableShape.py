from paya.util import short
import paya.runtime as r


class DeformableShape:

    #-----------------------------------------------------------|    Abstract I/O

    @property
    def geoInput(self):
        raise NotImplementedError

    @property
    def worldGeoOutput(self):
        raise NotImplementedError

    @property
    def localGeoOutput(self):
        raise NotImplementedError

    #--------------------------------------------------------|    Plug interops

    @classmethod
    def getPlugClass(cls):
        """
        :return: The geometry attribute subclass associated with this shape.
        :rtype: :class:`~paya.runtime.plugs.Geometry`
        """
        # The following should not error
        return getattr(r.plugs, cls.__name__)

    #--------------------------------------------------------|    History management

    def deleteHistory(self):
        """
        Deletes history on this node.

        :return: ``self``
        :rtype: :class:`DeformableShape`
        """
        r.delete(self, constructionHistory=True)
        return self

    def hasHistory(self):
        """
        :return: True if this shape has history, otherwise False.
        :rtype: bool
        """
        return bool(self.geoInput.inputs())

    @short(create='c')
    def getOrigInput(self, create=False):
        """
        :param bool create/c: create the original geometry if it doesn't
            already exist
        :return: The output of the best candidate for an 'original geometry'
            in this shape's history, or None
        :rtype: :class:`~paya.runtime.plugs.Geometry`, None
        """
        result = r.deformableShape(self, og=True)[0]

        if result:
            return r.Attribute(result)

        if create:
            result = r.deformableShape(self, cog=True)
            return r.Attribute(result[0])

    @short(create='c')
    def getHistoryInput(self, create=False):
        """
        :param create/c: create a historical input if it doesn't already exist
        :return: The input into this shape, or None
        :rtype: :class:`~paya.runtime.plugs.Geometry`, None
        """
        inputs = self.geoInput.inputs(plugs=True)

        if inputs:
            return inputs[0]

        if create:
            return self.getOrigInput(create=True)