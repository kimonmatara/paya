import pymel.core.datatypes as _dt
import paya.lib.typeman as _tm
import paya.runtime as r

if not r.pluginInfo('quatNodes', q=True, loaded=True):
    r.loadPlugin('quatNodes')


class Quaternion:

    #-----------------------------------------------------------|    Addition

    def __add__(self, other):
        """
        Implements **addition** (``+``).

        Overloads :meth:`pymel.core.datatypes.Quaternion.__add__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 4):
                node = r.nodes.QuatAdd.createNode()

                for src, dest in zip(self, node.attr('input1Quat')):
                    dest.set(src)

                if dim is 1:
                    for child in node.attr('input2Quat'):
                        other >> child

                else:
                    for src, dest in zip(
                        other,
                        node.attr('input2Quat')
                    ):
                        src >> dest

                return node.attr('outputQuat')

            return NotImplemented

        return _dt.Quaternion.__add__(self, other)

    def __radd__(self, other):
        """
        Implements **reflected addition** (``+``).

        Overloads :meth:`pymel.core.datatypes.Quaternion.__radd__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 4):
                node = r.nodes.QuatAdd.createNode()

                for src, dest in zip(self, node.attr('input2Quat')):
                    dest.set(src)

                if dim is 1:
                    for child in node.attr('input1Quat'):
                        other >> child

                else:
                    for src, dest in zip(
                        other,
                        node.attr('input1Quat')
                    ):
                        src >> dest

                return node.attr('outputQuat')

            return NotImplemented

        return _dt.Quaternion.__radd__(self, other)
    
    #-----------------------------------------------------------|    Subtraction

    def __sub__(self, other):
        """
        Implements **subtraction** (``-``).

        Overloads :meth:`pymel.core.datatypes.Quaternion.__sub__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 4):
                node = r.nodes.QuatSub.createNode()

                for src, dest in zip(self, node.attr('input1Quat')):
                    dest.set(src)

                if dim is 1:
                    for child in node.attr('input2Quat'):
                        other >> child

                else:
                    for src, dest in zip(
                        other,
                        node.attr('input2Quat')
                    ):
                        src >> dest

                return node.attr('outputQuat')

            return NotImplemented

        return _dt.Quaternion.__sub__(self, other)

    def __rsub__(self, other):
        """
        Implements **reflected subtraction** (``-``).

        Overloads :meth:`pymel.core.datatypes.Quaternion.__rsub__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 4):
                node = r.nodes.QuatSub.createNode()

                for src, dest in zip(self, node.attr('input2Quat')):
                    dest.set(src)

                if dim is 1:
                    for child in node.attr('input1Quat'):
                        other >> child

                else:
                    for src, dest in zip(
                        other,
                        node.attr('input1Quat')
                    ):
                        src >> dest

                return node.attr('outputQuat')

            return NotImplemented

        return _dt.Quaternion.__rsub__(self, other)

    #-----------------------------------------------------------|    Multiplication

    def __mul__(self, other):
        """
        Implements **multiplication** (``*``).

        Overloads :meth:`pymel.core.datatypes.Quaternion.__mul__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 4):
                node = r.nodes.QuatProd.createNode()

                for src, dest in zip(self, node.attr('input1Quat')):
                    dest.set(src)

                if dim is 1:
                    for child in node.attr('input2Quat'):
                        other >> child

                else:
                    for src, dest in zip(
                        other,
                        node.attr('input2Quat')
                    ):
                        src >> dest

                return node.attr('outputQuat')

            return NotImplemented

        return _dt.Quaternion.__mul__(self, other)

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``).

        Overloads :meth:`pymel.core.datatypes.Quaternion.__rmul__` to add
        support for 1D or 3D plugs.
        """
        other, dim, isplug = _tm.mathInfo(other)

        if isplug:
            if dim in (1, 4):
                node = r.nodes.QuatProd.createNode()

                for src, dest in zip(self, node.attr('input2Quat')):
                    dest.set(src)

                if dim is 1:
                    for child in node.attr('input1Quat'):
                        other >> child

                else:
                    for src, dest in zip(
                        other,
                        node.attr('input1Quat')
                    ):
                        src >> dest

                return node.attr('outputQuat')

            return NotImplemented

        return _dt.Quaternion.__rmul__(self, other)