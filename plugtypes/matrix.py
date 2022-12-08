import pymel.core.nodetypes as _nt
from pymel.util import expandArgs
import paya.runtime as r
import paya.lib.mathops as _mo
from paya.util import resolveFlags, short, cap, undefined
from paya.config import takeUndefinedFromConfig


class Matrix:

    __math_dimension__ = 16

    #-----------------------------------------------------------|    Testing

    @short(name='n', size='siz')
    def createLocator(self, size=1.0, name=None):
        """
        Creates a locator and drives its SRT channels using this matrix.

        :shorthand: ``cl``

        :param str name/n: an optional name for the locator transform;
            defaults to a contextual name
        :param float size/siz: the locator display scale; defaults to 1.0
        :return: The locator.
        :rtype: :class:`~paya.runtime.nodes.Transform`
        """
        if not name:
            name = r.Name.make(nt='locator', xf=True)

        loc = r.spaceLocator(n=name)
        loc.attr('displayLocalAxis').set(True)
        loc.attr('localScale').set([size] * 3)

        decomposition = self.decompose(ro=loc.attr('ro'))

        for channel in ('translate', 'rotate', 'scale', 'shear'):
            decomposition[channel] >> loc.attr(channel)

        return loc

    cl = createLocator

    #-----------------------------------------------------------|    Addition

    def __add__(self, other, swap=False):
        """
        Implements **addition** (``+``).

        :param other: a 16D value or plug
        """
        other, dim, ut, isplug = _mo.info(other).values()

        if dim is 16:
            node = r.nodes.AddMatrix.createNode()

            self >> node.attr('matrixIn')[1 if swap else 0]
            node.attr('matrixIn')[0 if swap else 1].put(other, p=isplug)

            return node.attr('matrixSum')

        return NotImplemented

    def __radd__(self, other):
        """
        Implements **reflected addition** (``+``). See :meth:`__add__`.
        """
        return self.__add__(other, swap=True)

    #-----------------------------------------------------------|    Multiplication

    def mul(self, *others):
        """
        Multiplies this matrix in a chained manner with ``*others``.

        :param others: the other matrices (unpacked list)
        :type others: str, Matrix, Matrix, [list]
        :return: :class:`~paya.runtime.plugs.Matrix`
        """
        items = [self] * list(others)
        return _mo.multMatrices(*items)

    def __mul__(self, other, swap=False):
        """
        Implements **multiplication** (``*``).

        :param other: a value or plug of dimension 3 (left only) or 16.
        """
        other, dim, ut, isplug = _mo.info(other).values()

        if dim is 3 and swap:
            node = r.nodes.PointMatrixMult.createNode()
            node.attr('vectorMultiply').set(True)
            self >> node.attr('inMatrix')
            node.attr('inPoint').put(other, p=isplug)

            return node.attr('output')

        if dim is 16:
            node = r.nodes.MultMatrix.createNode()

            self >> node.attr('matrixIn')[1 if swap else 0]
            node.attr('matrixIn')[0 if swap else 1].put(other, p=isplug)

            return node.attr('matrixSum')

        return NotImplemented

    def __rmul__(self, other):
        """
        Implements **reflected multiplication** (``*``). See :meth:`__mul__`.
        """
        return self.__mul__(other, swap=True)

    #-----------------------------------------------------------|    Point-matrix mult

    def __rxor__(self, other):
        """
        Uses the exclusive-or operator (``^``) to implement
        **point-matrix multiplication** (reflected only).

        :param other: a 3D value or plug
        """
        other, dim, ut, isplug = _mo.info(other).values()

        if dim is 3:
            node = r.nodes.PointMatrixMult.createNode()
            self >> node.attr('inMatrix')
            node.attr('inPoint').put(other, p=isplug)

            return node.attr('output')

        return NotImplemented

    #-----------------------------------------------------------|    Filtering

    def _pick(
            self,
            translate=None,
            rotate=None,
            scale=None,
            shear=None
    ):
        translate, rotate, scale, shear = resolveFlags(
            translate, rotate, scale, shear
        )

        if not any([translate, rotate, scale, shear]):
            node = r.nodes.HoldMatrix.createNode()
            return node.attr('outMatrix')

        if all([translate, rotate, scale, shear]):
            return self.hold()

        node = r.nodes.PickMatrix.createNode()
        self >> node.attr('inputMatrix')

        for chan, state in zip(
            ['translate','rotate','scale','shear'],
            [translate, rotate, scale, shear]
        ):
            node.attr('use{}'.format(cap(chan))).set(state)

        return node.attr('outputMatrix')

    def normal(self):
        """
        :return: A version of this matrix with all axis vectors normalized.
        :rtype: :class:`Matrix`
        """
        out = r.nodes.FourByFourMatrix.createNode()
        self.x.normal() >> out.x
        self.y.normal() >> out.y
        self.z.normal() >> out.z
        self.t >> out.t

        return out.attr('output')

    @short(
        translate='t',
        rotate='r',
        scale='s',
        shear='sh'
    )
    def pick(
            self,
            translate=None,
            rotate=None,
            scale=None,
            shear=None,
            default=None
    ):
        """
        Filters this matrix through one or more pickMatrix nodes, depending on
        combinations with 'default'. Flags are defined by omission, Maya-style.

        :shorthand: pk

        :param bool translate/t: use translate
        :param bool rotate/r: use rotate
        :param bool scale/s: use scale
        :param shear/sh: use shear
        :param default: take omitted fields from this matrix; can be a value
            or plug; defaults to None
        :type default: list, :class:`~paya.runtime.data.Matrix`, str,
            :class:`~paya.runtime.plugs.Matrix`
        :return: The filtered matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        translate, rotate, scale, shear = resolveFlags(
            translate, rotate, scale, shear
        )

        if default:
            default = _mo.info(default)['item']

        if not any([translate, rotate, scale, shear]):
            return (default if default else self).hold()

        chunks = [] # (source, chanList)

        for chan, state in zip(
                ['scale','shear','rotate','translate'],
                [scale, shear, rotate, translate]
        ):
            src = self if state else default

            if src is None:
                continue

            if chunks:
                if chunks[-1][0] is src:
                    chunks[-1][1].append(chan)
                    continue

            chunks.append((src,[chan]))

        reduction = []

        for chunk in chunks:
            source, chanList = chunk
            picked = source._pick(**{chan:True for chan in chanList})
            reduction.append(picked)

        return _mo.multMatrices(*reduction)

    pk = pick

    #--------------------------------------------------------------------|    Signing

    def inverse(self):
        """
        :return: The inverse of this matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        node = r.nodes.InverseMatrix.createNode()
        self >> node.attr('inputMatrix')
        return node.attr('outputMatrix')

    #--------------------------------------------------------------------|    Conveniences

    def asOffset(self):
        """
        Inverts this matrix once, to create an offset matrix. Equivalent to:

        .. code-block:: python

            self.get().inverse() * self

        :return: The offset matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        return self.get().inverse() * self

    #--------------------------------------------------------------------|    Vector / point extractions

    @short(normalize='nr')
    def getAxis(self, axis, normalize=False):
        """
        Extracts the specified axis from this matrix as a vector output. If
        this is the output attribute of a fourByFourMatrix node, the method
        will defer to methods in
        :class:`~paya.runtime.nodes.FourByFourMatrix`.

        Used to implement the following properties: **x**, **y**, **z** and
        **translate**/**t**. The property versions will always return
        non-normalized outputs.

        :param str axis: the axis to extract, one of 'x', 'y', 'z', '-x',
            '-y', '-z' or 'translate' / 't'.
        :param bool normalize: normalize the extracted vector; defaults
            to False
        :return: :class:`Math3D`
        """
        if self.attrName(longName=True) == 'output':
            node = self.node()

            if isinstance(node, _nt.FourByFourMatrix):
                return node.getAxis(axis, nr=normalize)

        node = r.nodes.VectorProduct.createNode()

        if axis in ('translate', 't'):
            node.attr('operation').set(4)

        else:
            node.attr('operation').set(3)

        if normalize:
            node.attr('normalizeOutput').set(True)

        node.attr('input1').set(
            {
            'x':[1,0,0],
            'y':[0,1,0],
            'z':[0,0,1],
            '-x':[-1,0,0],
            '-y':[0,-1,0],
            '-z':[0,0,-1],
            't':[0,0,0],
            'translate':[0,0,0],
            }[axis]
        )

        self >> node.attr('matrix')

        return node.attr('output')

    def getX(self, normalize=False):
        """
        Extracts the X vector. Used to implement the **x** property.

        :param bool normalize: normalize the output; defaults to False
        :return: the extracted vector
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.getAxis('x', nr=normalize)

    def getY(self, normalize=False):
        """
        Extracts the Y vector. Used to implement the **y** property.

        :param bool normalize: normalize the output; defaults to False
        :return: the extracted vector
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.getAxis('y', nr=normalize)

    def getZ(self, normalize=False):
        """
        Extracts the Z vector. Used to implement the **z** property.

        :param bool normalize: normalize the output; defaults to False
        :return: the extracted vector
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        return self.getAxis('z', nr=normalize)

    def getTranslate(self, normalize=False):
        """
        Extracts the translation component. Used to implement the
        **translate** / **t** property.

        :param bool normalize: normalize the output; defaults to False
        :return: the extracted translation
        :rtype: :class:`~paya.runtime.plugs.Math3D`
        """
        return self.getAxis('t', nr=normalize)

    x = property(fget=getX)
    y = property(fget=getY)
    z = property(fget=getZ)
    t = translate = property(fget=getTranslate)

    #--------------------------------------------------------------------|    Misc

    def transpose(self):
        """
        :return: The transposition of this matrix.
        :rtype: :class:`~paya.runtime.plugs.Matrix`
        """
        node = r.nodes.TransposeMatrix.createNode()
        self >> node.attr('inputMatrix')
        return node.attr('outputMatrix')

    #--------------------------------------------------------------------|    Decomposition

    @short(rotateOrder='ro')
    def decompose(self, rotateOrder='xyz'):
        """
        Connects and configures a ``decomposeMatrix`` node.

        :param rotateOrder/ro: the rotate order to apply; defaults to 'xyz'
        :type rotateOrder/ro: str, int, Math1D
        :return: dictionary of {channelName:decomposeMatrixOutput}
        :rtype: dict
        """
        node = r.nodes.DecomposeMatrix.createNode()
        self >> node.attr('inputMatrix')
        rotateOrder >> node.attr('inputRotateOrder')

        breakout = {}

        for chan in ['translate', 'rotate', 'scale', 'shear']:
            breakout[chan] = node.attr('output{}'.format(cap(chan)))

        return breakout

    @short(
        translate='t',
        rotate='r',
        scale='s',
        shear='sh',
        compensatePivots='cp',
        compensateJointOrient='cjo',
        compensateRotateAxis='cra',
        compensateJointScale='cjs',
        worldSpace='ws',
        maintainOffset='mo'
    )
    def decomposeAndApply(
            self,
            *slaves,
            translate=None,
            rotate=None,
            scale=None,
            shear=None,
            compensatePivots=False,
            compensateJointOrient=True,
            compensateRotateAxis=False,
            compensateJointScale=True,
            worldSpace=False,
            maintainOffset=False
    ):
        """
        Decomposes and applies this matrix to one or more slave transforms.

        :param \*slaves: one or more transforms to drive
        :type \*slaves: :class:`~paya.runtime.nodes.Transform`, :class:`str`
        :param bool translate/t: apply translation
        :param bool rotate/r: apply rotation
        :param bool scale/s: apply scale
        :param bool shear/sh: apply shear
        :param bool maintainOffset/mo: maintain relative pose; defaults to
            ``False``
        :param bool worldSpace/ws: premultiply this matrix with
            ``parentInverseMatrix`` on the transform to negate the
            parent stack; defaults to ``False``
        :param bool compensateJointScale/cjs: account for
            segmentScaleCompensate on joints; defaults to ``True``
        :param bool compensateJointOrient/cjo: account for ``jointOrient`` on
            joints; defaults to ``True``
        :param bool compensateRotateAxis/cra: account for ``rotateAxis``;
            defaults to ``False``
        :param bool compensatePivots/cp: compensate for pivots (non-joint
            transforms only); this is expensive, so defaults to ``False``
        :return: ``self``
        :rtype: :class:`Matrix`
        """
        #-------------------------------------|    Prep / early bail

        slaves = [r.PyNode(slave) for slave in expandArgs(*slaves)]

        if not slaves:
            raise ValueError("No slaves specified.")

        if not slaves:
            raise ValueError("No slaves specified.")

        translate, rotate, scale, shear = \
            resolveFlags(translate, rotate, scale, shear)

        if not any([translate, rotate, scale, shear]):
            r.warning("No channels requested, skipping.")
            return self

        #-------------------------------------|    Preprocessing

        matrix = self

        if maintainOffset:
            matrix = matrix.asOffset()

        #-------------------------------------|    Iterate

        for slave in slaves:
            _matrix = matrix

            if maintainOffset:
                _matrix = slave.getMatrix(worldSpace=worldSpace) * _matrix

            if worldSpace:
                _matrix *= slave.attr('parentInverseMatrix')[0]

            _compensatePivots = compensatePivots
            _compensateJointOrient = compensateJointOrient
            _compensateRotateAxis = compensateRotateAxis
            _compensateJointScale = compensateJointScale

            isJoint = isinstance(slave, _nt.Joint)

            if isJoint:
                _compensatePivots = False

                fast = not any([
                    _compensateRotateAxis,
                    _compensateJointScale,
                    _compensateJointOrient
                ])

            else:
                _compensateJointScale = _compensateJointOrient = False
                fast = not (_compensateRotateAxis or _compensatePivots)

            if fast:
                decomposition = _matrix.decompose(ro=slave.attr('ro'))

                for channel, state in zip(
                    ['translate', 'rotate', 'scale', 'shear'],
                    [translate, rotate, scale, shear]
                ):
                    if state:
                        dest = slave.attr(channel)

                        try:
                            decomposition[channel] >> dest

                        except:
                            r.warning(
                                "Couldn't connect into attribute: {}".format(dest)
                            )

            else:
                #-------------------------|    Disassemble

                tmtx = _matrix.pk(t=True)

                if _compensateJointScale:
                    pismtx = slave.attr('inverseScale').asScaleMatrix()

                    _matrix = slave.attr('segmentScaleCompensate').ifElse(
                        _matrix * pismtx,
                        _matrix
                    ).setClass(r.plugs.Matrix)

                smtx = _matrix.pk(s=True, sh=True)
                rmtx = _matrix.pk(r=True)
                
                #-------------------------|    Rotation compensations

                if _compensateRotateAxis:
                    ramtx = slave.getRotateAxisMatrix(p=True)
                    rmtx = ramtx.inverse() * rmtx
        
                if _compensateJointOrient:
                    jomtx = slave.getJointOrientMatrix(p=True)
                    rmtx *= jomtx.inverse()
                    
                #-------------------------|    Pivot compensations

                if _compensatePivots:
                    # Solve as Maya would
        
                    ramtx = slave.getRotateAxisMatrix(p=True)
                    spmtx = slave.attr('scalePivot').asTranslateMatrix()
                    stmtx = slave.attr('scalePivotTranslate').asTranslateMatrix()
                    rpmtx = slave.attr('rotatePivot').asTranslateMatrix()
                    rtmtx = slave.attr('rotatePivotTranslate').asTranslateMatrix()
        
                    partialMatrix = spmtx.inverse() * smtx * spmtx * stmtx * \
                                    rpmtx.inverse() * ramtx * rmtx * rpmtx * rtmtx
        
                    # Capture and negate translation contribution
                    translateContribution = partialMatrix.pk(t=True)
                    tmtx *= translateContribution.inverse()
                    
                #-------------------------|    Reassemble & apply

                _matrix = smtx * rmtx * tmtx
                decomposition = _matrix.decompose(ro=slave.attr('ro'))
        
                for channel, state in zip(
                        ('translate', 'rotate', 'scale', 'shear'),
                        (translate, rotate, scale, shear)
                ):
                    if state:
                        source = decomposition[channel]
                        dest = slave.attr(channel)
        
                        try:
                             source >> dest
        
                        except:
                            r.warning(
                                "Couldn't connect into attribute: {}".format(dest)
                            )

    @short(worldSpace='ws',
           persistentCompensation='pc',
           preserveInheritsTransform='pit',
           maintainOffset='mo')
    def applyViaOpm(self,
                    *slaves,
                    worldSpace=False,
                    persistentCompensation=False,
                    preserveInheritsTransform=False,
                    maintainOffset=False):
        """
        Uses this matrix to drive one or more transforms via connections into
        ``offsetParentMatrix``, with compensations against the transforms'
        SRT channels.

        .. warning::

           When *worldSpace* is combined with *preserveInheritsTransform*,
           the matrix will only be localised against the current parent.
           The solution will break if the transform is subsequently
           reparented.

        :param \*slaves: one or more transforms to drive
        :type \*slaves: :class:`~paya.runtime.nodes.Transform`, :class:`str`
        :param bool worldSpace/ws: drive the slaves in world-space;
           defaults to ``False``
        :param bool maintainOffset/mo: preserve relative pose on application;
           defaults to ``False``
        :param bool persistentCompensation/pc: compensate for the transform's
           SRT channels persistently, so that the world pose will remain
           the same even if they change; defaults to ``False``
        :param preserveInheritsTransform/pit: when *worldSpace* is
           requested, don't edit the ``inheritsTransform`` attribute on
           the transform; instead, localise against the current parent;
           defaults to ``False``
        :return: ``self``
        :rtype: :class:`Matrix`
        """
        slaves = [r.PyNode(slave) for slave in expandArgs(*slaves)]

        if not slaves:
            raise ValueError("No slaves specified.")

        matrix = self

        if maintainOffset:
            matrix = matrix.asOffset()

        for slave in slaves:
            _matrix = matrix

            if maintainOffset:
                _matrix = slave.getMatrix(worldSpace=worldSpace) * _matrix

            if worldSpace:
                if preserveInheritsTransform:
                    pnt = slave.getParent()

                    if pnt:
                        _matrix *= pnt.attr('worldInverseMatrix')

                else:
                    slave.attr('inheritsTransform').set(False)

            _matrix = slave.attr('inverseMatrix').get(
                plug=persistentCompensation) * _matrix

            _matrix >> slave.attr('offsetParentMatrix')

    @short(worldSpace='ws',
           maintainOffset='mo',
           useOffsetParentMatrix='uop',
           preserveInheritsTransform='pit')
    @takeUndefinedFromConfig
    def drive(self,
               *slaves,
               worldSpace=False,
               maintainOffset=False,
               useOffsetParentMatrix=undefined,
               preserveInheritsTransform=False):
        """
        Drives one or more slaves using this matrix.

        :param \*slaves: one or more transforms to drive
        :type \*slaves: :class:`~paya.runtime.nodes.Transform`, :class:`str`

        :param bool worldSpace/ws: drive the slaves in world-space;
           defaults to ``False``
        :param preserveInheritsTransform/pit: when *worldSpace* is requested,
            don't edit the ``inheritsTransform`` attribute on the slave;
            instead, localise against its current parent; defaults to
            ``False``
        :param bool maintainOffset/mo: preserve relative pose on application;
           defaults to ``False``
        :param bool useOffsetParentMatrix/uop: connect into
            ``offsetParentMatrix`` instead of decomposing into SRT channels;
            defaults to namesake configuration flag; it that's omitted too,
            defaults to ``True`` if Maya >= 2022, otherwise ``False``
        :return: ``self``
        :rtype: :class:`Matrix`
        """
        if useOffsetParentMatrix:
            return self.applyViaOpm(
                *slaves,
                worldSpace=worldSpace,
                maintainOffset=maintainOffset,
                preserveInheritsTransform=preserveInheritsTransform
            )

        return self.decomposeAndApply(*slaves,
                                      worldSpace=worldSpace,
                                      maintainOffset=maintainOffset)

    #--------------------------------------------------------------------|    Hold

    def hold(self):
        """
        Connects a holdMatrix node and returns its output.

        This is useful in situations where a method such as pick() has nothing
        to do, but must return a new output to protect code branching.

        :return: The output of a holdMatrix node.
        :rtype: :class:`HoldMatrix`
        """
        node = r.nodes.HoldMatrix.createNode()
        self >> node.attr('inMatrix')
        return node.attr('outMatrix')

    #--------------------------------------------------------------------|    Conversions

    @short(rotateOrder='ro')
    def asEulerRotation(self, rotateOrder='xyz'):
        """
        Returns the euler decomposition of this matrix.

        :param rotateOrder/ro: The rotate order, defaults to ``'xyz'``
        :type rotateOrder/ro: int, str, Math1D
        :return: The Euler rotation output.
        :rtype: :class:`Math3D`
        """
        node = r.nodes.DecomposeMatrix.createNode()
        self >> node.attr('inputMatrix')
        rotateOrder >> node.attr('inputRotateOrder')

        return node.attr('outputRotate')

    def asQuaternion(self):
        """
        Returns a quaternion output for this matrix's rotation.

        :return: The quaternion.
        :rtype: :class:`Quaternion`
        """
        node = r.nodes.DecomposeMatrix.createNode()
        self >> node.attr('inputMatrix')
        return node.attr('outputQuat').setClass(r.plugs.Quaternion)