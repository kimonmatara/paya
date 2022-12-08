def clampindex(index, numelems, absolute=False):
    """
    Clamps an index, whether negative or positive, so that it
    remains within the range implied by numelems.

    :param int index: the index to clamp
    :param int numelems: the number of elements in the iterable
    :param bool absolute: clamp inside positive range
    :return: The clamped index.
    :rtype: int
    """
    minval = 0 if absolute else -numelems
    maxval = numelems-1

    index = max(minval,index)
    index = min(maxval,index)

    return index

def index_in_range(index, numelems):
    """
    :return: True if the index is 'legal'. Essentially a pre-emptive
        :class:`IndexError`.
    """
    return index >= -numelems and index <= numelems-1

def absindex(
        index,
        numelems,
        loop=False
):
    """
    Resolves a negative (reverse) index into a positive (forward) one.

    :param int index: the index to edit
    :param int numelems: the number of elements in the iterable
    :param bool loop: if this is ``False``, and the index is out of range,
        :class:`IndexError` will be raised; otherwise, the index will be
        wound over; defaults to False
    :return: The resolved index.
    :rtype: int
    """
    if not loop:
        if not index_in_range(index,numelems):
            raise IndexError("Out of range.")

    return index % numelems

#----------------------------------------------------------------|    Reordering

def send_indices_relative(
        indicesToMove,
        refIndex,
        lst,
        after=True
):
    """
    Sends members at the specified indices into one contiguous block after
    ``refIndex``. This is an in-place operation

    :param list indicesToMove: the indices to move
    :param int refIndex: the reference index
    :param list lst: the list
    :param bool after: insert the indices *after* the reference index;
        defaults to ``True``
    :rtype: None
    """
    num = len(lst)

    indicesToMove = [absindex(x,num) for x in indicesToMove]
    indicesToMove.sort()

    refIndex = absindex(refIndex,num)

    asindices = list(range(num))

    popped = []

    for index in indicesToMove:
        actualindex = asindices.index(index)
        popped.append(asindices.pop(actualindex))

    refIndex = asindices.index(refIndex)

    if after:
        head = asindices[:refIndex+1]
        tail = asindices[refIndex+1:]

    else:
        head = asindices[:refIndex]
        tail = asindices[refIndex:]

    flat = head + popped + tail

    lst[:] = [lst[x] for x in flat]

def send_indices_before(indicesToMove, refIndex, lst):
    """
    Equivalent to ``send_indices_relative(after=False)``.
    """
    send_indices_relative(
        indicesToMove,
        refIndex,
        lst,
        after=False
    )

def send_indices_after(indicesToMove, refIndex, lst):
    """
    Equivalent to ``send_indices_relative(after=True)``.
    """
    send_indices_relative(
        indicesToMove,
        refIndex,
        lst,
        after=True
    )

def nudge_index(index, lst, offset):
    """
    Nudges an index in the direction and distance specified by 'offset'.

    :param int index: the index of the member to nudge
    :param list lst: the list to edit
    :param int offset: the shift offset
    :rtype: ``None``
    """
    if offset == 0: return

    num = len(lst)

    index = absindex(index,num)

    targetindex = index + offset

    targetindex = clampindex(
        targetindex,
        num,
        absolute=True
    )

    if targetindex == index: return

    send_indices_relative(
        [index],
        targetindex,
        lst,
        after=offset > 0
    )

def nudge_indices(indices, lst, offset):
    """
    Suitable for multi-selection list reordering. It clamps for out-of-range
    shifts, and maintains order within contiguous selection groups.

    This is an in-place operation.

    :param indices: the indices to nudge
    :type indices: list of int
    :param list lst: the list to edit
    :param int offset: the shift offset
    :rtype: ``None``
    """
    num = len(lst)

    indices_to_shift = [absindex(i,num) for i in indices]
    indices_to_shift.sort()

    mixed_together = []
    shift_groups = []

    for x, index in enumerate(range(num)):

        if index in indices_to_shift:
            if x == 0:
                new = True
            else:
                last_elem = mixed_together[-1]

                if isinstance(last_elem,list):
                    new = index != last_elem[-1]+1
                else: new = True

            if new:
                newgp = [index]
                mixed_together.append(newgp)
                shift_groups.append(newgp)
            else:
                mixed_together[-1].append(index)

        else:
            mixed_together.append(index)

    if offset < 0:
        shift_groups = reversed(shift_groups)

    for x, shift_group in enumerate(shift_groups):

        index = mixed_together.index(shift_group)
        newindex = index + offset

        clamped = clampindex(
            newindex, len(mixed_together),
            absolute=True
        )

        delta = clamped - index

        nudge_index(index, mixed_together, delta)

    flattened = []

    for item in mixed_together:
        if isinstance(item,list):
            flattened += item

        else:
            flattened.append(item)

    lst[:] = [lst[x] for x in flattened]

def without_duplicates(iterable):
    """
    :param iterable: the iterable to inspect
    :return: an order-preserved list of members in 'iterable', with duplicates
        omitted.
    :rtype: list
    """
    out = []

    for item in iterable:
        if item not in out:
            out.append(item)

    return out