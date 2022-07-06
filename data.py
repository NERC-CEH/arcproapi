"""Operations on data"""
from warnings import warn as _warn
import os.path as _path

import fuckit as _fuckit

import arcpy as _arcpy
import pandas as _pd
import numpy as _np

import arcproapi.struct as _struct
import arcproapi.errors as _errors
import arcproapi.crud as _crud
import arcproapi.orm as _orm
import arcproapi.common as _common
from arcproapi.common import get_row_count2 as get_row_count2
from arcproapi.common import get_row_count as get_row_count  # noqa

import funclite.iolib as _iolib
import funclite.baselib as _baselib


def fields_copy_by_join(fc_dest: str, fc_dest_key_col: str, fc_src: str, fc_src_key_col: str, cols_to_copy: (list, tuple) = ()):
    """Join values from one table to another using dictionary.

    Arcpy supports extending tables using numpy arrays:
    https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/extendtable.htm

    Add fields from one table to another by using a dictionary rather
    than joining tables.  There must be a field with common values between the
    two tables to enable attribute matching.  Values from "join_key" field in
    "join_table" should be unique.  This function can be faster than a standard
    Join Tool for tables with only couple of hundreds or thousands of records.
    This function alters the input source_table.
    Returns path to the altered source table.

    source_table (str): table to add fields
    in_field (str): join field with common values from join_table
    join_table (str): table containing fields to add
    join_key (str): common field to match values to source_table
    join_values (list, tuple): fields to add from join_table to source_table

    Returns: None


    Examples:
        >>> parcels = r'C:\Temp\Parcels.gdb\Parcels'
        >>> permits = r'C:\Temp\Parcels.gdb\Permits'
        >>> add_flds = ['PERMIT_NUM', 'PERMIT_DATE', 'NOTE']
        >>> fields_copy_by_join(parcels, 'PIN', 'permits', 'PARCEL_ID', add_flds)
    """
    # Needs debugging

    # Get Catalog path (for feature layers and table views)
    cat_path = _arcpy.Describe(fc_dest).catalogPath

    # Find out if source table is NULLABLE
    if not _path.splitext(cat_path)[1] in ['.dbf', '.shp']:
        nullable = 'NULLABLE'
    else:
        nullable = 'NON_NULLABLE'

    # Add fields to be copied
    update_fields = []
    join_list = _arcpy.ListFields(fc_src)
    for field in join_list:
        ftype = field.type
        name = field.name
        length = field.length
        pres = field.precision
        scale = field.scale
        alias = field.aliasName
        domain = field.domain
        for fldb in cols_to_copy:
            if fldb == name:
                name = _struct.field_name_create(fc_dest, fldb)
                _arcpy.AddField_management(fc_dest, name, ftype, pres, scale, length, alias, nullable, '', domain)
                update_fields.insert(cols_to_copy.index(fldb), name.encode('utf-8'))

    path_dict = {}
    cols_to_copy.insert(0, fc_src_key_col)
    with _arcpy.da.SearchCursor(fc_src, cols_to_copy) as srows:
        for srow in srows:
            path_dict[srow[0]] = tuple(srow[1:])

    # Update Cursor
    update_index = list(range(len(update_fields)))
    row_index = list(x + 1 for x in update_index)
    update_fields.insert(0, fc_dest_key_col)
    with _arcpy.da.UpdateCursor(fc_dest, update_fields) as urows:
        for row in urows:
            if row[0] in path_dict:
                the_val = [path_dict[row[0]][i] for i in update_index]
                for r, v in zip(row_index, the_val):
                    row[r] = v
                urows.updateRow(row)


def poly_from_extent(ext, sr):
    """Make an arcpy polygon object from an input extent object.

    Returns a polygon geometry object.

    Required:
    ext -- extent object
    sr -- spatial reference

    Example
    >>> ext_ =
    .,.
    326  #WKID for WGS 84
    >>> poly = poly_from_extent(ext_, sr)
    >>> _arcpy.CopyFeatures_management(poly, r'C:\Temp\Project_boundary.shp')
    """
    array = _arcpy.Array()
    array.add(ext.lowerLeft)
    array.add(ext.lowerRight)
    array.add(ext.upperRight)
    array.add(ext.upperLeft)
    array.add(ext.lowerLeft)
    return _arcpy.Polygon(array, sr)


