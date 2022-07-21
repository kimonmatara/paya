class Lattice:

    #-----------------------------------------------------|    Abstract I/O

    @property
    def geoInput(self):
        return self.attr('latticeInput')

    @property
    def worldGeoOutput(self):
        return self.attr('worldLattice')

    @property
    def localGeoOutput(self):
        return self.attr('latticeOutput')