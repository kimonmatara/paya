from functools import wraps

import maya.cmds as m
import pymel.core as p
import paya.lib.names as _nm


def partCreator(f):
    @wraps(f)
    def wrapped(cls, *args, **kwargs):
        with cls._getCreateNameContext():
            with _nm.Name(suffix=cls.__suffix__):
                groupNode = cls.createNode()
            self = cls(groupNode)

            with p.NodeTracker() as tracker:
                result = f(self, *args, **kwargs)
                self._postCreate()

            allNodes = tracker.getNodes()
            groupNode.tag('dependencies', allNodes)

            xforms = [node for node in allNodes \
                if isinstance(node, p.nodetypes.Transform)]

            orphans = [xform for xform in xforms if not xform.getParent()]

            if orphans:
                p.parent(orphans, groupNode)

            return cls(groupNode)

    return classmethod(wrapped)