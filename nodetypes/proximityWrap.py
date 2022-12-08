import paya.runtime as r
from paya.util import short
import maya.internal.nodes.proximitywrap.cmd_create as cmd_create
import maya.internal.nodes.proximitywrap.node_interface as node_interface


class ProximityWrap:

    @classmethod
    @short(name='n',
           masters='m',
           slaves='s',
           wrapMode='wmd',
           falloffScale='sfo',
           dropoffRateScale='sdpo',
           smoothInfluences='sinf',
           smoothNormals='snrm',
           softNormalization='sftn')
    def create(
            cls,
            name=None,
            masters=None,
            slaves=None,
            wrapMode='Surface',
            falloffScale=1.0,
            dropoffRateScale=0.0,
            smoothInfluences=0,
            smoothNormals=0,
            softNormalization=False
    ):
        r.select(cl=True)
        node = r.PyNode(cmd_create.Command().command(name=name)[0])

        if name is None:
            name = r.nodes.ProximityWrap.makeName()

        node.rename(name)

        wrapMode >> node.attr('wrapMode')
        falloffScale >> node.attr('falloffScale')
        dropoffRateScale >> node.attr('dropoffRateScale')
        smoothInfluences >> node.attr('smoothInfluences')
        smoothNormals >> node.attr('smoothNormals')
        softNormalization >> node.attr('softNormalization')

        if masters:
            node.addMasters(masters)

        if slaves:
            node.addSlaves(slaves)

        return node

    def addMasters(self, shapes):
        shapes = [str(r.pn(x).toShape()) for x in r.util.expandArgs(shapes)]
        ni = node_interface.NodeInterface(str(self))
        ni.addDrivers(shapes)

    def addSlaves(self, shapes):
        shapes = [str(r.pn(x).toShape()) for x in r.util.expandArgs(shapes)]
        ni = node_interface.NodeInterface(str(self))
        ni.addShapesToDeformer(shapes)