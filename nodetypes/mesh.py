import paya.runtime as r
from paya.util import short


class Mesh:

    #-----------------------------------------------------|    Abstract I/O

    @property
    def geoInput(self):
        return self.attr('inMesh')

    @property
    def worldGeoOutput(self):
        return self.attr('worldMesh')[0]

    @property
    def localGeoOutput(self):
        return self.attr('outMesh')

    #-----------------------------------------------------|    Attachments

    @short(name='n')
    def initUtilUVSet(self, name='rig_util'):
        """
        Creates an auto projected UV set for attachments etc.
        """
        if self.hasHistory():
            raise RuntimeError(
                "Can't create utility UV set on a mesh with history.")

        if name in self.getUVSetNames():
            r.warning("Utility UV set 'rig_util' already exists.")
            return self

        numFaces = self.numFaces()

        r.polyAutoProjection(
            '{}.f[:{}]'.format(self, numFaces-1),
            lm=0,
            pb=0,
            ibd=1,
            cm=1,
            l=2,
            sc=1,
            o=0,
            p=12,
            uvSetName=name,
            ps=0.2,
            ws=0,
            ch=False
        )

        r.select(cl=True)
        return self

    @short(uvSet='uvs',
           vertexIndices='vi',
           uvPairs='uvp')
    def initUVPin(self,
                  uvPairs=None,
                  vertexIndices=None,
                  uvSet=None):
        if uvSet is None:
            uvSet = self.getCurrentUVSetName()

        if vertexIndices is not None:
            uvPairs = []

            for vertexIndex in vertexIndices:
                point = r.pointPosition(self.comp('vtx')[vertexIndex], world=True)
                uv = self.getUVAtPoint(point, space='world', uvSet=uvSet)
                uvPairs.append(uv)

        return r.nodes.UvPin.create(
            geometry=self,
            uvPairs=uvPairs,
            uvSet=uvSet
        )