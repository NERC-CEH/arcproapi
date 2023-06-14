"""Operations on data"""
import string
from warnings import warn as _warn
import os.path as _path

import fuckit as _fuckit

import pandas as _pd
import numpy as _np

import arcpy as _arcpy
from arcpy.conversion import TableToDBASE, TableToExcel, TableToGeodatabase, TableToSAS, TableToTable, ExcelToTable  # noqa
from arcpy.management import MakeAggregationQueryLayer, MakeQueryLayer, MakeQueryTable  # noqa   Expose here as useful inbult tools


import funclite.iolib as _iolib
import funclite.baselib as _baselib
import funclite.stringslib as _stringslib
from funclite.pandaslib import df_to_dict_as_records_flatten1 as df_to_dict  # noqa Used to convert a standard dataframe into one accepted by field_update_from_dict and field_update_from_dict1
import funclite.pandaslib as pandaslib  # noqa   no _ as want to expose it to pass agg funcs to ResultsAsPandas instances

import arcproapi.structure as _struct
from arcproapi.structure import gdb_csv_import as csv_to_table  # noqa  data-like operations defined in structure. They are imported here for convieniance

import arcproapi.errors as _errors
import arcproapi.crud as _crud
import arcproapi.orm as _orm
import arcproapi.sql as _sql
import arcproapi.decs as _decs
import arcproapi.common as _common
import arcproapi.conversion as conversion

#  More data-like functions, imported for convieniance
from arcproapi.common import get_row_count2 as get_row_count2
from arcproapi.common import get_row_count as get_row_count  # noqa
from arcproapi.export import excel_sheets_to_gdb as excel_import_sheets  # noqa Rearranged, import here so as not to break scripts/compatibility

with _fuckit:
    from arcproapi.common import release
    if int(release()[0]) > 2 and _arcpy.GetInstallInfo()['ProductName'] == 'ArcGISPro':
        from arcpy.conversion import ExportTable, ExportFeatures  # noqa
    import xlwings as _xlwings  # never will be implemented on linux


class Excel:
    """
    Work with excel workbooks.
    """

    @staticmethod
    def excel_worksheets_get(workbook: str) -> list[str]:
        """
        List of worksheets in workbook

        Args:
            workbook (str): The workbook (xlsx)

        Returns:
            list[str]: list of workbooks

        Examples:
            >>> Excel.excel_worksheets_get('C:/temp/my.xlsx')
            ['Sheet1', 'Sheet2']
        """
        workbook = _path.normpath(workbook)
        fld, fname = _iolib.get_file_parts2(workbook)[0:2]
        with _xlwings.App(visible=False) as App:
            _ = App.books.open(workbook)
            out = [sht.name for sht in App.books[fname].sheets]
        return out


    @staticmethod
    def excel_listobjects_get(workbook: str) -> list[str]:
        """
        Get list of listobjects in an excel workbook

        Args:
            workbook (str): The workbook

        Returns:
            list[str]: List of listobjects

        Examples:
            >>> Excel.excel_listobjects_get('C:/temp/my.xlsx')
            ['Table1', 'Table2']
        """
        workbook = _path.normpath(workbook)
        fld, fname = _iolib.get_file_parts2(workbook)[0:2]
        with _xlwings.App(visible=False) as App:
            _ = App.books.open(workbook)
            out = [lo.name for lo in _baselib.list_flatten([sheet.tables for sheet in App.books[fname].sheets])]
        return out


class _MixinResultsAsPandas:
    def __init__(self):
        self.df = None
        self.df_lower = None

    def aggregate(self, groupflds: (str, list[str]), valueflds: (str, list[str]), *funcs, **kwargs) -> (_pd.DataFrame, None):
        """
        Return an aggregated dataframe.
        This is a call to funclite.pandaslib.GroupBy. See documentation for more help.

        Everything is forced to lower case, so don't worry about the case of underlying fields in the table/fc

        Args:
            groupflds: List of fields to groupby, or single string
            valueflds: list of fields to apply the aggregate funcs on. Accepts a string as well
            funcs: functions, pass as arguments
            kwargs: keyword arguments, passed to pandaslib.GroupBy

        Returns:
            None: If self.df_lower evaluates to False
            pandas.DataFrame: The aggregation of cls.df_lower.

        Examples:
            >>> import numpy as np
            >>> ResultsAsPandas(..args..).aggregate('country', ['population', 'age'], np.max, np.mean, pandaslib.GroupBy.fMSE)  # noqa
            country population_max  population_mean age_max age_mean
            Wales   3500000        1234567          101     56
            England ...
        """
        if not self.df_lower: return None  # noqa
        if isinstance(groupflds, str): groupflds = [groupflds]
        if isinstance(valueflds, str): valueflds = [valueflds]
        groupflds = list(map(str.lower, groupflds))
        valueflds = list(map(str.lower, valueflds))

        return pandaslib.GroupBy(self.df_lower, groupflds=groupflds, valueflds=valueflds, *funcs, **kwargs).result

    def view(self) -> None:
        """Open self.df in excel"""
        _xlwings.view(self.df)

    def fields_get(self, as_objs: bool = False) -> (list[str], list[_arcpy.Field]):
        """
        Get list of field names, either as arcpy Fields or as strings

        Args:
            as_objs (bool): As Fields, otherwise strings

        Returns:
            list[str]: If as_objs is False
            list[_arcpy.Field]: If as_objs is True

        """
        return _struct.fc_fields_get(self.fname_output, as_objs=as_objs)  # noqa

    def shape_area(self, where: (str, None) = None, conv_func=conversion.m2_to_km2, **kwargs) -> float:
        """
        Sum the area of the shapes matching the where filter, and convert using conv_func

        Args:
            where (str, None): where to filter records, applied to the class instance of **df_lower** using the pandas.DataFrame.query method and ** not ** the underlying database.
            conv_func: A conversion function, if None is passed, then no conversion is applied
            kwargs: Additional kwargs passed to DataFrame.query

        Returns:
            float: Sum of polygon areas, returns 0 if no records matched.

        Notes:
            Assumed that layers have BNG spatial reference, hence Shape_Area is square meters. If this is not the case, then use a custom conversion function, otherwise the returned area will be wrong.

        Examples:
            >>> ResultsAsPandas(..args..).shape_area(where="crn in ('A123', 'A234')")  # noqa
            0.43245
        """
        if not conv_func:
            conv_func = lambda v: v
        lst = self.df_lower.query(expr=where, **kwargs)['shape_area'].to_list()
        if lst:
            return conv_func(sum(lst))
        return 0

    @property
    def row_count(self, query: (str, None) = None, **kwargs) -> int:
        """
        Get row count

        Args:
            query (str, None): Expression passed to DataFrame.query to filter records
            kwargs: keyword arguments passed to DataFrame.query. e.g. engine='python'. See the pandas documentation.

        Returns: int: Row count
        """
        if query:
            return len(self.df_lower.query(expr=query, **kwargs))
        return len(self.df_lower)

    def shape_length(self, where: (str, None) = None, conv_func=lambda v: v, **kwargs) -> float:
        """
        Sum the length of the shapes matching the where filter, and convert using conv_func

        Args:
            where (str, None): where to filter records, applied to the class instance of **df_lower** using the pandas.DataFrame.query method and ** not ** the underlying database.
            conv_func: A conversion function, if None is passed, then no conversion is applied
            kwargs: Additional kwargs passed to DataFrame.query

        Returns:
            float: Sum of feature lengths, returns 0 if no records matched.

        Notes:
            Assumed that layers have BNG spatial reference, hence Shape_Length is meters.
            Unlike the shape_area method, this defaults to returning lengths uncoverted (i.e. in meters if spatial ref is BNG).
            Currently the additional tables functionality does not allow providing custom where, as_int or as_float to the additional dataframes

        Examples:
            Total shape lengths for the specified crns in kilometers
            >>> ResultsAsPandas(..args..).shape_length(where="crn in ('A123', 'A234'), conv_func=lambda v:v/1000")  # noqa
            0.3245
        """
        if not conv_func:
            conv_func = lambda v: v

        lst = self.df_lower.query(expr=where, **kwargs)['shape_length'].to_list()
        if lst:
            return conv_func(sum(lst))
        return 0