def tuple_list_to_table(x, out_tbl, cols, null_number=None, null_text=None):
    """Save a list of tuples as table out_tbl and return catalog path to it.

    Required:
    x -- list of tuples (no nesting!), can be list of lists or tuple of tuples
    out_tbl -- path to the output table
    cols -- list of tuples defining columns of x. Can be defined as:
        [('colname1', 'type1'), ('colname2', 'type2'), ...]
        ['colname1:type1:lgt1', 'colname2:type2', ('colname3', 'type3')]
        [('colname1', 'type1'), 'colname2:type2:lgt2, ...]
        where types are case insensitive members of:
        ('SHORT', 'SMALLINTEGER', 'LONG', 'INTEGER', 'TEXT', 'STRING', 'DOUBLE',
        'FLOAT')
        Each column definition can have third element for length of the field,
        e.g.: ('ATextColumn', 'TEXT', 250).
        To leave out length, simply leave it out or set to '#'

    Optional:
    nullNumber -- a value to replace null (None) values in numeric columns, default is None and does no replacement
    nullText -- a value to replace null (None) values in text columns, default is None and does no replacement

    Example:
    >>> x_ = [(...),(...),(...),(...),(...), ...]
    >>> ot = 'c:\\temp\\foo.dbf'
    >>> tuple_list_to_table(x_, ot, [('IDO', 'SHORT'), ('NAME', 'TEXT', 200)]
    >>> tuple_list_to_table(x_, ot, ['IDO:SHORT', 'NAME:TEXT:200']
    """

    # decode column names, types, and lengths
    cols = [tuple(c.split(":")) if type(c) not in (tuple, list) else c for c in cols]

    # remember what indexes to replace if values are null
    replace_numbers, replaces_text = [], []
    for i in range(len(cols)):
        if cols[i][1].upper() in ('TEXT', 'STRING'):
            replaces_text.append(i)
        else:
            replace_numbers.append(i)

    do_replace_number = False if null_number is None else True
    do_replace_text = False if null_text is None else True
    do_replace = do_replace_number or do_replace_text

    dname = _path.dirname(out_tbl)
    if dname in ('', u''): dname = _arcpy.env.workspace
    r = _arcpy.CreateTable_management(dname, _path.basename(out_tbl))
    out_tbl = r.getOutput(0)

    # add the specified fields
    for f in cols:
        fname = f[0]
        ftype = f[1].upper()
        flength = '#'
        if len(f) > 2:
            flength = int(f[2]) if str(f[2]).isdigit() else '#'
        _arcpy.AddField_management(out_tbl, fname, ftype, '#', '#', flength)
    # rewrite all tuples
    fields = [c[0] for c in cols]

    with _arcpy.da.InsertCursor(out_tbl, fields) as ic:
        for rw in x:
            if do_replace:
                rw = list(rw)
                # TODO This looks bugged, need to debug
                if i in replace_numbers:  # noqa
                    if rw[i] is None:
                        rw[i] = null_number
                if i in replaces_text:
                    if rw[i] is None:
                        rw[i] = null_text
                rw = tuple(rw)
            ic.insertRow(rw)
    return out_tbl


