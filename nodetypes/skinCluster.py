import maya.cmds as m
from paya.util import short
import pymel.util as _pu
import paya.runtime as r


class SkinCluster:

    #------------------------------------------------------------|    Constructor

    @classmethod
    @short(
        bindMethod='bm',
        dropoffRate='dr',
        maximumInfluences='mi',
        name='n',
        normalizeWeights='nw',
        obeyMaximumInfluences='omi',
        skinMethod='sm',
        toSelectedBones='tsb',
        weightDistribution='wd',
        nameFromGeo='nfg',
        geometry='g',
        influence='inf',
        replace='rep'
    )
    def create(
            cls,
            *args,
            bindMethod=0, # closest
            dropoffRate=4.5,
            maximumInfluences=None,
            name=None,
            normalizeWeights=1, # interactive
            obeyMaximumInfluences=False,
            skinMethod=0, # linear
            toSelectedBones=True,
            weightDistribution=0, # distance
            nameFromGeo=False,
            geometry=None,
            influence=None,
            multi=False,
            replace=False,
            **kwargs
    ):
        """
        Lightweight convenience wrapper / constructor for skinClusters, with the
        following differences from the standard
        :func:`~pymel.core.animation.skinCluster` command:

        -   Positional arguments can be omitted, and the 'geometry' and
            'influence' keyword arguments used instead on creation
        -   A select subset of flags are pre-loaded with common defaults (see
            below)
        -   Added 'nameFromGeo / nag' option
        -   Added 'multi' option
        -   Added 'replace' option

        :param \*args: forwarded to :func:`~pymel.core.animation.skinCluster`
        :param int bindMethod/bm: see Maya help; defaults to 0 (closest)
        :param float dropoffRate/dr: see Maya help; defaults to 4.5
        :param maximumInfluences/mi: see Maya help; defaults to None
        :type maximumInfluences/mi: None, int
        :param name/n: one or more name elements for the deformer; ignored if
            'nameFromGeo' is True; defaults to None
        :type name/n: list, tuple, None, str, int
        :param int normalizeWeights/nw: see Maya help; defaults to 1
            (interactive)
        :param bool obeyMaximumInfluences/omi: see Maya help; defaults to
            False
        :param int skinMethod/sm: see Maya help; defaults to 0 (linear)
        :param bool toSelectedBones/tsb: see Maya help; defaults to True
        :param int weightDistribution/wd: see Maya help; defaults to 0
            (distance)
        :param bool nameFromGeo/nfg: derive deformer names from geometry
            names; defaults to False
        :param geometry/g: the geometry to bind to; defaults to None
        :type geometry/g: list, tuple,
            :class:`~paya.runtime.nodes.DeformableShape`,
            :class:`~paya.runtime.nodes.Transform`
        :param influence/inf: one or more influences; defaults to None
        :type influence/inf: list, tuple,
            :class:`~paya.runtime.nodes.Transform`
        :param bool multi: set this to True to create multiple skinClusters
            across all passed geometries; defaults to False
        :param bool replace/rep: remove any existing skinClusters from the passed
            geometries; defaults to False
        :param \*\*kwargs: forwarded to
            :func:`~pymel.core.animation.skinCluster`
        :return: :class:`SkinCluster` or [:class:`SkinCluster`]
        """
        #-------------------------------------------|    Prep

        # Sift geos / infls

        infls, geos = cls._splitArgsIntoInflsGeos(
            *args, influence=influence, geometry=geometry)

        numGeos = len(geos)
        numInfls = len(infls)

        if not numGeos:
            raise RuntimeError("No geometries specified.")

        if not numInfls:
            raise RuntimeError("No influences specified.")

        buildKwargs = {
            'bm': bindMethod,
            'dr': dropoffRate,
            'nw': normalizeWeights,
            'sm': skinMethod,
            'tsb': toSelectedBones,
            'wd': weightDistribution
        }

        if maximumInfluences is not None:
            buildKwargs['mi'] = maximumInfluences
            buildKwargs['omi'] = obeyMaximumInfluences

        buildKwargs.update(kwargs)

        if numGeos > 1:
            if multi:
                out = []

                for geo in geos:
                    result = cls.create(
                        inf=infls,
                        g=geo,
                        nfg=nameFromGeo,
                        n=name,
                        rep=replace,
                        **buildKwargs
                    )

                    out.append(result)

                return out

            else:
                raise RuntimeError(
                    "Set 'multi' to True to bind more than one geometry."
                )

        if replace:
            existing = []

            for geo in geos:
                existing += cls.getFromGeo(geo)

            if existing:
                r.delete(existing)

        # Resolve name

        if nameFromGeo:
            geoBasename = geos[0
                ].toTransform().basename(sts=True, sns=True)

            name = cls.makeName(geoBasename)

        else:
            name = cls.makeName(name)

        buildKwargs['n'] = name

        # Exec
        buildArgs = infls + geos
        return r.skinCluster(*buildArgs, **buildKwargs)

    @staticmethod
    def _splitArgsIntoInflsGeos(*args, geometry=None, influence=None):
        geos = []
        infls = []

        items = list(map(r.PyNode, _pu.expandArgs(*args)))

        for item in items:
            if isinstance(item, r.nodetypes.DeformableShape):
                geos.append(item)

            elif isinstance(item, r.nodetypes.Transform):
                shapes = item.getShapes(noIntermediate=True)

                states = [isinstance(shape,
                    r.nodetypes.DeformableShape) for shape in shapes]

                if all(states):
                    geos.append(item)

                elif not any(states):
                    infls.append(item)

                else:
                    raise RuntimeError(
                        "Can't determine whether {} is a geometry or "+
                        "influence. Pass through 'influence' or 'geometry'"+
                        " to disambiguate.".format(item)
                    )

            else:
                raise RuntimeError(
                        "Can't determine whether {} is a geometry or "+
                        "influence. Pass through 'influence' or 'geometry'"+
                        " to disambiguate.".format(item)
                    )

        if geometry:
            geos += list(map(r.PyNode, _pu.expandArgs(geometry)))

        if influence:
            infls += list(map(r.PyNode, _pu.expandArgs(influence)))

        return infls, geos

    #------------------------------------------------------------|    Macros

    def macro(self):
        """
        :return: A simplified representation of this deformer that can
            be used by :meth:`createFromMacro` to recreate it.
        :rtype: dict
        """
        macro = r.nodes.DependNode.macro(self)

        macro['influence'] = [str(inf) for inf in self.getInfluence()]

        _self = macro['name']

        for flag in ['bindMethod', 'maximumInfluences', 'obeyMaxInfluences',
                     'skinMethod', 'weightDistribution']:
            macro[flag] = m.skinCluster(_self, q=True, **{flag:True})

        macro['geometry'] = [str(shape) for shape in self.getShapes()]

        for attrName in ['deformUserNormals', 'useComponents',
                         'envelope', 'dqsSupportNonRigid']:
            macro[attrName] = self.attr(attrName).get()

        macro['dqsScale'] = dqs = {}

        wlist = [self.attr('dqsScale')]
        wlist += wlist[0].getChildren()

        for plug in wlist:
            val = plug.get()
            inputs = plug.inputs(plugs=True)

            if inputs:
                input = str(inputs[0])

            else:
                input = None

            dqs[plug.attrName()] = {'value': val, 'input': input}

        return macro

    @classmethod
    def createFromMacro(cls, macro, **overrides):
        """
        Recreates this skinCluster using the type of macro returned by
        :meth:`macro`.

        :param dict macro: the type of macro returned by :meth:`macro`.
        :param \*\*overrides: overrides to the macro, passed-in as keyword
            arguments
        :return: The reconstructed skinCluster.
        :rtype: :class:`SkinCluster`
        """
        macro = macro.copy()
        macro.update(overrides)

        shape = macro['geometry'][0]
        influences = macro['influence']

        buildArgs = influences + [shape]
        buildKwargs = {k: macro[k] for k in [
            'bindMethod', 'maximumInfluences', 'obeyMaxInfluences',
            'skinMethod', 'weightDistribution', 'name']}

        buildKwargs['toSelectedBones'] = True

        skin = r.skinCluster(*buildArgs, **buildKwargs)

        config = {k: macro[k] for k in
            ['deformUserNormals', 'useComponents',
             'envelope', 'dqsSupportNonRigid']}

        for k, v in config.items():
            skin.attr(k).set(v)

        for attrName, attrInfo in macro['dqsScale'].items():
            input = attrInfo['input']
            value = attrInfo['value']
            plug = skin.attr(attrName)

            if input:
                try:
                    r.connectAttr(input, plug)

                except RuntimeError:
                    r.warning(
                        ("Couldn't connect {} into {}; "+
                         "setting the value instead.").format(input, plug)
                    )

                    plug.set(value)

            else:
                plug.set(value)

        return skin

    #----------------------------------------------------|    Copying

    @short(
        name='n',
        replace='rep',
        sourceUVSet='suv',
        destUVSet='duv',
        method='m',
        weights='w'
    )
    def copyTo(
            self,
            geo,
            name=None,
            replace=True,
            weights=True,
            method='index',
            sourceUVSet=None,
            destUVSet=None
    ):
        """
        Copies this skinCluster to the specified geometry.

        :param geo: the geometry to copy to
        :type geo: str, :class:`~paya.runtime.nodes.DagNode`
        :param name/n: one or more name elements for the new skinCluster;
            defaults to None
        :type name/n: None, str, int, list, tuple
        :param bool replace/rep: if the destination geometry already has a
            skinCluster, remove it; defaults to True
        :param bool weights/w: copy weights too; defaults to True
        :param str method/m: the weight-copying method; one of:

            - ``index`` (via XML)
            - ``bilinear`` (via XML)
            - ``barycentric`` (via XML)
            - ``nearest`` (via XML)
            - ``over`` (via XML)

            - ``closestPoint`` (in-scene)
            - ``closestComponent`` (in-scene)
            - ``uv`` (in-scene)
            - ``rayCast`` (in-scene)

        :param sourceUVSet/suv: if specified, 'method' will be overriden to
            'uv'; if omitted, and 'method' is 'uv', the current UV set will
            be used; defaults to None
        :type sourceUVSet/suv: str, None
        :param destUVSet/duv: if specified, 'method' will be overriden to
            'uv'; if omitted, and 'method' is 'uv', the current UV set will
            be used; defaults to None
        :type destUVSet/duv: str, None
        :return: The new skinCluster.
        :rtype: :class:`SkinCluster`
        """
        geoShape = r.PyNode(geo).toShape()

        if replace:
            for existing in self.getFromGeo(geoShape):
                r.delete(existing)

        macro = self.macro()
        macro['geometry'] = [geoShape]

        if not name:
            geoXf = geoShape.getParent()
            name = geoXf.basename(sns=True)

        macro['name'] = self.makeName(name)

        newSkin = self.createFromMacro(macro)

        if weights:
            newSkin.copyWeightsFrom(
                self,
                dsh=geoShape,
                suv=sourceUVSet,
                duv=destUVSet,
                m=method
            )

        return newSkin

    def _padBlendWeights(self):
        # Set any missing array indices on ``.blendWeights`` to 0.0. This is a
        # workaround for the following bug:
        #
        # When the ``.blendWeights`` array is sparsely populated, dumping and
        # reloading the attribute via :func:`deformerWeights` results in wrong
        # index mapping.

        plug = self.attr('blendWeights')
        indices = plug.getArrayIndices()
        shape = self.getShapes()[0]
        numVerts = shape.numVertices()

        missingIndices = list(sorted(set(range(numVerts))-set(indices)))

        _plug = str(plug)

        for index in missingIndices:
            m.setAttr('{}[{}]'.format(_plug, index), 0.0)

        return missingIndices

    @short(
        remap='r',
        vertexConnections='vc',
        weightTolerance='wt',
        weightPrecision='wp',
        shape='sh',
        attribute='at',
        defaultValue='dv'
    )
    def dumpWeights(
            self,
            filepath,
            shape=None,
            remap=None,
            vertexConnections=None,
            weightPrecision=None,
            weightTolerance=None,
            attribute=None,
            defaultValue=None
    ):
        """
        Overloads :meth:`paya.runtime.nodes.GeometryFilter.dumpWeights` to
        include DQ blend weights by default, and to work around this bug:

        When the ``.blendWeights`` array on a skinCluster is sparsely
        populated (as is typically the case), dumping and reloading it
        via ``deformerWeights(at='blendWeights')`` results in a wrong
        index mapping.
        """
        if attribute is None:
            attribute = []

        else:
            attribute = list(_pu.expandArgs(attribute))

        attribute.append('blendWeights')
        indicesToRemove = self._padBlendWeights()

        r.nodes.GeometryFilter.dumpWeights(
            self,
            filepath,
            sh=shape,
            at=attribute,
            r=remap,
            vc=vertexConnections,
            wp=weightPrecision,
            wt=weightTolerance,
            dv=defaultValue
        )

        _plug = '{}.blendWeights'.format(str(self))

        for index in indicesToRemove:
            m.removeMultiInstance('{}[{}]'.format(_plug, index))

        return self