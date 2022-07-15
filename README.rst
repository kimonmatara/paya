Paya: PyMEL for Riggers
=======================

Paya is an object-oriented toolkit for Maya riggers. Unlike other libraries, it doesn't re-wrap ``maya.cmds`` or the
`OpenMaya <https://help.autodesk.com/view/MAYAUL/2023/ENU/?guid=Maya_SDK_Maya_Python_API_html>`_ API. Instead, it adds
functionality to `PyMEL <https://help.autodesk.com/view/MAYAUL/2022/ENU/?guid=__PyMel_index_html>`_ types at runtime
for an integrated and familiar experience.

Included is the most comprehensive, and intuitive, implementation of **maths rigging using Python operators ** available
anywhere, with over 100 methods for linear algebra, trigonometry and more.

Customisation is easy, and goes far beyond PyMEL's
`virtual classes <https://github.com/LumaPictures/pymel/blob/master/examples/customClasses.py>`_ system to add support
for attribute (including subtype), component and data types with true inheritance for the first time.

.. admonition:: New in version 0.7

    *   A concise, Pythonic interface for managing blend shape targets, including tangent- and
        transform- space, inverted correctives and more. Never use ``blendShape()`` again!
    *   A new ``combine()`` method on scalar attributes leverages ``combinationShape``
        nodes
    *   And more!


Full documentation can be found `here <https://kimonmatara.github.io/paya/>`_.