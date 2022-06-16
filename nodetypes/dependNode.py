from paya.util import short
import paya.lib.names as _nm
import paya.runtime as r


class MakeName(object):

     def __get__(self, inst, instype):
        @short(name='n', inherit='i', suffix='s', padding='pad')
        def makeName(*elems, name=None,
                     inherit=True, suffix=True, padding=None):
            """
            Generates a context-appropriate Maya name. Results will vary
            depending on whether this method is called on a class or on a
            node instance.

            :param elems: one or more name elements, packed or unpacked
            :type elems: int, str
            :param name/n: pass-through for any elements provided via a
                ``name/n`` keyword argument; these will always be prepended;
                defaults to None
            :type name/n: None, str
            :param padding/pad: optional padding depth for any integers;
                defaults to None
            :type padding/pad: None, int
            :param bool inherit/i: inherit prefixes from
                :class:`~paya.lib.names.Name` blocks; defaults to True
            :param suffix/suf: optional override for ``config.autoSuffix``; if
                ``True``, apply suffixes; if ``False``, omit them; if a
                string, use it; defaults to None
            :type suffix/s: bool, str
            :return: The name.
            :rtype: str
            """
            kwargs = {'inherit': True, 'name': name, 'suffix': suffix}

            if inst:
                kwargs['node'] = inst

            else:
                kwargs['nodeType'] = instype.__melnode__

            return _nm.make(*elems, **kwargs)

        return makeName


class DependNode:

    #-----------------------------------------------------------|    Name management

    makeName = MakeName()

    #-----------------------------------------------------------|    Constructors

    @classmethod
    def createNode(cls, **nameOptions):
        """
        Object-oriented version of :func:`pymel.core.general.createNode` with
        managed naming.

        :param \*\*nameOptions: passed-through to :meth:`~DependNode.makeName`
        :return: The constructed node.
        :rtype: :class:`DependNode`
        """
        return r.createNode(cls.__melnode__, n=cls.makeName(**nameOptions))