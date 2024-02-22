"""Operations on data"""
import math as _math
import string as _string
from abc import ABCMeta as _ABCMeta
from warnings import warn as _warn
import os.path as _path
import inspect as _inspect
import more_itertools as _more_itertools

import fuckit as _fuckit

import pandas as _pd
import numpy as _np

import arcpy as _arcpy

from arcpy.conversion import TableToDBASE, TableToExcel, TableToGeodatabase, TableToSAS, TableToTable, ExcelToTable  # noqa
from arcpy.management import MakeAggregationQueryLayer, MakeQueryLayer, MakeQueryTable, CalculateField, CalculateStatistics, DeleteIdentical  # noqa   Expose here as useful inbult tools
from arcpy.analysis import CountOverlappingFeatures, SummarizeNearby, SummarizeWithin  # noqa

with _fuckit:
    from arcproapi.common import release

    if int(release()[0]) > 2 and _arcpy.GetInstallInfo()['ProductName'] == 'ArcGISPro':
        from arcpy.conversion import ExportTable, ExportFeatures  # noqa
    import xlwings as _xlwings  # never will be implemented on linux

import great_expectations as _gx

import funclite.iolib as _iolib
import funclite.baselib as _baselib
import funclite.stringslib as _stringslib
from funclite.mixins import MixinNameSpace as _MixinNameSpace
import funclite.pandaslib as _pandaslib  # noqa
from funclite.pandaslib import df_to_dict_as_records_flatten1 as df_to_dict  # noqa Used to convert a standard dataframe into one accepted by field_update_from_dict and field_update_from_dict_addnew
import funclite.pandaslib as pandaslib  # noqa   no _ as want to expose it to pass agg funcs to ResultsAsPandas instances

import arcproapi.structure as _struct

import arcproapi.mixins as _mixins
import arcproapi.errors as _errors
import arcproapi.crud as _crud
import arcproapi.orm as _orm
import arcproapi.sql as _sql
import arcproapi.decs as _decs
import arcproapi.common as _common
import arcproapi.geom as _geom

#  More data-like functions, imported for convieniance
from arcproapi.common import get_row_count2 as get_row_count2
from arcproapi.common import get_row_count as get_row_count  # noqa
from arcproapi.export import excel_sheets_to_gdb as excel_import_sheets, csv_to_gdb as csv_to_table  # noqa Rearranged, import here so as not to break scripts/compatibility

# TODO: All functions that write/delete/update spatial layers need to support transactions using the Editor object - otherwise an error is raised when layers are involved in a topology (and other similiar conditions)
# See https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/editor.htm and https://pro.arcgis.com/en/pro-app/latest/tool-reference/tool-errors-and-warnings/160001-170000/tool-errors-and-warnings-160226-160250-160250.htm

_sort_list_set = lambda lst: sorted(list(set(lst)))

class Funcs(_MixinNameSpace, metaclass=_ABCMeta):
    """
    Defines some commonly used functions to use in the various field_apply/recalculate methods in this module.

    Methods:
        FidToOneZero: After a spatial operation, e.g. union, we get FID_<table_name> cols. This reduces those scenarios to a 1 or a 0. "0 = 0;  <Null> = 0;  -1 = 0;  > 0 = 1
    """

    @staticmethod
    def ShapeToHash(shape) -> str:
        """
        Takes the value in an arcpy Shape@ field (Shape@ should be used to specify the shape col),
        and returns a unique hash value as a string.

        Args:
            shape: the shape returned by asking for Shape@, for example in a searchcursor loop

        Returns:
            The hashed value

        Notes:
            This method is defined in geom.py
        """
        return _geom.shape_hash(shape)


    @staticmethod
    def FloatToLong(v: float) -> int:
        """
        Scientific round on float,  to integer (long datatype in ESRI).
        Args:
            v (float): the value

        Returns:
            int: The rounded float as an int
        """
        return int(round(v, 0))

    @staticmethod
    def LongToOneZero(v: int) -> int:
        """
        After a spatial operation, e.g. union, we get FID_<table_name> cols. This reduces those scenarios to a 1 or a 0. "0 = 0;  <Null> = 0;  -1 = 0;  > 0 = 1

        Returns: int: 1 or 0
        """
        if not v: return 0
        if v == -1: return 0
        if v < -1: return 0
        return 1

    @staticmethod
    def LongsToOneZeroOr(*args) -> int:
        """
        Pict 1 if any int > 0 and not null/none else 0

        Returns:
            int: 1 or 0

        Examples:

            >>> Funcs.LongsToOneZeroOr(12, 0, None)
            1

            >>> Funcs.LongsToOneZeroOr(-1, 0, None)
            0
        """
        return 1 if any([Funcs.LongToOneZero(v) for v in args]) else 0

    @staticmethod
    def LongsToOneZeroAll(*args) -> int:
        """
        Pict 1 if all int args > 0 and not null/none else 0

        Returns:
            int: 1 or 0

        Examples:

            >>> Funcs.LongsToOneZeroAll(12, 1, 2)
            1

            >>> Funcs.LongsToOneZeroOr(12, 1, 0)
            0
        """
        return 1 if all([Funcs.LongToOneZero(v) for v in args]) else 0

    @staticmethod
    def TextToOneZero(v: str) -> int:
        """
        Reduce text to 1 or 0. If not isinstance(v, str), also return 0

        Returns: int: 1 or 0
        """
        if not isinstance(v, str): return 0
        if not v: return 0
        return 1

    @staticmethod
    def PickFirst(*args, default: (str, int, float) = 'Unspecified'):
        """
        Pick the firt value that evaluates to True.

        Args:
            *args: values
            default: What to return if no field values evaluate to True

        Returns:
            The value of the first field to evaluate to true

        Examples:

            >>> Funcs.PickFirst('', '', 'hello', False)
            'hello'

            >>> Funcs.PickFirst(False, False, '', None, default=0)  # noqa
            0
        """
        for s in args:
            if s: return s
        return default

    @staticmethod
    def PickLong(*args):
        """
        Picks the value which is not -1, <null> or 0. Picks the first one if multiple are not -1/null/0
        If all args evaluate 0, return 0
        Returns: int

        Examples:

            Get first

            >>> Funcs.PickLong(-1, 0, 0, 34, 54)
            34

            All evaluate to 0 with LongToOneZero

            >>> Funcs.PickLong(-1, None, 0)
            0
        """
        for n in args:
            if Funcs.LongToOneZero(n): return n
        return 0

    @staticmethod
    def Area_m2_to_km2(v: (float, None)):
        """
        Conversion from m2 to km2. If v evaluates to false, returns 0

        Args:
            v: value

        Returns:
            float: area as km2.

        Examples:

            Behaviour on none/null

            >>> Funcs.Area_m2_to_km2(None)  # noqa
            0
        """
        return v / 1000000 if v else 0

    @staticmethod
    def ThinnessRationFromShapePlanar(poly: _arcpy.Polygon) -> float:
        """
        Thinness ratio.
        See https://tereshenkov.wordpress.com/2014/04/08/fighting-sliver-polygons-in-arcgis-thinness-ratio/

        Args:
            poly: instance of arcpy.Polygon

        Returns:
            float: the ratio

        Notes:
            Only supports projected coordinate systems
        """
        numerator = 4 * _math.pi * (poly.getArea('PLANAR'))
        denom = poly.length / (_math.pi * _math.pi)
        return numerator / denom

    @staticmethod
    def ThinnessRatioValues(area: float, perimeter: float, ret_on_none=0) -> float:
        """
        Thinness ratio.
        See https://tereshenkov.wordpress.com/2014/04/08/fighting-sliver-polygons-in-arcgis-thinness-ratio/

        Args:
            area: area
            perimeter: permiter

            ret_on_none:
                Value to return if area or perimeter are None.
                I've seen tools (e.g. Eliminate) return null shapes with corresponding null lengths and areas, this gets over the issue

        Returns:
            float: the ratio
        """
        if area is None or perimeter is None: return ret_on_none
        numerator = 4 * _math.pi * area
        denom = perimeter * perimeter
        return numerator / denom


class Excel(_MixinNameSpace):  # noqa
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


