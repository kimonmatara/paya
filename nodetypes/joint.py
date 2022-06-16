from paya.util import short
import paya.runtime as r


class Joint:

    #------------------------------------------------------------|    Constructor

    @classmethod
    @short(
        displayLocalAxis='dla',
        worldMatrix='wm',
        under='u',
        name='n',
        inherit='i',
        suffix='s'
    )
    def create(
            cls,
            displayLocalAxis=True,
            worldMatrix=None,
            under=None,
            name=None,
            inherit=True,
            suffix=True
    ):
        joint = cls.createNode(n=name, i=inherit, s=suffix)

        if under:
            joint.setParent(under)

        if worldMatrix:
            joint.setMatrix(worldMatrix, worldSpace=True)
            r.makeIdentity(joint, apply=True, r=True, jo=False)

        if displayLocalAxis:
            joint.attr('dla').set(True)

        return joint

    #------------------------------------------------------------|    Inspections

    def skinClusters(self):
        """
        :return: All the skinClusters this joint participates in, in no
            particular order.
        :rtype: list
        """
        outputs = self.attr('worldMatrix'
                            )[0].outputs(plugs=True, type='skinCluster')

        out = []

        for output in outputs:
            if output.attrName() == 'ma':
                out.append(output.node())

        return list(set(out))

    #------------------------------------------------------------|    Chain

    def chainFromHere(self, end=None):
        """
        :param end: an optional end joint
        :type end: str or :class:`~paya.nodetypes.joint.Joint`
        :return: A chain from this joint up to and including 'end'
            (if provided), or terminating before the first branch.
        :rtype: :class:`~paya.lib.skel.Chain`
        """
        if end:
            return r.Chain.getFromStartEnd(self, end)

        return r.Chain.getFromRoot(self)