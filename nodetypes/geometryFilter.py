import os

import maya.cmds as m
import paya.lib.xmlweights as _xw
from paya.util import short
import pymel.util as _pu
import paya.runtime as r


class GeometryFilter:

    #----------------------------------------------------|    Loader

    @classmethod
    def getFromGeo(cls, *geometry):
        """
        :param \*geometry: the geometries to inspect
        :type \*geometry: list, tuple,
            :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.DeformableShape`,
        :return: Deformers of this type detected across the specified
            geometries.
        :rtype: [:class:`~paya.runtime.nodes.GeometryFilter`]
        """
        out = []
        geos = list(map(r.PyNode, _pu.expandArgs(*geometry)))

        if not geos:
            raise RuntimeError("No geometries specified.")

        shapes = [geo.toShape() for geo in geos]

        for shape in shapes:
            history = shape.history(type=cls.__melnode__)

            if history:
                for deformer in history:
                    assocGeo = r.deformer(deformer, q=True, g=True)

                    if assocGeo:
                        assocGeo = map(r.PyNode, assocGeo)
                        if any([shape in shapes for shape in assocGeo]):
                            out.append(deformer)

        _out = []

        for item in out:
            if item not in _out:
                _out.append(item)

        return _out

    #----------------------------------------------------|    DG inspections

    def getShapes(self):
        """
        Convenience wrapper for
        :func:`deformer(q=True, g=True)<pymel.core.animation.deformer>`.

        :rtype: The shapes affected by this deformer.
        :return: [:class:`~paya.runtime.nodes.DeformableShape`]
        """
        out = r.deformer(self, q=True, g=True)

        if not out:
            out = []

        return out

    #----------------------------------------------------|    XML weight I/O

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
        Wrapper for :func:`~pymel.internal.pmcmds.deformerWeights` in 'export'
        mode. Arguments are post-processed to ensure that only relevant
        deformers and shapes are included. See Maya help for
        :func:`deformerWeights` for complete flag information.

        :param str filepath: the path to the XML file.
        :param shape/sh: the shape to export weights for; if omitted, all
            associated shapes are included
        :type shape/sh: list, tuple, str, :class:`~pymel.core.general.PyNode`
        :return: ``self``
        :rtype: :class:`GeometryFilter`
        """
        _xw.dump(
            filepath,
            df=self,
            sh=shape,
            r=remap,
            vc=vertexConnections,
            wp=weightPrecision,
            wt=weightTolerance,
            at=attribute,
            dv=defaultValue
        )

        return self

    @short(
        shape='sh',
        method='m',
        worldSpace='ws',
        attribute='at',
        ignoreName='ig',
        positionTolerance='pt',
        remap='r'
    )
    def loadWeights(
            self,
            filepath,
            shape=None,
            method='index',
            worldSpace=None,
            attribute=None,
            ignoreName=None,
            positionTolerance=None,
            remap=None
    ):
        """
        Wrapper for :func:`~pymel.internal.pmcmds.deformerWeights` in 'import'
        mode. Arguments are post-processed to ensure that only relevant
        deformers and shapes are included. See Maya help for
        :func:`deformerWeights` for complete flag information.

        :param str filepath: the path to the XML file.
        :param shape/sh: the shape to export weights for; if omitted, all
            associated shapes are included
        :type shape/sh: list, tuple, str, :class:`~pymel.core.general.PyNode`
        :return: ``self``
        :rtype: :class:`GeometryFilter`
        """
        _xw.load(
            filepath,
            df=self,
            sh=shape,
            r=remap,
            m=method,
            ws=worldSpace,
            at=attribute,
            ig=ignoreName,
            pt=positionTolerance
        )

        return self

    @short(
        sourceShape='ssh',
        destShape='dsh',
        sourceUVSet='suv',
        destUVSet='duv',
        method='m'
    )
    def copyWeightsFrom(
            self,
            sourceDeformer,
            sourceShape=None,
            destShape=None,
            sourceUVSet=None,
            destUVSet=None,
            method='index'
    ):
        """
        Copies weights from another deformer to this one.

        :param sourceDeformer: the deformer to copy weights from
        :type sourceDeformer: str, :class:`~paya.runtime.nodes.GeometryFilter`
        :param sourceShape/ssh: the shape to copy weights from; if omitted,
            defaults to the first detected shape
        :type sourceShape/ssh: str, :class:`~paya.runtime.nodes.DagNode`
        :param destShape/dsh: the shape to copy weights to; if omitted,
            defaults to the first detected shape
        :type destShape/dsh: str, :class:`~paya.runtime.nodes.DagNode`
        :param sourceUVSet/suv: if specified, 'method' will be overriden to
            'uv'; if omitted, and 'method' is 'uv', the current UV set will
            be used; defaults to None
        :type sourceUVSet/suv: str, None
        :param destUVSet/duv: if specified, 'method' will be overriden to
            'uv'; if omitted, and 'method' is 'uv', the current UV set will
            be used; defaults to None
        :type destUVSet/duv: str, None
        :param str method/m: one of:

            - ``index`` (via XML)
            - ``bilinear`` (via XML)
            - ``barycentric`` (via XML)
            - ``nearest`` (via XML)
            - ``over`` (via XML)

            - ``closestPoint`` (in-scene)
            - ``closestComponent`` (in-scene)
            - ``uv`` (in-scene)
            - ``rayCast`` (in-scene)

        :return: ``self``
        :rtype: :class:`GeometryFilter`
        """
        sourceDeformer = r.PyNode(sourceDeformer)

        if sourceShape:
            sourceShape = r.PyNode(sourceShape).toShape()

        else:
            sourceShape = sourceDeformer.getShapes()[0]

        if destShape:
            destShape = r.PyNode(destShape).toShape()

        else:
            destShape = self.getShapes()[0]

        if sourceUVSet or destUVSet:
            method = 'uv'

        if method in ('over', 'index', 'nearest', 'bilinear', 'barycentric'):
            self._copyWeightsViaXMLFrom(
                sourceDeformer, sourceShape, destShape, method
            )

        else:
            self._copyWeightsViaCmdFrom(
                sourceDeformer,
                sourceShape,
                destShape,
                method,
                sourceUVSet=sourceUVSet,
                destUVSet=destUVSet
            )

    def _copyWeightsViaXMLFrom(
            self,
            sourceDeformer,
            sourceShape,
            destShape,
            method
    ):
        kwargs = {}

        bothSkins = sourceDeformer.__melnode__ == \
                    'skinCluster' and self.__melnode__ == 'skinCluster'

        if bothSkins:
            kwargs['attribute'] = 'blendWeights'

        tmpPath = _xw.getTempFilePath()

        vertexConnections = method in ('bilinear', 'barycentric')
        sourceDeformer.dumpWeights(tmpPath, vc=vertexConnections, **kwargs)

        remap = [
            '{};{}'.format(str(sourceDeformer), str(self)),
            '{};{}'.format(sourceShape.basename(), destShape.basename())
        ]

        try:
            self.loadWeights(tmpPath, m=method, r=remap, **kwargs)

        finally:
            os.remove(tmpPath)

    def _copyWeightsViaCmdFrom(
            self,
            sourceDeformer,
            sourceShape,
            destShape,
            method,
            sourceUVSet=None,
            destUVSet=None
    ):
        if sourceUVSet or destUVSet:
            method = 'uv'

        if method == 'uv':
            if not sourceUVSet:
                sourceUVSet = sourceShape.getCurrentUVSetName()

            if not destUVSet:
                destUVSet = destShape.getCurrentUVSetName()

        kwargs = {'nm': True}

        uv = method == 'uv'

        if method == 'uv':
            kwargs['uvSpace'] = [sourceUVSet, destUVSet]

        else:
            kwargs['sa'] = method

        _sourceDeformer = str(sourceDeformer)
        _destDeformer = str(self)

        if sourceDeformer.__melnode__ == 'skinCluster' \
            and self.__melnode__ == 'skinCluster':

            cmd = m.copySkinWeights
            kwargs['ss'] = _sourceDeformer
            kwargs['ds'] = _destDeformer
            kwargs['ia'] = 'oneToOne'

        else:
            cmd = m.copyDeformerWeights
            kwargs['sd'] = _sourceDeformer
            kwargs['ds'] = _destDeformer
            kwargs['ss'] = str(sourceShape)
            kwargs['ds'] = str(destShape)

        cmd(**kwargs)