class ResultAsPandas(_mixins.MixinPandasHelper):
    """
    Get the results of any arcpy operation which returns a table or layer, as a pandas dataframe.

    Also exposes pandas aggregate functions to summarise the data and some other "helper" methods.

    Also has a mechanism to load secondary results sets. These are exposed as a dictionary collection of _LayerDataFrame objects. See the examples.

    Args:
        tool: An arcpy tool which supports the in_features argument and a single out_feature class (support is being extended).
        columns: columns to retain in the resulting dataframe
        additional_layer_args (tuple[str]): List of the kwargs that point to additional output tables. This allows additional dataframes to be exposed. As an example, see the CountOverlappingFeatures which accepts an argument to define output_overlap_table.
        where: where query to apply to the underlying spatial results table/feature class, passed to data.table_as_pandas2
        as_int (tuple[str], list[str]): List of cols forced to an int in the resulting dataframe
        as_float (tuple[str], list[str]): List of cols forced to a float in the resulting dataframe

        memory_workspace (str):
            Results are created in an memory workspace.
            Arcgispro supports two memory workspace directives - in_memory and memory.
            in_memory supports more functionality than memory, but it is likely that ESRI will extend "memory" functionality but depreciate "in_memory".

    Members:
        df (_pd.DataFrame): Dataframe of the output layer
        df_lower (_pd.DataFrame): Dataframe of the output layer, all col names forced to lower case
        _fname_output (str): Name of the in-memory layer/table output created by execution of "tool"
        execution_result (_arcpy.Result): The result object returned from execution of "tool"
        Results: A dictionary of all Results, the main result is keyed as "main", with any additional results keyed with the values in the additional_layer_args member.


    Raises:
        errors.DataUnknownKeywordsForTool: If the arcpy tool does not support in_features or in_dataset keyword arguments

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


        Export the results to a feature class in a geodatabase, single line call.

        >>> from arcpy.conversion import ExportFeatures
        >>> ExportFeatures(ResultAsPandas(arcpy.analysis.Clip, 'C:/my.shp', 'C:/clip.shp').result_memory_layer, 'C:/the.gdb/clip_result')  # noqa


        View the result in excel from CountOverlappingFeatures

        >>> arcdata.ResultAsPandas(arcpy.analysis.CountOverlappingFeatures, ['./my.gdb/england', './my.gdb/uk']).view()  # noqa

    """

    class _LayerDataFrame(_mixins.MixinPandasHelper):
        def __init__(self, arg_name: str, fname_output: str, df: _pd.DataFrame = None):  # noqa
            self.arg_name = arg_name
            self.fname_output = fname_output
            self._df = None
            self.df_lower = None
            self.df = df

        @property
        def df(self):
            return self._df

        @df.setter
        def df(self, df: _pd.DataFrame):
            if self._df is None:
                self._df = df

            if self.df_lower is None:
                self.df_lower = df.copy()
                self.df_lower.columns = self.df_lower.columns.str.lower()

    def __init__(self,  # noqa
                 tool,
                 in_features: (list[str], str),
                 columns: list[str] = None,
                 additional_layer_args: (tuple[str], str) = (),
                 where: str = None,
                 exclude_cols: tuple[str] = ('Shape',),
                 as_int: (tuple[str], list[str]) = (),
                 as_float: (tuple[str], list[str]) = (),
                 memory_workspace: str = 'in_memory',
                 **kwargs):

        self._kwargs = kwargs
        self._tool = tool
        self._in_features = in_features
        self.result_memory_layer = memory_lyr_get(memory_workspace)
        self._memory_workspace = memory_workspace
        self.Results = {}

        if additional_layer_args:
            if isinstance(additional_layer_args, str): additional_layer_args = (additional_layer_args,)
            for s in additional_layer_args:
                lyr_tmp = r'%s\%s' % ('in_memory', _stringslib.rndstr(from_=_string.ascii_lowercase))
                self.Results[s] = ResultAsPandas._LayerDataFrame(s, lyr_tmp)
                kwargs[s] = lyr_tmp

        errstr = 'The tool "%s" had unknown keywords. ' % str(tool)
        errstr += 'Currently code only accepts tools which support arguments "in_features", "in_dataset" and the "in_polygons in_sum_features" pairing. '
        errstr += 'Along with analysis.Near.\n\nThis will need fixing in code.'

        keys = dict(_inspect.signature(tool).parameters).keys()
        if 'in_dataset' in keys:
            self.execution_result = tool(in_dataset=in_features, out_dataset=self.result_memory_layer, **kwargs)
        elif 'in_features' in keys:
            if 'out_table' in keys:  # CheckGeometry
                self.execution_result = tool(in_features=in_features, out_table=self.result_memory_layer, **kwargs)
            elif 'out_feature_class' in keys:
                self.execution_result = tool(in_features=in_features, out_feature_class=self.result_memory_layer, **kwargs)
            else:
                # Just try and get the outtable for tools that i'm not aware of yet
                no_out = True
                for out in keys:
                    if out.startswith('out_'):
                        no_out = False
                        self.execution_result = tool(in_features=in_features, out_feature_class=self.result_memory_layer, **kwargs)
                        break
                if no_out:
                    raise _errors.DataUnknownKeywordsForTool(errstr)
        elif 'in_polygons' in keys and 'in_sum_features' in keys:  # arcpy.analysis.SummarizeWithin & SummarizeNearBy
            self.execution_result = tool(*in_features, out_feature_class=self.result_memory_layer, **kwargs)
        else:
            raise _errors.DataUnknownKeywordsForTool(errstr)

        self.df = table_as_pandas2(self.result_memory_layer, cols=columns, where=where, exclude_cols=exclude_cols, as_int=as_int, as_float=as_float)
        self.df_lower = self.df.copy()
        self.df_lower.columns = self.df_lower.columns.str.lower()

        # check, LDF should behave as byref
        for LDF in self.Results.values():
            LDF.df = table_as_pandas2(LDF.fname_output, exclude_cols=('Shape',))

        self.Results['main'] = ResultAsPandas._LayerDataFrame('main', self.result_memory_layer, self.df)


def tuple_list_to_table(x, out_tbl, cols, null_number=None, null_text=None):
    """Save a list of tuples as table out_tbl and return catalog path to it.

    Args:
        x (tuple[tuple], list[list]): list of tuples (no nesting!), can be list of lists or tuple of tuples
        out_tbl (str): path to the output table

        cols list[tuple]: list of tuples defining columns of x. Can be defined as:
            [('colname1', 'type1'), ('colname2', 'type2'), ...]
            ['colname1:type1:lgt1', 'colname2:type2', ('colname3', 'type3')]
            [('colname1', 'type1'), 'colname2:type2:lgt2, ...]
            where types are case insensitive members of ('SHORT', 'SMALLINTEGER', 'LONG', 'INTEGER', 'TEXT', 'STRING', 'DOUBLE', 'FLOAT')
            Each column definition can have third element for length of the field,
            e.g.: ('ATextColumn', 'TEXT', 250).
            To leave out length, simply leave it out or set to '#'

        nullNumber (int, None): A value to replace null (None) values in numeric columns, default is None and does no replacement
        nullText (str, None): A value to replace null (None) values in text columns, default is None and does no replacement

    Examples:
        >>> x_ = [(...),(...),(...),(...),(...), ...]
        >>> tuple_list_to_table(x_, 'c:\\temp\\foo.dbf', [('IDO', 'SHORT'), ('NAME', 'TEXT', 200)]
        >>> tuple_list_to_table(x_, 'c:\\temp\\foo.dbf', ['IDO:SHORT', 'NAME:TEXT:200']
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
        col (str, list): column name(s) as string, a csv or semi-colon seperated string, or a list
        where (str): where clause
        order_by (str): order by clause like '"OBJECTID" ASC, "Shape_Area" DESC', default is None, which means order by object id if exists
        distinct (bool): unique values only

    Returns:
        list(tuple): list of tuples if mutliple columns requested
        list: list lof values if single col defined

    Raises:
        RuntimeError: Columns defined in order_by must be in col, otherwise a RuntimeError is raised
        errors.FieldNotFound: If the field or fields do not exist in fname

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

    # This check was added as we get a wierd error if field doesnt exists in enterprise geodatabase - make warning more explicit
    bad_fields = _baselib.list_not(list(map(str.lower, cols)), list(map(str.lower, _struct.field_list(fname))))
    if bad_fields:
        raise _errors.FieldNotFound('Field(s) "%s" not found in "%s"' % (bad_fields, fname))

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


def field_values_multi_table(fnames: list, fields: (str, list), distinct: bool = True):
    """
    Get field values from multiple layers/tables.

    If distinct is used, a sorted distinct flattened list is returned.
    Otherwise, the values are returned as is from the field_values function.


    Args:
        fnames: list of layers/fnames (is normpathed)

        fields:
            If fields is a string, then the same field is used for all fnames.
            Otherwise the list of fields is passed as is based on index. Note that fields may be nested tuples or list. See the underlying function field_values

        distinct: Flattens and returns distinct values across all "cells" read from fnames and fields

    Raises:
        ValueError: IF the length of "fnames" and "fields" doesnt match, and "fields" was a tuple or list

    Returns:
        list: Unique list of values
    """

    paths = list(map(_path.normpath, fnames))
    if isinstance(str, fields):
        fields = [fields] * len(fnames)

    if len(fnames) != len(fields):
        raise ValueError('The length of "fnames" and "fields" lists must match.')

    out = []
    for i, fname in paths:
        out.extend(field_values(fname, fields[i], distinct=distinct))

    if distinct:
        return _sort_list_set(_baselib.list_flatten(out))

    return out


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

        >>> field_get_dup_values('c:/my.gdb/sum_of_stuff', 'n', value_list_only=True)
        [2, 10]


        fave_colour colour has 2 occurences of blue and 5 occurences of black, ignore case

        >>> field_get_dup_values('c:/my.gdb/fave_colour', 'colour', False, f=str.lower)
        {'blue':2,'black':5}
    """
    fname = _path.normpath(fname)
    vals = list(map(f, field_values(fname, col)))
    res = _baselib.list_get_dups(vals, value_list_only=value_list_only)
    return res


def fields_get_dup_values(fname: str, cols: list, value_list_only: bool = False, sep: str = _stringslib.Characters.Language.emdash,  f: any = lambda v: v):
    """
    Check a set of columns for duplicate values across those columns.
    i.e. Treat the columns as being a compound key

    Args:
        fname (str): Feature class or table
        cols (list, tuple): cols to check
        value_list_only (bool): Get as simple list rather than dict
        sep: Seperator for the returned field values (defaults to emdash)
        f (any): function passed to map, typical use would be f=str.lower to make duplicate checks case insensitive

    Returns:
        list: Simple list of values which have duplicates
        dict: A dictionary of duplicates. Keys are the duplicate values and values are is the counts of duplicate values

    Examples:

        Error in data, duplicate for Wales and England

        >>> fields_get_dup_values('c:/my.gdb/country', ['name', 'continent'], value_list_only=True)
        ['Wales - Europe', 'England - Europe']

        Ask for dup number, Wales has two dups, England has 5

        >>> field_get_dup_values('c:/my.gdb/fave_colour', 'colour', value_list_only=False, f=str.lower)
        {'Wales - Europe': 2, 'England - Europe': 5}
    """
    vals = []
    splitter = '+_)(*&^]'
    fname = _path.normpath(fname)
    for col in cols:
        vals += list(map(lambda s: str(f(s)), field_values(fname, col)))  # lambda forces to a string, required for the join on the next line
    concat = [splitter.join(v) for v in zip(*vals)]

    def _rep(s):
        return s.replace(splitter, sep)

    dups: dict = _baselib.list_get_dups(concat)  # noqa
    if value_list_only:
        if not dups: return []
        return list(map(_rep, dups.keys()))

    if not dups: return {}
    return {_rep(k): v for k, v in dups.items()}



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
    Import a dataframe into a geodatabase.

    *** This often fails due to codepage errors and similiar. Use pandas_to_table2 which gets the job done much more reliably ***

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

    Read Notes for caveat with empty string/null handling

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

    Notes:
        Because this method first exports to csv, then it doesn't differentiate between empty strings and missing data.
        This becomes an issue where fields in the underlying data are not nullable.
        Blanket solutions would result in numeric fields being interpreted as string data types.
        An untested workaround would be to write single quotes to string fields only i.e. ''.

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