def field_values(fname: str, col: (str, list), where: (str, None) = None, order_by: (str, None) = None, distinct: bool = False) -> any:
    """(str, str|iter, str, str, bool) -> list

    Return a list of all values in column col in table tbl.

    If col is a single column, returns a list of values, otherwise returns
    a list of tuples of values where each tuple is one row.

    Columns included in the o parameter must be included in the col parameter!

    Args:
        fname (str): input table or table view
        col (str, list): column name(s) as string, a csv or colon seperated string, or a list
        where (str): where clause
        order_by (str): order by clause like '"OBJECTID" ASC, "Shape_Area" DESC',
                        default is None, which means order by object id if exists
        distinct (bool): unique values only

    Returns:
        list(tuple): list of tuples if mutliple columns requested
        list: list lof values if single col defined

    Raises:
        RuntimeError: Columns defined in order_by must be in col, otherwise a RuntimeError is raised

    Examples:
        >>> field_values('c:\\foo\\bar.shp', col='Shape_Length')
        [1.23,2.34, ..]

        Need to check return values our regads SHAPE@XY
        >>> field_values('c:\\foo\\bar.shp', col='SHAPE@XY')

        Multiple columns with where and order by clauses
        >>> field_values('c:\\foo\\bar.shp', col='OID@;Shape_Length', where='"OBJECTID" < 3', order_by='Shape_Length ASC')
        [(1, 2.34), (2, 1.55), ..]

        RuntimeError raised, order_by col not in cols
        >>> field_values('c:\\foo\\bar.shp', col='SHAPE@XY', order_by='Shape_Length DESC')
        Traceback (most recent call last): ....
    """

    # unpack column names
    if isinstance(col, (list, tuple)):
        cols = col
    else:
        col = str(col)
        separ = ';' if ';' in col else ','
        cols = [c.strip() for c in col.split(separ)]

    # indicate whether one or more than one columns were specified
    multicols = False
    if len(cols) > 1:
        multicols = True

    # construct order by clause
    if order_by is not None:
        order_by = 'ORDER BY ' + str(order_by)

    # retrieve values with search cursor
    ret = []
    with _arcpy.da.SearchCursor(fname, cols, where_clause=where, sql_clause=(None, order_by)) as sc:
        for row in sc:
            if multicols:
                ret.append(row)
            else:
                ret.append(row[0])

    if distinct:
        ret = list(set(ret))

    return ret


def field_get_dup_values(fname, col, value_list_only=True, f=lambda v: v) -> (list, dict):
    """
    Check a col for duplicates

    Args:
        fname:
        col (str): col to check
        value_list_only (bool): Get as simple list rather than dict
        f: function passed to map, typical use would be f=str.lower to make duplicate checks case insensitive

    Returns:
        list: Simple list of values which have duplicates
        dict: A dictionary of duplicates. Keys are the duplicate values and values are is the counts of duplicate values

    Examples:
        sum_of_stuff col n, as duplicates for 2 and 10. Asked for simple list
        >>> field_get_dup_values('c:/my.gdb/sum_of_stuff','n')
        [2, 10]

        fave_colour colour has 2 occurence of blue and 5 occurences of black - and we asked for this detail
        and don't care about case
        >>> field_get_dup_values('c:/my.gdb/fave_colour','colour', False, f=str.lower)
        {'blue':2,'black':5}
    """
    # DEBUG THIS
    fname = _path.normpath(fname)
    vals = list(map(f, field_values(fname, col)))
    res = _baselib.list_get_dups(vals, value_list_only=value_list_only)
    return res


def table_as_pandas(fname, cols=(), where='', null_value=_np.NaN, **kwargs):
    """(str, iter:str, iter:str, str, dict) -> pandas.dataframe
    Get a feature layer or table as a pandas dataframe

    See https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/featureclasstonumpyarray.htm
    for list of named arguments and special column names

    Note:
        The Arcpy FeatureClassToNumpyArray is bugged, and will fail on dates with null values.
        If this happens, use table_as_pandas2

    Parameters
    fname (str): path to data
    cols (list, tuple): tuple of the columns to retrieve
    out_headers (list, tuple): list of header names to use for the returned dataframe
    where (str): a where statement to filter results (see https://pro.arcgis.com/en/pro-app/latest/help/mapping/navigation/sql-reference-for-elements-used-in-query-expressions.htm)
    kwargs: additionl arguments to pass to arcpy.da.FeatureClassToNumPyArray

    Example
        >>> df = table_as_pandas('c:/lyr.shp', ('id','contact_name'), "contact_name='John'", skip_nulls=False)
    """
    fname = _path.normpath(fname)
    c = '*' if not cols else cols
    return _pd.DataFrame(_arcpy.da.FeatureClassToNumPyArray(fname, field_names=c, where_clause=where, null_value=null_value, **kwargs))


