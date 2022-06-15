import pymel.core.nodetypes as _nt
import pymel.core.datatypes as _dt
import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r


class EulerRotation:

    #-----------------------------------------------------------|    Getter

    @short(plug='p')
    def get(self, plug=False, **kwargs):
        """
        Overrides :meth:`~paya.plugtypes.attribute.Attribute.get` to return
        :class:`~paya.datatypes.eulerRotation.EulerRotation` values.
        """
        if plug:
            return self

        result = r.plugs.Attribute.get(self, **kwargs)

        if isinstance(result, _dt.Vector):
            return r.data.EulerRotation(result)

        return result

    def isRotateChannel(self):
        """
        :return: True if this is the ``rotate`` channel on a transform,
            otherwise False.
        :rtype: bool
        """
        return self.attrName(longName=True
            ) == 'rotate' and isinstance(self.node(), _nt.Transform)

    #-----------------------------------------------------------|    Conversions

    @short(rotateOrder='ro')
    def asQuaternion(self, rotateOrder='xyz'):
        """
        Returns this euler compound as a quaternion.

        :param rotateOrder/ro: the rotate order, defaults to 'xyz'
        :type rotateOrder/ro: :class:`Math1D`, str, int
        :return: The quaternion.
        :rtype: :class:`~paya.plugtypes.quaternion.Quaternion`
        """
        node = r.nodes.EulerToQuat.createNode()
        self >> node.attr('inputRotate')
        rotateOrder >> node.attr('inputRotateOrder')

        return node.attr('outputQuat')

    @short(rotateOrder='ro')
    def asRotateMatrix(self, rotateOrder='xyz'):
        """
        Returns this euler compound as a rotation matrix.

        :param rotateOrder/ro: the rotate order, defaults to 'xyz'
        :type rotateOrder/ro: :class:`Math1D`, str, int
        :return: A triple euler angle compound.
        :rtype: :class:`~paya.plugtypes.math3D.Math3D`
        """
        node = r.nodes.ComposeMatrix.createNode()
        self >> node.attr('inputRotate')
        rotateOrder >> node.attr('inputRotateOrder')

        return node.attr('outputMatrix')