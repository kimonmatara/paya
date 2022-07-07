import xml.etree.ElementTree as ET
import os.path

import maya.cmds as m
import posixpath
from paya.util import short, toOs, toPosix, without_duplicates
import pymel.util as _pu
import paya.runtime as r

def shortName(x):
    return str(x).split('|')[-1]


class GeometryFilter:

    __config_attrs__ = None # used by getSettings(); if None,
                            # NotImplementedError will be raised

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

    #----------------------------------------------------|    Macros etc.

    def getSettings(self):
        """
        :raises NotImplementedError: the deformer class does not define
            ``__config_attrs__``
        :return: configuration values for this deformer, as a mapping of
            *attribute name: attribute value*
        :rtype: dict
        """
        attrNames = self.__config_attrs__

        if attrNames is None:
            raise NotImplementedError("Not implemented for this deformer.")

        return {attrName: self.attr(attrName).get() for attrName in attrNames}

    def applySettings(self, settings):
        """
        :param dict settings: a dictionary returned by :meth:`getSettings`
        :return: ``self``
        :rtype: :class:`GeometryFilter`
        """
        for attrName, attrValue in settings.items():
            self.attr(attrName).set(attrValue)

        return self

    #----------------------------------------------------|    XML weight dumping

    @short(
        remap='r',
        vertexConnections='vc',
        weightTolerance='wt',
        weightPrecision='wp',
        shape='sh'
    )
    def dumpWeights(
            self,
            filepath,
            shape=None,
            remap=None,
            vertexConnections=False,
            weightPrecision=None,
            weightTolerance=None
    ):
        """
        Dumps this deformer's weights on a single shape to an XML file.

        :param shape: the shape with the weights; if omitted, the first shape
            associated with this deformer is used; defaults to None
        :type shape: str, :class:`~paya.runtime.nodes.DeformableShape`,
            :class:`~paya.runtime.nodes.Transform`
        :param str filepath: the path to the XML file; must be POSIX per
            Maya's preference
        :param str remap/r: see Maya help for
            :func:`~pymel.internal.pmcmds.deformerWeights`; defaults to None
        :param bool vertexConnections/vc: see Maya help for
            :func:`~pymel.internal.pmcmds.deformerWeights`; defaults to False
        :param int weightPrecision/wp: see Maya help for
            :func:`~pymel.internal.pmcmds.deformerWeights`; defaults to None
        :param float weightTolerance/wt: see Maya help for
            :func:`~pymel.internal.pmcmds.deformerWeights`; defaults to None
        :return: ``self``
        :rtype: :class:`~paya.runtime.nodes.GeometryFilter`
        """
        # deformerWeights() is buggy. For a reliable export:
        # - Don't specify deformers to include; instead, specify deformers on
        #   on the geometry to *skip* (via -sk)
        # - Specify the shape via -sh

        #--------------|    Prep args

        if shape is None:
            shapes = r.deformer(self, q=True, g=True)

            if shapes:
                shape = shapes[0]

            else:
                raise RuntimeError("Could not resolve shape.")

        else:
            shape = r.PyNode(shape).toShape()

        allDeformers = shape.history(type='geometryFilter')
        skip = list(map(str, filter(lambda x: x != self, allDeformers)))

        parentdir, filename = posixpath.split(filepath)

        execArgs = [filename]

        execKwargs = {
            'path': parentdir,
            'vertexConnections': vertexConnections,
            'shape': str(shape),
            'skip': skip,
            'format': 'XML',
            'export': True
        }

        if remap is not None:
            execKwargs['remap'] = remap
            
        if weightPrecision is not None:
            execKwargs['weightPrecision'] = weightPrecision

        if weightTolerance is not None:
            execKwargs['weightTolerance'] = weightTolerance

        m.deformerWeights(*execArgs, **execKwargs)

        return self

    @short(
        ignoreName='ig',
        method='m',
        positionTolerance='pt',
        remap='r',
        shape='sh',
        worldSpace='ws'
    )
    def loadWeights(
            self,
            filepath,
            ignoreName=False,
            method='index',
            positionTolerance=None,
            remap=None,
            shape=None,
            worldSpace=None
    ):
        """
        Imports deformer weights for a specific shape from an XML file.

        :param str filepath: the path to the file (POSIX)
        :param bool ignoreName/ig: see Maya help for
            :func:`~pymel.internal.pmcmds.deformerWeights`; defaults to None
        :param str method/m:  see Maya help for
            :func:`~pymel.internal.pmcmds.deformerWeights`; defaults to 'index'
        :param float positionTolerance/pt: see Maya help for
            :func:`~pymel.internal.pmcmds.deformerWeights`; defaults to None
        :param str remap/r: see Maya help for
            :func:`~pymel.internal.pmcmds.deformerWeights`; note that this may
            be auto-populated to force a shape registration; defaults to None
        :param shape: the shape that carries the weights; if omitted, a best-
            match shape is sought amongst the deformer members and the XML
            shapes; defaults to None
        :param bool worldSpace/ws: see Maya help for
            :func:`~pymel.internal.pmcmds.deformerWeights`; defaults to None
        :return: ``self``
        :rtype: :class:`GeometryFilter`
        """
        userRemap = remap
        remap = None

        #------------------------------------------------|    Resolve shape

        _self = str(self)
        dshapes = m.deformer(_self, q=True, g=True)

        if not dshapes:
            raise RuntimeError("Deformer has no shape connections.")

        _dshapes = list(map(shortName, dshapes))

        tree = ET.parse(toOs(filepath))
        root = tree.getroot()

        weightEntries = root.findall('weights')

        _xshapes = without_duplicates(
            [weightEntry.attrib['shape'] for weightEntry in weightEntries]
        )

        if shape is None:
            for _xshape in _xshapes:
                for dshape, _dshape in zip(dshapes, _dshapes):
                    if _dshapes == _xshape:
                        shape = dshape
                        _shape = shortName(shape)
                        break

            if shape is None:
                shape = dshapes[0]
                _shape = shortName(shape)

                remap = '{};{}'.format(_xshapes[0], _shape)
                skip = _xshapes[1:]

            else:
                skip = [_xshape for _xshape in _xshapes if _xshape != _shape]

        else:
            shape = str(shape)
            _shape = shortName(shape)

            if _shape in _xshapes:
                skip = [_xshape for _xshape in _xshapes if _xshape != _shape]

            else:
                remap = '{};{}'.format(_xshapes[0], _shape)
                skip = _xshapes[1:]

        #------------------------------------------------|    Complete signature

        if remap is None:
            remap = userRemap

        elif userRemap is not None:
            raise ValueError("'remap' already in use")

        pdir, filename = os.path.split(filepath)

        kwargs = {
            'path': pdir,
            'skip': skip,
            'im': True,
            'format': 'XML',
            'method': method,
            'shape': shape,
            'deformer': _self
        }

        if positionTolerance is not None:
            kwargs['positionTolerance'] = positionTolerance

        if worldSpace is not None:
            kwargs['worldSpace'] = worldSpace

        if ignoreName is not None:
            kwargs['ignoreName'] = ignoreName

        if remap is not None:
            kwargs['remap'] = remap

        m.deformerWeights(filename, **kwargs)

        return self