class ResultAsPandas(_MixinResultsAsPandas):
    """
    Retreieve the results of any arcpy operation which returns and table or layer as a pandas dataframe.
    Also exposes pandas aggregate functions to summarise the data and some other "helper" methods.

    Also has a mechanism to load secondary results sets. These are exposed as a dictionary collection of _LayerDataFrame objects. See example

    Args:
        tool: An arcpy tool which supports the in_features argument and a single out_feature class
        columns: columns to retain in the resulting dataframe
        additional_layer_args (tuple[str]): List of the kwargs that point to additional output tables. This allows additional dataframe to be exposed. As an example, see the CountOverlappingFeatures which accepts an argument to define output_overlap_table.
        where: where query to apply to the underlying spatial results table/feature class, passed to data.table_as_pandas2
        as_int (tuple[str], list[str]): List of cols forced to an int in the resulting dataframe
        as_float (tuple[str], list[str]): List of cols forced to a float in the resulting dataframe

    Members:
        df (_pd.DataFrame): Dataframe of the output layer
        df_lower (_pd.DataFrame): Dataframe of the output layer, all col names forced to lower case
        _fname_output (str): Name of the in-memory layer/table output created by execution of "tool"
        tool_execution_result (_arcpy.Result): The result object returned from execution of "tool"
        Results: A dictionary of all Results, the main result is keyed as "main", with any additional results keyed with the values in the additional_layer_args member.

    Notes:
        Currently assumes that the in_features list is always called in_features in the tool
        The arguments "columns", "where", "as_int", "as_float" and "exclude_cols" are all passed to data.table_as_pandas2

    Examples:
        Get shape area sum from main results from an arcpy tool (assumpes Shape is returned)
        >>> RaP = ResultAsPandas(_arcpy.analysis.CountOverlappingFeatures, ['./my.gdb/england', './my.gdb/uk'])  # noqa
        >>> RaP.shape_area()
        334523.1332

        Get the additional results table from CountOverlappingFeatures
        >>> RaP = ResultAsPandas(_arcpy.analysis.CountOverlappingFeatures, ['./my.gdb/england', './my.gdb/uk'], additional_layer_args=('out_overlap_table',))  # noqa
        >>> RaP.Results['out_overlap_table'].df
        id  cola    colb    colc
        1   'a'     'cc'    5
        2   'b'     'dd'    10
        2   'b'     'dd'    10
        ...

        Now aggregate on the main result
        >>> import numpy as np
        >>> RaP.aggregate(['cola'], ['colc'], np.sum)  # noqa
        cola    sum_colc
        'a'     5
        'b'     20

    """
    class _LayerDataFrame(_MixinResultsAsPandas):
        def __init__(self, arg_name: str, fname_output: str, df: _pd.DataFrame = None):
            super().__init__()  # does nothing at moment, except stopping pycharm complaining
            self.arg_name = arg_name
            self.fname_output = fname_output
            self.df_lower = None
            self._df = df

        @property
        def df(self):
            return self._df

        @df.setter
        def df(self, df: _pd.DataFrame):
            if self._df is None:
                self._df = df
                return

            self.df_lower = df.copy()
            self.df_lower.columns = self.df_lower.columns.str.lower()


    def __init__(self, tool, in_features: (list[str], str), columns: list[str] = None, additional_layer_args: (tuple[str], str) = (), where: str = None, exclude_cols: tuple[str] = ('Shape',),
                 as_int: (tuple[str], list[str]) = (), as_float: (tuple[str], list[str]) = (), **kwargs):
        super().__init__()  # does nothing at moment, except stopping pycharm complaining
        self._kwargs = kwargs
        self._tool = tool
        self._in_features = in_features
        self._fname_output = r'%s\%s' % ('memory', _stringslib.rndstr(from_=string.ascii_lowercase))

        self.Results = {}

        if additional_layer_args:
            if isinstance(additional_layer_args, str): additional_layer_args = (additional_layer_args, )
            for s in additional_layer_args:
                lyr_tmp = r'%s\%s' % ('memory', _stringslib.rndstr(from_=string.ascii_lowercase))
                self.Results[s] = ResultAsPandas._LayerDataFrame(s, lyr_tmp)
                kwargs[s] = lyr_tmp

        self.execution_result = tool(in_features=in_features, out_feature_class=self._fname_output, **kwargs)
        self.df = table_as_pandas2(self._fname_output, cols=columns, where=where, exclude_cols=exclude_cols, as_int=as_int, as_float=as_float)
        self.df_lower = self.df.copy()
        self.df_lower.columns = self.df_lower.columns.str.lower()

        # check, LDF should behave as byref
        for LDF in self.Results.values():
            LDF.df = table_as_pandas2(LDF.fname_output, exclude_cols=('Shape',))

        self.Results['main'] = ResultAsPandas._LayerDataFrame('main', self._fname_output, self.df)





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
    """
    Return a list of all values in column col in table tbl.

    If col is a single column, returns a list of values, otherwise returns
    a list of tuples of values where each tuple is one row.

    Columns included in the o parameter must be included in the col parameter!

    Args:
        fname (str): input table or table view
        col (str, list): column name(s) as string, a csv or colon seperated string, or a list
        where (str): where clause
        order_by (str): order by clause like '"OBJECTID" ASC, "Shape_Area" DESC', default is None, which means order by object id if exists
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


def field_has_duplicates(fname: str, col: str, f: any = lambda v: v) -> bool:
    """
    Check a col for duplicates

    Args:
        fname (str): table or feature class
        col (str): col to check
        f: function passed to map, typical use would be f=str.lower to make duplicate checks case insensitive

    Returns:
        bool: True if duplicates found in field col.

    Examples:
        >>> field_get_dup_values('c:/my.gdb/everyones_fave_colour', 'colour', f=str.lower)
        True
    """
    s = field_get_dup_values(fname, col, value_list_only=True, f=f)
    if s:
        return True
    return False


def field_get_dup_values(fname: str, col: str, value_list_only: bool = False, f: any = lambda v: v):
    """
    Check a col for duplicates

    Args:
        fname (str): Feature class or table
        col (str): col to check
        value_list_only (bool): Get as simple list rather than dict
        f (any): function passed to map, typical use would be f=str.lower to make duplicate checks case insensitive

    Returns:
        list: Simple list of values which have duplicates
        dict: A dictionary of duplicates. Keys are the duplicate values and values are is the counts of duplicate values

    Examples:
        sum_of_stuff col n, has duplicates for 2 and 10. Asked for simple list
        >>> field_get_dup_values('c:/my.gdb/sum_of_stuff','n')
        [2, 10]

        fave_colour colour has 2 occurences of blue and 5 occurences of black - and we asked for this detail
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