def table_as_pandas2(fname: str, cols: (str, list) = None, where: str = None, exclude_cols: (str, list) = ('Shape',), as_int: (list, tuple) = (),
                     as_float: (list, tuple) = (), cols_lower: bool = False, **kwargs):
    """Export data in feature class/table fname to a pandas DataFrame

    Args:
        fname (str): Path to feature class or table.
        cols (str, list, tuple): column list to retrieve.
        where (str): where clause, passed as-is to SearchCursor
        exclude_cols (str, list, tuple, None): list of cols to exclude. Exludes Shape by default for performance reasons. Pass none or an empty tuple to NOT exclude any cols
        as_int (list, tuple, None): List of cols by name to force to int
        as_float (list, tuple, None): list of cols by name to force to float64
        cols_lower (bool): force dataframe columns to lowercase
        kwargs: keyword args passed to pandas.DataFrame.from_records. nrows is a useful option

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
    if exclude_cols is None: exclude_cols = tuple()

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

    if cols_lower:
        df.columns = df.columns.str.lower()
        return df
    return df


def shape_area_add(fname: str, fld, overwrite: bool = False, show_progress: bool = False) -> int:
    """
    Add a shape area field "fld".
    Primarily used for in-memory layers which frequently do not carry over a shape_area or shape_length fields and do not recalculate these fields after changes.

    Optionally delete and recalculate if overwrite is True.

    Args:
        fname: fname
        fld: field name to add
        overwrite: Allow overwriting of field if it already exists
        show_progress: show progress

    Notes:
        Also see shape_length_add.
        overwrite wont work where Shape_Area and Shape_Length are read-only
    """
    fname = _path.normpath(fname)
    oidfld = _common.oid_field(fname)
    if show_progress:
        PP = _iolib.PrintProgress(get_row_count(fname) * 2, init_msg='Writing shape area to %s ...' % fld)

    rows = {}
    for row in _arcpy.da.SearchCursor(fname, [oidfld, 'SHAPE@AREA']):
        rows[row[0]] = row[1]
        if show_progress: PP.increment()  # noqa

    # Put after previous code deliverately
    if overwrite:
        # recent change means this no longer raises an error if field exists
        _struct.DeleteField(fname, fld)

    _struct.AddField(fname, fld, 'FLOAT')
    with _arcpy.da.UpdateCursor(fname, [oidfld, fld]) as UC:
        j = 0
        for row in UC:
            row[1] = rows[row[0]]
            UC.updateRow(row)
            if show_progress: PP.increment()  # noqa
            j += 1
    return j


def shape_length_add(fname: str, fld, overwrite: bool = False, show_progress: bool = False) -> int:
    """
    Add a shape length field "fld".
    Primarily used for in-memory layers which frequently do not carry over a shape_area or shape_length field and do not recalculate these fields after changes.

    Args:
        fname: fname
        fld: field name to add
        overwrite (bool): Allow overwrite if field already exists
        show_progress: show progress

    Notes:
        Also see shape_length_add
        overwrite wont work where Shape_Area and Shape_Length are read-only
    """
    fname = _path.normpath(fname)
    oidfld = _common.oid_field(fname)
    if show_progress:
        PP = _iolib.PrintProgress(get_row_count(fname) * 2, init_msg='Writing shape length to %s ...' % fld)

    rows = {}
    for row in _arcpy.da.SearchCursor(fname, [oidfld, 'SHAPE@LENGTH']):  # more efficient to preload then write all in the looped update cursor
        rows[row[0]] = row[1]
        if show_progress: PP.increment()  # noqa

    # Put after previous code deliverately
    if overwrite:
        # recent change means this no longer raises an error if field exists
        _struct.DeleteField(fname, fld)

    _struct.AddField(fname, fld, 'FLOAT')
    with _arcpy.da.UpdateCursor(fname, [oidfld, fld]) as UC:
        j = 0
        for row in UC:
            row[1] = rows[row[0]]
            UC.updateRow(row)
            if show_progress: PP.increment()  # noqa
            j += 1
    return j


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


def field_update_from_dict_addnew(fname: str, dict_: dict, col_to_update: str, key_col: str,
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
        >>> field_update_from_dict_addnew(fc, d, col_to_update='country_code', key_col='country_num', na='Other')
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

    if _arcpy.env.workspace or _struct.fc_in_toplogy(fname):  # debug the fc_in_topology call
        edit = _arcpy.da.Editor(_arcpy.env.workspace)
        edit.startEditing(False, False)
        edit.startOperation()

    # if you are here debugging an unexplained da.UpdateCursor invalid col error - check the where clause - you get an invalid col error if there are Nones in an IN query e.g. cola in (None,'a')
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

    if _arcpy.env.workspace or _struct.fc_in_toplogy(fname):
        edit.stopOperation()  # noqa
        if edit.isEditing:
            edit.stopEditing(save_changes=True)  # noqa
        del edit

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
        cols_to_copy (str, list, tuple): String or iterable of field names in src to copy to dest. Case insensitive.

        rename_to (str, list, tuple, None):
            Rename cols_to_copy to this name or list of names.
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

        Simple copy of country_name to wards, assuming wards share a countryid foreign key

        >>> fields_copy_by_join(r'C:\my.gdb\countries', 'countryid', 'C:\my.gdb\wards', 'countryid', 'country_name')
        123

        Simple copy as above, but rename the country_name field to country

        >>> fields_copy_by_join(r'C:\my.gdb\countries', 'countryid', 'C:\my.gdb\wards', 'countryid', 'country_name', rename_to='country')
        123

        Copy multiple fields and rename them to country and area_km2

        >>> fields_copy_by_join(r'C:\my.gdb\countries', 'countryid', 'C:\my.gdb\wards', 'countryid', ['country_name', 'area'], rename_to=['country', 'area_km2'])
        123

        Field SQ_ID already exists in destination, but setting error_if_dest_cols_exists=False copies
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
        cols_to_copy = [cols_to_copy.lower()]
    else:
        cols_to_copy = list(map(str, cols_to_copy))

    if isinstance(rename_to, str):
        rename_to = [rename_to]

    if not rename_to:
        rename_to = list(cols_to_copy)  # make a proper copy

    # Some basic validation, so we error early.
    if show_progress: print('\nPerforming some validation steps ...')

    if len(rename_to) != len(cols_to_copy):
        raise ValueError('If rename_to is passed, then assert len(cols_to_copy) == len(rename_to)')

    if not _struct.field_exists(fc_src, fc_src_key_col, case_insensitive=True):
        raise ValueError('The primary key field %s does not exist in source %s. This is case sensitive' % (fc_src_key_col, fc_src))

    if not _struct.field_exists(fc_dest, fc_dest_key_col, case_insensitive=True):
        raise ValueError('The foreign key field %s does not exist in destination %s. This is case sensitive' % (fc_dest_key_col, fc_dest))

    if error_if_dest_cols_exists:
        d = _struct.field_list_compare(fc_dest, rename_to)['a_and_b']  # noqa TODO Check this works
        if d:
            raise _errors.StructFieldExists('error_if_dest_cols_exists was True and field(s) %s already exist in destination %s' % (fc_dest, str(d)))

    if not allow_duplicates_in_pk:
        if field_has_duplicates(fc_src, fc_src_key_col):
            raise _errors.DataFieldValuesNotUnique('Field values in "%s", field %s must be unique.' % (fc_src, fc_src_key_col))

    # join_list may now be out of order with rename_to
    join_list_temp = [f for f in _arcpy.ListFields(fc_src) if f.name.lower() in map(str.lower, cols_to_copy)]
    if len(join_list_temp) != len(cols_to_copy):
        raise ValueError(
            'Expected %s fields in source, got %s. Check the names of the columns you have asked to copy. Field name comparisons are case sensitive here.' % (len(cols_to_copy), len(join_list_temp)))

    # create join_list, restoring order, so our source data cols match order of rename_to
    join_list = [None] * len(cols_to_copy)
    for f in join_list_temp:
        join_list[cols_to_copy.index(f.name.lower())] = f

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
    isedit = False
    fc = _path.normpath(fc)
    if show_progress:
        max_ = _struct.get_row_count2(fc, where=where_clause)
        PP = _iolib.PrintProgress(maximum=max_, init_msg='Applying func "%s" to column "%s" ...' % (func.__name__, col_to_update))  # noqa

    if isinstance(arg_cols, str): arg_cols = [arg_cols]
    if isinstance(arg_cols, tuple): arg_cols = list(arg_cols)
    j = 0
    try:
        # Update cursor behaves differently the environment has a workspace set
        # Specifically, updates must be put in an edit session, otherwise arcpy raises
        # an error about not being able to make changes outside of an edit session
        # Hence the following code triggering an edit session if we have a workspace
        # Also if the layer is in a topology, then it can only be edited in an Editor session
        if _arcpy.env.workspace or _struct.fc_in_toplogy(fc):
            edit = _arcpy.da.Editor(_arcpy.env.workspace)
            edit.startEditing(False, False)
            edit.startOperation()
            isedit = True

        with _arcpy.da.UpdateCursor(fc, arg_cols + [col_to_update], where_clause=where_clause) as cursor:
            for i, row in enumerate(cursor):
                row[-1] = func(*row[0:len(arg_cols)])
                cursor.updateRow(row)
                if show_progress:
                    PP.increment()  # noqa
                j += 1

        if _arcpy.env.workspace or _struct.fc_in_toplogy(fc):
            edit.stopOperation()  # noqa
            if edit.isEditing:
                edit.stopEditing(save_changes=True)  # noqa
            del edit
            isedit = False
        return j
    except Exception as e:
        with _fuckit:
            edit.stopOperation()
            edit.stopEditing(save_changes=False)  # noqa
            del edit
        raise Exception('An exception occured. %s.\n\nException: %s' % (
            'Changes applied by field_recalculate were rolled back' if isedit else 'No edit session was active. Changes could not be rolled back', _baselib.exception_to_str(e))) from e


field_apply_func = field_recalculate  # noqa For convieniance. Original func left in to not break code


def field_apply_and_add(fname: str, in_fields: (list[str], str), new_field: str, func, field_type: (str, None) = None, field_length: (int, None) = None, allow_edit: bool = False, show_progress: bool = True, **kwargs) -> int:
    """ Add the square type based on sq_id.

    Args:
        fname (str): feature class/table name
        in_fields (str): fields whose values are passed to func
        new_field (str): name of field to add, or edit if allow_edit is True
        func: The function to apply, should return a single value and take as many args as fields passed to in_fields
        field_type: The field type, SHORT, LONG, TEXT etc. See ESRIs AddField method for options
        field_length: length of field (for text fields
        allow_edit (bool): Allow editing. i.e. use a field that currently exists.
        show_progress (bool): Show progress
        **kwargs: passed to ESRIs AddField

    Raises:
        ValueError: If allow_edit was False but new_field already exists
        ValueError: If allow_edit was False and no field_type was specified
        ValueError: If field_type not in ['TEXT', 'FLOAT', 'REAL', 'SHORT', 'LONG', 'DATE', 'DATETIME']

    Returns:
        int: Number of records edited

    Notes:
        Ultimately looks up if is a CS square from erammp.data.
        If there are invalid sq_ids, a warning message will be printed ot the console


    Examples:

        Add a col

        >>> field_apply_and_add('C:/my.gdb/squares')
        300
    """
    if not field_type and not allow_edit:
        raise ValueError('allow_edit was False and no field_type was specified')

    if field_type and field_type.lower() not in ['text', 'float', 'short', 'date', 'datetime']:
        raise ValueError("field_type only supports ['TEXT', 'FLOAT', 'REAL', 'SHORT', 'LONG', 'DATE', 'DATETIME'].")
    fname = _path.normpath(fname)

    if isinstance(in_fields, str): in_fields = [in_fields]

    if allow_edit:
        if not _struct.field_exists(fname, new_field):
            _struct.AddField(fname, new_field, field_type, field_length=field_length, **kwargs)
    else:
        # Check first so can raise a known error rather than generic arcpy one
        if _struct.field_exists(fname, new_field):
            raise ValueError('Field "%s" already exists and allow_edit was False.' % new_field)
        _struct.AddField(fname, new_field, field_type, field_length=field_length, **kwargs)
    i = field_recalculate(fname, in_fields, new_field, func, show_progress=show_progress)
    return i


def memory_lyr_get(workspace='in_memory') -> str:
    """ Just get an 8 char string to use as name for temp layer.

    Returns:
        str: tmp layer pointer

    Examples:
        >>> memory_lyr_get()
        'in_memory/arehrwfs
    """
    return '%s/%s' % (workspace, _stringslib.rndstr(from_=_string.ascii_lowercase))


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

        >>> del_rows('c:/my.gdb/coutries', '*', '*', where='OBJECTID<10')

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


def del_rows_where(fname: str, where: str = None, show_progress: bool = True) -> int:
    """
    Delete rows based on a where. Tiny wrapper around del_rows

    ** CARE ** - If no where is specified .. ALL ROWS WILL BE DELETED

    Args:
        fname (str): path to feature class/layer
        where (str, None): where string to prefilter rows
        show_progress (bool): Show progress bar, costs a bit of time to determine row count

    Raises:
        DataDeleteAllRowsWithNoWhere: If asked to delete all rows (vals='*') with no where specified

    Returns:
        int: Number of deleted rows

    Notes:
        Calls del_rows

    Examples:
        Use wildcard delete, we don't care about cols, so just use OBJECTID\n

        >>> del_rows('c:/my.gdb/coutries', where='OBJECTID<10')
        9

        Delete everything!!!

        >>> del_rows('c:/my.gdb/coutries')
        999
    """
    return del_rows(fname, cols='*', vals='*', where=where, show_progress=show_progress, no_warn=True)


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
    Calls arcpy.analysis.Select, which recieves the kwargs

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


# Devnote - it is better to use copy_shape here, Python does not support "Shape@ =" as a kwarg (@ is invalid) and so using this design decision means the caller does not have to know the name of the shape field in "fname".
def features_copy(source: str, dest: str, workspace: str, where_clause: str = '*', fixed_values=None, copy_shape: bool = True, force_add: bool = True, fail_on_exists: bool = True,
                  expected_row_cnt: int = None, no_progress: bool = False, enable_transactions: bool = False, **kwargs) -> int:
    """Copy features from one table or featureclass to another. i.e. The shape and fields as given as kwargs.

    If you get an error, double check field names, noting that field names are case sensitive.

    Also see features_copy2, for a simplified but much quicker alternative.

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
        enable_transactions (bool): Enable transactions, leaving disabled should increase performance

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
        >>> features_copy('c:/my.gdb/world_counties', 'c:/my.gdb/euro_countries', 'c:/my.gdb', where_clause='country="EU"',
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
    with _orm.ORM(dest, workspace=workspace, enable_transactions=enable_transactions, enable_log=False, **kws) as Dest:
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
        if enable_transactions: Dest.tran_commit()
    return i


# Devnote - it is better to use copy_shape here, Python does not support "Shape@ =" as a kwarg (@ is invalid) and so using this design decision means the caller does not have to know the name of the shape field in "fname".
def features_copy2(source: str, dest: str, where_clause: str = '*', fixed_values=None, copy_shape: bool = True,
                   show_progress: bool = True, validate_cols: bool = False, **kwargs) -> int:
    """Copy features from one table or featureclass to another. Has much faster performance than
     features copy, but fewer validation options and cannot be transactionalised

    Fixed_values only are supported, the rows written to dest will match the number of rows matching the where_clause in source.

    If you get an error, double check field names and field types between the source and dest.

    Args:
        source (str): path to source feature class/table
        dest (str): path to destination feature class/table
        where_clause (str): used to filter the target table, i.e. a geodatabase compatible "where" SQL query for "source".

        fixed_values (dict):
            pass a dictionary kwargs (field:value) of fields in the destination to assign fixed values to.
            For example: {'sq_id':1234} would write all destination sq_ids as 1234 which matched the where_clause
            Note that **kwargs will override fixed_values if these fields (keys) are duplicated between
            the two.

        copy_shape (bool): set to false if working with a table, otherwise set this to true to transfer geometry
        show_progress (bool): show progress
        kwargs (any): Keyword arguments, where key is field in dest, and value is field in src. E.g. dest_field='src_field'
        validate_cols: If True, then a pass is made over the cols defined, and a descriptive error is raise with invalid cols reported

    Raises:
        errors.FieldNotFound: If validate_cols was True, and invalid field args were passed.

    Returns:
        int: Number of records added to dest

    Notes:
        As this does not support transactions, it will fail if dest is in a topology and in other circumstances.
        See https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/insertcursor-class.htm
        If kwargs and fixed_values are not passed, then a warning is raised and no rows are written and 0 is returned

    Examples:

        >>> features_copy2('c:/my.gdb/world_counties', 'c:/my.gdb/euro_countries', 'c:/my.gdb', where_clause='country="EU"',
        >>>    copy_shape=True,
        >>>    eu_country='world_country', population='population')
        33
    """
    source = _path.normpath(source)
    dest = _path.normpath(dest)

    if copy_shape:
        if not _struct.field_shape(dest) or not _struct.field_shape(source):
            raise _errors.ShapeNotSupported('copy_shape was True, but the source "%s" or dest "%s" do not have a Shape field.\nPass copy_shape=False if this is expected.' % (source, dest))

    if validate_cols:
        if show_progress: print('\nValidating fields ...')
        dest_cols_db = list(map(str.lower, _struct.fc_fields_get(dest)))
        src_cols_db = list(map(str.lower, _struct.fc_fields_get(source)))


        dest_cols_write = []
        dest_cols_write += list(map(str.lower, fixed_values.keys()))
        dest_cols_write += list(map(str.lower, kwargs.keys()))

        src_cols_read = list(map(str.lower, kwargs.values()))

        dest_bad = _baselib.list_not(dest_cols_write, dest_cols_db)
        src_bad = _baselib.list_not(src_cols_read, src_cols_db)

        if dest_bad or src_bad:
            raise _errors.FieldNotFound('Field validation failed.\nFields not in source:%s\nFields not in dest:%s' % (src_bad, dest_bad))
        else:
            if show_progress: print('\nAll field arguments looking good ...')

    if 'where' in map(str.lower, kwargs.keys()):
        _warn('keyword "where" in kwargs.keys(), did you mean to set a where clause? If so, use where_clause=<MY QUERY>')


    if not kwargs and not fixed_values:
        _warn('Source columns (kwargs) and fixed values (fixed_values) not provided. No rows written to %s.\nIs this what you intended?' % dest)
        return 0

    n = get_row_count2(source, where=where_clause)  # this is also a check that the where clause is valid
    if n == 0:
        _warn('No records matched the where clause %s.\nIs this expected?' % where_clause)
        return 0

    if show_progress:
        PP = _iolib.PrintProgress(maximum=n * 2, init_msg='\nImporting rows to %s' % source)

    # Important thing here is that we are building the src and dest cols with matching indexes in the list
    # Excepting that dest_cols has the fixed_value columns that will be set appended to the end of the dest col list
    src_cols = []
    dest_cols = []
    if kwargs:
        src_cols += list(kwargs.values())
        dest_cols += list(kwargs.keys())
    if copy_shape:
        src_cols += ['SHAPE@']
        dest_cols += ['SHAPE@']
    if fixed_values:
        dest_cols += list(fixed_values.keys())

    insert_rows = []

    # for efficiency, build all the rows before running the insert
    if src_cols:
        with _arcpy.da.SearchCursor(source, src_cols, where_clause=where_clause) as SCur:
            for row in SCur:
                row = list(row)
                if fixed_values:
                    row += list(fixed_values.values())
                insert_rows += [row]
                if show_progress: PP.increment()  # noqa
    else:  # we only get here if no kwargs AND we havent asked to copy the geometry (copy_shape is False)
        for x in range(n):
            insert_rows += [list(fixed_values.values())]
            if show_progress: PP.increment()  # noqa

    i = 0
    with _arcpy.da.InsertCursor(dest, dest_cols) as InsCur:
        for row in insert_rows:
            InsCur.insertRow(row)
            i += 1
            if show_progress: PP.increment()

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
    out_tmp = 'in_memory/%s' % _stringslib.get_random_string(length=8, from_=_string.ascii_lowercase)
    _arcpy.analysis.Statistics(fname,  # noqa
                               out_tmp,
                               statistics_fields=statistics_fields,
                               case_field=case_field,
                               concatenation_separator=concatenation_separator
                               )
    df = table_as_pandas2(out_tmp)
    return df


class Spatial(_MixinNameSpace):  # noqa

    @staticmethod
    @_decs.environ_persist
    def unionise_self_overlapping_clean(source: str, dest: str, rank_cols: list = None, rank_func=None, reverse: bool = False, dissolve_cols: list[str] = None, multi_part='MULTI_PART',
                                        overwrite: bool = False, show_progress: bool = False) -> bool:
        """
        Clean up a single layer which has overlapping polygons based on a rank function. The top ranked polygon is retained, while other polygons are all removed.
        When running a union on a single layer, duplicate polygons are created for each overlapping area in the original layer. See the union documentation.
        By passing a custom rank function and the columns it applies to, all duplicate polys can be selectively removed because the top ranked is retained.

        Args:
            source: input feature class
            dest: save cleaned unionised layer here
            rank_cols: Cols passed to rank function, if none is passed, the first by oid order in the unionised layer will be retained. NB rank_cols are in the unionised layer.
            rank_func: a function that accepts the values passed in rank_cols applied to the original layer. The function should accept a single argument and return an orderable key (e.g. simple numeric rank). The lowest value is retained.
            reverse: Reverse the rank order (highest "rank" will be retained)
            dissolve_cols (list(str), None): If provided, the unionised layer will be dissolved on these cols. Otherwise no dissolve will occur.
            multi_part (str, None): Passed to mutli_part argument of dissolve. Supports MULTI_PART or SINGLE_PART specifying if multipart features are created. If None, defaults to MULTI_PART. See https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/dissolve.htm.
            overwrite (bool): Allow overwrite
            show_progress (bool): show progress

        Returns:
            bool: True if there were overlaps, else False

        Examples:

            Clean country layer of overlaps, where there is an overlap, the country with the lowest population * gdp is kept.
            Finally the unionised layer is dissolved by country name.

            >>> func = lambda x: x[0] * x[1]
            >>> Spatial.unionise_self_overlapping_clean('C:/my.gdb/coutry', 'C:/my.gdb/country_clean', ['population', 'gdp'], func, dissolve_cols=['country_name'])
        """
        source = _path.normpath(source)
        dest = _path.normpath(dest)
        out = False
        try:
            lyr_union = r"in_memory/%s" % _stringslib.rndstr(from_=_string.ascii_lowercase)
            if show_progress: print('\nRunning the union ...')
            _arcpy.analysis.Union([source], lyr_union, "ALL", None, "GAPS")  # noqa
            oidfld = _struct.field_oid(lyr_union)
            df_union = table_as_pandas2(lyr_union)

            # IN_FID is the df_union objectid
            if show_progress: print('\nIdentifying identical polygons ...')
            Res = ResultAsPandas(_arcpy.management.FindIdentical, lyr_union, as_int=['OBJECTID', 'IN_FID', 'FEAT_SEQ'], output_record_option='ONLY_DUPLICATES', fields=['Shape'])

            last_feat_seq = None
            dup_dict = {}
            if not rank_cols: rank_cols = [oidfld]
            if show_progress and len(Res.df_lower) > 0: PP = _iolib.PrintProgress(maximum=len(Res.df_lower), init_msg='Deleting duplicate rows in in-memory union layer...')
            row = None
            for row in Res.df_lower.itertuples(index=False):
                # dup dict will look like for example (3 rank cols)...
                # {1:[10, 23, 'uraquay'], 2:[2, 5, 'chile'], ...}
                if not last_feat_seq:
                    last_feat_seq = row.feat_seq  # noqa
                    dup_dict[row.in_fid] = list(  # noqa
                        df_union.query('%s==%s' % (oidfld, row.in_fid))[rank_cols].iloc[0])  # noqa  Get first (and only) row of the dataframe as a list and put in dictionary with key row.in_fid
                elif row.feat_seq == last_feat_seq:  # noqa
                    dup_dict[row.in_fid] = list(df_union.query('%s==%s' % (oidfld, row.in_fid))[rank_cols].iloc[0])  # noqa
                else:
                    last_feat_seq, dup_dict = Spatial._del_dups(lyr_union, df_union, dup_dict, row, rank_func, reverse, rank_cols, oidfld)  # noqa
                    out = True
                if show_progress: PP.increment()  # noqa

            # Delete last duplicate set - if debugging remember this ** ONLY CONTAINS THE LAST DUPLICATE TO DELETE **
            if dup_dict and row:  # noqa
                Spatial._del_dups(lyr_union, df_union, dup_dict, row, rank_func, reverse, rank_cols, oidfld)  # noqa
                out = True

            # sanity check - did we get rid of all dups
            # RChk = arcdata.ResultAsPandas(arcpy.management.FindIdentical, lyr_union, as_int=['OBJECTID', 'IN_FID', 'FEAT_SEQ'], output_record_option='ONLY_DUPLICATES', fields=['Shape'])
            # assert len(RChk.df) == 0, 'Looks like there are still overlapping polygons in the unionised layer ...'
            _arcpy.env.workspace = _common.workspace_from_fname(dest)
            _arcpy.env.overwriteOutput = overwrite
            if dissolve_cols:
                if show_progress: print('\nRunning the dissolve ...')
                lyr_diss = r'in_memory/%s' % _stringslib.rndstr(from_=_string.ascii_lowercase)
                if show_progress: print('\nDissolving to in-memory layer ...')
                _arcpy.management.Dissolve(lyr_union, lyr_diss, dissolve_cols, multi_part=multi_part)
                if show_progress: print('\nExporting features to %s ...' % dest)
                _struct.ExportFeatures(lyr_diss, dest)
            else:
                if show_progress: print('\nExporting features to %s ...' % dest)
                _struct.ExportFeatures(lyr_union, dest)
        finally:
            with _fuckit:
                _struct.Delete(lyr_union)  # noqa
                _struct.Delete(lyr_diss)  # noqa
        return out

    @staticmethod
    def _del_dups(lyr_union, df_union, dup_dict: dict, row, rank_func, reverse, rank_cols, oidfld) -> (int, dict):
        del_ids = []
        for i, itm in enumerate(dict(sorted(dup_dict.items(), key=rank_func, reverse=reverse)).items()):
            if i != 0: del_ids += [itm[0]]  # only add to delids after 1st sorted dict item. i.e. we are retaining the first ordered record and deleting the rest

        if del_ids:
            n = 1
            while n > 0:  # weird behaviour when calling deletew against in-memory layer (see above) - want to make sure
                n = _crud.CRUD(lyr_union, enable_transactions=False).deletew(_sql.query_where_in(_struct.field_oid(lyr_union), del_ids))

        return row.feat_seq, {row.in_fid: list(df_union.query('%s==%s' % (oidfld, row.in_fid))[rank_cols].iloc[0])}

    @staticmethod
    @_decs.environ_persist
    def unionise(sources: list[str], dest: str, is_fields: (str, list[str], None) = 'ALL', rename_from: list[str] = None, rename_to: list[str] = None, keep_cols: (str, list[str], None) = 'ALL',
                 del_cols: (str, list[str], None) = None, overwrite=True, show_progress: bool = False, **kwargs) -> dict[str:list, str:list]:  # noqa
        """ Unionise multiple layers, keep fid cols, add is_<xxx> cols

        Args:
            sources (list[str]): list of sources
            dest (str): output name

            is_fields (str, list[str], None):
                Add is_ fields for these tables in the union.
                'ALL': Add is_ fields for all layers in the union.
                None: Add no is_ fields
                list[str]: Add for these only, this would be specified in the list as 'FID_<feature class name>'

            rename_from (list[str]): list of fields to rename, good candidates for renaming are the is_fields, which default to is_<tablename>
            rename_to (list[str]): new field names, matching rename_from by index


            keep_cols (str, list[str], None):

                Specify which fields to keep in the layer. keep_cols are added to is_fields. i.e. You do not have to specify is_fields in keep_cols.

                NB ** DO NOT SPECIFY NON-EDITABLE FIELDS - e.g. Shape, OBJECTID, Shape_Area, Shape_Length - An ESRI BUG WILL CAUSE DeleteFields to Fail **

                'ALL': Keep all fields resulting from the union.
                'FID': Keep all FID_ fields and the is_<fields> you specified
                list[str]: Keep readonly fields, these fields and the is_<fields> you specified.
                Empty list: Keep readonly fields and the is_<fields> you specified
                None: Retain read-only fields only.

            del_cols (str, list[str], None): Delete these cols. Invalid col names will be skipped and not raise an error.

            overwrite (bool): Allow overwrite of dest
            show_progress (bool): Print progress to the console
            kwargs: Keyword args passed to arcpy.analysis.Union. See https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/union.htm

        Returns:
             dict[str:list]: A dictionary of is_ fields which are added 'good' and not added 'bad'. e.g. {'good':['FID_country', 'FID_region'], 'bad':['FID_area']}

        Notes:
            Fields are renamed as the last operation just before exporting the final layer to dest. This is so is_ fields can be renamed.

        Examples:

            Unionise 3 layers, requesting is_ fields for two input layers (1 success, 1 failed) and saving as C:/my.gdb/unionised
            >>> Spatial.unionise(['C:/my.gdb/country', 'C:/my.gdb/region', 'C:/my.gdb/area'], 'C:/my.gdb/unionised', is_fields=['FID_country', 'FID_area'])  # noqa
            {'good':['FID_country',], 'bad':['FID_area']}
        """

        srcs = list(map(_path.normpath, sources))  # noqa
        dest = _path.normpath(dest)
        _arcpy.env.overwriteOutput = overwrite
        if isinstance(keep_cols, str): keep_cols = list[keep_cols]
        # Lets do this in memory for speed
        lyrtmp = 'in_memory\%s' % _stringslib.get_random_string(
            from_=_string.ascii_lowercase)  # need to use this as supports alterfield and several other features that memory workspace doesnt support
        fid_cols = ['FID_%s' % s for s in [_iolib.get_file_parts2(t)[1] for t in srcs]]
        if show_progress: print('\nPerforming initial Union ....')
        try:
            _arcpy.analysis.Union(srcs, lyrtmp, **kwargs)  # noqa
            # \\nerctbctdb\shared\shared\SPECIAL-ACL\ERAMMP2 Survey Restricted\common\data\GIS\nfs_land_analysis.gdb\permissionable_unionised_temp
            allflds = _struct.fc_fields_get(lyrtmp)

            # Now add the is_ cols
            out = _baselib.DictList()

            if is_fields is not None:
                if show_progress:
                    print('Adding is_ cols ...')
                    PP = _iolib.PrintProgress(fid_cols)

                for fidcol in fid_cols:
                    if fidcol.lower() in map(str.lower, allflds):
                        isfld = 'is_%s' % fidcol[4:]
                        if is_fields == 'ALL' or fidcol.lower() in map(str.lower, is_fields):
                            _struct.AddField(lyrtmp, isfld, 'SHORT')
                            field_apply_func(lyrtmp, fidcol, isfld, Funcs.LongToOneZero, show_progress=show_progress)
                            out['good'] = isfld  # this is a DictList, we dont need +=
                    else:
                        out['bad'] = fidcol  # this is a DictList, we dont need +=
                    if show_progress: PP.increment()  # noqa
            keep_cols_cpy = ['Shape']
            if keep_cols and isinstance(keep_cols, (list, tuple)):
                if show_progress: print('Deleting fields ...')
                keep_cols_cpy += list(keep_cols)
                keep_cols_cpy += out['good'] if out.get('good') else []
                _struct.DeleteField(lyrtmp, keep_cols_cpy, method='KEEP_FIELDS')  # Debug, this may fail and may have to restructure this Delete
            elif keep_cols == 'FID':
                if show_progress: print('Deleting fields ...')
                keep_cols_cpy += fid_cols
                keep_cols_cpy += out['good'] if out.get('good') else []
                _struct.DeleteField(lyrtmp, keep_cols_cpy, method='KEEP_FIELDS')  # Debug, this may fail and may have to restructure this Delete
            elif keep_cols is None:
                if show_progress: print('Deleting fields ...')
                _struct.DeleteField(lyrtmp, _struct.fc_fields_not_required(lyrtmp), method='DELETE_FIELDS')
            else:
                pass  # just to make code easier to read - if we are here, we are keeping all the cols

            if del_cols:  # this is in a loop so we continue if a single deletion fails
                if isinstance(del_cols, str): del_cols = [del_cols]
                for c in del_cols:
                    with _fuckit:
                        _struct.DeleteField(lyrtmp, c)

            if rename_from:
                if show_progress: print('Renaming fields ...')
                _struct.fields_rename(lyrtmp, rename_from, rename_to, skip_name_validation=False, show_progress=show_progress)

            if show_progress: print('Writing "%s" ...' % dest)
            _struct.ExportFeatures(lyrtmp, dest)

            ok = _struct.fc_aliases_clear(dest)  # suspect this isnt necessary as they are probably cleared when using in_memory layer, but leaving in until I get round to verifying
            if show_progress:
                if ok:
                    print('Aliases reset on fields %s' % ok)
                else:
                    print('Failed to reset aliases. This is not fatal. You will get this message if "dest" is in-memory.')
        finally:
            with _fuckit:
                _struct.Delete(lyrtmp)

        return dict(out)

    @staticmethod
    def features_overlapping(fname: str, fields: (str, list[str]) = None) -> tuple[bool, (None, list[list[int]])]:
        """
        Get overlapping features in a single feature class.
        and test if there were overlaps.

        Args:
            fname (str): feature class

            fields (str, list[str]):
                fields passed to FindIdentical, these are appended to Shape.
                The default is None, which considers Shape only.
                See https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/find-identical.htm

        Returns:
            tuple[bool, (None, list[list[int]])]: are there overlaps, and a list of lists, where the inner lists are the overlapping polygon ids from the input layer.
            The returned dataframe has columns objectid, in_fid, feat_seq. NB: objectid is just the key for these results and has no relation to the source layer.

        Examples:

            No overlaps in layer

            >>> Spatial.features_overlapping('C:/my.gdb/lyr')
            False, None


            Has overlaps, polygons with ids of 10 and 20 overlap and polygons with ids 25, 26 and 27 overlap.

            >>> Spatial.features_overlapping('C:/my.gdb/lyr')
            True, [[10, 20], [25, 26, 27], ...]
        """
        fname = _path.normpath(fname)  # noqa
        if isinstance(fields, str): fields = [fields]
        if fields is None: fields = []
        lyr_union = r"memory\%s" % _stringslib.rndstr(from_=_string.ascii_lowercase)

        try:
            _arcpy.analysis.Union([fname], lyr_union, "ALL", None, "GAPS")  # noqa
            idcol = 'FID_%s' % _path.basename(fname)
            # arcpy.management.FindIdentical("address_crn_lpis_sq_Union", r"S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\common\data\GIS\_arcpro_projects\gmep_surveys\gmep_surveys.gdb\address_crn_lp_FindIdentical", "Shape", None, 0, "ONLY_DUPLICATES")
            Res = ResultAsPandas(_arcpy.management.FindIdentical, lyr_union, as_int=['OBJECTID', 'IN_FID', 'FEAT_SEQ'], output_record_option='ONLY_DUPLICATES', fields=['Shape'] + fields)
            if not len(Res.df) or len(Res.df) == 0: return False, None  # noqa

            df_lyr_union = table_as_pandas2(lyr_union, [_struct.field_oid(lyr_union), idcol])
            ddf = pandas_join(Res.df_lower, df_lyr_union, 'in_fid', _struct.field_oid(lyr_union))
            out = []
            for row in ddf.iterrows():
                if len(out) < row[1].feat_seq:  # noqa
                    out.append([])
                ind = int(row[1].feat_seq - 1)
                out[ind] += [row[1][idcol]]  # noqa
        finally:
            _struct.fc_delete2(lyr_union)
        return True, out  # noqa

    @staticmethod
    @_decs.environ_persist
    def slivers_merge(source: str, dest: str, area_thresh: (float, None), thinness_thresh, thresh_operator: str = ' AND ', where_clause: str = '', shape_area_fld: str = 'Shape_Area',
                      shape_length_field: str = 'Shape_Length',
                      keep_thinness_in_dest: bool = False,
                      max_iterations: int = 20,
                      export_target_features: str = None, overwrite: bool = False, show_progress: bool = True, **kwargs) -> int:
        """
        Merge slivers in source layer to dest layer, using area and thinness ratio threshholds.
        Operates largely in memory for speed and allow overwriting of the source (set source and dest to the same)

        Features targetted for merging can be exported without creating the dest layer by setting dest to None and specifying export_target_features.

        Args:
            source (str): Source fc

            dest (str): Dest fc, this can be source as the bulk of the processingis in_memory.
                        Accept None, to not export - but export_target_features should be set.

            area_thresh (float): The area threshhold for sliver selection
            thinness_thresh (float): The thinness threshhold for sliver selection. thinness is a value between 0 and 1. 0.1 is a good target to start around.
            thresh_operator (str): AND or OR, applied to threshholds. Note the spaces.
            where_clause (str): Additional preselection filter, ANDED with the threshhold where
            shape_area_fld (str): The shape_area field in source feature class
            shape_length_field (str): The shape length field in the source feature class
            keep_thinness_in_dest (bool): Keep the thinness field in "dest".
            max_iterations: maximum allowed iterations. If set to 1, that allows a single pass. ... etc.
            export_target_features (str, None): Export the features that are selected for merging here.
            overwrite (bool): allow overwriting
            show_progress (bool): show progress

            **kwargs:
                Passed as-is to the Elimate tool.
                "ex_where_clause" (exclude where clause) is particularly useful and will be applied in addition to "where_clause"
                "selection" defaults to "LENGTH", but accepts "AREA", where it merges with longest shared boundary and greatest area neighbour respectively.
        Raises:
            UserWarning: If dest and export_target_features args evaluated to False.
            ValueError: If source and dest are the same, and overwrite is False
            ValueError: IF max_iterations looks invalid
            errors.FieldExists: If field "thinness" already exists in "source"

        Returns:
            int: The number of slivers merged

        Notes:
            Uses the eliminate tool which requires an advanced license. See https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/eliminate.htm.
            Pass dest=None and a valid path for export_target_features to just review which features we would attempt to merge.
            This also performs multipart to single part.
        """

        def _get_where(area_fld: str, area_thr: float, thinness_thr: float, where_cl) -> str:
            area_thresh_sql = '%s < %s' % (area_fld, area_thr) if area_thresh else ''
            thinness_thresh_sql = '%s < %s' % ('thinness', thinness_thr) if thinness_thr else ''
            where_ = thresh_operator.join([area_thresh_sql, thinness_thresh_sql])
            if where_cl:
                where_ = "(%s) AND (%s)" % (where_clause, where_)
            return where_

        if not isinstance(max_iterations, int) or max_iterations <= 0 or max_iterations > 1000:
            raise ValueError(
                'max_iterations was invalid against criteria:\n"isinstance(max_iterations, int) or max_iterations <= 0 or max_iterations > 1000".\nThis is used to exit a possibly infinite loop, so get it right!')

        if not dest and not export_target_features:
            raise UserWarning('dest and export_target_features both evaluated to False. Set both, or one or the other')

        _arcpy.env.workspace = _common.gdb_from_fname('in_memory')

        # add the ratio fld and calc
        if _struct.field_exists(source, 'thinness'):
            raise _errors.FieldExists('Field "%s" already exists in "%s"' % (source, 'thinness'))

        try:
            # Copy source to in_memory
            source = _path.normpath(source)
            if source.lower() == _path.normpath(dest).lower() and not overwrite:
                raise ValueError('source and dest were the same and overwrite was False')

            fname_mem = 'in_memory/%s' % _stringslib.get_random_string(from_=_string.ascii_lowercase)
            if show_progress: print('\nExploding %s to %s ...' % (source, fname_mem))
            _arcpy.management.MultipartToSinglepart(source, fname_mem)  # necessary for the Eliminate tool, plus also stick it in_memory
            # But - in_memory layer - length and area fields will be borked - we recalulate them in the while loop

            _struct.AddField(fname_mem, 'thinness', 'DOUBLE')
            fname_mem_oid = _struct.field_oid(fname_mem)

            if show_progress: print('\nSelecting sliver polygons ...')

            counts = []
            itern = 0
            stuck_factor = 2
            stuck = False
            while True:
                fname_mem_rcnt = get_row_count(fname_mem)
                if show_progress: print('\nRunning iteration %s of the Eliminate loop ... Input layer has %s polygons.' % ((len(counts) + 1), fname_mem_rcnt))

                # Safety net in potential infinite loop, 20 is arbitary
                itern += 1
                if itern > max_iterations:
                    print('\nIterations exceeded %s. This is unexpected. Breaking out of loop. Check results.' % max_iterations)
                    break

                # we need to recalculate our thinness because we are using an in-memory layer
                shape_length_add(fname_mem, shape_length_field, overwrite=True, show_progress=show_progress)
                shape_area_add(fname_mem, shape_area_fld, overwrite=True, show_progress=show_progress)

                if show_progress: print('\nRemoving rows with null length or area ...')
                _crud.CRUD(fname_mem, enable_transactions=False).deletew(
                    '%s OR %s' % (_sql.is_null(shape_length_field), _sql.is_null(shape_area_fld)))  # shouldnt me needed, but results of previous eliminates can generate null shapes
                field_apply_func(fname_mem, [shape_area_fld, shape_length_field], 'thinness', Funcs.ThinnessRatioValues, show_progress=show_progress)

                _arcpy.management.MakeFeatureLayer(fname_mem, 'lyrmem')

                # This is a bit of a kludge, but the idea is to decrease the number of selected features
                # to merge up some smaller slivers with other slivers that now do not match the selection criteria (but are still slivers by the original passed criteria)
                # the stuck_factor selects for increasingly smaller slivers, but we will eventually exit according to max_iterations
                where = _get_where(shape_area_fld, area_thresh, thinness_thresh, where_clause)
                where_stuck = ''
                if len(counts) > 1 and counts[-1] / counts[-2] > 0.8 and not stuck:
                    stuck = True
                    if show_progress: print('\nStuck, selecting subset ... Counts: %s; stuck: %s; stuck_factor: %s' % (counts, stuck, stuck_factor))
                    where_stuck = _get_where(shape_area_fld, area_thresh / stuck_factor, thinness_thresh / stuck_factor, where_clause)
                    stuck_factor += 1
                else:
                    stuck = False
                    stuck_factor = 2

                _arcpy.management.SelectLayerByAttribute('lyrmem', 'NEW_SELECTION', where_clause=where)
                counts += [int(_arcpy.management.GetCount('lyrmem')[0])]  # yes, getcount[0] is a fickin string
                if stuck:
                    if stuck_factor > 5:
                        # lets try something else, pick a random 50% subsample of the slivers to seed merges around
                        if show_progress: print('\nStuck ... using random strategy to unstick ...')
                        stuck_factor = 2
                        oids = [row[0] for row in _arcpy.da.SearchCursor('lyrmem', [fname_mem_oid])]
                        oidsrnd = _baselib.list_random_pick(oids, max(int(counts[-1] / 2), 0))
                        if not oidsrnd:
                            if show_progress: print('\nRandom slivers could not be picked. Failed to unstick. Exiting loop ...')
                            break

                        where_rand = '(%s) AND (%s)' % (_sql.query_where_in(fname_mem_oid, oidsrnd), _get_where(shape_area_fld, area_thresh, thinness_thresh, where_clause))
                        _arcpy.management.SelectLayerByAttribute('lyrmem', 'NEW_SELECTION', where_clause=where_rand)
                        z = int(_arcpy.management.GetCount('lyrmem')[0])
                        if z == 0 and show_progress:
                            print('\nRandom slivers could not be selected. This is unexpected. *** Debug required ***. Exiting loop ...')
                            break

                        if show_progress: print('\nPicked %s slivers randomly to merge ...' % z)
                    else:
                        _arcpy.management.SelectLayerByAttribute('lyrmem', 'NEW_SELECTION', where_clause=where_stuck)
                    stuck = False

                # Get out of the loop, nothing more to do. We have no slivers, or the number of slivers hasn't changed since last iteration.
                # This condition can happen - see the eliminate tool documentation
                if counts[0] == 0:
                    print('\n *** No slivers found in %s. Nothing to do. ***' % source)
                    return 0

                if len(counts) > 1 and counts[-1] == counts[-2]:
                    if show_progress: print('\nLast two loops failed to remove any slivers. Exiting loop.')
                    break

                if counts[-1] == 0:
                    if show_progress: print('\nMerged all slivers. No more work to do. Exiting loop.')
                    break

                # Export the features to merge, if weve asked for that. But just do it the first time.
                if export_target_features and len(counts) == 1:
                    export_target_features = _path.normpath(export_target_features)
                    if show_progress: print('\nExporting slivers to %s ...' % export_target_features)

                    if overwrite:
                        _struct.Delete(export_target_features)

                    _struct.ExportFeatures('lyrmem', export_target_features)
                    if not dest: return 0

                if show_progress: print('\nExecuting Eliminate tool ... Counts: %s; stuck: %s; stuck_factor: %s' % (counts, stuck, stuck_factor))
                eliminated_mem = 'in_memory/%s' % _stringslib.get_random_string(from_=_string.ascii_lowercase)
                _arcpy.management.Eliminate('lyrmem', eliminated_mem, **kwargs)
                _struct.Delete(fname_mem)  # lets not run out of memory
                _struct.Delete('lyrmem')
                fname_mem = eliminated_mem

            _arcpy.env.workspace = _common.workspace_from_fname(dest)
            _arcpy.env.overwriteOutput = overwrite
            if show_progress: print('\nExporting from memory to %s' % dest)
            if not keep_thinness_in_dest: _struct.DeleteField(eliminated_mem, 'thinness')  # noqa
            _struct.ExportFeatures(eliminated_mem, dest)  # noqa

        finally:
            with _fuckit:
                _struct.Delete(fname_mem)  # noqa
                _struct.Delete(eliminated_mem)  # noqa
                _struct.Delete('lyrmem')  # noqa

        if len(counts) == 1: return counts[0]
        return sum(_more_itertools.difference(counts, func=lambda x, y: (x - y) * -1, initial=1))


    @staticmethod
    def intersect_not(in_feature: str, in_feature1: str, **kwargs) -> list[int]:
        """
        Check if any features in in_feature DO NOT intersect with in_feature1.

        Returning a list of features which ** DO NOT ** intersect any in_feature.

        Args:
            in_feature: first feature
            in_feature1: other feature

            **kwargs:
                keyword arguments passed to arcpy.analysis.Intersect
                See https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/intersect.htm

        Raises:
            TypeError: If the ResultsAsPandas output ResultsAsPandas.df was not an isntance of pandas.DataFrame. This is an unexpected result would require further investigation.

        Returns:
            List of OIDs for the features that DO NOT intersect with in_feature
            Returns an empty list, if all features intersected

        Notes:
            This uses the standard intersect, if performance is an issue, then
            a new function could be created using the pairwise intersect
            But pairwise intersect is not available under the standard license
        """
        in_feature = _path.normpath(in_feature)
        in_feature1 = _path.normpath(in_feature1)


        RAP = ResultAsPandas(_arcpy.analysis.Intersect,
                             in_features=[in_feature, in_feature1],
                             join_attributes='ONLY_FID', **kwargs)

        if isinstance(RAP.df, _pd.DataFrame):
            if len(RAP.df) == 0: return field_values(in_feature, _common.oid_field(in_feature))  # i.e. no intersects, so all in_features DO NOT intersect in_feature1
        else:
            raise TypeError('ResultsAsPandas had an empty results dataframe. This is unexpected')
        in_feat_oids = field_values(in_feature, _common.oid_field(in_feature))
        fid_col = 'fid_%s' % _path.basename(in_feature).lower()
        in_feat_intersect_oids = list(map(int, RAP.df_lower[fid_col].to_list()))
        return sorted(_baselib.list_not(in_feat_oids, in_feat_intersect_oids))


class Validation:
    """ Instantiable class which exposes multiple data validation checks.
    Some validation checks are paired with another layer. If no other layer is provided then
    some validation checks (e.g. field is uniqe) can still be called.

    Loads tables and feature classes into dataframes, optionally excluding shape files for efficiency

    Methods:

    Fields:
        fname: The original feature class name
        gdb: The geodatabase

        gx_df:
            An instance of self.df, exposed as a great expectations data instance.
            See the great-expectations documentation for list of expectations.
            See https://github.com/great-expectations/great_expectations/blob/develop/examples/notebooks/explore_titanic_data.ipynb for some examples
            And https://greatexpectations.io/expectations/?filterType=Backend%20support&gotoPage=1&showFilters=true&viewType=Summary for list of expectations


    Raises:
        errors.FeatureClassOrTableNotFound: If parent or child table or feature class does not exist

    Examples:

        Make use of great expectations via gx_df

        >>> Validation('C:/country.shp').gx_df.expect_column_values_to_be_in_set("Continent", ['Asia', 'Europe', ...])
            {
              "meta": {},
              "exception_info": {
                "raised_exception": false,
                "exception_traceback": null,
                "exception_message": null
              },
              "success": true,
              "result": {
                "element_count": 1313,
                "missing_count": 0,
                "missing_percent": 0.0,
                "unexpected_count": 0,
                "unexpected_percent": 0.0,
                "unexpected_percent_total": 0.0,
                "unexpected_percent_nonmissing": 0.0,
                "partial_unexpected_list": []
              }
            }

    """

    def __init__(self, parent: str, no_shapes: bool = False):
        self.fname = _path.normpath(parent)
        self.gdb = _common.gdb_from_fname(self.fname)
        self.fname_base = _path.basename(self.fname)
        if not _struct.Exists(self.fname):
            raise _errors.FeatureClassOrTableNotFound('Parent feature class or table "%s" not found.' % self.fname)

        exclude_cols = ('Shape',) if no_shapes else tuple()
        self.df: _pd.DataFrame = table_as_pandas2(self.fname, exclude_cols=exclude_cols, cols_lower=True)
        self.gx_df: _gx.dataset.PandasDataset = _gx.from_pandas(self.df)  # noqa

    def near(self, is_near_fnames: (str, list[str]), threshhold: (float, int), is_near_filters: (str, list[str], None) = None, keep_cols: (tuple[str], None) = None, thresh_error_test='>=', raise_exception: bool = False, show_progress: bool = False, **kwargs) -> (_pd.DataFrame, None):
        """
        Get

        Columns are case insensitive and all set to lower case in the resulting pandas dataframes.

        Can also be used for a "within" by setting an appropriate threshhold

        Args:

            is_near_fnames: Single feature class or list of feature classes containing near feature candidates

            threshhold:
                Threshhold distance, above which is considered as suspect, only results above threshold are returned.
                Distance is in planar units of "fname" feature class.
                This can be overridden by defining kwargs which are passed to arcpy.analyss.Near

            is_near_filters:
                Filter applied to is_near_fnames feature classes. The filter is applied via arcpy, hence the format is that used by ESRI feature layers.
                If multiple is_near_fnames are passed, but is_near_filters is a string or a length 1 iterable, then the filter is applied to all layers.
                This is really useful if, for example, we have a subset of sample sites for a given year that we wish to validate a dataset against


            thresh_error_test:
                Conditional statement text defining the threshhold boundary condition test.
                Examples include '==', '<=', '>'. If records match the test, this is the exception condition is met.
                The default is ">=", hence any record that is >= threshhold from any feature in in_near_names is an exception.

            keep_cols:
                List of cols to keep from fname.
                The output result cols  'NEAR_FID', 'NEAR_DIST', 'NEAR_FC' and the OID of fname are always retained

            raise_exception:
                If True, will raise an exception if any records above threshhold are found.
                This is useful for processing pipelines, where we want execution to halt if anything is suspect.

            show_progress: show progress

            kwargs:
                Keyword arguments passed to arcpy.analysis.Near.
                Supports search_radius, location, angle, method, field_names, distance_unit
                See https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/near.htm

        Raises:
            UserWarning: If raise_exception is True and suspect records (above threshhold distance) are found

        Returns:

            pandas.DataFrame:
                A dataframe of features in fname which are greater than threshold distance from is_near_fnames if there were exceptions

            None:
                If no exceptions were found
        """
        fname = self.fname
        if not thresh_error_test: thresh_error_test = '>='
        if isinstance(is_near_fnames, str): is_near_fnames = [is_near_fnames]
        is_near_fnames = [_path.normpath(s) for s in is_near_fnames]

        oid_fname = _common.get_id_col(fname)
        keep = [oid_fname]
        keep += ['NEAR_FID', 'NEAR_DIST', 'NEAR_FC']
        keep += keep_cols if isinstance(keep_cols, (list, tuple)) else []
        keep = list(set(keep))
        keep = list(map(str.lower, keep))

        if isinstance(is_near_filters, str):
            is_near_filters = [is_near_filters]

        if is_near_filters and len(is_near_filters) == 1 and len(is_near_fnames) > 1:
            is_near_filters = is_near_filters * len(is_near_fnames)

        is_near_fnames_tmp = []
        try:
            if is_near_filters:
                # This creates in memory layers filtered for the wheres
                if len(is_near_filters) != len(is_near_fnames):
                    raise ValueError('len(is_near_filters) != len(is_near_fnames)')

                is_near_fnames_tmp = [memory_lyr_get() for _ in is_near_fnames]
                for i, lyr in enumerate(is_near_fnames_tmp):
                    _arcpy.conversion.ExportFeatures(is_near_fnames[i], is_near_fnames_tmp[i], where_clause=is_near_filters[i])

                kwargs['near_features'] = is_near_fnames_tmp
            else:  # no filters, much easier!
                kwargs['near_features'] = is_near_fnames

            Nr = ResultAsPandas(_arcpy.analysis.Near, in_features=fname, **kwargs)

            Nr.df_lower: _pd.DataFrame  # noqa for pycharm autocomplete
            Nr.df_lower = Nr.df_lower[keep]

            Nr.df_lower.query('NEAR_DIST %s @threshhold' % thresh_error_test, inplace=True)
            if len(Nr.df_lower) > 0 and raise_exception:
                raise UserWarning('Layer %s had features outside of threshold distance condition "%s %s" with features %s' % (fname, thresh_error_test, threshhold, is_near_fnames))
        finally:
            with _fuckit:
                [_struct.Delete(s) for s in is_near_fnames_tmp]

        return Nr.df_lower if len(Nr.df_lower) > 0 else None

    def referential_integrity(self, parent_field, child, child_field, in_parent_only_is_error: bool = False, as_oids=False, raise_exception: bool = False) -> (dict[str:list], None):
        """
        Wrapper around key_info. Exposed here as key_info is primarily a data validation check.
        So more obvious here, but no need to refactor.

        Args:
            parent_field (str): The key field in the parent
            child (str): Child entity
            child_field (str): key field in the child
            in_parent_only_is_error: Consider a value in parent but not in child to be an exception.
            as_oids (bool): Get unique oids instead of distinct values

            raise_exception:
                If True, will raise an exception referential integrity is broken.
                This is useful for processing pipelines, where we want execution to halt if anything is suspect.

        Returns:

            dict[str:list]:
                dictionary key errors, with keys "parent_only" and "child_only" if key errors were found
                dict{'parent_only': [..], 'both': [..], 'child_only': [..]

            None: if no issues

        Notes:
            The OIDs can be used for futher processing ...


        Examples:


            Single line RI check

            >>> Validation('C:/my.shp').referential_integrity('cname', 'C:/my.gdb/towns', 'cname', in_parent_only_is_error=True)  # noqa
            {'parent_only': ['NoTownCountry',...], 'child_only': ['NoCountryTown',...]}
        """
        parent = self.fname
        res = key_info(parent, parent_field, child, child_field, as_oids)
        if raise_exception:
            if res['child_only']:
                raise UserWarning('Invalid foreign key values "%s" in "%s.%s"' % (res['child_only'], child, child_field))
            if in_parent_only_is_error and res['parent_only']:
                raise UserWarning('Primary key values "%s" in parent "%s.%s" were not in child "%s.%s"' % (res['parent_only'], parent, parent_field, child, child_field))

        out_dict = {}
        if res['child_only']:
            out_dict['child_only'] = res['child_only']

        if in_parent_only_is_error and res['parent_only']:
            out_dict['parent_only'] = res['parent_only']

        return out_dict if out_dict else None


    def intersects_all(self, in_feature: str, **kwargs) -> (list[int], None):
        """
        Check that no features in our layer are fully outside of in_feature.

        E.g. No polygons are outside of a square sample area.

        Args:
            in_feature: Feature to check against
            **kwargs: passed to arcpy.analysis.Intersect

        Returns:
            None: If there were no issues, i.e. all features in our layer (self.fname) intersected with at least one feature in fc in_feature
            list[int]: List of OIDs in self.fname that had no intersect with in_Feature


        Examples:

            Check passed, all lpis polygons lie within sample_squares

            >>> Validation('C:/my.gdb/lpis').intersects_all('C:/my.gdb/sample_squares')
            None

            Check failed, some lpis polygons are outside of our sample_squares

            >>> Validation('C:/my.gdb/lpis').intersects_all('C:/my.gdb/sample_squares')
            [12, 33, 55]
        """
        out = Spatial.intersect_not(self.fname, in_feature, **kwargs)
        if not out: return None
        return out  # noqa





def vertext_add(fname, vertex_index: (int, str), x_field: str, y_field: str = 'y', field_type='DOUBLE', where_clause: (str, None) = '*', fail_on_exists: bool = True,
                show_progress: bool = False) -> int:
    """
    Add the x and y coordinates of the row shape's first or last vertex (e.g. the origin of each square in a grid-like feature class for each grid cell)
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
rows_delete_where = del_rows_where  # noqa. For conveniance, should of been called this in first place but don't break existing code







if __name__ == '__main__':
    # quick debugging
    # Spatial.slivers_merge('C:/GIS/nfs_land_analysis_local.gdb/permissionable_by_land_sq', 'C:/GIS/nfs_land_analysis_local.gdb/permissionable_by_land_sq_sliverless',
    #                     area_thresh=50, thinness_thresh=0.1, thresh_operator=' OR ',
    #                    export_target_features=None,  # 'C:/GIS/nfs_land_analysis_local.gdb/slivers_temp'
    #                   max_iterations=100,
    #                  keep_thinness_in_dest=True,
    #                 overwrite=True, show_progress=True)

    # fname_tmp = r'C:\GIS\nfs_land_analysis_local.gdb\permissionable_by_land_union'
    # has_overlaps, fids_overlapping = Spatial.features_overlapping(fname_tmp)
    # Spatial.unionise_self_overlapping_clean(fname_tmp, r'C:\GIS\nfs_land_analysis_local.gdb\permissionable_by_land_union_cleaned', multi_part='SINGLE_PART', show_progress=True)
    pass
