class Mesh:

    #-----------------------------------------------------|    Abstract I/O

    @property
    def geoInput(self):
        return self.attr('inMesh')

    @property
    def worldGeoOutput(self):
        return self.attr('worldMesh')

    @property
    def localGeoOutput(self):
        return self.attr('outMesh')