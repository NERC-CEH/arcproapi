"""helper functions etc"""
from enum import Enum as _Enum
import time as _time
import os as _os
import os.path as _path
import datetime as _datetime
import sys as _sys
import math as _math
from pathlib import Path as _Path
import functools as _functools

import fuckit as _fuckit
import arcpy as _arcpy

import arcproapi.errors as _errors

import funclite.iolib as _iolib

# Keys is the field type string as a property of arcpy ListFields Field instance
# Values are the type strings used by arcpy AddField
lut_field_types = {
    'Date': 'DATE',
    'String': 'TEXT',
    'Single': 'FLOAT',
    'Double': 'DOUBLE',
    'SmallInteger': 'SHORT',
    'Integer': 'LONG',
    'GUID': 'GUID',
    'Raster': 'RASTER'
}


class Version(_Enum):
    """Version enumeration"""
    ArcPro = 1
    ArcMap = 2


class FieldNamesSpecial:
    """ Special field name mappings as text, used in cursors for example
    """
    shape = 'SHAPE@'
    oid = 'OID@'
    wkt = 'SHAPE@WKT'
    area = 'SHAPE@AREA'
    length = 'SHAPE@LENGTH'
    wkb = 'SHAPE@WKB'
    json = 'SHAPE@JSON'
    m = 'SHAPE@M'
    z = 'SHAPE@Z'
    x = 'SHAPE@X'
    y = 'SHAPE@Y'
    true_centroid = 'SHAPE@TRUECENTROID'
    xy = 'SHAPE@XY'
    xyz = 'SHAPE@XYZ'


class EnumFieldTypeText(_Enum):
    """Field Type text as required for addfield..

    See also eFieldTypeTextForListFields which is the values
    returned by the the type property of an arcpy.Field instance.

    Notes:
        FLOAT is single precision, DOUBLE is double precision.

    Examples:
        >>> EnumFieldTypeText.DATE.name
        'DATE'
    """
    DATE = 1
    TEXT = 2
    FLOAT = 3
    DOUBLE = 4
    SHORT = 5
    LONG = 6
    GUID = 7
    RASTER = 8
    All = 99


class eFieldTypeTextForListFields(_Enum):
    """ These are the field type texts that are passed to arcpy.ListFields
    """
    All = 1
    BLOB = 2
    Date = 3
    Double = 4
    Geometry = 5
    GlobalID = 6
    GUID = 7
    Integer = 8
    OID = 9
    Raster = 10
    Single = 11
    SmallInteger = 12
    String = 13


def tstamp(p="", tf="%Y%m%d%H%M%S", d="_", m=False, s=()):
    """Returns time stamped string.

    Return string like p + time in tf + d + s[0] + d + s[1] + d + ... s[n]
    If m is True, it will print a message too.

    Optional:
    p -- prefix
    tf -- fime format, default is "%Y%m%d%H%M%S" (i.e. YYYYMMDDHHMMSS)
    d -- delimiter between elements of s
    s -- tuple or list of postfixes

    Example:
    >>> tstamp() # '20140216184029'
    >>> tstamp("lr") # 'lr20140216184045'
    >>> tstamp("lr", "%H%M%S") # 'lr184045'
    >>> tstamp("lr", "%H%M%S") # 'lr184045'
    >>> tstamp("lr", "%H%M%S", s=('run',1)) # 'lr184527_run_1'
    """
    bits = str(d).join(map(str, s))
    if bits: bits = d + bits
    stamp = str(p) + _time.strftime(tf, _time.localtime()) + bits
    if m: msg(stamp, "")
    return stamp


