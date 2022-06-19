import pymel.core as p


class Compound:

    #-----------------------------------------------------------------|    Connection management

    def splitInputs(self):
        """
        Splits any compound-level input into per-child connections. The
        compound-level connection is maintained.

        :return: ``self``
        """
        inputs = self.inputs(plugs=True)

        if inputs:
            input = inputs[0]

            srcChildren = input.getChildren()
            destChildren = self.getChildren()

            for srcChild, destChild in zip(srcChildren, destChildren):
                srcChild >> destChild

        return self

    #-----------------------------------------------------------------|    Iteration

    def __iter__(self):
        """
        Extends iteration to compounds. If this is a compound AND a multi,
        array iteration will take precedence. In those cases, use
        :meth:`~pymel.core.general.Attribute.getChildren` to disambiguate.
        """
        if self.isMulti():
            return p.Attribute.__iter__(self)

        return iter(self.getChildren())