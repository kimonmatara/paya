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
    def lock(self, recursive=False, **kwargs):
        """
        Overloads :class:`~pymel.core.general.Attribute` to implement the
        *recursive* option and return ``self``.

        :param bool recursive/r: if this is a compound, lock its children too;
            defaults to False
        :param \*\*kwargs: forwarded to
            :meth:`~pymel.core.general.Attribute.lock`
        :return: ``self``
        :rtype: :class:`~paya.plugtypes.attribute.Attribute`
        """
        p.Attribute.lock(self, **kwargs)

        if recursive:
            for child in self.getChildren():
                child.lock(**kwargs)

        return self

    @short(recursive='r', force='f')
    def unlock(self, recursive=False, force=False, **kwargs):
        """
        Overloads :class:`~pymel.core.general.Attribute` to implement the
        *recursive* and *force* options and return ``self``.

        :param bool recursive/r: if this is a compound, unlock the children
            too; defaults to False
        :param bool force/f: if this is the child of a compound, unlock the
            compound parent too; defaults to False
        :param \*\*kwargs: forwarded to
            :meth:`~pymel.core.general.Attribute.unlock`
        :return: ``self``
        :rtype: :class:`~paya.plugtypes.attribute.Attribute`
        """
        p.Attribute.unlock(self, **kwargs)

        if recursive:
            for child in self.getChildren():
                p.Attribute.unlock(child, **kwargs)

        return self

    @short(recursive='r')
    def hide(self, recursive=False):
        """
        Turns off *keyable* and *channelBox* for this attribute.

        :param bool recursive/r: if this is a compound, edit the children too;
            defaults to False
        :return: ``self``
        :rtype: :class:`~paya.plugtypes.attribute.Attribute`
        """
        r.plugs.Attribute.hide(self)

        if recursive:
            for child in self.getChildren():
                child.hide()

        return self

    @short(recursive='r', force='f')
    def release(self, recursive=False, force=False):
        """
        Unlocks this attribute and disconnects any inputs.

        :param bool force/f: if this is the child of a compound, unlock
            the parent too; defaults to False
        :param bool recursive/r: if this is a compound, release child attributes
            too; defaults to False
        :return:
        """
        r.plugs.Attribute.release(self)

        if recursive:
            for child in self.getChildren():
                child.release()

        return self

    @short(recursive='r', force='f')
    def show(self, recursive=False, force=False, **kwargs):
        """
        Unhides this attribute in the channel box.

        :param bool recursive/r: if this is a compound, edit the children
            as well; defaults to False
        :param bool force/f: if this is the child of a compound, edit the
            parent attribute too; defaults to False

        :param bool channelBox/cb: reveal by making the attribute settable
        :param bool keyable/k: reveal by making the attribute keyable
            (the default)
        :return: ``self``
        :rtype: :class:`~paya.plugtypes.attribute.Attribute`
        """
        r.plugs.Attribute.show(self)

        if recursive:
            for child in self.getChildren():
                r.plugs.Attribute.show(child, **kwargs)

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