def msg(x, timef='%Y-%m-%d %H:%M:%S', verbose=True, log=None, level='message'):
    """Print (and optionally log) a message using print and _arcpy.AddMessage.

    In python console, _arcpy.AddMessage does not work but print does.
    A message like 'P:2014-02-16 20:44:35: foo' is printed.
    In geoprocessing windows, print does not work but _arcpy.AddMessage does,
    A message like 'T:2014-02-16 20:44:35: foo' is printed.
    In Windows command line, both messages are printed.

    _arcpy.AddWarning is used if level is 'warning'
    _arcpy.AddError is used if level is 'error', sys.exit() is called then.

    If log file does not exist, it is created, otherwise message is appended.

    Required:
    x -- content of the message

    Optional:
    timef -- time format, default is "%Y-%m-%d %H:%M:%S" (YYYY-MM-DD HH:MM:SS)
    verbose -- if True (default) print the message to the console
    log -- file to append the message to, the default is None (i.e. no appending)
    level -- one of 'message'|'warning'|'error' or 0|1|2 respectively

    Example:
    >>> msg('foo') # P:2014-02-16 20:44:35: foo
    >>> msg('foo', '%H%M%S') # P:204503: foo
    >>> msg('foo', '%H%M%S', True, 'c:\\temp\\log.txt') # P:204531: foo
    """
    x = str(x)
    level = str(level).lower()
    doexit = False
    tstamp_ = _time.strftime(timef, _time.localtime())
    if verbose:
        m = tstamp_ + ": " + x
        if level in ('message', '0'):
            print("P:" + m)
            _arcpy.AddMessage("T:" + m)
        elif level in ('warning', '1'):
            print("W:" + m)
            _arcpy.AddWarning("T:" + m)
        elif level in ('error', '2'):
            print("E:" + m)
            _arcpy.AddError("T:" + m)
            doexit = True
        else:
            em = "Level %s not in 'message'|'warning'|'error'|0|1|2." % level
            raise _errors.ArcapiError(em)

    if log not in ("", None):
        with open(log, "a") as fl:
            fl.write("P:" + tstamp_ + ": " + x + "\n")

    if doexit:
        try:
            _sys.exit()
        except:
            pass


def find(pattern, path, sub_dirs=True):
    """Find files matching a wild card pattern.

    Parameters:
    pattern -- wild card search (str)
    path -- root directory to search
    sub_dirs -- search through all sub directories? default is True (bool)

    Example:
    >>> # find SQL databases (.mdf files)
    >>> find('*.mdf', r'\\ArcServer1\SDE')
    \\arcserver1\SDE\ALBT\Albertville.mdf
    \\arcserver1\SDE\ARLI\Arlington.mdf
    \\arcserver1\SDE\BELL\BellePlaine.mdf
    \\arcserver1\SDE\BGLK\BigLake.mdf
    """
    import fnmatch

    the_files = []
    for path, dirs, files in _os.walk(path):
        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                the_files.append(_path.abspath(_path.join(path, filename)))
        if sub_dirs in [False, 'false', 0]:
            break
    return the_files


def fix_args(arg, arg_type=list):
    """Fixe arguments from a script tool.

    For example, when using a script tool with a multivalue parameter,
    it comes in as "val_a;val_b;val_c".  This function can automatically
    fix arguments based on the arg_type.
    Another example is the boolean type returned from a script tool -
    instead of True and False, it is returned as "true" and "false".

    Required:
    arg --  argument from script tool (_arcpy.GetParameterAsText() or sys.argv[1]) (str)
    arg_type -- type to convert argument from script tool parameter. Default is list.

    Example:
    >>> # example of list returned from script tool multiparameter argument
    >>> arg = "val_a;val_b;val_c"  # noqa
    >>> fix_args(arg, list)  # noqa
    ['val_a', 'val_b', 'val_c']
    """
    if arg_type == list:
        if isinstance(arg, str):
            # need to replace extra quotes for paths with spaces
            # or anything else that has a space in it
            return map(lambda a: a.replace("';'", ";"), arg.split(';'))
        else:
            return list(arg)
    if arg_type == float:
        if arg != '#':
            return float(arg)
        else:
            return ''
    if arg_type == int:
        return int(arg)
    if arg_type == bool:
        if str(arg).lower() == 'true' or arg == 1:
            return True
        else:
            return False
    if arg_type == str:
        if arg in [None, '', '#']:
            return ''
    return arg


def concatenate(vals=(), delimiter='', number_only=False):
    """Concatenate a list of values using a specified delimiter.

    Required:
    vals -- list of values to concatenate

    Optional:
    delimiter -- separator for new concatenated string. Default is '' (no delimiter)
    number_only -- if True, only numbers in list will be used. Default is False (bool)
    """
    if number_only:
        return delimiter.join(''.join(str(i) for i in v if str(v).isdigit()) for v in vals)
    else:
        return delimiter.join(map(str, vals))


