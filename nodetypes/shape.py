from paya.util import short
import paya.runtime as r


class Shape:

    #-----------------------------------------------------------|    Constructors

    @classmethod
    @short(
        name='n',
        parent='p',
        conformShapeName='csn',
        intermediate='i'
    )
    def createShape(
            cls,
            name=None,
            parent=None,
            conformShapeName=None,
            intermediate=False
    ):
        """
        Basic shape constructor.

        :param str name/n: the shape name; defaults to a contextual name
        :param parent/p: a custom destination parent; defaults to None
        :type parent/p: None, str, :class:`~paya.runtime.nodes.Transform`
        :param bool conformShapeName/csn: ignored if *parent* was omitted;
            rename the shape after it is reparented; defaults to True if
            *parent* was provided, otherwise False
        :param bool intermediate/i: create the shape as an intermediate
            object; defaults to False
        :return: The shape node.
        :rtype: :class:`Shape`
        """
        kwargs = {'ss': True}

        if parent:
            kwargs['parent'] = parent

        if name is None:
            if parent and conformShapeName:
                name = str(parent).split('|')[-1]+'Shape'

            else:
                name = cls.makeName()

        kwargs['name'] = name

        shape = cls.createNode(**kwargs)

        if intermediate:
            shape.attr('intermediateObject').set(True)

        return shape

    #--------------------------------------------------------|    Shape / transform management

    def toShape(self):
        """
        :return: If this node is a transform, its first shape child;
            otherwise, the node itself.
        :rtype: :class:`~paya.runtime.nodes.Shape` or
            :class:`~paya.runtime.nodes.Transform`
        """
        return self

    def toTransform(self):
        """
        :return: If this node is a shape, its parent; otherwise, the node
            itself.
        :rtype: :class:`~paya.runtime.nodes.Shape` or
            :class:`~paya.runtime.nodes.Transform`
        """
        return self.getParent()

    #-----------------------------------------------------------|    Name management

    def conformName(self):
        """
        Conforms this shape's name to a Maya-standard format derived from the
        transform parent.

        :return: ``self``
        :rtype: :class:`Shape`
        """
        # Pseudo:
        #     If this shape is intermediate:
        #         give it lowest priority and derive a name from the xform
        #     else:
        #         rename all intermediate shapes to temporary
        #         give this least priority amongst hero shapes
        #         rename intermediate shapes back to original and let Maya
        #         append numbers where needed

        xf = self.getParent()
        bn = xf.basename()
        isInterm = self.isIntermediate()

        def withoutSelf(itr):
            return [member for member in itr if member != self]

        heroShapes = withoutSelf(xf.getHeroShapes())
        intermShapes = withoutSelf(xf.getIntermediateShapes())

        if isInterm:
            otherShapes = heroShapes + intermShapes

        else:
            otherShapes = heroShapes
            origIntermNames = []

            for shape in intermShapes:
                origIntermNames.append(shape.basename())
                shape.rename('temporary_name')

        reservedNames = [otherShape.basename() for otherShape in otherShapes]

        count = 0

        while True:
            name = '{}Shape'.format(bn)

            if count:
                name += str(count)

            if name in reservedNames:
                count += 1
                continue

            break

        self.rename(name)

        if not isInterm:
            for shape, origName in zip(
                intermShapes, origIntermNames
            ):
                shape.rename(origName)

        return self