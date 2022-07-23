import paya.lib.plugops as _po
import maya.cmds as m
import maya.mel as mel
import pymel.util as _pu
from paya.util import short
import paya.runtime as r

if not r.pluginInfo('curveWarp', q=True, loaded=True):
    r.loadPlugin('curveWarp')


class CurveWarp:

    #------------------------------------------------------------|    Constructor

    @classmethod
    @short(
        aimCurve='aic',
        autoNormals='aut',
        alignment='ali',
        offset='off',
        loopClosedCurves='lcc',
        samplingAccuracy='acc',
        name='n',
        closestPoint='cp',
        keepLength='kl'
    )
    def create(
            cls,
            *geometryAndCurve,
            aimCurve=None,
            autoNormals=True,
            closestPoint=True,
            keepLength=True,
            loopClosedCurves=True,
            alignment='auto',
            samplingAccuracy=1.0,
            offset=0.0,
            name=None
    ):
        """
        Initialises a curveWarp deformer.

        :param \*geometryAndCurve: required; the curve and one or more
            meshes to bind, in no particular order
        :type:
            str,
            :class:`~paya.runtime.nodes.NurbsCurve`,
            :class:`~paya.runtime.nodes.Mesh`,
            :class:`~paya.runtime.nodes.Transform`
        :param aimCurve/aic: a curve to use for up vector resolution;
            defaults to False
        :type aimCurve/aic: str, None,
            :class:`~paya.runtime.nodes.Transform`,
            :class:`~paya.runtime.nodes.NurbsCurve`
        :param bool autoNormals/aut: if no *aimCurve* is provided, set normal
            calculation on the node (attribute ``aimMode``) to 'Auto'
            rather than 'Curve Normals'; defaults to True
        :param bool closestPoint/cp: set this to False when the two curves
            are of matched domain, to cut down on extraneous closest-point
            calculations; defaults to True
        :param bool keepLength/kl: keep the driven geometries' lengths;
            defaults to True
        :param bool loopClosedCurves/lcc: loop sliding on closed curves;
            defaults to True
        :param alignment/ali: an index or enum key for the ``alignment``
            node attribute:

            - 1: 'Auto' (the default)
            - 2: 'X'
            - 3: 'Y'
            - 4: 'Z'
        :param float samplingAccuracy/acc: the curve sampling accuracy;
            defaults to 1.0
        :param offset/off: a slide offset along the curve; defaults to
            0.0
        :type offset/off: float, :class:`~paya.runtime.plugs.Math1D`
        :param name/n: one or more name elements for the node
        :type name/n: None, str, int, list, tuple
        :return: The deformer node.
        :rtype: :class:`CurveWarp`
        """
        geometryAndCurve = [r.PyNode(x
            ) for x in _pu.expandArgs(*geometryAndCurve)]

        if not geometryAndCurve:
            raise ValueError(
                "Please specify a curve and one or more geometries."
            )

        curve = None
        geometry = []

        for item in geometryAndCurve:
            item = item.toShape()

            if isinstance(item, r.nodes.Mesh):
                geometry.append(item.toTransform())

            elif isinstance(item, r.nodes.NurbsCurve):
                if curve is None:
                    curve = item.toTransform()

                else:
                    raise ValueError("More than one curve specified.")

        geometry = [item.toTransform() for item in geometry]
        r.select(geometry, curve)
        node = r.PyNode(mel.eval('createCurveWarp'))

        name = cls.makeName(name)
        m.evalDeferred('m.rename("{}", "{}")'.format(str(node), name))

        # Config
        if aimCurve:
            aimCurve = _po.asGeoPlug(aimCurve, ws=True)
            aimCurve >> node.attr('aimCurve')
            node.attr('aimMode').set(3)

        else:
            node.attr('aimMode').set(2 if autoNormals else 1)

        node.attr('keepLength').set(keepLength)
        offset >> node.attr('offset')
        node.attr('samplingAccuracy').set(samplingAccuracy)
        node.attr('loopClosedCurves').set(loopClosedCurves)

        if isinstance(alignment, int):
            node.attr('alignmentMode').set(alignment)

        elif isinstance(alignment, str):
            keys = [key.lower() for key in \
                    node.attr('alignmentMode').getEnums().keys()]

            index = keys.index(alignment.lower()) + 1
            node.attr('alignmentMode').set(index)

        node.attr('aimCurveMode').set(2 if closestPoint else 1)

        return node