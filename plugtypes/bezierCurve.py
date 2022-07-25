import maya.OpenMaya as om
import paya.runtime as r


class BezierCurve:

    #----------------------------------------------------|    Analysis

    def getShapeMFn(self):
        """
        Returns an API function set for the shape type associated with this
        plug, initialised around the MObject of the data block. Useful for
        performing spot inspections (like ``numCVs()`` on a curve output)
        without creating a shape.

        :return: The function set.
        :rtype: :class:`~maya.OpenMaya.MFnDagNode`
        """
        # This will crash if called on a root array mplug, so force an index

        if self.isArray():
            plug = self[0]

        else:
            plug = self

        mplug = plug.__apimplug__()
        handle = mplug.asMDataHandle()
        mobj = handle.data()

        return om.MFnNurbsCurve(mobj)