def pandas_to_table(df: _pd.DataFrame, fname: str, overwrite=False, max_str_len=0, fix_ascii_errors=False):
    """

    Args:

        max_str_len (int): pandas dataframes usually stores strings as objects.
            If max_str_len is 0, then the length of the max string will be used to convert the object type to a byte field,
            else max_str_len will be used, allowing for longer strings to be stored in the created table
        df (pandas.DataFrame): the pandas dataframe
        fname (str): table name to write
        overwrite (bool): Overwrite fname, otherwise an error will be raised if fname exists
        max_str_len (int): fix the string length
        .
        fix_ascii_errors:
            remove none ascii characters if they exist in object cols
            (work around for bugged arcpy.da.NumpyArrayToTable

    Raises:
        RunTimeError: If fname already exists and overwrite is False

    Returns: None

    Notes:
        ArcPy.da.NumPyArrayToTable silently fixes invalid characters in record names,
        replacing them with an underscore. e.g. My% will become 'my_'
        So advise manually checking column names created in the final export.

    Examples:
        >>> d = _pd.DataFrame({'A':['a','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']})  # noqa
        >>> pandas_to_table(df, 'C:/my.gdb/test')  # noqa
    """
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_records.html
    # https://numpy.org/doc/stable/reference/arrays.scalars.html#built-in-scalar-types
    # https://pro.arcgis.com/en/pro-app/2.8/arcpy/data-access/numpyarraytotable.htm
    # https://numpy.org/doc/stable/user/basics.rec.html
    fname = _path.normpath(fname)
    df_copy = df.copy(deep=True)
    if overwrite:
        _struct.fc_delete2(fname)

    if max_str_len:
        s = '|S%s' % max_str_len
    else:
        s = 'bytes'

    for i, t in enumerate(df_copy.dtypes):
        if str(t) == 'object':  # object, assume string .. ok for now, extend on a case by case basis as expect other stuff will error like dates
            if fix_ascii_errors:
                df_copy[df_copy.columns[i]] = df_copy[df_copy.columns[i]].apply(lambda x: x.encode('ascii', 'ignore').decode('ascii'))
            df_copy[df_copy.columns[i]] = df_copy[df_copy.columns[i]].astype(s)
    recarray = df_copy.to_records(index=False)
    _arcpy.da.NumPyArrayToTable(recarray, fname)


def pandas_to_table2(df: _pd.DataFrame, workspace: str, tablename: str, overwrite=False, del_cols=(), **kwargs):
    """
    Uses a different kludge to get around bugs with pandas no-ascii strings
    and arcpys bug on importing pandas cols of type object - the default
    col type class for pandas string representations.

    Args:
        df (pandas.DataFrame): the pandas dataframe
        workspace (str): gdb
        tablename (str): tablename to create in workspace
        overwrite (bool): Overwrite fname, otherwise an error will be raised if fname exists
        del_cols (tuple): Tuple of columns to discard, arcpy.conversion.table2table can create eroneous cols.
        **kwargs: passed to pandas.to_csv (used as an intermediary to get over bugs in ArcPy

    Raises:
        RunTimeError: If fname already exists and overwrite is False
        IOError: If the feature class to write exists and arcpy reports it as locked

    Returns: None

    Examples:
        >>> df = _pd.DataFrame({'A':['a','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']})  # noqa
        >>> pandas_to_table2(df, 'C:/my.gdb', 'my_table_name')  # noqa
    """

    workspace = _path.normpath(workspace)
    tmp_file = _iolib.get_temp_fname(suffix='.csv')
    df.replace('"', "'", inplace=True)
    df.to_csv(tmp_file, sep=',', index=False, **kwargs)
    fname = _iolib.fixp(workspace, tablename)

    if _common.is_locked(fname):
        raise IOError('%s is locked. Make sure all projects are closed')

    if overwrite:
        _struct.fc_delete2(fname)
    _arcpy.conversion.TableToTable(tmp_file, workspace, tablename)  # noqa
    if del_cols:
        with _fuckit:
            _arcpy.DeleteField_management(fname, del_cols)
    _iolib.file_delete(tmp_file)


