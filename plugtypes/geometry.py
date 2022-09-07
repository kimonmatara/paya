import maya.OpenMaya as om
from paya.util import short
import paya.runtime as r


class Geometry:

    #---------------------------------------------------------|    Shape management

    @short(
        name='n',
        parent='p',
        intermediate='i',
        conformShapeName='csn'
    )
    def createShape(
            self,
            name=None,
            parent=None,
            intermediate=False,
            conformShapeName=None
    ):
        """
        Creates a shape node and connects this geometry output into its input.

        :param str name/n: a name for the shape; defaults to ``None``
        :param parent/p: a transform parent for the new shape; a new transform
            will be generated if this is omitted
        :type parent/p: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool intermediate/i: make the shape an intermediate objects;
            defaults to False
        :param bool conformShapeName/csn: ignored if *parent* was omitted;
            rename the shape after it is reparented; defaults to True if
            *parent* was provided, otherwise False
        :return: The new shape.
        :rtype: :class:`~paya.runtime.nodes.Shape`
        """
        # Get the namesake shape class
        clsname = self.__class__.__name__
        cls = getattr(r.nodes, clsname)
        nodeType = cls.__melnode__

        # Create the shape node; this will be nested under a transform we may
        # or may not keep

        shape = cls.createShape(n=name,
                                p=parent,
                                csn=conformShapeName,
                                i=intermediate)

        self >> shape.geoInput

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
        try:
            return getattr(self, '_shapeMFn')

        except AttributeError:
            # This will crash if called on a root array mplug, so force an
            # index

            if self.isArray():
                plug = self[0]

            else:
                plug = self

            plug.evaluate()
            mplug = plug.__apimplug__()
            handle = mplug.asMDataHandle()
            mobj = handle.data()

            mfnClass = getattr(om, 'MFn'+self.__class__.__name__)
            self._shapeMFn = out = mfnClass(mobj)

            return out

    #---------------------------------------------------------|    Geometry filtering

    @short(invertTransform='itf', freezeNormals='fn')
    def transform(self, matrix, invertTransform=False, freezeNormals=0):
        """
        Transforms this geometry by the specified matrix and returns the result.

        :param matrix: the matrix to use
        :param bool invertTransform/itf: invert the transform; defaults to
            False
        :param freezeNormals/fn: a setting for the 'freezeNormals'
            attribute on ``transformGeometry``. This should be an integer
            index or an enum label. The available settings are:

            0: 'Never'
            1: 'Always'
            2: 'Non-rigid Transformations Only'

            Defaults to 0 ('Never').
        :type freezeNormals/fn: str, int
        :return: The transformed geometry.
        :rtype: :class:`~paya.runtime.plugs.Geometry`
        """
        node = r.nodes.TransformGeometry.createNode()
        self >> node.attr('inputGeometry')

        node.attr('freezeNormals').set(freezeNormals)
        node.attr('invertTransform').set(invertTransform)
        matrix >> node.attr('transform')

        return node.attr('outputGeometry').setClass(self.__class__)