def arctype_to_ptype(esri_field_type):
    """(str)->Obj:Type
    Convert ArcGIS field type string to Python type.
      tp -- ArcGIS type as string like SHORT|LONG|TEXT|DOUBLE|FLOAT...

    Returns string for GUID, RASTER, BLOB, or other exotic types.

    Example:
    >>> arctype_to_ptype("SHORT")  # returns int
    >>> arctype_to_ptype("long")  # returns int
    >>> arctype_to_ptype("SmallInteger")  # returns int
    >>> arctype_to_ptype("DATE")  # returns datetime.datetime
    """
    esri_field_type = str(esri_field_type).upper().strip()

    if esri_field_type == "TEXT" or esri_field_type == "STRING":
        return str
    elif esri_field_type == "SHORT" or esri_field_type == "SMALLINTEGER":
        return int
    elif esri_field_type == "LONG" or esri_field_type == "INTEGER":
        return int
    elif esri_field_type == "DATE" or esri_field_type == "DATETIME":
        return _datetime.datetime
    elif esri_field_type == "FLOAT" or esri_field_type == "SINGLE":
        return float
    elif esri_field_type == "DOUBLE":
        return float
    else:
        return str


def list_data(top, **options):
    """Walk down a file structure and pick up all data sets (items).
    Returns a generator of full paths to the items.
    Uses _arcpy.da.Walk to discover GIS data.

    Use the oneach parameter to do something with each item as it is discovered.

    Parameters:
        top -- full path to the root workspace to start from

    Optional keyword arguments:
        exclude -- Function that takes item as a parameter and returns True if
            the item should be skipped. Default is None, all items are listed.
        exclude_dir -- Function that takes the directory name as a parameter and
            returns True if the whole directory should be skipped.
            Default is None, all directories are listed.
        oneach -- Function that takes the item as a parameter.
            Default is None and does nothing
        onerror -- Function to handle errors, see _arcpy.da.Walk help
        datatypes -- list of all data types to discover, see _arcpy.da.Walk help
        type -- Feature and raster data types to discover, see _arcpy.da.Walk help
            Feature: Multipatch, Multipoint, Point, Polygon, Polyline
            Raster: BIL, BIP, BMP, BSQ, DAT, GIF, GRID, IMG, JP2, JPG, PNG, TIF
        skippers -- iterable of strings, item is skipped if it contains a skipper
            Skippers are not case sensitive

    Example:
    >>> list_data(r'c:\temp')  # noqa
    >>> skippers = (".txt", ".xls", ".ttf")  # noqa
    >>> exclude = lambda a: "_expired2013" in a  # noqa
    >>> list_data(r'c:\temp', exclude=exclude, skippers=skippers)  # noqa
    """

    exclude = options.get('exclude', None)
    exclude_dir = options.get('exclude_dir', None)
    oneach = options.get('oneach', None)
    onerror = options.get('onerror', None)
    datatypes = options.get('datatypes', None)
    type_ = options.get('type', None)
    skippers = options.get('skippers', None)

    if skippers is not None:
        skippers = [str(sk).lower() for sk in skippers]

    for dirpath, dirnames, filenames in _arcpy.da.Walk(top, topdown=True, onerror=onerror, followlinks=False, datatype=datatypes, type=type_):

        if exclude_dir is not None:
            _ = [di for di in dirnames if not exclude_dir(di)]

        for filename in filenames:
            item = _path.join(dirpath, filename)
            if exclude is not None:
                # skip items for which exclude is True
                if exclude(item):
                    continue
            if skippers is not None:
                # skip items that contain any skipper values
                if any([item.lower().find(sk) > -1 for sk in skippers]):
                    continue
            if oneach is not None:
                # handle item if 'oneach' handler provided
                oneach(item)
            yield item


