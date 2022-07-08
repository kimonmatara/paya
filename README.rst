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

.. admonition:: New in version 0.6

    *   Maya's ``copyDeformerWeights()``, ``copySkinWeights()`` and ``deformerWeights()`` commands have been
        unified into simple-to-use methods for dumping, loading and copying deformer weights
    *   Smart new construction and copy methods for skinClusters
    *   ``Vector.blend()`` now supports angle-based blending (for both attributes and values, naturally)
    *   Easily create and drive twist chains
    *   And more !


Full documentation can be found `here <https://kimonmatara.github.io/paya/>`_.