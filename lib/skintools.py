import paya.runtime as r

@r
def quickBindSelection(popFrame=True, removeExisting=True):
    """
    :param bool popFrame: go the first frame in the timeline before binding,
        then return to current frame; defaults to ``True``
    :param bool removeExisting: remove existing skinClusters; defaults to
        ``True``
    :return: The generated skinClusters.
    :rtype: [:class:`~paya.runtime.nodes.SkinCluster`]
    """
    sel = r.ls(sl=True)

    joints = []
    geos = []

    for item in sel:
        if isinstance(item, r.nodetypes.Joint):
            joints.append(item)

        else:
            geos.append(item)

    kwargs = {
            'tsb': True,
            'bm': 0,
            'dr': 4.5,
            'nw': 1,
            'omi': False,
            'sm': 0,
            'wd': 0
        }

    out = []

    if popFrame:
        origTime = r.currentTime(q=True)
        r.currentTime(r.playbackOptions(q=True, min=True))

    for geo in geos:
        skins = r.nodes.SkinCluster.getFromGeo(geo)

        if skins:
            r.delete(skins)

        args = joints + [geo]
        out.append(r.skinCluster(*args, **kwargs))

    if popFrame:
        r.currentTime(origTime)
        r.refresh()

    return out