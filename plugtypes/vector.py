from paya.util import short
import paya.runtime as r


class Vector:

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    GENERAL
    #---------------------------------------------------------------|

    #-----------------------------------------------------------|    Testing

    @short(name='n', size='siz')
    def createLocator(self, name=None, size=1.0):
        """
        :shorthand: ``cl``

        :param str name/n: an optional name for the locator transform;
            defaults to a contextual name
        :param float size/siz: a single scalar for the locator's
            ``localScale`` channels; defaults to 1.0
        :return: A locator with this 3D compound piped into its
            ``translate`` channel.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        if name is None:
            name = r.Name.make(nt='locator', xf=True)

        loc = r.spaceLocator(n=name)
        loc.getShape().attr('localScale').set([size] * 3)
        self >> loc.attr('t')
        return loc

    cl = createLocator

    #-----------------------------------------------------------|    Getter

    def isTranslateChannel(self):
        """
        :return: True if this is the ``translate`` channel of a transform
            node, otherwise False.
        :rtype: bool
        """
        return self.attrName(longName=True
            ) == 'translate' and isinstance(
            self.node(), r.nodetypes.Transform)

    @short(plug='p')
    def get(self, plug=False, **kwargs):
        """
        Overrides :meth:`~paya.runtime.plugs.Attribute.get` to return
        :class:`~paya.runtime.data.Point` values if this is the translate
        channel of a transform node.
        """
        if plug:
            return self

        result = r.plugs.Math.get(self, **kwargs)

        if isinstance(result, r.datatypes.Vector):
            if self.isTranslateChannel():
                return r.data.Point(result)

        return result

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    OPERATORS
    #---------------------------------------------------------------|

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements element-wise **addition** (``+``).
        """
        item, dim, ut, isplug = r.mathInfo(other).values()

        if dim in (1, 3):
            node = r.nodes.PlusMinusAverage.createNode()

            self >> node.attr('input3D')[1 if swap else 0]

            if dim is 1:
                for dest in node.attr(
                        'input3D')[0 if swap else 1].getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input3D')[0 if swap else 1].put(other, p=isplug)

            return node.attr('output3D').setClass(type(self))

        return NotImplemented

    def __radd__(self, other):
        """
        Implements element-wise **reflected addition** (``-``).
        """
        return self.__add__(other, swap=True)

    #-----------------------------------------------------------|    Subtraction

    def __sub__(self, other, swap=False):
        """
        Implements element-wise **subtraction** (``-``).
        """
        item, dim, ut, isplug = r.mathInfo(other).values()

        if dim in (1, 3):
            node = r.nodes.PlusMinusAverage.createNode()
            node.attr('operation').set(2)

            self >> node.attr('input3D')[1 if swap else 0]

            if dim is 1:
                for dest in node.attr(
                        'input3D')[0 if swap else 1].getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input3D')[0 if swap else 1].put(other, p=isplug)

            return node.attr('output3D').setClass(type(self))

        return NotImplemented

    def __rsub__(self, other):
        """
        Implements element-wise **reflected subtraction** (``-``).
        """
        return self.__sub__(other, swap=True)

    #-----------------------------------------------------------|    Multiply

    def __mul__(self, other, swap=False):
        """
        Implements **multiplication** (``*``).
        """
        item, dim, unitType, isplug = r.mathInfo(other).values()

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            self >> node.attr('input{}'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr(
                        'input{}'.format(1 if swap else 2)).getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input{}'.format(
                    1 if swap else 2)).put(other, p=isplug)

            return node.attr('output').setClass(type(self))

        elif dim is 16 and not swap:
            node = r.nodes.PointMatrixMult.createNode()
            node.attr('vectorMultiply').set(True)
            self >> node.attr('inPoint')
            other >> node.attr('inMatrix')
            return node.attr('output').setClass(type(self))

        return NotImplemented

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``).
        """
        return self.__mul__(other, swap=True)

    #-----------------------------------------------------------|    Unary neg

    def __neg__(self):
        """
        Implements element-wise **unary negation** (``-``).
        """
        return self * -1

    #-----------------------------------------------------------|    Divide

    def __truediv__(self, other, swap=False):
        """
        Implements element-wise **division** (``/``).
        """
        item, dim, ut, isplug = r.mathInfo(other).values()

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(2)

            self >> node.attr('input{}'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr(
                        'input{}'.format(1 if swap else 2)).getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input{}'.format(
                    1 if swap else 2)).put(other, p=isplug)

            return node.attr('output').setClass(type(self))

        return NotImplemented

    def __rtruediv__(self, other):
        """
        Implements element-wise **reflected division** (``/``).
        """
        return self.__div__(other, swap=True)

    #-----------------------------------------------------------|    Power

    def __pow__(self, other, swap=False):
        """
        Implements element-wise **power** (``**``).
        """
        item, dim, ut, isplug = r.mathInfo(other).values()

        if dim in (1, 3):
            node = r.nodes.MultiplyDivide.createNode()
            node.attr('operation').set(3)

            self >> node.attr('input{}'.format(2 if swap else 1))

            if dim is 1:
                for dest in node.attr(
                        'input{}'.format(1 if swap else 2)).getChildren():
                    dest.put(other, p=isplug)
            else:
                node.attr('input{}'.format(
                    1 if swap else 2)).put(other, p=isplug)

            return node.attr('output').setClass(type(self))

        return NotImplemented

    def __rpow__(self, other):
        """
        Implements element-wise **reflected power** (``**``).
        """
        return self.__div__(other, swap=True)

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    RANGES
    #---------------------------------------------------------------|

    #-----------------------------------------------------------|    Blend

    @short(weight='w',
           swap='sw',
           includeLength='ilg',
           unwindSwitch='uws',
           clockNormal='cn')
    def blend(self,
              other,
              weight=0.5,
              swap=False,
              includeLength=False,
              clockNormal=None,
              unwindSwitch=None):
        """
        Blends this triple towards *other*. Blending will be linear or, if
        *clockNormal* is provided, by vector angle.

        :param other: the triple or vector towards which to blend
        :type other: :class:`list` [:class:`float`],
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Math3D`,
            :class:`str`
        :param weight/w: 0.5: the blending weight; when this is 1.0, *other*
            will take over fully; can be a value or plug; defaults to ``0.5``
        :type weight/w: :class:`str`, :class:`float`,
            :class:`~paya.runtime.plugs.Math1D`
        :param bool swap/sw: swap the inputs around; defaults to ``False``
        :param clockNormal/cn: if this is ``True``, this output and *other*
            will be regarded as vectors, and blended by angle; should be
            a vector perpendicular to both inputs; defaults to ``None``
        :type clockNormal/cn: :class:`list` [:class:`float`],
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Math3D`,
            :class:`str`
        :param bool includeLength/ilg: ignored if *clockNormal* was omitted;
            include vector lengths in the blending calculation; defaults to
            ``False``
        :param unwindSwitch/uws: ignored if *clockNormal* was omitted; an
            integer value or plug to pick an angle unwinding mode:

            - ``0`` for shortest (the default)
            - ``1`` for positive
            - ``2`` for negative

        :type unwindSwitch/uws: int, str, :class:`~paya.runtime.plugs.Math1D`
        :return: The blended triple or vector.
        :rtype: :class:`paya.runtime.plugs.Math3D`
        """
        other = r.conform(other)

        if swap:
            first, second = other, self
        else:
            first, second = self, other

        if clockNormal is None: # linear implementation
            node = r.nodes.BlendColors.createNode()
            first >> node.attr('color2')
            second >> node.attr('color1')
            weight >> node.attr('blender')
            return node.attr('output').setClass(type(self))

        # Angle-based implementation
        angle = first.angleTo(second, clockNormal=clockNormal)

        if unwindSwitch is not None:
            angle = angle.unwindSwitch(unwindSwitch)

        angle *= weight
        out = first.rotateByAxisAngle(clockNormal, angle)

        if includeLength:
            length = first.length().blend(second.length(), weight=weight)
            out = out.normal() * length

        return out.setClass(r.plugs.Vector)

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    VECTOR-SPECIFIC
    #---------------------------------------------------------------|

    def __xor__(self, other):
        """
        Uses the exclusive-or operator (``^``) to implement
        **point-matrix multiplication**.

        :param other: a matrix value or plug
        """
        node = r.nodes.PointMatrixMult.createNode()
        self >> node.attr('inPoint')
        other >> node.attr('inMatrix')
        return node.attr('output').setClass(type(self))

    def length(self):
        """
        :return: The length of this vector.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        node = r.nodes.DistanceBetween.createNode(n='mag')
        self >> node.attr('point2')
        return node.attr('distance')

    def normal(self):
        """
        :return: This vector, normalized.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self / self.length()

    @short(normalize='nr')
    def dot(self, other, normalize=False):
        """
        Returns the dot product of ``self`` and *other*.

        :param other: the other vector
        :type other: :class:`list`, :class:`tuple`,
            :class:`~paya.runtime.plugs.Math3D`
        :param bool normalize/nr: normalize the output; defaults to ``False``
        :return: :class:`paya.runtime.plugs.Math1D`
        """
        node = r.nodes.VectorProduct.createNode()
        self >> node.attr('input1')
        other >> node.attr('input2')
        node.attr('normalizeOutput').set(normalize)

        return node.attr('outputX')

    @short(normalize='nr', guard='g', inlineGate='ig')
    def cross(self, other, normalize=False, guard=False, inlineGate=None):
        """
        :param other: the other vector
        :type other: :class:`tuple`, :class:`list`,
            :class:`str`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :param bool normalize/nr: normalize the output; defaults to
            ``False``
        :param bool guard/g: switch the node to ``'No Operation'`` when the
            input vectors are aligned in either direction; defaults to
            ``False``
        :param bool inlineGate/ig: if you have a precooked gate for alignment
            (typically the output of a comparison operation), provide it here
            to prevent redundant checks; if provided, will override *guard*
            to ``True``; defaults to ``None``
        :return: The cross product.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return r.nodes.VectorProduct.createAsCross(
            self, other,
            normalize=normalize,
            guard=guard,
            inlineGate=inlineGate
        ).attr('output')

    @short(clockNormal='cn')
    def angleTo(self, other, clockNormal=None):
        """
        :param other: the other vector
        :type other: :class:`~paya.runtime.plugs.Vector`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.data.Point`, list, str
        :param clockNormal/cn: provide this to get a 360 angle; defaults to
            ``None``
        :type clockNormal/cn: ``None``, :class:`list`, :class:`tuple`,
            :class:`~paya.runtime.plugs.Vector`,
            :class:`~paya.runtime.data.Vector`
        :return: The angle from this vector to *other*.
        :rtype: :class:`~paya.runtime.plugs.Angle`
        """
        if clockNormal is None:
            complete = False

        else:
            complete = True
            clockNormal, cnDim, \
                cnUnitType, cnIsPlug = r.mathInfo(clockNormal).values()
            cross = self.cross(clockNormal)

        ab = r.createNode('angleBetween')
        self >> ab.attr('vector1')
        other >> ab.attr('vector2')
        angle = ab.attr('angle')

        if complete:
            dot = cross.dot(other, normalize=True)
            corrected = r.degToUI(360.0)-angle
            gate = dot.gt(0.0)
            angle = gate.ifElse(corrected, angle)

        return angle.setClass(r.plugs.Angle)

    def projectOnto(self, other):
        """
        See https://en.wikipedia.org/wiki/Vector_projection.

        :param other: the vector onto which to project this one
        :type other: :class:`list`, :class:`tuple`, :class:`str`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The project of this vector onto *other*.
        :rtype: :class:`Vector`
        """
        other = r.mathInfo(other)['item']
        return (self.dot(other) / other.dot(other)) * other

    def rejectFrom(self, other):
        """
        Same as 'make perpendicular to' (although length will change).
        See https://en.wikipedia.org/wiki/Vector_projection.

        :param other: the vector from which to reject this one
        :type other: :class:`list`, :class:`tuple`, :class:`str`,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`
        :return: The rejection of this vector from *other*.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        other = r.mathInfo(other)['item']
        cosTheta = self.dot(other, nr=True)
        rejection = self - (self.length() * cosTheta) * other.normal()
        return rejection

    def rotateByAxisAngle(self, axisVector, angle):
        """
        :param axisVector: the vector around which to rotate this vector
        :type axisVector: list, tuple, :class:`~paya.runtime.data.Vector`
            or :class:`~paya.runtime.plugs.Vector`
        :param angle: the angle of rotation
        :type angle: float, :class:`~paya.runtime.data.Angle`, str or
            class:`~paya.runtime.plugs.Math3D`
        :return: This vector, rotated around ``axisVector`` by the specified
            ``angle``.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        axisAngle = r.nodes.AxisAngleToQuat.createNode()
        axisVector >> axisAngle.attr('inputAxis')
        angle >> axisAngle.attr('inputAngle')
        quat = axisAngle.attr('outputQuat')
        matrix = quat.asRotateMatrix()

        return self * matrix

    #---------------------------------------------------------------|
    #---------------------------------------------------------------|    CONVERSIONS
    #---------------------------------------------------------------|

    def asTranslateMatrix(self):
        """
        Inserts this into the translate row of an identity matrix, and
        returns the matrix.

        :return: The translate matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        ffm = r.nodes.FourByFourMatrix.createNode()
        fields = ['in30', 'in31', 'in32']
        children = self.getChildren()

        for src, field in zip(self.getChildren(), fields):
            src >> ffm.attr(field)

        return ffm.attr('output')

    def asScaleMatrix(self):
        """
        Uses this output's three components as the magnitudes of
        an identity matrix's base vectors.

        :return: The scale matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        ffm = r.nodes.FourByFourMatrix.createNode()

        for src, field in zip(
            self.getChildren(),
            ['in00','in11','in22']
        ):
            src >> ffm.attr(field)

        return ffm.attr('output')

    def asRotateMatrix(self):
        """
        :return: This vector's orientation as a rotate matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        return self.asEulerRotation().asRotateMatrix()

    def asShearMatrix(self):
        """
        Composes this output's three components into a shear matrix.

        :return: The shear matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        cm = r.nodes.ComposeMatrix.createNode()
        self >> cm.attr('inputShear')
        return cm.attr('outputMatrix')

    def asEulerRotation(self):
        """
        Returns XYZ euler rotations for this vector.

        :return: A compound of three euler channels.
        :rtype: :class:`~paya.runtime.plugs.EulerRotation`
        """
        node = r.nodes.AngleBetween.createNode()
        self >> node.attr('vector2')
        return node.attr('euler')

    def asQuaternion(self):
        """
        :return: A quaternion representation of this vector's
            orientation.
        :rtype: :class:`~paya.runtime.plugs.Quaternion`
        """
        return self.asEulerRotation().asQuaternion()

    def asAxisAngle(self):
        """
        :return: An axis, angle representation of this vector.
        :rtype: :class:`tuple` (:class:`Vector`, :class:`Angle`)
        """
        node = r.nodes.AngleBetween.createNode()
        self >> node.attr('vector2')
        return (node.attr('axis'), node.attr('angle'))