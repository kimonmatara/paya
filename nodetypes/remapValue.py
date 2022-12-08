from paya.lib.typeman import plugCheck
import paya.lib.mathops as _mo
from paya.util import short
import paya.runtime as r

#-----------------------------------------------------------|
#-----------------------------------------------------------|   Errors
#-----------------------------------------------------------|

class NoCloneForPositionError(RuntimeError):
    """
    No clone was found for the specified sample position.
    """

#-----------------------------------------------------------|
#-----------------------------------------------------------|   Main class
#-----------------------------------------------------------|


class RemapValue:

    #-------------------------------------------------------|    Value management

    @short(interpolation='i')
    def setValues(self, positionValuePairs, interpolation='Linear'):
        """
        Sets (or connects) all values on this node. The entire previous
        configuration of the ``value`` compound multi is discarded.

        :param positions: the positions at which to set values
        :type positions: [float, :class:`~paya.runtime.plugs.Math1D`]
        :param values: the values to set; must be the same number as
            *positions*
        :type values:  [float, :class:`~paya.runtime.plugs.Math1D`]
        :param interpolation/i: this can be either one enum key or index
            for the value interpolation, or a list of them. The enums
            are:

            -   0: 'None'
            -   1: 'Linear' (the default)
            -   2: 'Smooth'
            -   3: 'Spline'
        :return: ``self``
        :rtype: :class:`RemapValue`
        """
        number = len(positionValuePairs)

        if isinstance(interpolation, (tuple, list)):
            if len(interpolation) is not number:
                raise ValueError("Incorrect number of interpolation entries.")

            interpolations = list(interpolation)

        else:
            interpolations = [interpolation] * number

        self.resetValues()
        positions, values = zip(*positionValuePairs)

        for i, position, value, interpolation in zip(
                range(number),
                positions,
                values,
                interpolations
        ):
            compound = self.attr('value')[i]
            position >> compound.attr('value_Position')
            value >> compound.attr('value_FloatValue')
            interpolation >> compound.attr('value_Interp')

        return self

    def resetValues(self):
        """
        Resets the *value* compound array.

        :return: ``self``
        :rtype: :class:`RemapValue`
        """
        indices = self.attr('value').getArrayIndices()

        for index in (0, 1):
            plug = self.attr('value')[index]

            if index in indices:
                plug.attr('value_Position').release()
                plug.attr('value_FloatValue').release()
                plug.attr('value_Interp').release()

            plug.attr('value_Position').set(index)
            plug.attr('value_FloatValue').set(index)
            plug.attr('value_Interp').set('Linear')

        for index in indices:
            if index in (0, 1):
                continue

            plug = self.attr('value')[index]
            plug.attr('value_Position').release()
            plug.attr('value_FloatValue').release()
            plug.attr('value_Interp').release()

            r.removeMultiInstance(plug, b=True)

    @short(reuse='re', plug='p')
    @plugCheck('position')
    def sampleValue(self, position, reuse=True, plug=None):
        """
        Samples an interpolated value at the specified position.

        :param position: the position at which to sample a value
        :type position: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool reuse/re: look for an existing sample for the same
            position value or plug; defaults to True
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The value sample output.
        :rtype: :class:`~paya.runtime.plugs.Math1D`
        """
        if reuse:
            try:
                output = self.findCloneWithPosition(position).attr('outValue')

                if plug:
                    return output

                return output.get()

            except NoCloneForPositionError:
                pass

        if plug:
            clone = self.createClone()
            clone.attr('inputValue').release()
            position >> clone.attr('inputValue')
            return clone.attr('outValue')

        if self.attr('inputValue').inputs() \
                or self.attr('inputValue').isLocked():
            raise RuntimeError(
                "Can't perform a one-off sample because the "+
                "inputValue attribute is occupied or locked.")

        self.attr('inputValue').set(position)
        return self.attr('outValue').get()

    #-------------------------------------------------------|    Color management
    
    @short(interpolation='i')
    def setColors(self, positionColorPairs, interpolation='Linear'):
        """
        Sets (or connects) all colors on this node. The entire previous
        configuration of the ``color`` compound multi is discarded.

        :param positions: the positions at which to set colors
        :type positions: [float, :class:`~paya.runtime.plugs.Math1D`]
        :param colors: the colors to set; must be the same number as
            *positions*
        :type colors:  [list, tuple, str,
            :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`]
        :param interpolation/i: this can be either one enum key or index
            for the color interpolation, or a list of them. The enums
            are:
            -   0: 'None'
            -   1: 'Linear' (the default)
            -   2: 'Smooth'
            -   3: 'Spline'
        :return: ``self``
        :rtype: :class:`RemapColor`
        """
        positionColorPairs = list(positionColorPairs)
        number = len(positionColorPairs)

        if isinstance(interpolation, (tuple, list)):
            if len(interpolation) is not number:
                raise ColorError("Incorrect number of interpolation entries.")

            interpolations = list(interpolation)

        else:
            interpolations = [interpolation] * number

        self.resetColors()
        positions, colors = zip(*positionColorPairs)

        for i, position, color, interpolation in zip(
                range(number),
                positions,
                colors,
                interpolations
        ):
            compound = self.attr('color')[i]

            position >> compound.attr('color_Position')
            color >> compound.attr('color_Color')
            interpolation >> compound.attr('color_Interp')

        return self

    def resetColors(self):
        """
        Resets the *color* compound array.

        :return: ``self``
        :rtype: :class:`RemapValue`
        """
        indices = self.attr('color').getArrayIndices()

        for index in (0, 1):
            plug = self.attr('color')[index]

            if index in indices:
                plug.attr('color_Position').release()
                plug.attr('color_Color').release(recursive=True)
                plug.attr('color_Interp').release()

            plug.attr('color_Position').set(index)
            plug.attr('color_Color').set([index]*3)
            plug.attr('color_Interp').set('Linear')

        for index in indices:
            if index in (0, 1):
                continue

            plug = self.attr('color')[index]
            plug.attr('color_Position').release()
            plug.attr('color_Color').release(recursive=True)
            plug.attr('color_Interp').release()

            r.removeMultiInstance(plug, b=True)

    @short(plug='p', reuse='re')
    @plugCheck('position')
    def sampleColor(self, position, plug=None, reuse=True):
        """
        Samples an interpolated color at the specified position.

        :param position: the position at which to sample a color
        :type position: float, :class:`~paya.runtime.plugs.Math1D`
        :param bool reuse/re: look for an existing sample for the same
            position value or plug; defaults to True
        :param bool plug/p: force a dynamic output, or indicate that one or
            more of the arguments are plugs to skip checks; defaults to
            ``None``
        :return: The color sample output.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        if reuse:
            try:
                output = self.findCloneWithPosition(position).attr('outColor')

                if plug:
                    return output

                return r.data.Vector(output.get())

            except NoCloneForPositionError:
                pass

        if plug:
            clone = self.createClone()
            clone.attr('inputValue').release()
            position >> clone.attr('inputValue')
            return clone.attr('outColor')

        if self.attr('inputValue').inputs() \
                or self.attr('inputValue').isLocked():
            raise RuntimeError(
                "Can't perform a one-off sample because the "+
                "inputValue attribute is occupied or locked.")

        self.attr('inputValue').set(position)
        out = self.attr('outColor').get()
        return out

    #-------------------------------------------------------|    State management

    @short(skipInputValue='siv')
    def resetNode(self, skipInputValue=False):
        """
        Removes all inputs from this node and resets all attributes to
        defaults.

        :param bool skipInputValue/siv: don't modify the ``inputValue``
            attribute; defaults to False
        :return: ``self``
        :rtype: :class:`RemapValue`
        """
        self.resetValues()
        self.resetColors()

        if not skipInputValue:
            self.attr('inputValue').release()
            self.attr('inputValue').set(0.0)

        for attrName, default in zip(
            ['inputMin', 'inputMax', 'outputMin',
                'outputMax', 'caching', 'frozen', 'nodeState'],
            [0.0, 0.0, 1.0, 0.0, 1.0, False, False, 0]
        ):
            plug = self.attr(attrName)
            plug.release()
            plug.set(default)

        return self

    #-------------------------------------------------------|    Sampling / cloning

    @short(skipInputValue='siv')
    def driveSlave(self, slave, skipInputValue=False):
        """
        Drives another ``remapValue`` node completely.

        :param slave: the node to drive
        :type slave: str, :class:`RemapValue`
        :param bool skipInputValue/siv: don't modify the slave ``inputValue``
            attribute; defaults to False
        :return: ``self``
        :rtype: :class:`RemapValue`
        """
        slave = r.pn(slave)
        slave.resetNode(skipInputValue=skipInputValue)
        
        if not skipInputValue:
            slave.attr('inputValue').release()
            self.attr('inputValue') >> slave.attr('inputValue')

        for attrName in ['inputMin', 'inputMax', 'outputMin', 'outputMax']:
            src = self.attr(attrName)
            dest = slave.attr(attrName)

            src >> dest

        # Values
        srcCompoundArr = self.attr('value')
        destCompoundArr = slave.attr('value')
        srcIndices = srcCompoundArr.getArrayIndices()
        destIndices = destCompoundArr.getArrayIndices()

        for srcIndex in srcIndices:
            srcCompound = srcCompoundArr[srcIndex]
            destCompound = destCompoundArr[srcIndex]

            for name in ['value_Position',
                         'value_FloatValue', 'value_Interp']:
                src = srcCompound.attr(name)
                dest = destCompound.attr(name)

                dest.release(recursive=True)
                src >> dest

        for destIndex in destIndices:
            if destIndex not in srcIndices:
                plug = destCompoundArr[destIndex]

                for name in ['value_Position',
                             'value_FloatValue', 'value_Interp']:
                    plug.attr(name).release(recursive=True)

                r.removeMultiInstance(plug, b=True)

        # Colors
        srcCompoundArr = self.attr('color')
        destCompoundArr = slave.attr('color')
        srcIndices = srcCompoundArr.getArrayIndices()
        destIndices = destCompoundArr.getArrayIndices()

        for srcIndex in srcIndices:
            srcCompound = srcCompoundArr[srcIndex]
            destCompound = destCompoundArr[srcIndex]

            for name in ['color_Position',
                         'color_Color', 'color_Interp']:
                src = srcCompound.attr(name)
                dest = destCompound.attr(name)

                dest.release(recursive=True)
                src >> dest

        for destIndex in destIndices:
            if destIndex not in srcIndices:
                plug = destCompoundArr[destIndex]

                for name in ['color_Position',
                             'color_Color', 'color_Interp']:
                    plug.attr(name).release(recursive=True)

                r.removeMultiInstance(plug, b=True)

    def createClone(self):
        """
        :return: A new ``remapValue`` node, driven by this one.
        :rtype: :class:`RemapValue`
        """
        clone = r.nodes.RemapValue.createNode(
            name='{}_clone'.format(self.basename(sts=True))
        )

        self.driveSlave(clone)
        self.attr('message') >> clone.addAttr('cloneMaster', at='message')

        return clone

    def getClones(self):
        """
        :return: Nodes created using :meth:`createClone`.
        :rtype: [:class:`RemapValue`]
        """
        outputs = self.attr('message').outputs(type='remapValue', plugs=True)
        outputs = [output for output in outputs \
            if output.attrName() == 'cloneMaster']

        return [output.node() for output in outputs]

    def findCloneWithPosition(self, position):
        """
        :param position: the position value or plug
        :type position: float, :class:`~paya.runtime.plugs.Math1D`
        :raises NoCloneForPositionError: No clone was found.
        :return: An existing clone configured for the specified position.
        :rtype: :class:`RemapValue`
        """
        position, pdim, put, pisplug = _mo.info(position).values()

        clones = self.getClones()

        for clone in clones:
            inputs = clone.attr('inputValue').inputs(plugs=True)

            if inputs and pisplug:
                if inputs[0] == position:
                    return clone.attr('outValue')

            elif (not inputs) and (not pisplug):
                if clone.attr('inputValue').get() == position:
                    return clone.attr('outValue')

        raise NoCloneForPositionError

    def updateClones(self):
        """
        Reconnects current clones. This is normally necessary after adding
        or removing ``color`` or ``value`` indices on this node.

        :return: ``self``
        :rtype: :class:`RemapValue`
        """
        for clone in self.getClones():
            self.driveSlave(clone, siv=True)