def head(tbl: str, n: int = 10, as_rows: bool = True, delimiter: str = "; ", geoms=None, cols: (list, tuple) = ("*",), w: str = "", verbose: bool = True):
    """Return top rows of table tbl.

    Returns a list where the first element is a list of tuples representing
    first n rows of table tbl, second element is a dictionary like:
    {i: {"name":f.name, "values":[1,2,3,4 ...]}} for each field index i.


    Args:
        tbl (str): The feature class or table
        n (int): number of rows to read, default is 10
        as_rows (bool): if True (default), columns are printed as rows, otherwise as columns
        delimiter (str): string to be used to separate values (if t is True)
        geoms: if None (default), print geometries 'as is', else as str(geom).
        cols (list, tuple): list of columns to include, include all by default, case insensitive
        w (str): where clause to limit selection from tbl
        verbose (bool): suppress printing if False, default is True

    Example:
        >>> tmp = head('c:\\foo\\bar.shp', 5, True, "|", " ")
    """
    allcols = ['*', ['*'], ('*',), [], ()]
    colslower = [c.lower() for c in cols]
    flds = _arcpy.ListFields(_arcpy.Describe(tbl).catalogPath)
    if cols not in allcols:
        flds = [f for f in flds if f.name.lower() in colslower]
    fs = {}
    nflds = len(flds)
    fieldnames = []
    for i in range(nflds):
        f = flds[i]
        if cols in allcols or f.name in cols:
            fieldnames.append(f.name)
            fs.update({i: {"name": f.name, "values": []}})
    i = 0
    hd = []
    with _arcpy.da.SearchCursor(tbl, fieldnames, where_clause=w) as sc:
        for row in sc:
            i += 1
            if i > n: break
            hd.append(row)
            for j in range(nflds):
                fs[j]["values"].append(row[j])

    if as_rows:
        labels = []
        values = []
        for fld in range(nflds):
            f = fs[fld]
            fl = flds[fld]
            labels.append(str(fl.name) + " (" + str(fl.type) + "," + str(fl.length) + ")")
            if fl.type.lower() == 'geometry' and (geoms is not None):
                values.append(delimiter.join(map(str, len(f["values"]) * [geoms])))
            else:
                values.append(delimiter.join(map(str, f["values"])))
        longest_label = max(map(len, labels))
        for lbl, v in zip(labels, values):
            toprint = lbl.ljust(longest_label, ".") + ": " + v
            _arcpy.AddMessage(toprint)
            if verbose:
                print(toprint)
    else:
        if verbose:
            print_tuples(hd, delim=delimiter, tbl=flds, geoms=geoms, returnit=False)
    return [hd, fs]


def pretty_now():
    return _time.strftime('%H:%M%p %Z on %b %d, %Y')


def editor_tracking_disable(fname: str) -> None:
    """
    Disable editor tracking. Won't raise an error if editor tracking for a specific option does not exist (e.g. last editor is not enabled').
    All errors are suppressed with fuckit.

    See https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/disable-editor-tracking.htm

    Args:
        fname (str): The table/layer

    Returns:
        None

    Examples:
        First setting a workspace
        >>> import arcpy
        >>> arcpy.env.workspace = 'C:/my.gdb'
        >>> editor_tracking_disable('MyLayer')
        \n\nWithout setting a workspace
        >>> editor_tracking_disable('C:/my.gdb/MyLayer')
    """
    fname = _path.normpath(fname)
    with _fuckit:
        _arcpy.management.DisableEditorTracking(fname, creator='DISABLE_CREATOR')
        _arcpy.management.DisableEditorTracking(fname, creation_date='DISABLE_CREATION_DATE')
        _arcpy.management.DisableEditorTracking(fname, last_editor='DISABLE_LAST_EDITOR')
        _arcpy.management.DisableEditorTracking(fname, last_edit_date='DISABLE_LAST_EDIT_DATE')


