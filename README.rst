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

.. admonition:: New in version 0.9

    *   Configure up vectors on NURBS and Bezier curves once, and have the information picked up automatically
        by methods such as ``matrixAtParam`` or
        ``fitChain``
    *   Brand new implementations for
        `parallel transport <https://www.semanticscholar.org/paper/Parallel-Transport-Approach-to-Curve-Framing-Hanson-Ma/ed416d01742e5e704357538c6817312ca6d8cb38?p2df>`_
    *   This version introduces a few **breaking changes** to streamline the codebase. See the
        release notes  for the full lowdown.


Full documentation can be found `here <https://kimonmatara.github.io/paya/>`_.