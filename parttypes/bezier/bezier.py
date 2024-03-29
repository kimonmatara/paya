import paya.lib.mathops as _mo
import paya.runtime as r
from paya.config import takeUndefinedFromConfig, undefined
from paya.lib.mathops import flipAxis
from paya.util import short, int_to_letter


class Bezier(r.parts.Part):
    # """
    # Bezier 'spine' part. Features:
    #
    # -   scalable tangents
    # -   squash / stretch / length preservation
    # -   distributed (floating) joints
    # -   parallel transport option for twist calculations
    # """

    #------------------------------------------------------------|    Constructor(s)

    @classmethod
    @takeUndefinedFromConfig
    def createChainFromBezierAndUpVectors(cls,
                                          numJoints,
                                          bezier,
                                          upVectors,

                                          downAxis=undefined,
                                          upAxis=undefined,
                                          opposite=False,

                                          resolution=9,
                                          parallelTransport=False,

                                          parent=None):
        """
        Creates a chain from a guide Bezier curve and matched per-anchor
        up vectors.

        :param int numJoints: the number of joints to generate
        :param bezier: the guide bezier curve
        :type bezier: :class:`str`, :class:`~paya.runtime.nodes.BezierCurve`,
            :class:`~paya.runtime.nodes.Transform`
        :param upVectors: one up vector per anchor on the Bezier curve
        :type upVectors: :class:`list` [:class:`list` [:class:`float`] |
            :class:`~paya.runtime.data.Vector`]
        :param str downAxis: the 'bone' axis; defaults to
            ``paya.config.downAxis``
        :param str upAxis: the axis to map to the up vectors; defaults to
            ``paya.config.upAxis``
        :param bool opposite: flips the (resolved) down axis; defaults to
            ``False``
        :param parallelTransport: resolve up vector blending using parallel
            transport; defaults to ``False``
        :param int resolution/res: the number of parallel-transport solutions to
             generate along the curve; higher numbers improve accuracy at the
             expense of performance; defaults to 9
        :param interpolation/i:: defines how to interpolate values from param:
            vector pairs:

            -   ``0`` (``'None'``) (you wouldn't normally want this)
            -   ``1`` (``'Linear'``) (the default)
            -   ``2`` (``'Smooth'``)
            -   ``3`` (``'Spline'``)

        :param parent: an optional destination parent for the chain;
            defaults to ``None``
        :type parent: ``None``, :class:`str`,
            :class:`~paya.runtime.nodes.Transform`
        :return: The generated chain.
        :rtype: :class:`Chain`
        """
        #--------------------------------------|    Init

        if numJoints < 2:
            raise RuntimeError("Need at least two joints.")

        bezier = r.PyNode(bezier)
        anchorGroups = bezier.getControlVerts(anchors=True)
        upVectors = [r.data.Vector(vector) for vector in upVectors]

        numAnchorGroups = len(anchorGroups)
        numUpVectors = len(upVectors)

        if numAnchorGroups < 2 or numUpVectors < 2:
            raise RuntimeError(
                "Need two or more bezier anchors and matching vectors.")

        if numAnchorGroups is not numUpVectors:
            raise RuntimeError(
                "Mismatched numbers of bezier anchors and up vectors.")

        if opposite:
            downAxis = flipAxis(downAxis)

        #--------------------------------------|    Prep matrices

        # Create a temporary sampler
        params = bezier.paramsAtAnchors()
        keymap = list(zip(params, upVectors))

        sampler = bezier.createUpVectorSampler(
            upVector=keymap,
            resolution=resolution,
            setAsDefault=False,
            parallelTransport=parallelTransport
        )

        matrices = bezier.distributeMatrices(
            numJoints,
            downAxis,
            upAxis,
            chain=True,
            upVectorSampler=sampler
        )

        sampler.remove()

        #--------------------------------------|    Draw the chain

        return r.Chain.createFromMatrices(matrices, parent=parent)

    # @r.partCreator
    # @short(numJoints=12,
    #        squashStretch='ss',
    #        allowStartTranslate='ast',
    #        allowEndTranslate='aet',
    #        parallelTransport='pt',
    #        resolution='res')
    # def create(self,
    #            anchorGroups,
    #            upVectors,
    #            numJoints=12,
    #            squashStretch=True,
    #            parallelTransport=False,
    #            resolution=9,
    #            allowStartTranslate=True,
    #            allowEndTranslate=True):
    #     """
    #     :param anchorGroups: a list of dictionaries (one per anchor), each
    #         comprising:
    #
    #         ::
    #
    #             {
    #                 'in': point position of 'in' tangent CV (if present)
    #                 'root': point position of main anchor CV
    #                 'out': point position of 'out' tangent CV (if present)
    #             }
    #
    #     :param upVectors: a list of up vectors (one per anchor)
    #     :type upVectors: :class:`list` [:class:`~paya.runtime.data.Vector`]
    #     :param int numJoints/nj: the number of joints to distribute along the
    #         curve; defaults to 12
    #     :param bool parallelTransport/pt: ignored if *numJoints* is 0; use
    #         parallel transport to distribute twist along the curve; defaults
    #         to ``False``
    #     :param int resolution/res: the number of parallel-transport solutions to
    #         generate along the curve; higher numbers improve accuracy at the
    #         expense of performance; defaults to 9
    #     :param bool allowStartTranslate/ast: unlock translate channels on the
    #         start control; defaults to ``True``
    #     :param allowEndTranslate/aet: unlock translate channels on the
    #         end control; defaults to ``True``
    #     """
    #     """
    #     :Pseudo:
    #         For anchor group, up vector:
    #             Draw a control
    #             Capture and transform CV points, add to points pool
    #             Capture up vector info from control
    #
    #         Draw live bezier from points pool
    #
    #         if squashStretch:
    #             Truncate curve for squash and stretch
    #
    #         Add up vector information to final curve
    #
    #         if numJoints:
    #             Distribute joints along final curve
    #     """
    #     downAxis = r.config['downAxis']
    #     absDownAxis = downAxis.strip('-')
    #
    #     upAxis = r.config['upAxis']
    #     absUpAxis = upAxis.strip('-')
    #
    #     absThirdAxis = _mo.missingAxis(absDownAxis, absUpAxis)
    #     rotateOrder = ''.join([absDownAxis, absUpAxis, absThirdAxis])
    #     scaleChannel = 's'+absDownAxis
    #
    #     addJoints = numJoints > 0
    #
    #     #-------------------------------------------|    Initial iteration
    #
    #     numAnchors = len(anchorGroups)
    #     controls = []
    #     liveUpVectors = []
    #     curvePoints = []
    #
    #     for i, anchorGroup, upVector in zip(
    #         range(numAnchors),
    #         anchorGroups,
    #         upVectors
    #     ):
    #         matrix = self.getDrawMatrixFromAnchorGroupAndUpVector(
    #             anchorGroup,
    #             upVector
    #         )
    #
    #         keyables = ['r', scaleChannel]
    #
    #         if not((i is 0 and not allowStartTranslate) \
    #                or (i is numAnchors-1 and not allowEndTranslate)):
    #             keyables.append('t')
    #
    #         with r.Name(int_to_letter(i+1).upper()):
    #             control = r.createControl(
    #                 worldMatrix=matrix,
    #                 parent=self.tree['controls'].node(),
    #                 rotateOrder=rotateOrder,
    #                 keyable=keyables,
    #                 pickWalkParent=controls[-1] if controls else None
    #             )
    #
    #         r.transformLimits(control,
    #                           **{'e'+scaleChannel:(True,False),
    #                              scaleChannel:(0.001, 1.0)})
    #
    #         thesePoints = anchorGroup.values()
    #         mtx = control.attr('wm').asOffset()
    #         curvePoints += [point ^ mtx for point in thesePoints]
    #
    #         if addJoints:
    #             liveUpVectors.append(control.attr('wm').getAxis(upAxis))
    #         controls.append(control)
    #
    #     #-------------------------------------------|    Draw the curve
    #
    #     with r.Name('bind'):
    #         bezier = r.nodes.BezierCurve.create(
    #             *curvePoints
    #         ).toTransform()
    #
    #     bezier.setParent(self.tree['util'].node(inheritsTransform=False))
    #     fullLengthStream = bezier.getHistoryPlug()
    #
    #     if addJoints:
    #         #-------------------------------------------|    Up vector info
    #
    #         # Add the up vector sampler to the full-length curve in all
    #         # cases
    #
    #         params = fullLengthStream.paramsAtAnchors()
    #         upVectorSampler = fullLengthStream.createUpVectorSampler(
    #             upVector=list(zip(params, liveUpVectors)),
    #             parallelTransport=parallelTransport,
    #             resolution=resolution
    #         )
    #
    #     #-------------------------------------------|    Squash-stretch
    #
    #     if squashStretch:
    #         squashy, stretchy = self.addSquashStretchAttrs(controls)
    #         outputStream = fullLengthStream.squashStretch(
    #             squashy,
    #             stretchy,
    #             vector=controls[-1].attr('wm').getAxis(downAxis),
    #             globalScale=self.getPartScale(p=True)
    #         )
    #     else:
    #         outputStream = fullLengthStream
    #
    #     outputStream >> bezier.attr('create')
    #
    #     #-------------------------------------------|    Joints
    #
    #     if addJoints:
    #
    #         #---------------------------------------|    Distribute
    #
    #         # Use the up-vector sampler from the full-length curve
    #         # in all cases
    #
    #         matrices = bezier.distributeMatrices(
    #             numJoints, downAxis, upAxis,
    #             globalScale=self.getPartScale(p=True),
    #             plug=True,
    #             upVectorSampler=upVectorSampler
    #         )
    #
    #         joints = []
    #
    #         for i, matrix in enumerate(matrices):
    #             with r.Name(i+1, padding=3):
    #                 joint = r.nodes.Joint.create(
    #                     worldMatrix=matrix,
    #                     parent=self.tree['joints'].node()
    #                 )
    #
    #             joints.append(joint)
    #
    #         self.tag('joints', joints)
    #
    #
    # @r.partCreator
    # def createFromBezierAndUpVectors(self,
    #                                  bezierGuide,
    #                                  upVectors,
    #                                  **kwargs):
    #     """
    #     Lets you create the system using a 'guide' bezier curve and a list of
    #     up vectors (one per anchor).
    #
    #     :param bezierGuide: a guide Bezier curve
    #     :type bezierGuide: :class:`str`,
    #         :class:`~paya.runtime.nodes.BezierCurve`,
    #         :class:`~paya.runtime.nodes.Transform`,
    #     :param upVectors: a list of up vectors (one per anchor)
    #     :type upVectors: :class:`list` [:class:`~paya.runtime.data.Vector`]
    #     :param \*\*kwargs: forwarded to :meth:`create`
    #     """
    #     bezierGuide = r.PyNode(bezierGuide)
    #     anchorGroups = bezierGuide.getControlVerts(anchors=True)
    #
    #     return self.create.__wrapped__(
    #         self,
    #         anchorGroups,
    #         upVectors,
    #         **kwargs
    #     )
    #
    # @r.partCreator
    # @short(closestPoint='cp')
    # def createFromTwoBeziers(self,
    #                          mainBezier,
    #                          upBezier,
    #                          closestPoint=False,
    #                          **kwargs):
    #     """
    #     Lets you create the system using 'main' and 'up' guide curves.
    #
    #     :param bezierGuide: the main guide Bezier curve
    #     :type bezierGuide: :class:`str`,
    #         :class:`~paya.runtime.nodes.BezierCurve`,
    #         :class:`~paya.runtime.nodes.Transform`,
    #     :param upBezier: the 'up' guide Bezier curve
    #     :type upBezier: :class:`str`,
    #         :class:`~paya.runtime.nodes.BezierCurve`,
    #         :class:`~paya.runtime.nodes.Transform`,
    #     :param closestPoint/cp: pull interests from the 'up' curve using
    #         closest point rather than matched parameter; set this to ``True``
    #         if the two curve domains don't match; defaults to ``False``
    #     :param \*\*kwargs: forwarded to :meth:`create`
    #     """
    #     mainBezier = r.PyNode(mainBezier)
    #     upBezier = r.PyNode(upBezier)
    #
    #     params = mainBezier.paramsAtAnchors()
    #     upVectors = []
    #
    #     for param in params:
    #         anchor = mainBezier.pointAtParam(param, worldSpace=True)
    #
    #         if closestPoint:
    #             interest = upBezier.nearestPoint(anchor, worldSpace=True)
    #         else:
    #             interest = upBezier.pointAtParam(param, worldSpace=True)
    #
    #         upVectors.append(interest-anchor)
    #
    #     return self.createFromBezierAndUpVectors.__wrapped__(
    #         self,
    #         mainBezier,
    #         upVectors,
    #         **kwargs
    #     )
    #
    # #----------------------------------------------------|
    # #----------------------------------------------------|    Partials
    # #----------------------------------------------------|
    #
    # @staticmethod
    # def getDrawMatrixFromAnchorGroupAndUpVector(anchorGroup, upVector):
    #     """
    #     :param anchorGroup: a dictionary comprising:
    #
    #         ::
    #
    #             {
    #                 'in': point position of 'in' tangent CV (if present)
    #                 'root': point position of main anchor CV
    #                 'out': point position of 'out' tangent CV (if present)
    #             }
    #
    #     :param upVector: the up vector for the anchor
    #     :type upVector: :class:`list`, :class:`tuple`,
    #         :class:`~paya.runtime.data.Vector`
    #     """
    #     end = anchorGroup.get('out', anchorGroup['root'])
    #     start = anchorGroup.get('in', anchorGroup['root'])
    #     tangent = end-start
    #
    #     return r.createMatrix(
    #         r.config['downAxis'], tangent,
    #         r.config['upAxis'], upVector,
    #         t=anchorGroup['root']
    #     ).pick(t=True, r=True)
    #
    # @staticmethod
    # def addSquashStretchAttrs(controls):
    #     """
    #     Adds synced ``squashy`` and ``stretchy`` attributes across a list
    #     of controls.
    #
    #     :param controls: the controls to add the attributes to
    #     :type controls: :class:`list` [:class:`~paya.runtime.nodes.Transform`]
    #     :return: The squashy and stretchy attributes.
    #     :rtype: :class:`list` [:class:`~paya.runtime.plugs.Double`,
    #         :class:`~paya.runtime.plugs.Double`]
    #     """
    #     controls = controls[::-1] # Add source attrs to end control
    #
    #     for control in controls:
    #         control.attrSections.add('SQUASH_STRETCH')
    #
    #     squashy = controls[0].addAttr('squashy', k=True, min=0, max=1, dv=0)
    #     stretchy = controls[0].addAttr('stretchy', k=True, min=0, max=1, dv=0)
    #
    #     for control in controls[1:]:
    #         for attr in (squashy, stretchy):
    #             attr.createProxy(node=control)
    #
    #     return squashy, stretchy