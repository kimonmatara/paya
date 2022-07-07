import pymel.util as _pu
import paya.runtime as r


class GeometryFilter:

    __config_attrs__ = None # used by getSettings(); if None,
                            # NotImplementedError will be raised

    #----------------------------------------------------|    Loader

    @classmethod
    def getFromGeo(cls, *geometry):
        """
        :param \*geometry: the geometries to inspect
        :type \*geometry: list, tuple,
            :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.DeformableShape`,
        :return: Deformers of this type detected across the specified
            geometries.
        :rtype: [:class:`~paya.runtime.nodes.GeometryFilter`]
        """
        out = []
        geos = list(map(r.PyNode, _pu.expandArgs(*geometry)))

        if not geos:
            raise RuntimeError("No geometries specified.")

        shapes = [geo.toShape() for geo in geos]

        for shape in shapes:
            history = shape.history(type=cls.__melnode__)

            if history:
                for deformer in history:
                    assocGeo = r.deformer(deformer, q=True, g=True)

                    if assocGeo:
                        assocGeo = map(r.PyNode, assocGeo)
                        if any([shape in shapes for shape in assocGeo]):
                            out.append(deformer)

        _out = []

        for item in out:
            if item not in _out:
                _out.append(item)

        return _out

    #----------------------------------------------------|    Macros etc.

    def getSettings(self):
        """
        :raises NotImplementedError: the deformer class does not define
            ``__config_attrs__``
        :return: configuration values for this deformer, as a mapping of
            *attribute name: attribute value*
        :rtype: dict
        """
        attrNames = self.__config_attrs__

        if attrNames is None:
            raise NotImplementedError("Not implemented for this deformer.")

        return {attrName: self.attr(attrName).get() for attrName in attrNames}

    def applySettings(self, settings):
        """
        :param dict settings: a dictionary returned by :meth:`getSettings`
        :return: ``self``
        :rtype: :class:`GeometryFilter`
        """
        for attrName, attrValue in settings.items():
            self.attr(attrName).set(attrValue)

        return self