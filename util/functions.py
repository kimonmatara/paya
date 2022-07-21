from functools import wraps


class short:
    """
    Decorator with keyword arguments, used to mimic Maya's 'shorthand'
    flags.

    Example:

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

def resolveFlags(*flags):
    """
    Used to mimic Maya flag behaviour.

    If only a subset of flags are defined, then:

        -   If the subset are a mixture of True / False, the other flags are
            set to False.

        -   If the subset are all True or all False, the remaining flags are
            set to the opposite.

    If all flags are None, all flags are set to True.
    If all flags are NOT None (i.e. all defined), they are all conformed to
    booleans.

    :param flags: one or more user flag arguments
    :return: The resolved flags.
    :rtype: tuple
    """
    numFlags = len(flags)

    if numFlags:
        numNones = flags.count(None)

        if numFlags is numNones:
            return [True] * numFlags

        else:
            if numNones is 0:
                return [bool(f) for f in flags]

            else:
                flags = [bool(f) if f is not None else None for f in flags]

                if True in flags:
                    flags = [False if f is None else f for f in flags]

                elif False in flags:
                    flags = [True if f is None else f for f in flags]

                return flags

    else:
        return ()


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