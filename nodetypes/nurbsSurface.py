class NurbsSurface:

    #-----------------------------------------------------|    Abstract I/O

    @property
    def geoInput(self):
        return self.attr('create')

    @property
    def worldGeoOutput(self):
        return self.attr('worldSpace')

    @property
    def localGeoOutput(self):
        return self.attr('local')