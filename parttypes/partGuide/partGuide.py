import re
import maya.cmds as m
from paya.util import uncap, int_to_letter, short
import paya.runtime as r


class PartGuide(r.parts.PartBase):

    #-----------------------------------------------------|    Create part

    @short(channelBox='cb',
           keyable='k',
           attributeType='at',
           defaultValue='dv')
    def addBuildSetting(self, name: str, defaultValue, **kwargs):
        """
        Convenience method. Adds a settable-only attribute to a
        'BUILD_SETTINGS' section on the group node. The *attributeType*
        can be omitted if *defaultValue* is :class:`float`, :class:`bool`
        or :class:`int`.

        :param str name: the attribute name
        :param defaultValue: the starting value for the attribute
        :param \*\*kwargs: forwarded to
            :class:`~paya.runtime.nodes.DependNode.addAttr`, except for
            *channelBox* / *keyable*, which will be overriden to ``True``
            and ``False`` respectively
        :return: The attribute.
        :rtype: :class:`~paya.runtime.plugs.Attribute`
        """
        if 'attributeType' not in kwargs:
            try:
                kwargs['attributeType'] = {
                    int: 'long',
                    bool: 'bool',
                    float: 'double'
                }[type(defaultValue)]
            except KeyError:
                raise RuntimeError(
                    "Could not derive an attribute type. "+
                    "Please pass it explicitly."
                )

        kwargs['channelBox'] = True
        kwargs['keyable'] = False
        kwargs['defaultValue'] = defaultValue

        node = self.node()
        if 'BUILD_SETTINGS' not in node.attrSections:
            node.attrSections.add('BUILD_SETTINGS')

        section = node.attrSections['BUILD_SETTINGS']
        out = node.addAttr(name, **kwargs)
        section.collect(name)
        return node.attr(name)

    def getBuildSettings(self):
        """
        :return: A mapping of ``{attrName: attrValue}`` for each attribute
            created using :meth:`addBuildSetting`.
        :rtype: :class:`dict`
        """
        node = self.node()
        out = {}

        if 'BUILD_SETTINGS' in node.attrSections:
            for attr in node.attrSections['BUILD_SETTINGS']:
                typ = attr.type()

                if typ in ['bool', 'double', 'long', 'int', 'float', 'enum']:
                    out[attr.attrName()] = attr.get()

                elif typ == 'enum':
                    out[attr.attrName()] = attr.get(asString=True)

        return out

    @classmethod
    def getPartClass(cls):
        """
        :return: The associated part subclass.
        :rtype: :class:`type`
        """
        clsname = re.match(r"^(.*)Guide$", cls.__name__).groups()[0]
        return getattr(r.parts, clsname)

    def getPartCreateArgsKwargs(self):
        """
        :raise NotImplementedError: Not implemented on this class.
        :return: Positional and keyword arguments that can be passed along
            to the ``create()`` method on the associated
            :class:`~paya.runtime.parts.Part` subclass.
        :rtype: (:class:`tuple`, :class:`dict`)
        """
        raise NotImplementedError

    def createPart(self):
        """
        Derives construction arguments from this guide and passed them along
        to ``create()`` on the associated :class:`~paya.runtime.parts.Part`
        subclass to build the part.

        If there is no active :class:`~paya.lib.names.Name` block, this guide's
        innermost namespace will be used for the name.

        :return: The constructed part.
        :rtype: :class:`~paya.runtime.parts.Part`
        """
        args, kwargs = self.getPartCreateArgsKwargs()
        partClass = self.getPartClass()

        if r.Name.__elems__:
            ctx = r.NullCtx()
        else:
            ns = self.node().namespace()

            if ns == ':':
                raise RuntimeError(
                    "Can't derive name elements for the new part.")

            elems = list(filter(bool, ns.split(':')))
            ctx = r.Name(elems[-1])

        with ctx:
            out = partClass.create(*args, **kwargs)

        return out

    #-----------------------------------------------------|    Construction

    @classmethod
    def _getCreateNameContext(cls):
        """
        Called before a build wrapped by
        :func:`~paya.part.partcreator.partCreator` to establish the naming
        environment.

        Guides are named according to these rules:

        -   The name element is always ``'guide'``; any enclosing blocks are
            ignored.
        -   There *must* be a namespace; if one is not active at the time of
            build, one will be derived, either from active
            :class:`~paya.lib.names.Name` elements or from the calling class
            name.

        :return: A configured context manager.
        :rtype: :class:`~paya.lib.names.Name`
        """
        nameArgs = ['guide']
        nameKwargs = {'inherit': False}

        currentNamespace = m.namespaceInfo(currentNamespace=True)

        if currentNamespace == ':':
            if r.Name.__elems__:
                targetNamespace = ':'+r.Name.make()
            else:
                mt = re.match(r"^(.*?)Guide$", cls.__name__)

                if mt:
                    targetNamespace = ':'+uncap(mt.groups()[0])
                else:
                    targetNamespace = uncap(cls.__name__)

            # Make the invented namespace unique
            num = 0

            while True:
                if num:
                    namespace = '{}_{}'.format(
                        targetNamespace, int_to_letter(num).upper())
                else:
                    namespace = targetNamespace

                if m.namespace(exists=namespace):
                    num += 1
                else:
                    break

            nameKwargs['namespace'] = namespace

        return r.Name(*nameArgs, **nameKwargs)