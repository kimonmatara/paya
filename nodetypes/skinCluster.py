import re
import os
import xml.etree.ElementTree as ET

import maya.cmds as m
from paya.util import short
import pymel.util as _pu
import maya.cmds as m
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
        -   Added 'multi' option
        -   Added 'replace' option

        :param \*args: forwarded to :func:`~pymel.core.animation.skinCluster`
        :param int bindMethod/bm: see Maya help; defaults to 0 (closest)
        :param float dropoffRate/dr: see Maya help; defaults to 4.5
        :param maximumInfluences/mi: see Maya help; defaults to None
        :type maximumInfluences/mi: None, int
        :param str name/n: a name for the skinCluster node; defaults to
            ``None``
        :param int normalizeWeights/nw: see Maya help; defaults to 1
            (interactive)
        :param bool obeyMaximumInfluences/omi: see Maya help; defaults to
            False
        :param int skinMethod/sm: see Maya help; defaults to 0 (linear)
        :param bool toSelectedBones/tsb: see Maya help; defaults to True
        :param int weightDistribution/wd: see Maya help; defaults to 0
            (distance)
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
            'n': name if name else cls.makeName(),
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

        # Exec
        buildArgs = infls + geos
        return r.skinCluster(*buildArgs, **buildKwargs)

    @staticmethod
    def _splitArgsIntoInflsGeos(*args, geometry=None, influence=None):
        # Returns infls, geos

        geos = []
        infls = []

        if geometry:
            geos += [r.PyNode(x) for x in _pu.expandArgs(geometry)]

        if influence:
            infls += [r.PyNode(x) for x in _pu.expandArgs(influence)]

        if args:
            args = [r.PyNode(x) for x in _pu.expandArgs(*args)]

            for arg in args:
                if isinstance(arg, r.nodetypes.Joint):
                    infls.append(arg)

                else:
                    geos.append(arg)

        return infls, geos

    @classmethod
    @short(
        worldSpace='ws',
        positionTolerance='pt',
        method='m',
        loadWeights='lw')
    def createFromXMLFile(cls,
                          xmlfile,
                          method='index',
                          worldSpace=None,
                          positionTolerance=None,
                          loadWeights=True):
        # Open the XML file
        tree = ET.parse(xmlfile)
        root = tree.getroot()

        # Get this information from the first available deformer entry:
        # Shape name
        # Deformer name (will assume it's a skinCluster)
        # influence names

        # Determine shape name
        shapeEntry = root.find('shape')
        shapeName = shapeEntry.attrib['name']
        matches = m.ls(shapeName)

        nm = len(matches)

        if nm is 0:
            raise RuntimeError(
                "Shape doesn't exist: {}".format(shapeName))

        if nm > 1:
            raise RuntimeError(
                "More than one match found for: {}".format(shapeName))

        shape = matches[0]

        # Determine deformer name
        weightEntries = root.findall('weights')

        deformerNames = list(set([weightEntry.attrib['deformer'] \
                         for weightEntry in weightEntries]))

        nm = len(deformerNames)

        if nm > 1:
            raise RuntimeError(
                "More than one deformers specified inside: {}".format(xmlfile)
            )

        if nm is 0:
            raise RuntimeError(
                "No deformer information found inside: {}".format(xmlfile)
            )

        deformer = deformerNames[0]

        # Deal with existing
        existing = r.nodes.SkinCluster.getFromGeo(shape)

        if existing:
            r.delete(existing)

        # Get influences
        joints = [weightEntry.attrib['source'] \
                  for weightEntry in weightEntries]

        for joint in joints:
            if not m.objExists(joint):
                m.createNode('joint', n=joint)

        # Create the deformer
        args = joints + [shape]
        kwargs = {
            'tsb': True,
            'n': deformerNames[0],
            'bm': 0,
            'dr': 4.5,
            'nw': 1,
            'omi': False,
            'sm': 0,
            'wd': 0
        }

        skin = r.skinCluster(*args, **kwargs)

        # Load weights
        if loadWeights:
            skin.loadWeights(xmlfile,
                             shape=shape,
                             method=method,
                             positionTolerance=positionTolerance)

        return skin

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
        :param str name/n: a name for the new skinCluster; defaults to
            ``None``
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
            name = str(self)+'_copy'

        macro['name'] = name

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

    #----------------------------------------------------|    Shape inversion

    @short(name='n')
    def invertShape(self, correctiveShape, name=None):
        """
        Given a corrective geometry for the current skinCluster pose, returns
        a reversed geometry suitable for use as a pre-deformation blend shape
        target.

        :param correctiveShape: the corrective (sculpt) shape
        :type correctiveShape: :class:`str`,
            :class:`~pymel.core.general.Shape`,
            :class:`~pymel.core.general.Transform`
        :param str name/n: a name for the inverted shape node; defaults to
            ``None``
        :return: The pre-deformation target.
        :rtype: :class:`~paya.runtime.nodes.GeometryShape`
        """
        correctiveShape = r.PyNode(correctiveShape).toShape()
        correctiveXf = correctiveShape.getParent()

        posedGeoXf = r.deformer(self, q=True, g=True)[0].getParent()

        outGeoXf = r.PyNode(r.invertShape(posedGeoXf, correctiveXf))
        outGeoShape = outGeoXf.getShape()

        if not name:
            name = outGeoShape.makeName()

        outGeoShape.rename(name)

        mt = re.match(r"^(.*?)Shape$", name)

        if mt:
            outGeoXf.rename(mt.groups()[0])

        else:
            outGeoXf.rename(
                r.Name.make(nt=outGeoShape.nodeType(), xf=True)
            )

        return outGeoXf

    #----------------------------------------------------|    Scene archiving

    @classmethod
    @short(
        vertexConnections='vc',
        weightTolerance='wt',
        weightPrecision='wp',
        makedirs='md'
    )
    def dumpAll(cls,
                destDir,
                clearDir=False, # clear existing XML files
                makedirs=False,
                vertexConnections=None,
                weightPrecision=None,
                weightTolerance=None
                ):
        if os.path.isdir(destDir):
            if clearDir:
                listing = os.listdir(destDir)

                for item in listing:
                    head, tail = os.path.splitext(item)
                    if tail == '.xml':
                        fullPath = os.path.join(destDir, item)
                        os.remove(fullPath)
                        print('Removed file: {}'.format(fullPath))

        else:
            if makedirs:
                os.makedirs(destDir)
                print("Created directory: ", destDir)
            else:
                print("Directory doesn't exist: ", destDir)

        skinClusters = r.ls(type='skinCluster')

        count = 0
        out = []

        for skinCluster in skinClusters:
            shape = r.skinCluster(skinCluster, q=True, geometry=True)[0]
            filename = '{}_on_{}.xml'.format(
                skinCluster.basename(), shape.basename())

            fullpath = os.path.join(destDir, filename)

            skinCluster.dumpWeights(
                fullpath,
                vertexConnections=vertexConnections,
                weightPrecision=weightPrecision,
                weightTolerance=weightTolerance
            )

            count += 1
            out.append(fullpath)

        if count:
            print("Dumped {} skinClusters into: {}".format(count, destDir))
        else:
            print("No skinClusters were found to dump.")

        return out

    @classmethod
    @short(method='m',
           worldSpace='ws',
           positionTolerance='pt')
    def loadAll(cls,
                sourceDir,
                method='index',
                worldSpace=None,
                positionTolerance=None):
        """
        To-Dos:
        - add option to just read weights, without recreating skins
        - add option to filter for shapes
        """
        listing = os.listdir(sourceDir)
        out = []

        for item in listing:
            head, tail = os.path.splitext(item)

            if tail == '.xml':
                fullPath = os.path.join(sourceDir, item)
                out.append(r.nodes.SkinCluster.createFromXMLFile(
                    fullPath,
                    method=method,
                    worldSpace=worldSpace,
                    positionTolerance=positionTolerance,
                    includeShapes=includeShapes,
                    excludeShapes=excludeShapes
                ))

        return out