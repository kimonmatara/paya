from paya.util import short
import paya.runtime as r


class RemapValue:

    #--------------------------------------------------|    Color config

    def resetColors(self):
        """
        Resets the entire ``color`` compound multi to the state it would
        be had the node just been created.

        :return: ``self``
        :rtype: :class:`RemapValue`
        """
        colMulti = self.attr('color')
        indices = colMulti.getArrayIndices()

        hasZero = 0 in indices
        hasOne = 1 in indices

        if not hasZero:
            colMulti[0].attr('color_Position').set(0.0)
            colMulti[0].attr('color_Color').set([0, 0, 0])
            colMulti[0].attr('color_Interp').set(1)

        if not hasZero:
            colMulti[1].attr('color_Position').set(1.0)
            colMulti[1].attr('color_Color').set([1, 1, 1])
            colMulti[1].attr('color_Interp').set(1)

        for index in indices:
            compound = colMulti[index]
            compound.attr('color_Position').release()
            compound.attr('color_Interp').release()
            compound.attr('color_Color').release(recursive=True)

            if index in (0, 1):
                compound.attr('color_Position').set(index)
                compound.attr('color_Color').set([index] * 3)
                compound.attr('color_Interp').set(1)

            else:
                r.removeMultiInstance(colMulti[index], b=True)

    @short(interpolation='i')
    def setColors(self, positions, colors, interpolation='Linear'):
        """
        Defines colors at the specified positions.

        :param positions: a list of color positions
        :type positions: [float, :class:`~paya.runtime.plugs.Math1D`]
        :param colors: a list of color vector values or plugs
        :type colors: [tuple, lists, :class:`~paya.runtime.data.Vector`,
            :class:`~paya.runtime.plugs.Vector`]
        :param interpolation/i: an enum or index for the 'interpolation'
            drop down for each color, where:

            0: 'None'
            1: 'Linear' (the default)
            2: 'Smooth'
            3: 'Spline
        :type interpolation/i: str, int, :class:`~paya.runtime.plugs.Math1D`
        :return: ``self``
        :rtype: :class:`RemapValue`
        """
        self.resetColors()

        for i, position, color in zip(
            range(len(positions)),
            positions,
            colors
        ):
            compound = self.attr('color')[i]
            position >> compound.attr('color_Position')
            color >> compound.attr('color_Color')
            interpolation >> compound.attr('color_Interp')

        return self

    #--------------------------------------------------|    Sampling

    def sampleColor(self, position):
        """
        Samples an interpolated color at the specified position.

        :param position: the position at which to sample the color
        :type position: float, str, :class:`~paya.runtime.plugs.Math1D`
        :return: The sampled color.
        :rtype: :class:`~paya.runtime.plugs.Vector`
        """
        name = type(self).makeName('{}_clone', format(self.basename()))
        dup = self.duplicate(n=name)[0]
        dup.attr('inputValue').unlock()
        position >> dup.attr('inputValue')

        srcIndices = self.attr('color').getArrayIndices()

        for index in srcIndices:
            srcCompound = self.attr('color')[index]
            destCompound = dup.attr('color')[index]

            for attrName in ('color_Position', 'color_Interp', 'color_Color'):
                src = srcCompound.attr(attrName)
                dest = destCompound.attr(attrName)

                src >> dest
                dest.lock()

        destIndices = dup.attr('color').getArrayIndices()

        for destIndex in destIndices:
            if destIndex in srcIndices:
                continue

            destCompound = dup.attr('color')[destIndex]

            for attrName in (
                    'color_Position', 'color_Color', 'color_Interp'):
                plug = destCompound.attr(attrName)
                plug.release()

            r.removeMultiInstance(destCompound, b=True)

        return dup.attr('outColor')