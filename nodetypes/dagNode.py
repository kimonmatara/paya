import paya.runtime as r
from paya.util import short
import paya.lib.names as _nm


class DagNode:

    #-----------------------------------------------------------|    Sampling

    @property
    def getWorldMatrix(self):
        return self.attr('wm').get

    gwm = getWorldMatrix

    @short(plug='p')
    def getWorldPosition(self, plug=False):
        """
        Returns the world translation of this DAG node.

        :shorthand: ``gwp``
        :param bool plug/p: return an attribute instead of a value; defaults
            to False
        :return: The position attribute or value.
        :rtype: :class:`~paya.datatypes.point.Point` or
           :class:`~paya.plugtypes.vector.Vector`
        """
        return self.getWorldMatrix(p=plug).t

    gwp = getWorldPosition

    #-----------------------------------------------------------|    Name management

    @short(
        stripNamespace='sns',
        stripTypeSuffix='sts',
        stripDagPath='sdp'
    )
    def basename(
            self,
            stripNamespace=False,
            stripTypeSuffix=False,
            stripDagPath=True
    ):
        """
        Returns shorter versions of this node's name.

        :param bool stripNamespace/sns: remove namespace information; defaults to
            False
        :param bool stripDagPath/sdp: remove DAG path information; defaults to
            True
        :param bool stripTypeSuffix/sts: removes anything that looks like a type
            suffix; defaults to False
        :return: the modified name
        :rtype: str
        """
        return _nm.shorten(
            str(self),
            sns=stripNamespace,
            sts=stripTypeSuffix,
            sdp=stripDagPath
        )

    bn = basename