Paya: PyMEL for Riggers
=======================

Paya is an object-oriented toolkit for Maya riggers. Unlike other libraries, it doesn't re-wrap ``maya.cmds`` or the
`OpenMaya <https://help.autodesk.com/view/MAYAUL/2023/ENU/?guid=Maya_SDK_Maya_Python_API_html>`_ API. Instead, it adds
functionality to `PyMEL <https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=__PyMel_index_html>`_ types at runtime
for an integrated and familiar experience.

Included is the most comprehensive, and intuitive, implementation of :doc:`maths rigging using Python operators
<maths_rigging>` available anywhere, with over 100 methods for linear algebra, trigonometry and more.

Customisation is easy, and goes far beyond PyMEL's
`virtual classes <https://github.com/LumaPictures/pymel/blob/master/examples/customClasses.py>`_ system to add support
for attribute (including subtype), component and data types with true inheritance for the first time.

.. admonition:: New in version 0.8

    .. rubric:: Total Curve Madness

    *   Extensive :doc:`sampling and editing methods on NURBS and Bezier curve shapes, plugs and components
        <curves>`.
    *   :ref:`Complete curve framing <curve_framing>`: extract dynamic and static matrices from any point, parameter,
        length or fraction of a NURBS or Bezier curve.
    *   :ref:`Distribute joints and drive chains <curve_distributions>` with ease; control up vectors explicitly or with
        aim curves.
    *   :ref:`True, evaluated curve length locking <length_locking>`.
    *   Use plug methods to :ref:`work fully procedurally in the DG <procedural_geo_editing>` and only create shapes
        where you need them.
    *   :ref:`Create two- and three-point circular arcs that won't disappear with an error when the input points
        are in-line <arcs>`.
    *   Use ``clusterAll`` to cluster-up curves with automatic merging of overlapping
        CVs.
    *   Options to manage line widths added to the control shape methods and elsewhere.

    .. rubric:: Across the Board

    *   A standard constructor and smart editing methods for :class:`cluster <paya.runtime.nodes.Cluster>` deformers.
    *   A standard constructor for :class:`curveWarp <paya.runtime.nodes.CurveWarp>` deformers.
    *   New ``maintainOffset/mo`` and ``worldSpace`` options for ``decomposeAndApply``,
        and a dedicated ``applyViaOpm`` method
    *   New methods to :ref:`manage procedural history edits <procedural_geo_editing>` in Maya-standard ways:
        ``getOrigPlug``,
        ``getHistoryPlug``,
        ``deleteHistory`` and
        ``getShapeMFn``
    *   New maths methods: :meth:`~paya.runtime.plugs.Math1D.gatedClamp()` and
        :meth:`~paya.runtime.plugs.Vector.asShearMatrix()`
    *   And more! 


Full documentation can be found `here <https://kimonmatara.github.io/paya/>`_.