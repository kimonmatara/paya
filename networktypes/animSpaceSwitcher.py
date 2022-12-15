import maya.cmds as m
import paya.runtime as r
from pymel.util import expandArgs
from paya.util import short, resolveFlags, cap

#------------------------------------------------------|    HELPERS

def longChannelName(x):
    return {'t': 'translate', 'r': 'rotate', 's': 'scale'}.get(x, x)

def asMatrixPlug(x):
    if not isinstance(x, r.PyNode):
        x = r.PyNode(x)

    if isinstance(x, r.Attribute):
        return x

    return x.getWorldMatrix(plug=True)

#------------------------------------------------------|
#------------------------------------------------------|    MAIN CLASS
#------------------------------------------------------|

class AnimSpaceSwitcher(r.networks.System):
    """
    Animation-space switching system.
    """
    #--------------------------------------------------|    Acccesor(s)

    @classmethod
    def getFromControl(cls, control, channels=None, combo=None):
        if channels:
            channels = [longChannelName(x) for x in channels]

        control = r.PyNode(control)
        raise NotImplementedError
        nodesThatTagControl = control.taggedBy()

        systems = [network for network in \
                   cls.getAll() if network.getControl() == control]

        if channels or combo: # filter
            def filterer(system):
                usedChannels = [
                    chan for chan in ['translate', 'rotate', 'scale'] \
                    if getattr(system, 'uses{}'.format(cap(chan)))
                ]

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

        #----------------------------------------------|    Check inputs

        translate, rotate, scale = resolveFlags(
            translate, rotate, scale
        )

        if not any([translate, rotate, scale]):
            raise ValueError("No channels requested.")

        numLabels = len(labels)
        numTargets = len(targets)

        if numLabels is 0:
            raise ValueError("No labels specified.")

        if numTargets is 0:
            raise ValueError("No targets specified.")

        if numLabels != numTargets:
            raise ValueError("Miscmatched lengths or labels and targets.")

        control = r.PyNode(control)

        if slave is None:
            slave = control.getParent()

            if not slave:
                raise ValueError(
                    "Slave can't be auto-derived, specify explicitly."
                )
        else:
            slave = r.PyNode(slave)

        channelStates = list(zip(
            ['translate', 'rotate', 'scale'],
            [translate, rotate, scale]
        ))

        # Check channels free on slave
        for channelName, channelState in channelStates:
            if control.attr(channelName).hasInputs(recursive=True):
                raise RuntimeError(
                    "Channel '{}' on {} is already occupied.".format(
                        channelName, slave
                    )
                )

        if attrName is None:
            elems = [channelName for \
                     channelName, state in channelStates if state]
            attrName = '_'.join(elems+['space'])

        #----------------------------------------------|    Create node, tag

        node = cls.createNode()

        with r.NodeTracker() as tracker:

            #------------------------------------------|    Tagging

            usedChannels = [channelState[0] for channelState \
                            in channelStates if channelState[1]]

            node.addAttr('usedChannels',
                         dt='string').set(', '.join(usedChannels))

            enumName = ':'.join(labels)
            node.tag('slave', slave)
            node.tag('control', control)
            node.addAttr('labels', dt='string').set(enumName)
            node.tag('targets', targets)
            node.addAttr('attrName', dt='string').set(attrName)
            node.addAttr('defaultValue', at='long', dv=defaultValue)

            #------------------------------------------|    Main build

            # Attribute
            sectionName = 'SPACE_OPTIONS'

            if sectionName not in control.attrSections:
                control.attrSections.add(sectionName)

            userAttr = control.addAttr(
                attrName,
                at='enum',
                k=True,
                dv=defaultValue,
                enumName=enumName
            )

            node.tag('userAttr', userAttr)

            # Choice node
            choice = r.nodes.Choice.createNode()

            for i, target in enumerate(targets):
                asMatrixPlug(target) >> choice.attr('input')[i]

            userAttr >> choice.attr('selector')

            # Drive
            driverMatrix = choice.attr('output')
            driverMatrix *= slave.attr('parentInverseMatrix')[0]
            driverMatrix = slave.getMatrix() * driverMatrix.asOffset()
            driverMatrix.decomposeAndApply(
                slave,
                translate=translate,
                rotate=rotate,
                scale=scale
            )

        node.tag('allNodes', tracker.getNodes())

        #----------------------------------------------|    Finish

        return node

    @classmethod
    def createFromMacro(cls, macro):
        macro = macro.copy()
        control = macro.pop('control')
        labels = macro.pop('labels')
        targets = macro.pop('targets')

        return cls.create(control, labels, targets, **macro)

    #--------------------------------------------------|    Macro

    def macro(self):
        userAttr = self.getByTag('userAttr')[0]
        attrName = userAttr.attrName(longName=True)
        defaultValue = r.addAttr(userAttr, q=True, dv=True)

        out = {
            'attrName': attrName,
            'labels': userAttr.getEnums().keys(),
            'targets': [str(x).split('|')[-1] \
                        for x in self.getByTag('targets')],
            'defaultValue': defaultValue,
            'control': str(userAttr.node()).split('|')[-1],
            'slave': str(self.getByTag('slave')[0]).split('|')[-1]
        }

        out.update({channel: True for channel in self.getUsedChannels()})

        return out

    #--------------------------------------------------|    Inspections

    def usesChannels(self, *channels):
        if channels:
            channels = [longChannelName(x) for x in expandArgs(*channels)]
            return set(channels).issubset(set(self.getUsedChannels()))
        raise ValueError("No channels specified.")

    def getUsedChannels(self):
        return [item.strip() for item \
                 in self.attr('usedChannels').get().split(',')]

    def getControl(self):
        try:
            return self.getByTag('control')[0]
        except IndexError:
            pass

    def getUserAttr(self):
        try:
            return self.getByTag('userAttr')[0]
        except IndexError:
            pass

    def getLabels(self):
        attr = self.getUserAttr()

        if attr is not None:
            return attr.getEnums().keys()

        return []

    def getTargets(self):
        return self.getByTag('targets')

    #--------------------------------------------------|    Destructor

    def remove(self):
        # Capture some states
        slave = self.getByTag('slave')[0]
        mtx = slave.getMatrix(worldSpace=True)

        # Get tagged elems
        control = self.getByTag('control')[0]
        userAttr = self.getByTag('userAttr')[0]
        allNodes = self.getByTag('allNodes')

        # Remove dependencies
        self.lock()

        for node in allNodes:
            try:
                if r.objExists(node):
                    r.delete(node)
            except:
                continue

        self.unlock()
        slave.setMatrix(mtx, worldSpace=True)

        # Remove user attribute
        attrName = userAttr.attrName(longName=True)
        if control.hasAttr(attrName):
            control.deleteAttr(attrName)

        if 'SPACE_OPTIONS' in control.attrSections:
            section = control.attrSections['SPACE_OPTIONS']

            if not section:
                del(control.attrSections['SPACE_OPTIONS'])

        # Remove self
        r.delete(self)