def table_as_pandas2(fname: str, cols: (str, list) = None, where: str = None, exclude_cols: (str, list) = ('Shape', 'Shape_Length', 'Shape_Area'), **kwargs):
    """Export data in feature class/table fname to a pandas DataFrame

    Args:
        fname (str): Path to feature class or table.
        cols (str, list, tuple): column list to retrieve.
        where (str): where clause, passed as-is to SearchCursor
        exclude_cols (str, list, tuple): list of cols to exclude
        kwargs: keyword args passed to pandas.DataFrame.from_records

    Returns:
        pandas.DataFrame: The feature class or table converted to a pandas DataFrame

    Notes:
        The primay key of fname is used as the dataframes index.
        For performance reasons and erroneous errors when viewing the data (e.g. in xlwings), exclude the shape column if not needed.

    Examples:
        >>> df = table_as_pandas2('C:/my.gdb/fc', ['OBJECTID', 'modified_date'], where='OBJECTID>10')  # noqa
    """

    if isinstance(exclude_cols, str): exclude_cols = [exclude_cols]
    if isinstance(cols, str): cols = [cols]

    def _filt(s, col_list):
        return s.lower() not in map(str.lower, col_list)

    flds = _struct.field_list(fname)
    if not cols:
        cols = list(filter(lambda f: _filt(f, exclude_cols), flds))

    df = _pd.DataFrame.from_records(data=_arcpy.da.SearchCursor(fname, cols, where_clause=where), columns=cols, **kwargs)
    return df


def table_as_dict(fname, cols=None, where=None, exclude_cols=('Shape', 'Shape_Length', 'Shape_Area'), **kwargs) -> dict:
    """(str, iter, iter)
    load data from an ESRI feature set or table and return as a dict.

    Args:
        fname: Path to feature class or table.
        cols: column list to retrieve.
        where: where clause, passed as-is to SearchCursor
        exclude_cols: list of cols to exclude
        **kwargs: keyword args passed to pandas.DataFrame.from_records

    Returns: dict

    Notes:
        The primay key of fname is used as the intermediary dataframes index prior to conversion to a dict.
        For performance reasons and erroneous errors when viewing the data (e.g. in xlwings), exclude the shape column if not needed (default).
        This function is just a call to table_as_pandas2, with the output dataframe then converted to a dict in pandas

    Examples:
        >>> df = table_as_dict('C:/my.gdb/fc', [OBJECTID, modified_date], where='OBJECTID>10')  # noqa
    """
    df = table_as_pandas2(fname, cols=cols, where=where, exclude_cols=exclude_cols, **kwargs)
    return df.to_dict()


def field_update_from_dict2(fname: str, key_dict: dict, update_dict: dict, where: str = '', na: any = None, case_insentive: bool = True) -> int:  # noqa
    """Update columns in a table which match values ib key_dict.

    Differs from field_update_from_dict as dicts are in long form and column updates.

    Args:
        fname (str): table to update
        key_dict (dict): match this dict, where keys are col names and values are values to match
        update_dict (dict): update values, keys are col names, values oare value to write
        where (str): where clause to prefilter rows
        na (bool): value to be used instead of new value for non-matching records,
            default is None, use (1,1) to leave original value if match is not found
        case_insentive (bool): ignore case for key_dict

    Returns:
        int: Number of updated records

    Examples:
        Write values of keyA and keyB to keyACopy and keyBCopy where (kayA==1 AND keyB==10) OR (kayA==2 AND keyB==20)
        >>> field_update_from_dict2('c:/my.gdb', {'keyA':[1,2],'keyB':[10,20]}, {'keyACopy':[1,2], 'keyBCopy':[10,20]})  # noqa
    """
    raise NotImplementedError


