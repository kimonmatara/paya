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
        :type rotateOrder/ro: :class:`int`, :class:`str`,
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

        if isinstance(result, r.datatypes.Vector):
            rotation = r.data.EulerRotation(result)
            node = self.node()

            if isinstance(node, r.nodetypes.Transform):
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

            if isinstance(value, r.datatypes.EulerRotation):
                currentUnit = om.MAngle.uiUnit()

                if currentUnit == om.MAngle.kRadians:
                    if value.unit != 'radians':
                        value = _pu.radians(value)

                elif value.unit != 'degrees':
                    value = _pu.degrees(value)

                args = [value]

        r.plugs.Vector.set(self, *args, **kwargs)

    def isTranslateChannel(self):
        """
        :return: True if this is the ``translate`` channel of a transform
            node, otherwise False.
        :rtype: bool
        """
        return False

    def isRotateChannel(self):
        """
        :return: True if this is the ``rotate`` channel on a transform,
            otherwise False.
        :rtype: bool
        """
        return self.attrName(longName=True
            ) == 'rotate' and isinstance(self.node(), r.nodetypes.Transform)

    #-----------------------------------------------------------|    Conversions

    @short(rotateOrder='ro')
    def reorder(self, newRotateOrder, rotateOrder='xyz'):
        """
        :param newRotateOrder: The new rotate order, e.g. ``'yxz'``.
        :type newRotateOrder: :class:`str`, :class:`int`,
            :class:`~paya.runtime.plugs.Math1D`
        :param rotateOrder/ro: The old rotate order; defaults to ``'xyz'``
        :type rotateOrder/ro: :class:`str`, :class:`int`,
            :class:`~paya.runtime.plugs.Math1D`
        :return: The reordered euler rotation.
        :rtype: :class:`EulerRotation`
        """
        quat = self.asQuaternion(rotateOrder=rotateOrder)
        return quat.asEulerRotation(newRotateOrder)

    @short(rotateOrder='ro')
    def asQuaternion(self, rotateOrder='xyz'):
        """
        :param rotateOrder/ro: the rotate order, defaults to 'xyz'
        :type rotateOrder/ro: :class:`Math1D`, str, int
        :return: A quaternion representation of this euler rotation.
        :rtype: :class:`~paya.runtime.plugs.Quaternion`
        """
        node = r.nodes.EulerToQuat.createNode()
        self >> node.attr('inputRotate')
        rotateOrder >> node.attr('inputRotateOrder')

        return node.attr('outputQuat')

    @short(rotateOrder='ro')
    def asAxisAngle(self, rotateOrder='xyz'):
        """
        :param rotateOrder/ro: this output's rotate order
        :type rotateOrder/ro: :class:`str`, :class:`int`,
            :class:`~paya.runtime.plugs.Math1D`
        :return: An axis-angle representation of this euler rotation.
        :rtype: :class:`tuple` (:class:`Vector`, :class:`Angle`)
        """
        quat = self.asQuaternion(ro=rotateOrder)
        return quat.asAxisAngle()

    @short(rotateOrder='ro')
    def asRotateMatrix(self, rotateOrder='xyz'):
        """
        :param rotateOrder/ro: the rotate order, defaults to 'xyz'
        :type rotateOrder/ro: :class:`Math1D`, str, int
        :return: This euler rotation as a matrix.
        :rtype: :class:`~paya.runtime.plugs.Math3D`
        """
        node = r.nodes.ComposeMatrix.createNode()
        self >> node.attr('inputRotate')
        rotateOrder >> node.attr('inputRotateOrder')

        return node.attr('outputMatrix')

    def asEulerRotation(self):
        """
        Overrides :meth:`~paya.runtime.plugs.Vector.asEulerRotation` to
        return ``self``.
        """
        return self