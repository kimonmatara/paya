import pymel.core.datatypes as _dt
import paya.lib.mathops as _mo
import paya.runtime as r


class EulerRotation:

    #-----------------------------------------------------------|    Addition

    def __add__(self, other):
        """
        Implements **addition** (``+``).

        Overloads :meth:`pymel.core.datatypes.EulerRotation.__add__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.make()

                node.attr('input3D')[0].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[1]:
                        other >> child

                else:
                    other >> node.attr('input3D')[1]

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
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.make()

                node.attr('input3D')[1].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[0]:
                        other >> child

                else:
                    other >> node.attr('input3D')[0]

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
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.make()
                node.attr('operation').set(2)

                node.attr('input3D')[0].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[1]:
                        other >> child

                else:
                    other >> node.attr('input3D')[1]

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
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.PlusMinusAverage.make()
                node.attr('operation').set(2)

                node.attr('input3D')[1].set(self)

                if dim is 1:
                    for child in node.attr('input3D')[0]:
                        other >> child

                else:
                    other >> node.attr('input3D')[0]

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
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.make()
                node.attr('input1').set(self)

                if dim is 1:
                    for child in node.attr('input2'):
                        other >> child

                else:
                    other >> node.attr('input2')

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
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.make()
                node.attr('input2').set(self)

                if dim is 1:
                    for child in node.attr('input1'):
                        other >> child

                else:
                    other >> node.attr('input1')

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
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.make()
                node.attr('operation').set(2)
                node.attr('input1').set(self)

                if dim is 1:
                    for child in node.attr('input2'):
                        other >> child

                else:
                    other >> node.attr('input2')

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
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.make()
                node.attr('operation').set(2)
                node.attr('input2').set(self)

                if dim is 1:
                    for child in node.attr('input1'):
                        other >> child

                else:
                    other >> node.attr('input1')

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
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.make()
                node.attr('operation').set(3)
                node.attr('input1').set(self)

                if dim is 1:
                    for child in node.attr('input2'):
                        other >> child

                else:
                    other >> node.attr('input2')

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
        other, dim, isplug = _mo.info(other)

        if isplug:
            if dim in (1, 3):
                node = r.nodes.MultiplyDivide.make()
                node.attr('operation').set(3)
                node.attr('input2').set(self)

                if dim is 1:
                    for child in node.attr('input1'):
                        other >> child

                else:
                    other >> node.attr('input1')

                return node.attr('output')

            else:
                return NotImplemented

        return _dt.EulerRotation.__rpow__(self, other)