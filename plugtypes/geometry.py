import maya.OpenMaya as om
from paya.util import short
import paya.runtime as r


class Geometry:

    #---------------------------------------------------------|    Shape management

    @short(
        under='u',
        intermediate='i',
        name=None,
        conformShapeNames='csn'
    )
    def createShape(
            self,
            name=None,
            under=None,
            intermediate=False,
            conformShapeNames=True
    ):
        """
        Creates a shape node and connects this geometry output into its input.

        :param name/n: one or more name elements
        :type name/n: None, str, int, list, tuple
        :param under/u: a transform parent for the new shape; a new transform
            will be generated if this is omitted
        :type under/u: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool intermediate/i: make the shape an intermediate objects;
            defaults to False
        :param bool conformShapeNames/csn: ignored if 'under' is None; run a
            conform on the destination transform's shapes after reparenting;
            defaults to True
        :return: The new shape.
        :rtype: :class:`~paya.runtime.nodes.Shape`
        """
        clsname = self.__class__.__name__
        nodeType = clsname[0].lower() + clsname[1:]

        shape = r.createNode(nodeType)
        self >> shape.geoInput

        if intermediate:
            shape.attr('intermediateObject').set(True)

        xf = shape.getParent()

        doRename = not(under and conformShapeNames)

        if doRename:
            name = shape.__class__.makeName(n=name)
            xf.rename(name)

        if under:
            r.parent(shape, under, r=True, shape=True)
            r.delete(xf)

            if conformShapeNames:
                r.PyNode(under).conformShapeNames()

        return shape

    def getShapeMFn(self):
        """
        Returns an API function set for the shape type associated with this
        plug, initialised around the MObject of the data block. Useful for
        performing spot inspections (like ``numCVs()`` on a curve output)
        without creating a shape.

        :return: The function set.
        :rtype: :class:`~maya.OpenMaya.MFnDagNode`
        """
        mplug = self.__apimplug__()
        handle = mplug.asMDataHandle()
        mobj = handle.data()

        mfnClass = getattr(om, 'MFn'+self.__class__.__name__)
        return mfnClass(mobj)