def print_tuples(x, delim=" ", tbl=None, geoms=None, fillchar=" ", padding=1, verbose=True, returnit=False):
    """Print and/or return list of tuples formatted as a table.


    Intended for quick printing of lists of tuples in the terminal.
    Returns None or the formatted table depending on value of returnit.


    Required:
    x -- input list of tuples to print (can be tuple of tuples, list of lists).


    Optional:
    delim -- delimiter to use between columns
    tbl -- table or list of _arcpy.Field objects to take column headings from (default is None)
    geoms -- if None (default), print geometries 'as is', else as str(geom).
        Works only is valid tbl is specified.
    filchar -- string to be used to pad values
    padding -- how many extra fillchars to use in cells
    verbose -- suppress printing when False, default is True
    returnit -- if True, return the formatted table, else return None (default)
    """
    lpadding, rpadding = padding, padding
    fch = fillchar
    # find column widths
    gi = None
    if tbl is None:
        nms = ["V" + str(a) for a in range(len(x[0]))]
        tps = ["LONG" if str(ti).isdigit() else "TEXT" for ti in x[0]]
        geoms = None
    else:
        nms, tps = [], []
        i = 0
        if isinstance(tbl, list) or isinstance(tbl, tuple):
            fields = tbl
        else:
            fields = _arcpy.ListFields(tbl)
        for f in fields:
            nms.append(f.name)
            tps.append(f.type)
            if f.type.lower() == "geometry" and geoms is not None:
                gi = i  # index of geometry column
            i += 1

    to_left = []
    left_types = ("STRING", "TEXT")  # field types to be left justified
    for nmi in range(len(nms)):
        if tps[nmi].upper() in left_types:
            to_left.append(nmi)
    widths = []
    for nmi in range(len(nms)):
        widths.append(len(str(nms[nmi])))
    for tpl in x:
        for nmi in range(len(nms)):
            if geoms is not None and nmi == gi:
                clen = len(str(geoms))
            else:
                clen = len(str(tpl[nmi]))
            if clen > widths[nmi]:
                widths[nmi] = clen

    sbuilder = []
    frmtd = []
    for nmi in range(len(nms)):
        pad = widths[nmi] + lpadding + rpadding
        frmtd.append(str(nms[nmi]).center(pad, fch))

    hdr = delim.join(frmtd)
    if verbose: print(hdr)  # print header
    sbuilder.append(hdr)
    for r in x:
        frmtd = []
        for nmi in range(len(nms)):
            if nmi in to_left:
                if geoms is not None and nmi == gi:
                    pad = widths[nmi] + rpadding
                    padfull = pad + lpadding
                    valf = str(geoms).ljust(pad, fch).rjust(padfull, fch)
                else:
                    pad = widths[nmi] + rpadding
                    padfull = pad + lpadding
                    valf = str(r[nmi]).ljust(pad, fch).rjust(padfull, fch)
            else:
                if geoms is not None and nmi == gi:
                    pad = widths[nmi] + lpadding
                    padfull = pad + rpadding
                    valf = str(geoms).rjust(pad, fch).ljust(padfull, fch)
                else:
                    pad = widths[nmi] + lpadding
                    padfull = pad + rpadding
                    valf = str(r[nmi]).rjust(pad, fch).ljust(padfull, fch)
            frmtd.append(valf)
        rw = delim.join(frmtd)

        if verbose:
            print(rw)  # print row
        sbuilder.append(rw)

    ret = "\n".join(sbuilder) if returnit else None
    return ret


def nrow(x):
    """Return number of rows in a table as integer.

    Required:
    x -- input table or table view

    Example:
    >>> nrow('c:\\foo\\bar.shp')
    """
    return int(_arcpy.GetCount_management(x).getOutput(0))


def get_row_count(fname: str) -> int:
    """Return number of rows in a table as integer.

    Args:
        fname (str): Input table or table view

    Notes:
        Same as nrow (which it wraps)

    Returns:
        int: Row count of table/feature class fname

    Examples:
        >>> get_row_count('c:\\foo\\bar.shp')
        12
    """
    return nrow(fname)


def get_row_count2(fname: str, where: (str, None) = None) -> int:
    """
    Get nr rows using a SearchCursor, allowing use of a where clause

    Args:
        fname (str): path to feature class/layer
        where (str): where SQL string, passed to the searchcursor where_clause

    Returns:
        int: Row count of table/feature class fname

    Examples:
        >>> get_row_count2('c:\\foo\\bar.shp', where='OBJECTID>10')
        2
    """
    n = 0
    try:
        with _arcpy.da.SearchCursor(fname, ['OID@'], where_clause=where) as Cur:
            for _ in Cur:
                n += 1
    except RuntimeError as e:
        if 'field was not found' in str(e):
            raise ValueError('Get_row_count2 failed. The where clause "%s" referenced a field that does not exist in %s' % (where, fname))
    return n


def is_locked(fname: str) -> (bool, None):
    """
    Check of feature class schema is locked

    Args:
        fname (str): Feature class/table etc.

    Returns:
         bool: True if schema locked else False
         None: fname does not exist

     Notes:
         This checks for a schema lock, a schema lock does not necessarily
         indicate that data could not be added or edited .. but is a
         pretty good indication that anything you do with the table is
         going to fail ... and that may fail silently.

     Examples:
         >>> is_locked('C:/my.gdb/mylayer')
         False
         >>> is_locked('C:/my.gdb/god')
         None
    """
    fname = _path.normpath(fname)
    if not _arcpy.Exists(fname):
        return None  # noqa
    return not _arcpy.TestSchemaLock(fname)