@_decs.environ_persist
def pandas_to_table2(df: _pd.DataFrame, workspace: str, tablename: str, overwrite=False, del_cols=(), **kwargs):
    """
    Uses a different kludge to get around bugs with pandas no-ascii strings
    and arcpys bug on importing pandas cols of type object - the default
    col type class for pandas string representations.

    Args:
        df (pandas.DataFrame): the pandas dataframe
        workspace (str): gdb
        tablename (str): tablename to create in workspace. Should be the table name only, and not a fully specified path
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
    _arcpy.env.workspace = workspace
    _arcpy.env.overwriteOutput = overwrite
    tmp_file = _iolib.get_temp_fname(suffix='.csv')
    df.replace('"', "'", inplace=True)
    df.to_csv(tmp_file, sep=',', index=False, **kwargs)  # noqa
    fname = _iolib.fixp(workspace, tablename)

    if _common.is_locked(fname):
        raise IOError('%s is locked. Make sure all projects are closed')

    # if overwrite:
    #    _struct.fc_delete2(fname)
    if '/' in tablename or '\\' in tablename:
        tablename = _path.basename(tablename)

    _arcpy.conversion.TableToTable(tmp_file, workspace, tablename)  # noqa

    if del_cols:
        with _fuckit:
            _arcpy.DeleteField_management(fname, del_cols)
    _iolib.file_delete(tmp_file)


def table_as_pandas2(fname: str, cols: (str, list) = None, where: str = None, exclude_cols: (str, list) = ('Shape', 'Shape_Length', 'Shape_Area'), as_int: (list, tuple) = (),
                     as_float: (list, tuple) = (), **kwargs):
    """Export data in feature class/table fname to a pandas DataFrame

    Args:
        fname (str): Path to feature class or table.
        cols (str, list, tuple): column list to retrieve.
        where (str): where clause, passed as-is to SearchCursor
        exclude_cols (str, list, tuple): list of cols to exclude
        as_int (list, tuple, None): List of cols by name to force to int
        as_float (list, tuple, None): list of cols by name to force to float64
        kwargs: keyword args passed to pandas.DataFrame.from_records

    Returns:
        pandas.DataFrame: The feature class or table converted to a pandas DataFrame

    Warnings:
        Raises a warning if as_int and as_float fail to cooerce to their respective type.
        Common cause of this is nan/na/none values in the coerced column.

    Notes:
        The primay key of fname is used as the dataframes index.
        For performance reasons and erroneous errors when viewing the data (e.g. in xlwings), exclude the shape column if not needed.
        The as_int and as_float allows forcing of col to int or float, by default this data is interpreted as objects by pandas (read as strings by SearchCursor).
        "where" is called on arcpy SearchCursor, hence ignores any type conversions forced by as_int and as_float.

        To avoid warnings and correctly cooerce to int and float, a prior call to field_apply_func, using lambda x: 0 if not x or x is None else x
        will clear up those null values (provided zeros are acceptable).

    Examples:
        Get from feature class fc, forcing objectid to be an int
        >>> df = table_as_pandas2('C:/my.gdb/fc', ['OBJECTID', 'modified_date'], as_int='OBJECTID', where='OBJECTID>10')  # noqa
    """

    if isinstance(exclude_cols, str): exclude_cols = [exclude_cols]
    if isinstance(cols, str): cols = [cols]

    def _filt(ss, col_list):
        return ss.lower() not in map(str.lower, col_list)

    flds = _struct.field_list(fname)
    if not cols:
        cols = list(filter(lambda f: _filt(f, exclude_cols), flds))

    df = _pd.DataFrame.from_records(data=_arcpy.da.SearchCursor(fname, cols, where_clause=where), columns=cols, **kwargs)

    if isinstance(as_int, str):
        as_int = (as_int,)

    if isinstance(as_float, str):
        as_float = (as_float,)

    for s in as_int:
        try:
            df[s] = df[s].astype(str).astype(int)
        except:
            _warn('Column %s could not be coerced to type int. It probably contains nan/none/na values' % s)

    for s in as_float:
        try:
            df[s] = df[s].astype(str).astype(float)
        except:
            _warn('Column %s could not be coerced to type int. It probably contains nan/none/na values' % s)

    return df


def table_as_dict(fname, cols=None, where=None, exclude_cols=('Shape', 'Shape_Length', 'Shape_Area'), orient='list', **kwargs) -> dict:
    """(str, iter, iter)
    load data from an ESRI feature set or table and return as a dict.

    Args:
        fname: Path to feature class or table.
        cols: column list to retrieve.
        where: where clause, passed as-is to SearchCursor
        exclude_cols: list of cols to exclude
        orient: passed to pandas.DataFrame.to_dict. See https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_dict.html
        **kwargs: keyword args passed to pandas.DataFrame.from_records

    Returns: dict

    Notes:
        The primay key of fname is used as the intermediary dataframe's index prior to conversion to a dict.
        For performance reasons and erroneous errors when viewing the data (e.g. in xlwings), exclude the shape column if not needed (default).
        This function is just a call to table_as_pandas2, with the output dataframe then converted to a dict in pandas

    Examples:
        >>> df = table_as_dict('C:/my.gdb/fc', [OBJECTID, modified_date], where='OBJECTID>10')  # noqa
    """
    df = table_as_pandas2(fname, cols=cols, where=where, exclude_cols=exclude_cols, **kwargs)
    return df.to_dict(orient=orient)


def table_dump_from_sde_to_excel(sde_file: str, lyr, xlsx_root_folder: str, **kwargs) -> str:
    """
    Dump Enterprise geodatabase layer defined by sde connection file to excel.
    The excel file name is generated from current date and the source layer name.

    Args:
        sde_file (str): SDE file
        lyr (str): feature class/table name.
        xlsx_root_folder (str): Root folder in which to save the xlsx
        kwargs (any): Passed to data.table_as_pandas2

    Returns:
        str: The excel file name.

    Examples:
        >>> table_dump_from_sde_to_excel('C:/my.sde', 'MyDataTable')
    """
    sde_file = _iolib.fixp(sde_file, lyr)
    dest_xlsx = _iolib.fixp(xlsx_root_folder,
                            '%s_%s.xlsx' % (_iolib.pretty_date_now(with_time=True, time_sep=''), lyr)
                            )

    df = table_as_pandas2(sde_file, **kwargs)
    df.to_excel(dest_xlsx)
    return dest_xlsx



def field_update_from_dict1(fname: str, dict_: dict, col_to_update: str, key_col: str,
                            where: str = '', na: any = (1, 1),
                            field_length: int = 50, show_progress=False, init_msg: str = ''):
    """Update column in a table with values from a dictionary.
    Will add the column (col_to_update) if it does not exist.

    The added column is forced to a text of length field_length.

    *** DANGER *** Passing na=None will overwrite any unmatched records, USE WITH EXTREME CAUTION!!!!

    Args:
        fname (str): table to update
        dict_ (dict): dictionary with new values
        col_to_update (str): name of the column of fname to update

        key_col (str): column in fname to be used as keys to look up values in the feature class,
            default is None, which means to use objectid field.

        where (str): where clause to select rows to update in the feature class

        na (any): value to be used instead of new value for non-matching records,
            Pass None to null out unmatched values. (1,1) will leave original value if match is not found

        field_length (int): Field length
        show_progress (bool): Show progress
        init_msg (str): Passed to progress status

    Returns:
        int: Number of updated records

    Notes:
        A small wrapper around field_update_from_dict

    Examples:
        >>> fc = 'c:\\foo\\bar.shp'
        >>> d = {1: 'EN', 2:'ST', 3:'WL', 4:'NI'}
        Explicit declaration of update and key columns. Here we assume the numerics in d are "country_num"
        and we update country_code accordingly.
        >>> field_update_from_dict1(fc, d, col_to_update='country_code', key_col='country_num', na='Other')
    """
    if not _struct.field_exists(fname, col_to_update):
        _struct.AddField(fname, col_to_update, 'TEXT', field_length=field_length, field_is_nullable=True)
    i = field_update_from_dict(fname, dict_, col_to_update, key_col, where=where, na=na, show_progress=show_progress, init_msg=init_msg)
    return i


def field_update_from_dict(fname: str, dict_: dict, col_to_update: str, key_col: str = None, where: str = '', na: any = (1, 1), show_progress=False, init_msg: str = '') -> int:
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
            default is (1,1), which leaves original value. Else use na=None to null unmatched values.
        show_progress (bool): Show progress
        init_msg (str): Passed to the progress status

    Returns:
        int: Number of updated records

    Notes:
        Use data.df_to_dict (direct import of funclite.pandaslib.df_to_dict_as_records_flatten1) to convert a dataframe to the required format to
        be consumed by this function.

    Examples:
        >>> fc = 'c:\\foo\\bar.shp'
        >>> d = {1: 'EN', 2:'ST', 3:'WL', 4:'NI'}
        Dictionary keys are table index numbers (ObjectID, OID etc), no need to pass key_col as objectid is assumed
        >>> field_update_from_dict(fc, d, 'country_code')
        Explicit declaration of update and key columns. Here we assume the numerics in d are "country_num"
        and we update country_code accordingly.
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

    if show_progress:
        PP = _iolib.PrintProgress(maximum=n, init_msg=init_msg)

    with _arcpy.da.UpdateCursor(fname, cols, where_clause=where) as uc:
        for row in uc:
            ido = row[0]
            if identity:
                # branch that leaves unmatched records unchanged if na = (1,1)
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
            if show_progress:
                PP.increment()  # noqa
    return cnt


def fields_copy_by_join(fc_dest: str, fc_dest_key_col: str, fc_src: str, fc_src_key_col: str, cols_to_copy: (str, list, tuple), rename_to: (str, tuple, list, None) = None,
                        error_if_dest_cols_exists: bool = True, ignore_type_on_lookup: bool = False, allow_duplicates_in_pk: bool = False, show_progress: bool = True) -> int:
    """
    Add fields from one table to another using a shared candidate key field.

    This can also be used to copy data between existing fields by setting
    error_if_dest_cols_exists = False. It will also work with a mix of
    destination fields that already exist and dont exist.

    Args:
        fc_dest (str): table to add fields to
        fc_dest_key_col (str): Foreign key field name in destination
        fc_src (str): Table with source data
        fc_src_key_col (str): Primary key field name in source, matched with fc_dest_key_col
        cols_to_copy (str, list, tuple): String or iterable of field names in src to copy to dest.

        rename_to (str, list, tuple, None): Rename cols_to_copy to this name or list of names.\n
        If this argument is included, its length must match len(cols_to_copy)

        error_if_dest_cols_exists: If True and any cols_to_copy already exists, then raises StructFieldExists
        ignore_type_on_lookup (bool): Some "clever" people mix types on pk-fk tables across data sources. This will do its best to ignore this kind of stupidity
        allow_duplicates_in_pk (bool): Ignore duplicates values in the column fc_dest.fc_dest_key_col. Takes the row value in this instance
        show_progress (bool): Show progress messages and indicator

    Returns:.
        int: Number of rows updated in dest

    Raises:
        errors.DataFieldValuesNotUnique: If field values in the source field were not unique.
        errors.StructFieldExists: If error_if_dest_col_exists and any col already exists in the destination

    Notes:
        Arcpy supports extending tables using numpy arrays, consider using this for improved performance (can be finiky)
        https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/extendtable.htm
        ignore_types_on_lookup. If True then null fields in the primary key will be treated the same as the text 'None'

    Examples:
        \nSimple copy of country_name to wards, assuming wards share a countryid foreign key
        >>> fields_copy_by_join(r'C:\my.gdb\countries', 'countryid', 'C:\my.gdb\wards', 'countryid', 'country_name')
        123
        \n\nSimple copy as above, but rename the country_name field to country
        >>> fields_copy_by_join(r'C:\my.gdb\countries', 'countryid', 'C:\my.gdb\wards', 'countryid', 'country_name', rename_to='country')
        123
        \n\nCopy multiple fields and rename them to country and area_km2
        >>> fields_copy_by_join(r'C:\my.gdb\countries', 'countryid', 'C:\my.gdb\wards', 'countryid', ['country_name', 'area'], rename_to=['country', 'area_km2'])
        123
        \n\nField SQ_ID already exists in destination, but setting error_if_dest_cols_exists=False copies
        \ndata from SRC.CEH_ID to DEST.SQ_ID with relationship SRC.SQ_ID --< DEST.WEB_ID, overwriting what is
        \nalready there. Data type mismatches may also cause an error.
        >>> fields_copy_by_join(DEST, 'WEB_ID', SRC, 'SQ_ID', 'CEH_ID', 'SQ_ID', error_if_dest_cols_exists=False)  # noqa
        300
    """
    # TODO Needs testing for multiple fields
    # TODO Also support compound primary keys in src
    fc_dest = _path.normpath(fc_dest)
    fc_src = _path.normpath(fc_src)

    if isinstance(cols_to_copy, str):
        cols_to_copy = [cols_to_copy]

    if isinstance(rename_to, str):
        rename_to = [rename_to]

    if not rename_to:
        rename_to = list(cols_to_copy)  # make a proper copy

    # Some basic validation, so we error early.
    if show_progress: print('\nPerforming some validation steps ...')

    if len(rename_to) != len(cols_to_copy):
        raise ValueError('If rename_to is passed, then assert len(cols_to_copy) == len(rename_to)')

    if not _struct.field_exists(fc_src, fc_src_key_col, case_insensitive=False):
        raise ValueError('The primary key field %s does not exist in source %s. This is case sensitive' % (fc_src_key_col, fc_src))

    if not _struct.field_exists(fc_dest, fc_dest_key_col, case_insensitive=False):
        raise ValueError('The foreign key field %s does not exist in destination %s. This is case sensitive' % (fc_dest_key_col, fc_dest))

    if error_if_dest_cols_exists:
        d = _struct.field_list_compare(fc_dest, rename_to)['a_and_b']  # noqa TODO Check this works
        if d:
            raise _errors.StructFieldExists('error_if_dest_cols_exists was True and field(s) %s already exist in destination %s' % (fc_dest, str(d)))

    if not allow_duplicates_in_pk:
        if field_has_duplicates(fc_src, fc_src_key_col):
            raise _errors.DataFieldValuesNotUnique('Field values in the data source field %s must be unique.' % fc_src_key_col)

    # join_list may now be out of order with rename_to
    join_list_temp = [f for f in _arcpy.ListFields(fc_src) if f.name in cols_to_copy]
    if len(join_list_temp) != len(cols_to_copy):
        raise ValueError(
            'Expected %s fields in source, got %s. Check the names of the columns you have asked to copy. Field name comparisons are case sensitive here.' % (len(cols_to_copy), len(join_list_temp)))

    # create join_list, restoring order, so our source data cols match order of rename_to
    join_list = [None] * len(cols_to_copy)
    for f in join_list_temp:
        join_list[cols_to_copy.index(f.name)] = f

    # ######################################
    # Add fields to be copied to destination
    # ######################################
    if show_progress:
        PP = _iolib.PrintProgress(iter_=join_list, init_msg='Copying field definitions to destination (as required) ...')

    for i, f in enumerate(join_list):
        _struct.field_copy_definition(fc_src, fc_dest, f.name, rename_to[i], silent_skip_on_exists=not error_if_dest_cols_exists)  # noqa
        if show_progress:
            PP.increment()  # noqa

    # #################################
    # Now read src records into a dict
    # #################################
    src_rows_dict = {}
    if ignore_type_on_lookup:
        f_ignore = lambda vv: str(vv)
    else:
        f_ignore = lambda vv: vv

    cols_to_copy.insert(0, fc_src_key_col)  # just add the src primary key to the start of cols_to_copy

    if show_progress:
        PP = _iolib.PrintProgress(maximum=get_row_count(fc_src), init_msg='2 of 3. Reading data from source ...')

    pkvalues = []
    with _arcpy.da.SearchCursor(fc_src, cols_to_copy) as srows:
        for srow in srows:
            # create dict .... {'row 1 key value': (row 1 field 1 value, row 1 field 2 value ...), 'row key value 2': (...)}
            if not srow[0] in pkvalues:  # don't add if we have duplicate primary key values, as can happen if allow_duplicates_in_pk == True
                src_rows_dict[f_ignore(srow[0])] = tuple(srow[1:])  # f_ignore making all keys strings if we want to ignore type matching on PK/FK
                pkvalues += [srow[0]]
            if show_progress:
                PP.increment()  # noqa

    ####################################################
    # Write the records from the dict to the destination
    ####################################################
    if show_progress:
        PP = _iolib.PrintProgress(maximum=get_row_count(fc_dest), init_msg='3 of 3. Writing data to destination ...')

    rename_to.insert(0, fc_dest_key_col)  # noqa Insert the source key field at list[0]
    n = 0

    with _arcpy.da.UpdateCursor(fc_dest, rename_to) as urows:
        for row in urows:
            if f_ignore(row[0]) in map(f_ignore,
                                       src_rows_dict.keys()):  # map is just so we convert everything to a string for comparisons, ignoring stuff like one PK field is an int and the FK field is a string.
                for i, v in enumerate(src_rows_dict[f_ignore(row[0])]):
                    row[i + 1] = v  # first row is the foreign key col we inserted earlier. So shift index up 1
                urows.updateRow(row)
                n += 1
            PP.increment()
    return n


# this could be extented to allow multi argument functions by providing named arguments
# to pass thru
def fields_apply_func(fname, cols, *args, where_clause=None, show_progress=False) -> int:
    """
    Applys each function passed to args to each column in cols.
    *** Each function must accept the same args in the same order ***

    Args:
        fname (str): path to feature class/shapefile (e.g. c:\tmp\myfile.shp)
        cols (str, iter): iterable of columns to transform with func(s) in args. Accepts a str for single col.
        args (any): 1 or more single argument function pointers
        where_clause (str, None): applied to filter rows to be updated (STATE="Washington")
        show_progress (bool): Have this func print a progress bar to the console

    Returns:
        int: Number of records processed

    Notes:
        TIP: Use inspect.getfullargspec(<func>).args to get a function argument lists when calling this function.

    Examples:
        >>> f1 = str.lower: f2 = str.upper
        >>> fields_apply_func('c:/my.shp', ['street','town'], f1, f2, where_clause='town="bangor"')
    """
    fname = _path.normpath(fname)
    if show_progress:
        max_ = int(_arcpy.GetCount_management(fname)[0])  # yes get count management gets the count as a fucking string
        PP = _iolib.PrintProgress(maximum=max_, init_msg='Running fields_apply_func...')

    if isinstance(cols, str): cols = [cols]
    try:
        # Update cursor behaves differently when the environment has a workspace set
        # Specifically, updates must be put in an edit session, otherwise arcpy raises
        # an error about not being able to make changes outside of an edit session
        # Hence the following code triggering an edit session if we have a workspace
        if _arcpy.env.workspace:
            edit = _arcpy.da.Editor(_arcpy.env.workspace)
            edit.startEditing(False, False)
            edit.startOperation()
        n = 0
        with _arcpy.da.UpdateCursor(fname, cols, where_clause=where_clause) as cursor:
            for i, row in enumerate(cursor):
                vals = [row[j] for j in range(len(cols))]
                for f in args:  # function chaining
                    vals = [f(v) for v in vals]  # pass in our function to correct the data

                for k, v in enumerate(vals):
                    row[k] = v
                cursor.updateRow(row)
                if show_progress:
                    PP.increment()  # noqa
                n += 1

        if _arcpy.env.workspace:
            edit.stopOperation()  # noqa
            if edit.isEditing:
                edit.stopEditing(save_changes=True)  # noqa
            del edit

    except Exception as e:
        with _fuckit:
            edit.stopOperation()
            edit.stopEditing(save_changes=False)  # noqa
            del edit
        raise Exception('An exception occured and changes applied by fields_apply_func were rolled back. Further error details follow.') from e
    return n


# this could be extended to allow multi argument functions by providing named arguments
# to pass thru
def field_recalculate(fc: str, arg_cols: (str, list, tuple), col_to_update: str, func, where_clause: (str, None) = None, show_progress: bool = False) -> int:
    """
    Very similiar to ArcPro's Calculate Field.
    Take in_cols values, apply a function to these values to recalculate col_to_update.

    Note that each function must accept exactly len(in_cols) arguments.

    Arguments are matched by order, so in_cols[0], is passed as first argument to func.

    Args:
        fc (str): path to feature class/shapefile (e.g. c:\tmp\myfile.shp)
        arg_cols (str, iter): iterable of columns to transform with func(s) in args (str for single col is ok)
        col_to_update (str): column to update
        func (function): A function object which excepts len(in_cols) number of arguments.
        where_clause (str): applied to filter rows to be updated (STATE="Washington")
        show_progress (bool): Have this func print a progress bar to the console

    Returns:
        int: Number of records processed

    Notes:
        arcproapi.structure exposes AddField, use this to add your field to recalculate if it doesnt exist!
        TIP: Use inspect.getfullargspec(<func>).args to get a function argument list when calling this function.

    Examples:
        Set field "coord_sum" to be the product of fields easting, northing, elevation for all rows in Bangor.
        >>> f1 = lambda x, y, z: x + y + z
        >>> field_recalculate('c:/my.shp', ['easting','northing', 'elevation'], 'coord_sum', f1, where_clause='town="bangor"')

    TODO: Test/Debug field_recalculate
    """
    fc = _path.normpath(fc)
    if show_progress:
        max_ = _struct.get_row_count2(fc, where=where_clause)
        PP = _iolib.PrintProgress(maximum=max_, init_msg='Applying func "%s" to column "%s" ...' % (func.__name__, col_to_update))  # noqa

    if isinstance(arg_cols, str): arg_cols = [arg_cols]
    j = 0
    try:
        # Update cursor behaves differently the environment has a workspace set
        # Specifically, updates must be put in an edit session, otherwise arcpy raises
        # an error about not being able to make changes outside of an edit session
        # Hence the following code triggering an edit session if we have a workspace
        if _arcpy.env.workspace:
            edit = _arcpy.da.Editor(_arcpy.env.workspace)
            edit.startEditing(False, False)
            edit.startOperation()

        with _arcpy.da.UpdateCursor(fc, arg_cols + [col_to_update], where_clause=where_clause) as cursor:
            for i, row in enumerate(cursor):
                row[-1] = func(*row[0:len(arg_cols)])
                cursor.updateRow(row)
                if show_progress:
                    PP.increment()  # noqa
                j += 1

        if _arcpy.env.workspace:
            edit.stopOperation()  # noqa
            if edit.isEditing:
                edit.stopEditing(save_changes=True)  # noqa
            del edit
        return j
    except Exception as e:
        with _fuckit:
            edit.stopOperation()
            edit.stopEditing(save_changes=False)  # noqa
            del edit
        raise Exception('An exception occured and changes applied by field_recalculate were rolled back.\n\nException: %s' % str(e)) from e


field_apply_func = field_recalculate  # noqa For convieniance. Original func left in to not break code


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
        Delete rows where (cola=1 and colb='a') OR (cola=2 and colb='b') OR (cola=3 and colb='c')
        >>> del_rows('c:/shp.shp', ['cola','colb'], [[1,2,3],['a','b','c']])
        >>> del_rows('c:/shp.shp', 'cola', 1)  # deletes every record where cola==1

        Use wildcard delete, we don't care about cols, so just use OBJECTID\n
        >>> del_rows('c:/my.gdb/coutries', 'OBJECTID', '*', where='OBJECTID<10')

        Delete everything\n
        >>> del_rows('c:/my.gdb/countries', '*', '*', no_warn=True)
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
    Joins all dataframes by a _common column

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


def features_copy_to_new(source: str, dest: str, where_clause: (None, str) = None, **kwargs):
    """
    Copy features to a new source based on a where clause.
    Calls arcpy.analysis.Select, which recieves kwargs

    Args:
        source (str): Source layer, normpathed
        dest (str): Destination, normpathed
        where_clause (None, str): Where clause to select records for copying
        kwargs: Keyword arguments, passed to arcpy.analysis.Select

    Returns:
        None

    # TODO Debug features_copy_to_new
    """
    source = _path.normpath(source)
    dest = _path.normpath(dest)
    oids_to_select = []

    with _arcpy.da.SearchCursor(source, ['OID@'], where_clause=where_clause) as cursor:
        for row in cursor:
            oids_to_select.append(row[0])

    sql = "{0} IN {1}".format(_arcpy.AddFieldDelimiters(source, _arcpy.Describe(source).OIDFieldName), tuple(oids_to_select))
    _arcpy.analysis.Select(source, dest, sql, **kwargs)  # noqa


def key_info(parent: str, parent_field: str, child: str, child_field: str, as_oids: bool = False) -> dict:
    """
    Get a dictionary listing the "primary key" values not in child foreign key values.
    This is a quick validation tool. A set of more advanced validation tools is planned
    in a dedicated module, integrating arcproapi connection objects with the
    great expectations package.

    TODO: Support compound keys

    Args:
        parent (str): Parent entity
        parent_field (str): The key field in the parent
        child (str): Child entity
        child_field (str): key field in the child
        as_oids (bool): Get unique oids instead of distinct values

    Returns:
        dict: dict{'parent_only': [..], 'both': [..], 'child_only': [..]

    Notes:
        The OIDs can be used for futher processing ...

    Examples:
        >>> key_info('C:/my.gdb/coutries', 'cname', 'C:/my.gdb/towns', 'cname')
        {'parent_only': ['NoTownCountry',...], 'both': ['England',...,], 'child_only': ['NoCountryTown',...]}

        Now with oids
        >>> key_info('C:/my.gdb/coutries', 'cname', 'C:/my.gdb/towns', 'cname', as_oids=True)
        {'parent_only': [232, 343], 'both': [1,2,...], 'child_only': [56,77,...]}

    Notes:
        This is also exposed in arcapipro.info
    """

    parent_values = field_values(parent, parent_field, distinct=True)
    child_values = field_values(child, child_field, distinct=True)

    if not as_oids:
        d = _baselib.list_sym_diff(parent_values, child_values, rename_keys=('parent_only', 'both', 'child_only'))
        return d

    where = _sql.query_where_in(parent_field, parent_values)
    parent_oids = field_values(parent, 'OID@', where=where)

    where = _sql.query_where_in(child_field, child_values)
    child_oids = field_values(child, 'OID@', where=where)

    d = _baselib.list_sym_diff(parent_oids, child_oids, rename_keys=('parent_only', 'both', 'child_only'))
    return d


def features_delete_orphaned(parent: str, parent_field: str, child: str, child_field: str) -> None:
    """
    Delete orphaned features/table records

    TODO: features_delete_orphaned support compound keys and test

    Args:
        parent (str):
        parent_field (str):
        child (str):
        child_field (str):

    Returns:
        None

    Examples:
        Delete all rows in regions, which where country_name does not exist in countries
        >>> features_delete_orphaned('c:/my.gdb/countries', 'country_name', 'c:/my.gdb/regions', 'country_name')
    """
    oids = key_info(parent, parent_field, child, child_field, as_oids=True)['child_only']
    if oids:
        with _crud.CRUD(child, enable_transactions=False) as crud:
            crud.deletew(_sql.query_where_in('OID@', oids))


def features_copy(source: str, dest: str, workspace: str, where_clause: str = '*', fixed_values=None, copy_shape: bool = True, force_add: bool = True, fail_on_exists: bool = True,
                  expected_row_cnt: int = None, no_progress: bool = False, **kwargs) -> int:
    """Copy features from one table or featureclass to another. i.e. The shape and fields as given as kwargs.

    If you get an error, double check field names, noting that field names are case sensitive.

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

        kwargs (any): Keyword arguments, where key is field in dest, and value is field in src. E.g. dest_field='src_field'

    Returns:
        int: Number of records added to dest

    Raises:
        DataNoRowsMatched: If no records matched the where clause in source
        DataUnexpectedRowCount: If expected_row_cnt is defined, but a different number of records to copy matched where_clause

    Notes:
        This action is wrapped in a transaction, if any one row fails to add
        (e.g. because a duplicate row would be created and fail_on_exists==True), then all
        changes will be rolled back

    Examples:
        >>> features_copy('c@/my.gdb/world_counties', 'c:/my.gdb/euro_countries', 'c:/my.gdb', where_clause='country="EU"',
        >>>    copy_shape=True, fail_on_exists=True,
        >>>    eu_country='world_country', population='population')
    """
    if 'where' in map(str.lower, kwargs.keys()):
        _warn('keyword "where" in kwargs.keys(), did you mean to set a where clause? If so, use where_clause=<MY QUERY>')

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


def table_summary_as_pandas(fname: str, statistics_fields: (str, list[list[str]]), case_field: (str, list[str], None) = None, concatenation_separator='') -> _pd.DataFrame:
    """
    Execute a table summary against a feature class or table
    and return the result as a pandas dataframe.

    Arguments are passed to arcpy.analysis.Statistics
    See https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/summary-statistics.htm

    Args:
        fname (str): feature class/table
        statistics_fields (list[str]): List of fields to aggregate with the aggregate function (see link)
        case_field (list[str]): Fields to group by
        concatenation_separator (str): Character or characters used to concatenate values when the CONCATENATION option is used in  statistics_fields

    Returns:
        pandas.DataFrame: The results of the aggregation as a pandas dataframe

    Notes:
        As with all operations on features, field names appear to be case insensitive, at least in file geodatabases.

    Examples:
        >>> table_summary_as_pandas('C:/my.gdb/countries', [['country', 'COUNT'], ['population', 'MAX']], 'continent')  # noqa
        continent   FREQUENCY   COUNT_country   MAX_population
        'Europe'    20          20              70000000
        'Asia'      25          25              200000000
        ...
    """

    fname = _path.normpath(fname)
    out_tmp = 'in_memory/%s' % _stringslib.get_random_string(length=8, from_=string.ascii_lowercase)
    _arcpy.analysis.Statistics(fname,  # noqa
                               out_tmp,
                               statistics_fields=statistics_fields,
                               case_field=case_field,
                               concatenation_separator=concatenation_separator
                               )
    df = table_as_pandas2(out_tmp)
    return df


def vertext_add(fname, vertex_index: (int, str), x_field: str, y_field: str = 'y', field_type='DOUBLE', where_clause: (str, None) = '*', fail_on_exists: bool = True,
                show_progress: bool = False) -> int:
    """
    Add the x and y coordinates of a vertex
    Args:
        fname (str): The layer
        vertex_index (int, str): Index of the vertext, pass 'last' to get the last vertext in the shape. Pass 0 or 'first' to get the first
        x_field ():  Field name for x coordinate
        y_field (str): Field name for y coordinate
        field_type (str): Passed to AddField when creating new fields. 'FLOAT', 'DOUBLE', 'LONG' recommended
        where_clause (str): Record filter passed to the crud.UpdateCursor
        fail_on_exists (bool): Fail if either x_field or y_field already exists, otherwise will overwrite if exists
        show_progress (bool): Show progress in terminal

    Returns:
        int: Number of records edited

    Notes:
        Use LONG for easting and northings.
        If fail_on_exists is used, then no fields will be added if only the x or y field already exists, preserving the current structure.
        If the feature is multipart, it uses the first part.

    Examples:
        >>>
    """
    fname = _path.normpath(fname)
    if str(vertex_index).lower() == 'first': vertex_index = 0

    x_exists = _struct.field_exists(fname, x_field)
    y_exists = _struct.field_exists(fname, y_field)
    if fail_on_exists and (x_exists or y_exists):
        raise _errors.StructFieldExists('Field %s or/and %s already exists and fail_on_exists was True' % (x_field, y_field))

    if not x_exists:
        _struct.AddField(fname, x_field, field_type=field_type, field_is_nullable=True)

    if not y_exists:
        _struct.AddField(fname, y_field, field_type=field_type, field_is_nullable=True)

    if show_progress:
        PP = _iolib.PrintProgress(maximum=get_row_count(fname), init_msg='Adding vertex coords...')
    j = 0
    with _crud.UpdateCursor(fname, ['OID@', x_field, y_field], where_clause=where_clause, load_shape=True) as UpdCur:
        for R in UpdCur:
            if len(R.Shape) > 1:
                _warn('Multipart feature found for row with OID=%s' % R[0])

            if str(vertex_index).lower() == 'last':
                R[x_field] = R['SHAPE@'].lastPoint.X
                R[y_field] = R['SHAPE@'].lastPoint.Y
            else:
                R[x_field] = R['SHAPE@'][0][vertex_index].X
                R[y_field] = R['SHAPE@'][0][vertex_index].Y

            UpdCur.updateRow(R)
            j += 1
            if show_progress:
                PP.increment()  # noqa
    return j


rows_delete = del_rows  # noqa. For conveniance, should of been called this in first place but don't break existing code

if __name__ == '__main__':
    # quick debugging

    # features copy
    # src = r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\GIS\erammp.gdb\nrw_permissionable_clipped'
    # dst = r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\GIS\_arcpro_projects\drone_pilot_20220725\drone_pilot_20220725.gdb\parcels'
    # wsp = r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\GIS\_arcpro_projects\drone_pilot_20220725\drone_pilot_20220725.gdb'
    # features_copy(src, dst, wsp, where_clause='sq_id=34158', permission='permission', sq_id='sq_id')

    # fields_copy_by_join
    # fname_local = 'C:/GIS/erammp_local/submission/curated_raw/botany_curated_raw_local.gdb/plot'
    # dfout = table_summary_as_pandas(fname_local, [['OBJECTID', 'MEAN'], ['PLOT_NuMBER', 'RANGE']], ['plot_type'])  # noqa

    # i = vertext_add(r'C:\GIS\erammp_local\submission\curated_raw\freshwater_curated_raw.gdb\stream_sites', 1, x_field='easting_vertex', y_field='northing_vertex', fail_on_exists=False, show_progress=True)
    RaP = ResultAsPandas(_arcpy.analysis.CountOverlappingFeatures,  # noqa
                         [r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\common\data\GIS\erammp_common.gdb\sq',
                          r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\current\data\GIS\erammp_current.gdb\sq_in_survey'],
                         additional_layer_args=('out_overlap_table',)
                         )

    pass
