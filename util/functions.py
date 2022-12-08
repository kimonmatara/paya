import inspect
from functools import wraps

class Undefined:
    """
    An instance of this class, ``undefined`` in this module, is used across
    Paya for keyword argument defaults for which ``None`` would not represent
    omission.
    """
    def __bool__(self):
        return False

    def __repr__(self):
        return '<undefined>'

undefined = Undefined()

class short:
    """
    Decorator with keyword arguments, used to mimic Maya's 'shorthand'
    flags.

    :Example:

        .. code-block:: python

            @short(numJoints='nj')
            def makeJoints(numJoints=16):
                [...]

            # This can then be called as:
            makeJoints(nj=5)
    """
    def __init__(self, **mapping):
        self.reverse_mapping = {v:k for k, v in mapping.items()}

    def __call__(self, f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            resolved = {}

            for k, v in kwargs.items():
                k = self.reverse_mapping.get(k,k)
                resolved[k] = v

            return f(*args, **resolved)

        return wrapper

def resolveFlags(*flags, radio=None):
    """
    Resolves passed-in user option values by omission, Maya style.

    :Example:

        .. code-block:: python

            userVals = resolveFlags(True, None, None)
            # True, False, False

            userVals = resolveFlags(False, None, None)
            # False, True, True

            userVals = resolveFlags(None, None, None)
            # True, True, True

            userVals = resolveFlags(True, None, False)
            # True, True, False

            userVals = resolveFlags(None, None, None, radio=0)
            # True, False, False

            userVals = resolveFlags(None, False, None, radio=0)
            # True, False, False

            userVals = resolveFlags(True, None, True, radio=0)
            # ValueError: Multiple radio selection.

    :param \*flags: the passed-in user option values, in order
    :type \*flags: :class:`bool`, ``None``
    :param radio: if this is defined, it should be an integer specifying
        which item should be ``True`` in a single-selection radio setup;
        defaults to ``None``
    :return: The resolved flag values, in order.
    :rtype: :class:`tuple` [:class:`bool`]
    """
    numFlags = len(flags)
    flags = [bool(flag) if flag is not None else flag for flag in flags]

    if radio is None:
        defined = [flag for flag in flags if flag is not None]
        numDefined = len(defined)

        if numDefined is 0:
            return [True] * numFlags
        elif numDefined is numFlags:
            return flags
        else: # subset
            numSet = len(set(defined))

            if numSet is 1:
                flags = [(not defined[0]) \
                        if flag is None else flag for flag in flags]
            else:
                flags = [True \
                        if flag is None else flag for flag in flags]

            return flags

    else:
        _flags = [False] * numFlags

        numTrues = flags.count(True)

        if numTrues:
            if numTrues > 1:
                raise ValueError("Multiple radio selection.")
            else:
                _flags[flags.index(True)] = True
        else:
            numFalses = flags.count(False)

            if numFalses is numFlags-1:
                _flags[flags.index(None)] = True

            else:
                _flags[radio] = True

        return _flags


@short(gate='g')
def conditionalExpandArgs(*args, gate=None):
    """
    Flattens tuples and lists in user arguments into a single list.

    :param \*args: the arguments to expand
    :param gate/g: if provided, this should be a callable that takes
        one argument and returns ``True`` if the item should be expanded
        or not (useful for preserving vectors in list form etc.); will
        only be used for tuples and lists; defaults to None
    :return: The flattened args.
    :rtype: list
    """
    out = []

    if gate is None:
        gate = lambda x: True

    def expand(x):
        if isinstance(x, (tuple, list)):
            x = list(x)

            if gate(x):
                for member in x:
                    expand(member)

            else:
                out.append(x)

        else:
            out.append(x)

    expand(args)

    return out

def sigCollectsKwargs(signature):
    """
    :param signature: the signature object
    :type signature: :class:`inspect.Signature`
    :return: ``True`` if the signature object collects keyword arguments,
        otherwise ``False``.
    """
    for param in signature.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

    return False

def sigWithAddedKwargs(signature, **kwargs):
    """
    :param signature: the original signature object
    :type signature: :class:`inspect.Signature`
    :param \*\*kwargs: defines keywords arguments, with defaults, to add to
        the signature copy.
    :return: A copy of *signature* with the passed keyword arguments mixed-in.
    """
    existingParams = list(signature.parameters.values())

    newParams = []

    for k, v in kwargs.items():
        newParam = inspect.Parameter(
            k, inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=v)

        newParams.append(newParam)

    # Add new parameters, but only before any **kwargs collection

    kwargsIndex = None

    for i, param in enumerate(existingParams):
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            kwargsIndex = i
            break

    if kwargsIndex is None:
        existingParams += newParams

    else:
        existingParams = \
            existingParams[:kwargsIndex] \
            + [newParams] + existingParams[kwargsIndex:]

    newsig = signature.replace(parameters=existingParams)
    return newsig