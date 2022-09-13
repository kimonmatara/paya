import maya.OpenMaya as om
import pymel.util as _pu
import pymel.core.nodetypes as _nt
import pymel.core.datatypes as _dt
from paya.util import short
import paya.runtime as r


class EulerRotation:

    #-----------------------------------------------------------|    Testing

    @short(name='n', rotateOrder='ro', size='siz')
    def createLocator(self, name=None, rotateOrder='xyz', size=1.0):
        """
        :shorthand: ``cl``

        :param str name/n: an optional name for the locator transform;
            defaults to a contextual name
        :param rotateOrder/ro: the rotate order of this euler rotation;
            defaults to 'xyz'
        :type rotateOrder/ro: int, str,
            :class:`~paya.runtime.plugs.Attribute`
        :return: A locator with this euler rotation piped into its
            ``rotate`` channels.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        if not name:
            name = r.Name.make(nt='locator', xf=True)

        loc = r.spaceLocator(n=name)
        rotateOrder >> loc.attr('ro')
        self >> loc.attr('r')
        loc.attr('localScale').set([size]*3)

        return loc

    cl = createLocator

    #-----------------------------------------------------------|    Getter

    @short(plug='p')
    def get(self, plug=False, **kwargs):
        """
        Overrides :meth:`~paya.runtime.plugs.Attribute.get` to return
        :class:`~paya.runtime.data.EulerRotation` values. If this is the
        ``rotate`` channel on a transform node, rotation order is taken
        from the transform.
        """
        if plug:
            return self

        result = r.plugs.Attribute.get(self, **kwargs)

        if isinstance(result, _dt.Vector):
            rotation = r.data.EulerRotation(result)
            node = self.node()

            if isinstance(node, _nt.Transform):
                if self.attrName() == 'r':
                    order = node.attr(
                        'rotateOrder').get(asString=True).upper()
                    rotation.order = order

            return rotation

        return result

    def set(self, *args, **kwargs):
        """
        Overloads :meth:`~paya.runtime.plugs.Attribute.get` to ensure
        that instances of :class:`~paya.runtime.data.EulerRotation`
        with units that don't match the UI setting are set correctly.
        """
        if args:
            value = args[0]

            if isinstance(value, _dt.EulerRotation):
                currentUnit = om.MAngle.uiUnit()

                if currentUnit == om.MAngle.kRadians:
                    if value.unit != 'radians':
                        value = _pu.radians(value)

                elif value.unit != 'degrees':
                    value = _pu.degrees(value)

                args = [value]

        r.plugs.Math3D.set(self, *args, **kwargs)

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
        :rtype: :class:`~paya.runtime.plugs.Quaternion`
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
        :rtype: :class:`~paya.runtime.plugs.Math3D`
        """
        node = r.nodes.ComposeMatrix.createNode()
        self >> node.attr('inputRotate')
        rotateOrder >> node.attr('inputRotateOrder')

        return node.attr('outputMatrix')