def field_update_from_dict(fname: str, dict_: dict, col_to_update: str, key_col: str = None, where: str = '', na: any = None) -> int:
    """Update column in a table with values from a dictionary.

    Return number of updated records.

    Args:
        fname: table to update
        dict_: dictionary with new values
        col_to_update: name of the column of fname to update
        key_col: column in fname to be used as keys to look up values in the feature class,
            default is None, which means to use objectid field.
        where: where clause to select rows to update in the feature class
        na: value to be used instead of new value for non-matching records,
            default is None, use (1,1) to leave original value if match is not found

    Returns:
        int: Number of updated records

    Examples:
        >>> fc = 'c:\\foo\\bar.shp'
        >>> d = {1: 'EN', 2:'ST', 3:'WL', 4:'NI'}
        .
        Dictionary keys are table index numbers (ObjectID, OID etc)
        >>> field_update_from_dict(fc, d, 'country_code')
        .
        Explicit declaration of update and key columns
        >>> field_update_from_dict(fc, d, col_to_update='country_code', key_col='country_num', na='Other')
    """
    fname = _path.normpath(fname)

    if key_col is None:
        key_col = _arcpy.Describe(fname).OIDFieldName

    # indicate whether to leave nonmatching values unchenged or set to na
    identity = na == (1, 1)

    if col_to_update == key_col:
        selfupdate = True
        cols = [key_col]
    else:
        selfupdate = False
        cols = [key_col, col_to_update]

    cnt = 0

    n = get_row_count2(fname, where)
    if n == 0:
        _warn('No records matched where query "%s" in %s. Did you expect this?' % (where, fname))

    PP = _iolib.PrintProgress(maximum=n)
    with _arcpy.da.UpdateCursor(fname, cols, where_clause=where) as uc:
        for row in uc:
            ido = row[0]
            if identity:
                # branch that leaves unmatched records unchanged but only if we are using an identity, weird
                if ido in dict_:
                    newval = dict_[ido]
                    if selfupdate:
                        row[0] = newval
                    else:
                        row[1] = newval
                    uc.updateRow(row)
                    cnt += 1
                else:
                    pass
            else:
                # branch that sets unmatched records to na
                newval = dict_.get(ido, na)
                if selfupdate:
                    row[0] = newval
                else:
                    row[1] = newval
                uc.updateRow(row)
                cnt += 1
            PP.increment()
    return cnt


# this could be extented to allow multi argument functions by providing named arguments
# to pass thru
def fields_apply_func(fc, cols, *args, where_clause=None, show_progress=False):
    """(str, iter|str, *args, str|None, bool)->None

    Updates all cols in where_clause filtered layer fc and applies
    functions passed to args to them.

    fc: path to feature class/shapefile (e.g. c:\tmp\myfile.shp)
    cols: iterable of columns to transform with func(s) in args (str for single col is ok)
    args: 1 or more single argument function pointers
    where_clause: applied to filter rows to be updated (STATE="Washington")
    show_progress: Have this func print a progress bar to the console


    Example
    f1 = str.lower: f2 = str.upper
    fields_apply_func('c:/my.shp', ['street','town'], f1, f2, where_clause='town="bangor"')
    """
    fc = _path.normpath(fc)
    if show_progress:
        max_ = int(_arcpy.GetCount_management(fc)[0])  # yes get count management gets the count as a fucking string
        PP = _iolib.PrintProgress(maximum=max_)

    if isinstance(cols, str): cols = [cols]

    with _arcpy.da.UpdateCursor(fc, cols, where_clause=where_clause) as cursor:
        for i, row in enumerate(cursor):
            vals = [row[j] for j in range(len(cols))]
            for f in args:  # function chaining
                vals = [f(v) for v in vals]  # pass in our function to correct the data

            for k, v in enumerate(vals):
                row[k] = v
                cursor.updateRow(row)
            if show_progress:
                PP.increment()  # noqa


