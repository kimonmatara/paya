from paya.util import short
import pymel.core.datatypes as _dt
import paya.lib.typeman as _tm
import paya.runtime as r


class EulerRotation:

    #-----------------------------------------------------------|    Testing

    @short(name='n')
    def createLocator(self, name=None):
        """
        :shorthand: ``cl``

        :param str name/n: an optional name for the locator transform; defaults
            to a contextual name
        :return: A locator with this euler rotation piped into its
            ``rotate`` channels.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        if name is None:
            name = r.Name.make(nt='locator', xf=True)

        loc = r.spaceLocator(n=name)
        loc.attr('ro').set(self.order.lower())
        loc.attr('r').set(self)
        return loc

    cl = createLocator

    #-----------------------------------------------------------|    Addition

    def __add__(self, other):
        """
        Implements **addition** (``+``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__add__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.createNode()

                node.attr('input3D')[0].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[1]:
                        child.put(other, p=isplug)

                else:
                    node.attr('input3D')[1].put(other, p=isplug)

                return node.attr('output3D')

            else:
                return NotImplemented

        return _dt.EulerRotation.__add__(self, other)

    def __radd__(self, other):
        """
        Implements **reflected addition** (``+``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__radd__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.createNode()
                node.attr('input3D')[1].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[0]:
                        child.put(other, p=isplug)

                else:
                    node.attr('input3D')[0].put(other, p=isplug)

                return node.attr('output3D')

            else:
                return NotImplemented

        return _dt.EulerRotation.__radd__(self, other)
    
    #-----------------------------------------------------------|    Subtraction
    
    def __sub__(self, other):
        """
        Implements **subtraction** (``-``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__sub__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.createNode()
                node.attr('operation').set(2)

                node.attr('input3D')[0].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[1]:
                        child.put(other, p=isplug)

                else:
                    node.attr('input3D')[1].put(other, p=isplug)

                return node.attr('output3D')

            else:
                return NotImplemented

        return _dt.EulerRotation.__sub__(self, other)

    def __rsub__(self, other):
        """
        Implements **reflected subtraction** (``-``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__rsub__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.createNode()
                node.attr('operation').set(2)

                node.attr('input3D')[1].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[0]:
                        child.put(other, p=isplug)

                else:
                    node.attr('input3D')[0].put(other, p=isplug)

                return node.attr('output3D')

            else:
                return NotImplemented

        return _dt.EulerRotation.__rsub__(self, other)

    #-----------------------------------------------------------|    Multiplication

    def __mul__(self, other):
        """
        Implements **multiplication** (``*``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__mul__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('input1').set(self)

                if dim is 1:
                    for child in node.attr('input2'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input2').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.EulerRotation.__mul__(self, other)

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__rmul__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('input2').set(self)

                if dim is 1:
                    for child in node.attr('input1'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input1').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.EulerRotation.__rmul__(self, other)
    
    #-----------------------------------------------------------|    Division
    
    def __truediv__(self, other):
        """
        Implements **division** (``/``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__truediv__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('operation').set(2)
                node.attr('input1').set(self)

                if dim is 1:
                    for child in node.attr('input2'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input2').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.EulerRotation.__truediv__(self, other)

    def __rtruediv__(self, other):
        """
        Implements **reflected division** (``/``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__rtruediv__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('operation').set(2)
                node.attr('input2').set(self)

                if dim is 1:
                    for child in node.attr('input1'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input1').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.EulerRotation.__rtruediv__(self, other)
    
    #-----------------------------------------------------------|    Power

    def __pow__(self, other):
        """
        Implements **power** (``**``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__pow__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('operation').set(3)
                node.attr('input1').set(self)

                if dim is 1:
                    for child in node.attr('input2'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input2').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.EulerRotation.__pow__(self, other)

    def __rpow__(self, other):
        """
        Implements **reflected power** (``**``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__rpow__` to add
        support for 1D and 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.createNode()
                node.attr('operation').set(3)
                node.attr('input2').set(self)

                if dim is 1:
                    for child in node.attr('input1'):
                        child.put(other, p=isplug)

                else:
                    node.attr('input1').put(other, p=isplug)

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.EulerRotation.__rpow__(self, other)

    @short(rotateOrder='ro')
    def asRotateMatrix(self, rotateOrder=None):
        """
        :param rotateOrder/ro: override the rotate order; this doesn't perform
            any reordering, it merely treats the rotation differently when
            composing the matrix; defaults to None
        :type rotateOrder/ro: None, int, str
        :return: This euler rotation as a matrix.
        :rtype: :class:`~paya.runtime.data.Matrix`
        """
        if rotateOrder is None:
            return self.asMatrix()

        if isinstance(rotateOrder, str):
            rotateOrder = 'XYZ'

        elif isinstance(rotateOrder, int):
            rotateOrder = self.order.enumtype.keys()[rotateOrder]

        else:
            # Assume it's an EnumValue, cast it to string
            rotateOrder = str(rotateOrder)

        rotation = self.copy()
        rotation.order = rotateOrder

        return rotation.asMatrix()

    def copy(self):
        """
        Overloads the base :meth:`~pymel.core.datatypes.EulerRotation.copy` to
        include rotation order.

        :return: A copy of this euler rotation.
        :rtype: :class:`EulerRotation`.
        """
        out = _dt.EulerRotation.copy(self)
        out.order = self.order
        return out