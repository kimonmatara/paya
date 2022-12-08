import paya.runtime as r
from paya.util import short

class UvPin:

    @classmethod
    @short(geometry='g', uvPairs='uvp')
    def create(cls, geometry=None, uvSet=None, uvPairs=None):
        node = cls.createNode()

        if geometry:
            geometry = r.PyNode(geometry)
            origPlug = geometry.getOrigPlug(create=True)
            origPlug >> node.attr('originalGeometry')
            geometry.worldGeoOutput >> node.attr('deformedGeometry')

            if uvSet is None:
                uvSet = geometry.getCurrentUVSetName()

        if uvSet:
            node.attr('uvSetName').set(uvSet)

        if uvPairs:
            for i, uvPair in enumerate(uvPairs):
                uvPair[0] >> node.attr('coordinate')[i].coordinateU
                uvPair[1] >> node.attr('coordinate')[i].coordinateV

        return node