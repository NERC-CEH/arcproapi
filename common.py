"""helper functions etc"""
import time as _time
import os as _os
import os.path as _path
import datetime as _datetime
import sys as _sys

import arcpy as _arcpy


import arcapi.errors


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


class FieldNamesSpecial:
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
            raise arcapi.errors.ArcapiError(em)

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


def head(tbl, n=10, t=True, delimiter="; ", geoms=None, cols=("*",), w="", verbose=True):
    """Return top rows of table tbl.


    Returns a list where the first element is a list of tuples representing
    first n rows of table tbl, second element is a dictionary like:
    {i: {"name":f.name, "values":[1,2,3,4 ...]}} for each field index i.


    Optional:
    n -- number of rows to read, default is 10
    t -- if True (default), columns are printed as rows, otherwise as columns
    delimiter -- string to be used to separate values (if t is True)
    geoms -- if None (default), print geometries 'as is', else as str(geom).
    cols -- list of columns to include, include all by default, case insensitive
    w, where clause to limit selection from tbl
    verbose -- suppress printing if False, default is True

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

    if t:
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


def types(x, filterer=None):
    """Return list of column types of a table.

    Required:
    x -- input table or table view

    Optional:
    filterer -- function, only fields where filterer returns True are listed

    Example:
    >>> types('c:\\foo\\bar.shp', lambda f: f.name.startswith('eggs'))  # noqa
    """
    flds = _arcpy.ListFields(x)
    if filterer is None: filterer = lambda a: True
    return [f.type for f in flds if filterer(f)]


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
    with _arcpy.da.SearchCursor(fname, ['OID@'], where_clause=where) as Cur:
        for row in Cur:
            n += 1
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
        return None
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


def columns_delim(fname: str, cols: (str, list, tuple)) -> list:
    """
    Get a list of properly delimited fields - used to generate where clauses
    for example by pypika

    Args:
        fname (str): fully qualified path to the datasource
        cols (list, str, tuple): string or iterable of column names

    Notes:
        https://github.com/kayak/pypika
        https://desktop.arcgis.com/en/arcmap/10.3/analyze/arcpy-functions/addfielddelimiters.htm

    Examples:
        >>> columns_delim('c:/geo.gdb', ('col_a', 'col_b'))
        ['"col_a"', '"col_b"']
    """
    if isinstance(cols, str): cols = (cols,)
    return [_arcpy.AddFieldDelimiters(fname, s) for s in cols]



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
    return '.gdb' in fname


# this is reproduced in stuct, but don't import as will end up with circular reference issues
def oid_field(fname):
    """(str)->str
    Get the primary key field names

    Args:
        fname (str): path to feature class/table etc.

    Returns:
         str: Name of the autoincremental primary key field
    """
    return _arcpy.Describe(fname).OIDFieldName

# this is reproduced in stuct, but don't import as will end up with circular reference issues
def shape_field(fname):
    """(str)->str
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
