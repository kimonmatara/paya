import maya.OpenMaya as om
import pymel.util as _pu
import pymel.core.nodetypes as _nt
import pymel.core.datatypes as _dt
import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r


class EulerRotation:

    #-----------------------------------------------------------|    Testing

    @short(name='n', rotateOrder='ro')
    def createLocator(self, name=None, rotateOrder='xyz'):
        """
        :shorthand: ``cl``

        :param name/n: one or more optional name elements; defaults to None
        :rtype name/n: None, list, int, str
        :param rotateOrder/ro: the rotate order of this euler rotation;
            defaults to 'xyz'
        :type rotateOrder/ro: int, str,
            :class:`~paya.plugtypes.attribute.Attribute`
        :return: A locator with this euler rotation piped into its
            ``rotate`` channels.
        :rtype: :class:`~paya.nodetypes.transform.Transform`
        """
        loc = r.nodes.Locator.createNode(n=name).getParent()
        rotateOrder >> loc.attr('ro')
        self >> loc.attr('r')

        return loc

    cl = createLocator

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

    def set(self, value, **kwargs):
        """
        Overloads :meth:`~paya.plugtypes.attribute.Attribute.get` to ensure
        that instances of :class:`~paya.datatypes.eulerRotation.EulerRotation`
        with units that don't match the UI setting are set correctly.
        """
        if isinstance(value, _dt.EulerRotation):
            currentUnit = om.MAngle.uiUnit()

            if currentUnit == om.MAngle.kRadians:
                if value.unit != 'radians':
                    value = _pu.radians(value)

            elif value.unit != 'degrees':
                value = _pu.degrees(value)

        return r.plugs.Math3D.set(self, value, **kwargs)

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