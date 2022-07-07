import pymel.util as _pu
import paya.runtime as r


class GeometryFilter:

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