def names(fname, filterer=None):
    """(str, func)->list

    Returns a list of column names of a table.

    Parameters:
    fname -- input table or table view
    filterer -- function, only fields where filterer returns True are listed

    Example:
    >>> names('c:\\foo\\bar.shp', lambda f: f.name.startswith('eggs'))  # noqa
    >>> ['eggscellent']
    """
    flds = _arcpy.ListFields(fname)
    if filterer is None: filterer = lambda a: True
    return [f.name for f in flds if filterer(f)]


def get_id_col(fname):
    """get name of objectid/fid column

    This will save lots of annoyance as ArcGIS will change the name
    of the autoincremental key field dependant on the source type"""
    return names(fname)[0]


def columns_delim(cols: (str, list, tuple), fname_or_db: str = '') -> list:
    """
    Get a list of properly delimited fields - used to generate where clauses
    for example by pypika

    Args:
        cols (list, str, tuple): string or iterable of column names
        fname_or_db (str): fully qualified path to the datasource

    Notes:
        https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/addfielddelimiters.htm
        Defaults to the current workspace if fname_or_db evaluates to false

    Examples:
        >>> columns_delim(('col_a', 'col_b'), 'c:/geo.gdb')
        ['"col_a"', '"col_b"']
    """
    if not fname_or_db:
        fname_or_db = _arcpy.env.workspace
    if isinstance(cols, str): cols = (cols,)
    return [_arcpy.AddFieldDelimiters(fname_or_db, s) for s in cols]


def is_shp(fname: str) -> bool:
    """Does it look like a shape file

    Args:
        fname (str): feature class

    Returns: bool

    Notes:
        Currently just checks for .shp at end of fname

    TODO:
        make is_shape and is_gdb robust
    """
    return fname[-4:] == '.shp'


def is_gdb(fname):
    """Does it look like a gdb feature class

    Args:
        fname (str): feature class

    Returns: bool

    Notes:
        currently just checks for .gdb in fname

    TODO:
        make is_shape and is_gdb robust
    """
    return fname[-4:] == '.gdb'


def gdb_from_fname(fname: str) -> str:
    """
    Get gdb path from a full qualified feature class or table path.

    Args:
        fname (str): the full qualified path

    Returns:
        str: The gdb path. Empty string if ".gdb" not in fname

    Notes:
        Just looks for gdb and slices the string out accordingly.
        Hence will fail if you have a path with multiple occurences of ".gdb"
        *** Superseeded by workspace_from_fname which handles any compatible spatial data source ***

    Examples:
        >>> gdb_from_fname('C:/my.gdb/my/layer')
        'C:/my.gdb'
    """
    if '.gdb' in fname:
        return fname[0:fname.index('.gdb\\') + 4]
    return ''


def workspace_from_fname(fname: str, simple_gdb_test: bool = True) -> (str, None):
    """ Get the workspace from a given layer/table name.

    Also see gdb_from_fname - which this superceeds, but performs quicker for file geodatabases.

    Currently supports Enterprise geodatabases and file geodatabases'

    Args:
        fname (str): The layer or feature class path
        simple_gdb_test (bool): Enable calling gdb_from_fname first to try and get the workspace, can save time if know we have a gdb.

    Returns:
        str: The workspace name
        None: If no geodatabase could be discerned from fname

    Notes:
        Oracle SDE layers are a pain and need fully qualifying with schema names.
        Use an instance of arcproapi.connection.OracleSDELayer to ease creation of fully qualified paths for SDE layers.

        This attempt to call Describe until it gets a match on known properties for spatial databases. Hence performance will probably be slow.
        At some time, ESRI will hopefully implement the database source when Describe-ing a table or feature class

    Examples:
        >>> workspace_from_fname('C:/my.gdb/my_layer', simple_gdb_test=True)
        'C:/my.gdb'
    """
    fname = _path.normpath(fname)
    parts = _Path(fname).parts

    if simple_gdb_test:
        # if we have a gdb, lets just use that and get out of here for performance reasons, but stick in try catch so don't have to think.
        ws = None
        try:
            ws = gdb_from_fname(fname)  # returns empty string if fails
        except:
            pass
        if ws: return ws

    # TODO Debug/test workspace_from_fname
    for i in reversed(range(len(parts))):
        root = _iolib.fixp(*parts[0:i])
        # Add more try catches for other geodatabases - currently pGDBs and Enterprise Geodbs catered for
        try:
            D = _arcpy.Describe(root)
            try:
                if D.connectionproperties.instance:
                    return root
            except:
                pass

            if D.connectionproperties.database:
                return root
        except:
            pass
    return None  # noqa



