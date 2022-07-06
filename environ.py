"""ESRI Environment Querying and Handling"""
import os.path as _path

import arcpy as _arcpy

import arcproapi.common as _common


def environments_list(x=(), printit=False):
    """Return a list of 2-tuples of all arcgis environments.

    Optional:
    x -- list of names of environment settings, default is empty list, i.e. all
    printit -- if True, a readable representation of the dictionary is printed using Python's print function.

    Example:
    >>> tmp_ = environments_list(['snapRaster', 'extent'], False)
    >>> tmp1_ = environments_list([], True)
    """
    envs = [en for en in dir(_arcpy.env) if not en.startswith("_") and en not in ('items', 'keys', 'iteritems', 'iterkeys', 'values')]
    if len(x) > 0:
        x = [i.lower() for i in x]
        envs = [en for en in envs if en.lower() in x]
    ret = []
    for en in envs:
        env = getattr(_arcpy.env, en)
        if printit:
            print(str(str(en) + " ").ljust(30, ".") + ": " + str(env))
        ret.append((en, env))
    return ret


def workspace_in_memory_str():
    """get an in-memory workspace"""
    return 'in_memory'



def workspace_set(ws=None):
    """Get or set _arcpy.env.workspace and return its path.

    If ws is None and _arcpy.env.workspace is None, this function will set
    _arcpy.env.workspace to _arcpy.env.scratchGDB and return its path.

    Optional:
    ws -- path to workspace, default is None.
        If ws is a non-existing file geodatabse, it will be created.

    Example:
    >>> # if executed in order
    >>> ev = _arcpy.env
    >>> workspace_set() # sets env.workspace = ec.scratchGDB if ev.workspace is None
    >>> workspace_set('c:\\temp') # sets ev.workspace = 'c:\\temp', returns 'c:\\temp'
    >>> workspace_set() # now returns 'c:\\temp'
    """
    if ws is None:
        ws = _arcpy.env.workspace
        if ws is None:
            ws = _arcpy.env.scratchGDB
            _arcpy.env.workspace = ws
    else:
        if ws[-4:].lower() == '.gdb' and not _arcpy.Exists(ws):
            import re
            ws = _arcpy.management.CreateFileGDB(_path.dirname(ws), re.sub(".gdb", "", _path.basename(ws), re.IGNORECASE), "CURRENT").getOutput(0)
        _arcpy.env.workspace = ws
    return _arcpy.env.workspace


def scratch_workspace_set(ws=None):
    """Get or set _arcpy.env.scratchWorkspace and return its path.

    If ws is None and _arcpy.env.scratchWorkspace is None, this function will set
    _arcpy.env.scratchWorkspace to _arcpy.env.scratchGDB and return its path.

    This function 'swsp' has also an alias 'wsps'!

    Optional:
    ws -- path to scratch workspace, default is None
        If ws is a non-existing file geodatabse, it will be created.

    Example:
    >>> # if executed in order
    >>> ev = _arcpy.env
    >>> scratch_workspace_set() # sets ev.scratchWorkspace = ec.scratchGDB if ev.scratchWorkspace is None
    >>> scratch_workspace_set('c:\\temp') # sets ev.scratchWorkspace = 'c:\\temp', returns 'c:\\temp'
    >>> scratch_workspace_set() # now returns 'c:\\temp'
    """
    if ws is None:
        ws = _arcpy.env.scratchWorkspace
        if ws is None:
            ws = _arcpy.env.scratchGDB
            _arcpy.env.scratchWorkspace = ws
    else:
        if ws[-4:].lower() == '.gdb' and not _arcpy.Exists(ws):
            import re
            ws = _arcpy.management.CreateFileGDB(_path.dirname(ws), re.sub(".gdb", "", _path.basename(ws), re.IGNORECASE), "CURRENT").getOutput(0)
        _arcpy.env.scratchWorkspace = ws
    return _arcpy.env.scratchWorkspace


def scratch_get_dataset_fname(name, enforce=False):
    """Return path to a dataset called name in scratch workspace.

    LIMITATION: Reliable for geodatabases only! Does not handle extensions.

    Returns _path.join(_arcpy.env.scratchWorkspace, name).
    If scratchWorkspace is None, it tries workspace, then scratchGDB.

    This function 'to_scratch' has also an alias 'tos'!

    Required:
    name -- basename of the output dataset

    Optional:
    enforce -- if True, _arcpy.CreateScratchName is used to ensure name does not
        exist in scratch workspace, otherwise returns basename equal to name.

    Example:
    >>> scratch_get_dataset_fname('foo', False) # '...\\scratch.gdb\\foo'
    >>> scratch_get_dataset_fname('foo', True) # '...\\scratch.gdb\\foo0'
    >>> scratch_get_dataset_fname('foo.shp', False) # '...\\scratch.gdb\\foo_shp'
    >>> scratch_get_dataset_fname('foo.shp', True) # '...\\scratch.gdb\\foo_shp0'
    >>> scratch_get_dataset_fname('foo', False) # '...\\scratch.gdb\\foo'
    """
    ws = _arcpy.env.scratchWorkspace
    if ws is None: ws = _arcpy.env.workspace
    if ws is None: ws = _arcpy.env.scratchGDB

    if _arcpy.Describe(ws).workspaceType.lower() == 'filesystem':
        m = "Scratch workspace is a folder, scratch names may be incorrect."
        _common.msg(m)
        _arcpy.AddWarning(m)

    nm = _path.basename(name)
    nm = _arcpy.ValidateTableName(nm, ws)
    if enforce:
        nm = _arcpy.CreateScratchName(nm, workspace=ws)
    else:
        nm = _path.join(ws, nm)
    return nm
