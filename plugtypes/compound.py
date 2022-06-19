from paya.util import short
import pymel.core as p
import paya.runtime as r


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

    #-----------------------------------------------------------------|    State management

    @short(recursive='r')
    def release(self, recursive=False):
        """
        Unlocks this attribute and disconnects any inputs.

        :param bool recursive/r: if this is a compound, release child attributes
            too; defaults to False
        :return:
        """
        r.plugs.Attribute.release(self)

        if recursive:
            for child in self.getChildren():
                child.release(r=True)

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