def del_rows(fname: str, cols: any, vals: any, where: str = None, show_progress: bool = True, no_warn=False) -> int:
    """
    Delete rows which match criteria.

    Args:
        fname (str): path to feature class/layer
        cols (any):iterable or a string (e.g. ['cola','colb'] or 'cola'), also accepts "*" which just says get the OID field (combine with vals='*')

        vals (any): iterable of iterables, matched to cols, example [[1,2,3],['a','b','c']]. This would delete rows where (cola=1 AND colb='a') OR (cola=2 AND colb='b'), or a single value
                    Set vals to "*" to delete everything, for safety, only works when where is specified.

        where (str, None): where string to prefilter rows
        show_progress (bool): Show progress bar, costs a bit of time to determine row count
        no_warn (bool): Do not raise DataDeleteAllRowsWithNoWhere if asked to delete all rows (vals='*') with no where specified

    Raises:
        DataDeleteAllRowsWithNoWhere: If asked to delete all rows (vals='*') with no where specified

    Returns:
        int: Number of deleted rows

    Notes:
        This has not been tested with date strings passed to vals.
        Ensure vals are nested lists if not using single value, e.g. use: [[''], ['']] - NOT ['','']
        Multiple criteria is an (obviously) OR match, see examples.

    Examples:
        .
        Delete rows where (cola=1 and colb='a') OR (cola=2 and colb='b') OR (cola=3 and colb='c')
        >>> del_rows('c:/shp.shp', ['cola','colb'], [[1,2,3],['a','b','c']])
        >>> del_rows('c:/shp.shp', 'cola', 1)  # deletes every record where cola==1
        .
        Use wildcard delete, we don't care about cols, so just use OBJECTID
        >>> del_rows('c:/my.gdb', 'OBJECTID', '*', where='OBJECTID<10')
        .
        Delete everything
        >>> del_rows('c:/my.gdb', '*', '*', no_warn=True)
    """
    if cols == '*':
        cols = _struct.field_oid(fname)

    if not no_warn:
        if vals == '*' and not where:
            raise _errors.DataDeleteAllRowsWithNoWhere('Asked to delete all rows with no where (vals="*" and where in (None,"")')

    if isinstance(cols, str):
        cols = (cols,)

    if isinstance(vals, (str, int, float)) and vals != '*':
        vals = [[vals]]

    fname = _path.normpath(fname)
    if show_progress:
        PP = _iolib.PrintProgress(maximum=get_row_count2(fname, where))  # noqa

    j = 0
    with _arcpy.da.UpdateCursor(fname, cols, where_clause=where) as C:
        if vals == '*':
            for _ in C:
                C.deleteRow()
                j += 1
                if show_progress:
                    PP.increment()  # noqa
        else:
            # TODO Needs debugging and is probably dodgy
            if vals is None:
                criteria = [[None]]
            else:
                criteria = tuple(zip(*vals))

            for i, row in enumerate(C):
                for crit in criteria:
                    all_ = ([crit[k] == row[k] for k in range(len(crit))])
                    if all(all_):
                        C.deleteRow()
                        j += 1
                        break

                if show_progress:
                    PP.increment()  # noqa
    return j


# These are also in funclite.pandaslib, but reproduce them here.
def pandas_join_multi(dfs: list, key: str) -> _pd.DataFrame:
    """
    Joins all dataframes by a common column

    Args:
        dfs: list or tuple of dataframes
        key: candidate key column

    Returns:
        pandas.DataFrame: The joined dataframes

    Notes:
        Only supports a single column and assumes all key columns are named the same

    Examples:
          >>> pandas_join_multi([df1, df2, df3], key='objectid')  # noqa
    """
    df_first = dfs[0]
    for df in dfs[1:]:
        df_first = pandas_join(df_first, df, from_key=key, to_key=key)
    return df_first


# These are also in funclite.pandaslib, but reproduce them here.
def pandas_join(from_: _pd.DataFrame, to_: _pd.DataFrame, from_key: str, to_key: str, drop_wildcard: str = '__', how='left', **kwargs) -> _pd.DataFrame:
    """
    Join two pandas dataframes base on two named key cols.

    Args:
        from_: Datafrome
        to_: left join to this dataframe
        from_key: key in "from" table
        to_key: key in "to" table
        drop_wildcard: matched cols will be
        how: "left", "inner", "right"
        kwargs: Keyword args to pass to pandas join func

    Returns:
        pandas dataframe from the join

    Notes:
        See https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.join.html for kwargs
    """
    join = from_.set_index(from_key).join(to_.set_index(to_key), how=how, rsuffix=drop_wildcard, **kwargs)  # join on sq_id, left join as sanity check
    if drop_wildcard:
        join.drop(list(join.filter(regex=drop_wildcard)), axis=1, inplace=True)  # drop duplicate cols
    join = join.reset_index()
    return join


