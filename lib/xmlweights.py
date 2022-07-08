from tempfile import gettempdir
import os
import posixpath

import maya.cmds as m
import pymel.util as _pu

from paya.util import short, toPosix, without_duplicates
import paya.runtime as r


#------------------------------------------------------------|    Utilities

def getTempFilePath():
    num = 1
    td = gettempdir()

    while True:
        filename = 'payaXMLTemp{}.xml'.format(num)
        filepath = os.path.join(td, filename)

        if os.path.isfile(filepath):
            num += 1

        else:
            break

    return toPosix(filepath)

def shortName(x):
    return str(x).split('|')[-1]

def getShapesFromDeformers(deformers):
    out = []

    for deformer in deformers:
        shapes = m.deformer(deformer, q=True, g=True)

        if shapes:
            out += shapes

    return without_duplicates(out)

def getDeformersFromShapes(shapes):
    out = []

    for shape in shapes:
        shape = r.PyNode(shape)
        deformers = r.nodes.GeometryFilter.getFromGeo(shape)
        out += deformers

    out = list(map(str, out))
    return without_duplicates(out)

def isInside(x, members):
    _x = shortName(x)
    _members = list(map(shortName, members))
    return _x in _members

#------------------------------------------------------------|    Arg management

def fixKwargs(kwargs):
    # The only reliable way to run deformerWeights is to specify shapes via
    # -sh and deformers to skip via -df

    reqShapes = kwargs.get('shape', [])
    reqDeformers = kwargs.get('deformer', [])
    reqSkips = kwargs.get('skips', [])
    outSkips = []
    outShapes = []
    outDeformers = []

    if reqShapes:
        reqShapes = list(map(str, _pu.expandArgs(reqShapes)))

    if reqDeformers:
        reqDeformers = list(map(str, _pu.expandArgs(reqDeformers)))

    if reqSkips:
        reqSkips = list(map(str, _pu.expandArgs(reqSkips)))

    if reqShapes:
        outShapes = reqShapes

        if reqDeformers:
            assocDeformers = getDeformersFromShapes(reqShapes)
            outSkips = [d for d in assocDeformers if d not in reqDeformers]

    elif reqDeformers:
        outShapes = getShapesFromDeformers(reqDeformers)
        assocDeformers = getDeformersFromShapes(outShapes)

        outSkips = [d for d in assocDeformers if d not in reqDeformers]

    if reqSkips:
        outSkips = reqSkips + outSkips
        outSkips = without_duplicates(outSkips)

    if outSkips:
        kwargs['skip'] = outSkips

    if outShapes:
        kwargs['shape'] = outShapes

    if outDeformers:
        kwargs['deformer'] = outDeformers

#------------------------------------------------------------|    Basic I/O

@short(
    shape='sh',
    deformer='df',
    vertexConnections='vc',
    attribute='at',
    remap='r',
    weightPrecision='wp',
    weightTolerance='wt',
    skip='sk',
    defaultValue='dv'
)
def dump(
        filepath,
        shape=None,
        deformer=None,
        vertexConnections=None,
        weightPrecision=None,
        weightTolerance=None,
        remap=None,
        attribute=None,
        skip=None,
        defaultValue=None
):
    """
    Wrapper for :func:`~pymel.internal.pmcmds.deformerWeights` in 'export'
    mode. Arguments are post-processed to ensure that only requested deformers
    and shapes are included. See Maya help for :func:`deformerWeights` for
    flag information.
    """
    filepath = toPosix(filepath)
    pdir, filename = posixpath.split(filepath)

    kwargs = {'path': pdir, 'export': True}

    if skip is not None:
        kwargs['skip'] = skip

    if attribute is not None:
        kwargs['attribute'] = attribute

    if defaultValue is not None:
        kwargs['defaultValue'] = defaultValue

    if deformer:
        deformer = [str(x) for x in _pu.expandArgs(deformer)]

    if shape:
        shape = [str(x) for x in _pu.expandArgs(shape)]

    for name, val in zip(
        ['shape', 'deformer', 'vertexConnections', 'weightPrecision',
         'weightTolerance', 'remap', 'attribute'],
        [shape, deformer, vertexConnections, weightPrecision,
         weightTolerance, remap, attribute]
    ):
        if val is not None:
            kwargs[name] = val

    fixKwargs(kwargs)

    m.deformerWeights(filename, **kwargs)

@short(
    deformer='df',
    shape='sh',
    method='m',
    worldSpace='ws',
    attribute='at',
    ignoreName='ig',
    positionTolerance='pt',
    remap='r',
    skip='sk'
)
def load(
        filepath,
        deformer=None,
        shape=None,
        method='index',
        worldSpace=None,
        attribute=None,
        ignoreName=None,
        positionTolerance=None,
        remap=None,
        skip=None
):
    """
    Wrapper for :func:`~pymel.internal.pmcmds.deformerWeights` in 'import'
    mode. Arguments are post-processed to ensure that only requested deformers
    and shapes are included.  See Maya help for :func:`deformerWeights` for
    flag information.
    """
    if deformer:
        deformer = [str(x) for x in _pu.expandArgs(deformer)]

    if shape:
        shape = [str(x) for x in _pu.expandArgs(shape)]

    filepath = toPosix(filepath)
    pdir, filename = posixpath.split(filepath)

    kwargs = {
        'path': pdir,
        'im': True,
        'method': 'index'
    }

    if attribute is not None:
        kwargs['attribute'] = attribute

    if skip is not None:
        kwargs['skip'] = skip

    for name, val in zip(
        ['deformer', 'shape', 'worldSpace', 'attribute',
         'ignoreName', 'positionTolerance', 'remap'],
        [deformer, shape, worldSpace, attribute,
         ignoreName, positionTolerance, remap]
    ):
        if val is not None:
            kwargs[name] = val

    fixKwargs(kwargs)
    m.deformerWeights(filename, **kwargs)