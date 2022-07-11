class NurbsSurface:

    #-----------------------------------------------------|    Abstract I/O

    @property
    def geoInput(self):
        return self.attr('create')

    @property
    def worldGeoOutput(self):
        return self.attr('worldSpace')[0]

    @property
    def localGeoOutput(self):
        return self.attr('local')