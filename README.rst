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

.. admonition:: New in version 0.4.1

    *   A brand new toolset for skeletal chains and IK handles, spread across ``Joint``,
        ``IkHandle`` and ``Chain``

    *   Additions to vector and matrix attribute and data types: drive transforms via decomposition, with full
        accounting for ``jointOrient``, ``rotateAxis``, ``inverseScale`` and pivots; rotate vectors by axis-angle; and
        more

    *   Improvements to name management and plug setting

See `here <https://kimonmatara.github.io>`_ for full documentation.