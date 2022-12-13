import paya.runtime as r
from paya.util import short, resolveFlags

#------------------------------------------------------|    HELPERS

def asMatrixPlug(x):
    if not isinstance(x, r.PyNode):
        x = r.PyNode(x)

    if isinstance(x, r.Attribute):
        return x

    return x.getWorldMatrix(plug=True)

#------------------------------------------------------|
#------------------------------------------------------|    MAIN CLASS
#------------------------------------------------------|

class AnimSpaceSwitcher:
    """
    Animation-space switching system.
    """
    #--------------------------------------------------|    Constructor(s)

    @classmethod
    @short(translate='t',
           rotate='r',
           scale='s',
           defaultValue='dv',
           attrName='an',
           slave='slv')
    def create(cls,
               control,
               labels,
               targets,
               slave=None,
               translate=None,
               rotate=None,
               scale=None,
               attrName=None,
               defaultValue=0):
        """
        :param control: the control to carry the user attribute
        :type control: :class:`str`, :class:`~paya.runtime.nodes.DependNode`
        :param slave/slv: the transform to constrain; if omitted, defaults to
            the first offset group above *control*
        :type slave/slv: :class:`str`, :class:`~paya.runtime.nodes.Transform`
        :param targets: the target transforms or matrices
        :type targets: :class:`str`, :class:`~paya.runtime.plugs.Matrix`,
            :class:`~paya.runtime.nodes.Transform`
        :param labels: labels for the enum attribute
        :type labels: :class:`list` [:class:`str`]
        :param bool translate/t: drive translate channels; defaults to
            ``True``
        :param bool rotate/r: drive rotate channels; defaults to ``True``
        :param bool scale/s: drive scale channels; defaults to ``True``
        :param str attrName/an: a name for the enum attribute; if omitted,
            it will auto-generated as something like
            ``'translate_rotate_space'``.
        :param defaultValue/dv: the default value for the enum attribute;
            defaults to ``0``
        :type defaultValue/dv: :class:`int`, :class:`str`
        :return: The system's network node.
        :rtype: :class:`AnimSpaceSwitcher`
        """
        #------------------------------------------------|    Prep

        # Resolve requested channels
        translate, rotate, scale = resolveFlags(
            translate, rotate, scale
        )

        if not any([translate, rotate, scale]):
            raise ValueError("No channels requested.")

        control = r.PyNode(control)

        if slave is None:
            if isinstance(control, r.nodetypes.Transform):
                slave = control.getParent()

            if slave is None:
                raise RuntimeError(
                    "Slave can't be auto-derived, "+
                    "and must be specified explicitly."
                )
        else:
            slave = r.PyNode(slave)

        # Check target channels are free
        for channel, state in zip(
            ['translate', 'rotate', 'scale'],
            [translate, rotate, scale]
        ):
            if state:
                if slave.attr(channel).hasInputs(recursive=True):
                    raise RuntimeError(
                        "Channel '{}' is occupied.".format(channel)
                    )

        # Check has targets, labels and same len
        numTargets = len(targets)
        numLabels = len(labels)

        if not numTargets:
            raise ValueError("Need one or more targets.")

        if not numLabels:
            raise ValueError("Need one or more labels.")

        if numTargets != numLabels:
            raise ValueError("Mismatched number of labels and targets.")

        # Resolve attribute name
        if attrName is None:
            prefix = '_'.join([channel for channel, state in zip(
                ['translate', 'rotate', 'scale'],
                [translate, rotate, scale]
            ) if state])

            attrName = '{}_space'.format(prefix)

        # Check doesn't exist
        if control.hasAttr(attrName):
            raise RuntimeError(
                "Attribute already exists: {}".format(control.attr(attrName))
            )

        #------------------------------------------------|    Build

        #-------------------------|    Create the attribute

        if 'ANIM_SPACES' not in control.attrSections:
            control.attrSections.add('ANIM_SPACES')

        if isinstance(defaultValue, str):
            defaultValue = labels.index(defaultValue)

        attr = control.addAttr(
            attrName,
            at='enum',
            enumName=':'.join(labels),
            keyable=True,
            dv=defaultValue
        )

        with r.NodeTracker() as tracker:

            #---------------------|    Configure choice node

            cho = r.nodes.Choice.createNode()
            attr >> cho.attr('selector')

            for i, target in enumerate(targets):
                asMatrixPlug(target) >> cho.attr('input')[i]

            #---------------------|    Decompose and connect

            matrix = cho.attr('output')
            matrix *= slave.attr('parentInverseMatrix')
            matrix = slave.getMatrix() * matrix.asOffset()

            matrix.decomposeAndApply(slave,
                                     t=translate,
                                     r=rotate,
                                     s=scale,
                                     sh=False)

        #-------------------------|    Create network, tag stuff

        nw = cls.createNode()
        nw.tag('userAttr', attr)
        nw.tag('control', control)
        nw.tag('slave', slave)
        nw.tag('allNodes', tracker.getNodes())

        nw.addAttr('usesTranslate', at='bool', dv=translate)
        nw.addAttr('usesRotate', at='bool', dv=rotate)
        nw.addAttr('usesScale', at='bool', dv=scale)

        return nw

    #--------------------------------------------------|    Destructor

    def remove(self):
        """
        Removes this system and all dependencies, including the user
        attribute.
        """
        allNodes = self.getByTag('allNodes')
        control = self.getByTag('control')[0]
        slave = self.getByTag('slave')[0]

        mtx = slave.getMatrix(worldSpace=True)

        self.lock()

        for node in allNodes:
            if r.objExists(node):
                try:
                    r.delete(node)
                except:
                    continue


        slave.setMatrix(mtx, worldSpace=True)
        attr = self.getByTag('userAttr')[0]
        attr.release()
        control.deleteAttr(attr.attrName())

        if not control.attrSections['ANIM_SPACES']:
            del(control.attrSections['ANIM_SPACES'])

        self.unlock()
        self.clearTags()
        r.delete(self)

    #--------------------------------------------------|    Inspections

    @property
    def usesTranslate(self):
        return self.attr('usesTranslate').get()

    @property
    def usesRotate(self):
        return self.attr('usesRotate').get()

    @property
    def usesScale(self):
        return self.attr('usesScale').get()