def features_copy(source: str, dest: str, workspace: str, where_clause: str = '*', fixed_values=None, copy_shape: bool = True, force_add: bool = True, fail_on_exists: bool = True,
                  expected_row_cnt: int = None, no_progress: bool = False, **kwargs) -> int:
    """Copy features from one table or featureclass to another

    Args:
        source (str): path to source feature class/table
        dest (str): path to destination feature class/table
        workspace (str): path to workspace
        where_clause (str): used to filter the target table

        fixed_values (dict):
            pass a dictionary kwargs (field:value) of fields in the destination to assign fixed values to.
            For example: {'sq_id':1234} would write all destination sq_ids as 1234 which matched the where_clause
            Note that **kwargs will override fixed_values if these fields (keys) are duplicated between
            the two.

        copy_shape (bool): set to false if working with a table, otherwise set this to true to transfer geometry

        force_add (bool):
            Set to false when you want to raise an error of the feature added already exists by the candidate key.
            Set to True if adding records using members only, otherwise features will not be added if member values match.

        fail_on_exists (bool): Raise an error if a the add operation would create a duplicate record
        kwargs: keyword args, which form the field mappsings, e.g. Shape='Shape', Country='MyCountryName'.

        expected_row_cnt (int, None): If not none, check that the where clause pulls back expected_row_cnt records, else raise error
        Read this as <detination field>='target field'

        no_progress (bool): Suppress printing progress bar to the console

    Returns:
        int: Number of records added to dest

    Raises:
        DataNoRowsMatched: If no records matched the where clause in source
        DataUnexpectedRowCount: If expected_row_cnt is defined, but a different number of records to copy matched where_clause

    Notes:
        This action is wrapped in a transaction, if any one row fails to add
        (e.g. because a duplicate row would be created and fail_on_exists==True), then all
        changes will be rolled back

    Exmaples:
        >>> features_copy('c@/my.gdb/world_counties', 'c:/my.gdb/euro_countries', 'c:/my.gdb', where='country="EU"',
            copy_shape=True, fail_on_exists=True,
            eu_country='world_country', population='population')
    """
    source = _path.normpath(source)
    dest = _path.normpath(dest)
    workspace = _path.normpath(workspace)

    n = get_row_count2(source, where=where_clause)  # this is also a check that the where clause is valid
    if n == 0:
        raise _errors.DataNoRowsMatched('No records matched the where clause %s' % where_clause)

    if expected_row_cnt and expected_row_cnt != n:
        raise _errors.DataUnexpectedRowCount('Expected source rowcount of %s, got %s' % (expected_row_cnt, n))

    if not no_progress:
        PP = _iolib.PrintProgress(maximum=n)

    kws = {k: None for k in kwargs.keys()}
    if copy_shape:
        kws['SHAPE@'] = None
    i = 0
    with _orm.ORM(dest, workspace=workspace, enable_transactions=True, enable_log=False, **kws) as Dest:
        with _crud.SearchCursor(source, field_names=list(kwargs.values()), load_shape=copy_shape, where_clause=where_clause) as Cur:
            for row in Cur:

                # write fixed_values kwargs first
                if fixed_values:
                    for dest_key, v in fixed_values.items():
                        Dest[dest_key] = v

                # write passed **kwargs, overriding any duplication with fixed_values
                if kwargs:
                    for dest_key, src_key in kwargs.items():
                        Dest[dest_key] = row[src_key]

                if copy_shape:
                    Dest['SHAPE@'] = row['SHAPE@']
                Dest.add(tran_commit=False, force_add=force_add, fail_on_exists=fail_on_exists)
                i += 1
                if not no_progress:
                    PP.increment()  # noqa
        Dest.tran_commit()
    return i


if __name__ == '__main__':
    """quick debug calls here"""
    pass