# this is reproduced in stuct, but don'as_rows import as will end up with circular reference issues
def oid_field(fname):
    """(str)->str
    Get the primary key field names

    Args:
        fname (str): path to feature class/table etc.

    Returns:
         str: Name of the autoincremental primary key field
    """
    return _arcpy.Describe(fname).OIDFieldName


# this is reproduced in stuct. Dont refactor or will risk ending up with circular references
def shape_field(fname: str) -> str:
    """
    Return name of the Shape (Geometry) field in feature class fname

    Args:
        fname (str): path to feature class/table etc.

    Returns:
         str: Name of the shape/geometry field
    """
    return _arcpy.Describe(fname).ShapeFieldName


def oid_max(fname: str) -> (int, None):
    """Get maximum oid

    Params:
        fname (str): featureclass or table path

    Returns: (int, None): The maximum oid or None if the feature class is empty

    Examples:
        >>> oid_max('c:/my.shp')
        12
    """
    fname = _path.normpath(fname)
    oid = get_id_col(fname)
    _arcpy.Statistics_analysis(fname, 'IN_MEMORY/__stats__', [[oid, 'MAX']])
    with _arcpy.da.SearchCursor('IN_MEMORY/__stats__', '*') as Cur:
        for row in Cur:
            return int(row[2])
    return None


def extent(in_file: str, buffer_length=0, align=False):
    """
    Extracts the ext of a feature class, and applies an optional buffer
    and/or rounds coordinates to a suitable alignment.

    Args:
        in_file (str):  The file to be processed.
        buffer_length (int): The distance to buffer the file by, in the files units.
        align (bool): Align the coordinates to sensible values.

    Returns:
        square_extent (tuple): An ext array for use as an input to create_grid.
    """

    # Set initial ext from arcpy Describe object, and convert to int. Min
    # coordinates are rounded down, whilst max coordinates are rounded up.
    in_file = _path.normpath(in_file)
    desc = _arcpy.Describe(in_file)
    min_x = (int(desc.Extent.XMin))
    min_y = (int(desc.Extent.YMin))
    max_x = (int(_math.ceil(desc.Extent.XMax)))
    max_y = (int(_math.ceil(desc.Extent.YMax)))

    # Adjust extents with buffer.
    if buffer_length:
        buffer_length = int(buffer_length)
        min_x -= buffer_length
        min_y -= buffer_length
        max_x += buffer_length
        max_y += buffer_length

    # Create ext array.
    min_xy = (min_x, min_y)
    max_xy = (max_x, max_y)
    square_extent = (min_xy, max_xy)

    # Adjust ext further to align to suitable coordinates.
    if align:
        return extent_round(square_extent)
    else:
        return square_extent


def extent_round(ext: (list, tuple), digits: (int, None) = None):
    """
    Rounds an ext array to a set number of digits, with minimum coordinates
    rounded down, and maximum coordinates rounded up, effectivly buffering the
    ext. The number of digits is the number of "places" to be rounded to.
    For example, an input ext with xy values of min_x=123456, min_y=321654,
    max_x=321654, max_y=123456, and digits set to 2, the output would be
    min_x=123400, min_y=321600, max_x=321700, max_y=124500.

    Args:
        ext (sequence):
            An array that must be formatted with two sub-sequences, the first
            containing the min x and min y coordinates of the ext, and the
            second the max equivalents. For example:
            ext = ((min_x, min_y)), ((max_x, max_y)).

        digits (int):
            The number of "places" to set the ext to. If set to zero, this
            will return an ext array rounded to integers.

    Returns:
        square_extent (tuple): An ext array for use as an input to create_grid.
    """

    # Read ext corner values.
    min_x = ext[0][0]
    min_y = ext[0][1]
    max_x = ext[1][0]
    max_y = ext[1][1]

    # Read the length and height of the ext rectangle.
    length = max_x - min_x
    height = max_y - min_y

    # If no value is set for the digits (0 counts as a value here), select a
    # digits value of half the length of the longest rectangle side. For
    # example, a length of 100000 would produce a digits value of 3.
    if digits is None:
        if len(str(int(length))) >= len(str(int(height))):
            digits = len(str(int(length)))
        else:
            digits = len(str(int(height)))
        digits /= 2

    # Round the input values to the required number of places (digits).
    min_x = int(round(min_x, -digits))
    min_y = int(round(min_y, -digits))
    max_x = int(round(max_x, -digits))
    max_y = int(round(max_y, -digits))

    # Create a new ext array and return.
    square_extent = ((min_x, min_y), (max_x, max_y))
    return square_extent


