import pymel.core as p


class Compound:

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