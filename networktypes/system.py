import maya.cmds as m
from paya.util import short
import paya.runtime as r


class System:

    #------------------------------------------------|
    #------------------------------------------------|    ACCESSOR(S)
    #------------------------------------------------|

    @classmethod
    @short(exactType='et', checkNodeType='cnt')
    def matchesType(cls, network, exactType=False, checkNodeType=True):
        """
        :param network: The network node to inspect.
        :type network: :class:`str`, :class:`~paya.runtime.nodes.Network`
        :param bool checkNodeType: check that *network* is actually a network
            node; set this to ``False`` if you know this already; defaults to
            ``True``
        :param bool exactType/et: match the exact class only, excluding
            subclasses; defaults to ``False``
        :return: ``True`` if *network* matches this class or a subclass of this
            class.
        :rtype: :class:`bool`
        """
        network = str(network)

        if checkNodeType:
            if not(m.nodeType(network) == 'network'):
                raise RuntimeError('Not a network node: {}'.format(network))

        attr = '{}.payaSubtype'.format(network)

        if m.objExists(attr):
            val = m.getAttr(attr)

            refCls = getattr(r.networks, cls.__name__)

            if val:
                cls = getattr(r.networks, val)

                if exactType and cls is refCls:
                    return True

                elif issubclass(cls, refCls):
                    return True

        return False

    @classmethod
    def getAll(cls, exactType=False):
        """
        :param bool exactType/et: match the exact class only, excluding
            subclasses; defaults to ``False``
        :return: All ``network`` nodes in the scene whose ``payaSubtype``
            attribute is set to this class or a subclass of this class.
        :rtype: :class:`list` [:class:`System`]
        """
        return [r.PyNode(node).asSubtype() for node \
                in m.ls(type='network') if cls.matchesType(node, cnt=False)]