"""
Utilities for managing modules.
"""

import os
import sys

def path_to_dotpath(path):
    """
    Given a file system path to a module file, returns the dot-path to be
    used in import statements. ``__init__.py`` files must be present.

    :param str path: the full path to the module file
    :return: The dotted module name (path).
    :rtype: str
    """
    current = path
    elems = list()

    while True:
        if current == path:
            basename = os.path.splitext(
                os.path.basename(current)
            )[0]

            elems.insert(0,basename)
            current = os.path.dirname(current)
            continue

        listing = os.listdir(current)

        if '__init__.py' in listing or '__init__.pyc' in listing:
            elems.insert(0, os.path.basename(current))
            current = os.path.dirname(current)
        else:
            if current not in sys.path:
                raise RuntimeError('paya.util.modules.path_to_dotpath(): '+
                                   "The specified path, '"+path+"' cannot be "+
                                   'reached. Check __init__.py files and sys.path.')
            else: break

    return '.'.join(elems)