def release() -> str:
    """Get the release number.

    Returns:
        str: The release number

    Notes:
          This is also duplicated in root init

    Example:
        >>> release()
        '3.0'
    """
    return _arcpy.GetInstallInfo()['Version']


def version() -> Version:
    """
    Get version, ie ArcPro or ArcMap

    Returns:
        Version: Version as an enumeration.

    Examples:
        >>> version()
        Version.ArcPro
    """
    d = _arcpy.GetInstallInfo()
    return Version.ArcPro if d['ProductName'] == 'ArcGISPro' else Version.ArcMap


def pretty_field_mapping(field_map_str: str, to_console: bool = True, return_it: bool = False) -> (str, None):
    """Prettify a field mapping.
    Field mappings look messy when directly pasted from the arcpro tool history.
    Take the field mapping as pasted, and this will prettify it so that each line
    represent the mapping for a single field.

    This can be pasted in place of the long fieldmapping string pasted by default from arcpro tool history.

    Also see https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/spatial-join.htm

    Args:
        field_map_str (str): The field mapping string
        to_console (bool): Print it to the console
        return_it (bool): return the value

    Returns:
        str: The field mapping, prettified, if return_it == True
        None: if not return_it

    Notes:
        In pycharm, *** send this func to the python console by highlighting and pressing ALT-SHIFT-E ***

    Examples:
        >>> print(pretty_field_mapping(r'PLOT_TYPE "PLOT_TYPE" true true false 1 Text 0 0,First,#,veg_plot,PLOT_TYPE,0,1;PLOT_NUMBER "PLOT_NUMBER" true...'))
        (
        r'PLOT_TYPE "PLOT_TYPE" true ....
    """
    lst = ["r'%s;'\n" % v for v in field_map_str.split(';')]
    lst[-1] = lst[-1].replace(';', '')
    ss = '%s%s%s' % ('(\n', "".join(lst), ')')
    if ss[-1:] == ';':
        ss = ss[0:-1]
    if field_map_str[-1] == ',': ss += ','
    if to_console:
        print(ss)
    if return_it: return ss


def extent_where(fname: str, where: (str, None) = None) -> _arcpy.Extent:
    """
    Return an extent from shapes in where

    Args:
        fname (str): feature class
        where (str, None):

    Returns:
        _arcpy.Extent: The extent of the union for all shapes which match the where
    """
    fname = _path.normpath(fname)
    with _arcpy.da.SearchCursor(fname, 'SHAPE@', where) as cur:
        ext: _arcpy.Extent = _functools.reduce(_arcpy.Geometry.union, [shp for shp, in cur]).extent
    return ext

def extent_wheres(fnames: list[str], wheres: list[str]) -> _arcpy.Extent:
    """
    Get the union extent from multiple layers with matched wheres.
    Matching is by index

    Args:
        fnames (list[str]): list of feature class paths
        wheres (list[str]): list of wheres, None can be used to match all in a layer

    Raises:
        ValueError: If length of fnames and wheres does not match

    Returns:
        _arcpy.Extent: An extent object, of the union of all matching features

    Examples:
        Extent of all cities in England and Wales with a population > 10000
        >>> print(extent_wheres(['C:/my.gdb/country', 'C:/my.gdb/city'], ['country in ("England", "Wales")', 'population>10000']))
        227873.762207031 333000 229010.31060791 334146.519592285 NaN NaN NaN NaN
    """
    if len(fnames) != len(wheres):
        raise ValueError('length of fnames and wheres should be the same')
    exts = tuple(map(extent_where, fnames, wheres))
    ext = _functools.reduce(_arcpy.Geometry.union, [ex.polygon for ex in exts]).extent
    return ext


if __name__ == '__main__':
    """ Quick debug/test """
    sq = r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\common\data\GIS\erammp_common.gdb\sq'
    poll = r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\common\data\GIS\erammp_common.gdb\pollinator_transect'
    EX = extent_wheres([sq, poll], ['sq_id=35573']*2)
    pass
    # extall = _arcpy.Geometry(ext.po) .union()
