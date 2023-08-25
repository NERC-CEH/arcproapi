"""Connection Handlers, largely arcpy driven

Connections have prerequisits:
Excel:https://pro.arcgis.com/en/pro-app/latest/help/data/excel/work-with-excel-in-arcgis-pro.htm


Currently these connection are read only and return datasets as pandas dataframes.
"""
import os.path as _path
import pathlib as _pathlib
from enum import Enum as _Enum

import pandas as _pd
import arcpy as _arcpy
import xlwings as _xlwings
import fuckit as _fuckit

import funclite.iolib as _iolib
from funclite.iolib import fixp as _fixp
import arcproapi.data as _data


class ESRICursorType(_Enum):
    SearchCursor = 1
    UpdateCursor = 2
    InsertCursor = 3
    PandasDataframe = 4


class EnumDataSourceType(_Enum):
    ESRIShapefile = 1
    ESRIGeoDBFeatureClass = 2
    ESRIGeoDBTable = 3

    MSSQLServerTable = 4
    MSSQLServerSpatialTable = 8

    SQLiteTable = 5

    OracleTable = 6
    OracleSpatialTable = 7


class OracleSDE:
    """ Define connections using an SDE file.
    Assumes that password and username have been persisted to the file (at least for the moment!).

    Generates a path to the feature/table that can be used like a fGDB path to a layer/table.

    Args:
        sde_file (str): The sde file
        layer_name (str): The layer name (prepended with dataset, if in dataset)
        schema (str): The schema, in Oracle SDE the schema is prepended to datasets and the layer name.
        If this is provided, then the schema will be prepended to create a refrence
        to the layer as a shortcut to typing out this details in full.

    Notes:
        normpaths arguments, as always.

    Examples:
        No schema
        >>> SDELyr = OracleSDE('C:/my.sde', 'MYSCHEMA.mydataset/MYSCHEMA.my_layer', schema='')
        >>> SDELyr.feature_path
        'C:\\my.sde\\MYSCHEMA.mydataset/MYSCHEMA.my_layer'

        We cant be arsed writing out the full path with the schama
        >>> SDELyr = OracleSDE('C:/my.sde', 'my_layer', schema='MYSCHEMA')
        >>> SDELyr.feature_path
        'C:\\my.sde\\MYSCHEMA.mydataset/MYSCHEMA.my_layer'

    TODO: Integrate into ESRISDE connections
    """
    def __init__(self, sde_file: str, layer_name: str, schema: str = ''):
        self._sde_file = _path.normpath(sde_file)
        self._layer_name = layer_name
        self._schema = schema

        if schema:
            bits = ['%s.%s' % (schema, s) for s in _pathlib.Path(self._layer_name).parts]
            self.feature_path = _fixp(self._sde_file, *bits)
        else:
            self.feature_path = _fixp(self._sde_file, self._layer_name)


class _BaseFileSource:
    """base class for file type sources"""

    def __init__(self, fname: str):
        self.fname = _path.normpath(fname)

    @property
    def file_parts(self):
        """()->str,str,str
        get file parts of source

        >>> _BaseFileSource.file_parts
        'c:/temp','myfile.gdb','.gdb'
        """
        return _iolib.get_file_parts2(self.fname)


class ConfigTextFile(_BaseFileSource):
    """Text file connections
    """


class ConfigESRIGeoDBTableOrFeatureClass(_BaseFileSource):
    """store for table and feature class database information

    Args:
        fname: path to the geodatabase, use config.GeoDatabasePaths
    """

    def __init__(self, fname):
        super(ConfigESRIGeoDBTableOrFeatureClass, self).__init__(fname)


class ConfigESRIShp(_BaseFileSource):
    """Config class for ESRI Shape Files"""

    def __init__(self, fname):
        super(ConfigESRIShp, self).__init__(fname)


class ConfigExcel(_BaseFileSource):
    """store for table and feature class database information

    Parameters
    workbook:
        path to the workbook, i.e. xlsx file
    table:
        table name
    worksheet, range
        worksheet and range name, optionally expand the range (e.g. range='A1', expand_cell_range='table')
    expand_cell_range:
        accepts values of 'table', 'vertical', 'horizontal', True
    visibile:
        boolean to show workbook, useful for debugging

    """

    def __init__(self, workbook: str, table: str = '', worksheet: str = '', range_: str = '', expand_cell_range: bool = None):
        if expand_cell_range == True:  # noqa
            expand_cell_range = 'table'
        self.expand_cell_range = expand_cell_range
        self.workbook = workbook
        self.table = table
        self.worksheet = worksheet
        self.range = range_
        super(ConfigExcel, self).__init__(self.workbook)


class Excel(_BaseFileSource):
    """Excel connection class
    Use xlwings to expose xlwings Workbook, worksheet and table objects
    Loads data into a pandas dataframe as Excel().df

    Use as a Context Manager.

    Instantiated with a connections.ConfigExcel instance.


    Additional arguments are passed to the xlwings Book class instantiator.
    See https://docs.xlwings.org/en/stable/api.html

    Args:
        fname: fully qualified filename
        table_name: name of table/listobject in spreadsheet
        worksheet: name of worksheet use for cell_range, ignored if table_name provided
        cell_range: range in worksheet to return
        expand_cell_range: try and expand the range specified in cell_range
        args: Additional named arguments to pass to the xlwings.Book class instantiator

    Notes:
        That table_name takes precedent over worksheet and cell_range.
        Workbooks need to be saved manually, the App closes without saving

    Examples:
        >>> Config = ConfigExcel('C:/workbook.xlsx', table_name='myTable')
        >>> with Excel(Config, read_only=True) as Obj:
        >>>     print(Obj.Table.rows.count)
        >>>     my_pandas_dataframe = Obj.df

        or
        >>> Ex = Excel(Config, read_only=True)
        >>> Ex.df
        >>> Ex.close()
    """

    def __init__(self, Config: ConfigExcel, visible=False, **args):
        self._Config = Config
        self._visible = visible
        self.Workbook = None  # type: [None, _xlwings.main.Book]
        self.Worksheet = None
        self.App = None  # type: [None, _xlwings.main.App]
        self.Table = None  # type: [None, _xlwings.main.Table]
        self.Range = None  # type: [None, _xlwings.main.Range]
        self._args = args
        self.df = None  # type: [None, _pd.DataFrame]
        self._loaded = False  # flag used in refresh, don't refresh the xlwings objs once loaded
        super(Excel, self).__init__(fname=Config.workbook)
        self.refresh()

    def __enter__(self):
        """enter"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """exit"""
        self.close()

    def refresh(self) -> None:
        """
        Refreshes the pandas dataframe.

        Notes:
            Excel objects are updated live as they are a direct link to the spreadsheet
        """
        if not self._loaded:
            self.App = _xlwings.App(visible=self._visible)
            self.Workbook = _xlwings.Book(self._Config.workbook, **self._args)

        if self._Config.table:
            if not self._loaded:
                self.Table = self._get_table(self._Config.table)
                self.Range = self.Table.range
            self.df = self.Table.range.options(_pd.DataFrame, header=1, index=False).value
        elif self._Config.worksheet:
            if not self._loaded:  # load range from worksheet
                self.Worksheet = self.Workbook.sheets(self._Config.worksheet)
                if self._Config.expand_cell_range in ['table', 'horizontal', 'vertical']:
                    self.Range = self.Workbook.sheets[self._Config.worksheet].range(self._Config.range).expand(self._Config.expand_cell_range)
                else:
                    self.Range = self.Workbook.sheets[self._Config.worksheet].range(self._Config.range)
            self.df = self.Workbook.sheets[self._Config.worksheet].range(self._Config.range).options(
                _pd.DataFrame, header=1, index=False, expand=self._Config.expand_cell_range).value
        else:
            raise ValueError('ExcelConfig had a blank table_name and worksheet')

        self._loaded = True

    def close(self, kill=True):
        """release resources"""
        with _fuckit:
            self.App.quit()
            if kill: self.App.kill()  # really close it if close didn't work

    def _get_table(self, table_name):
        """(str) -> xlwings:Table

        Get an xlwings table object from the table name
        """
        for sheet in self.Workbook.sheets:
            for tbl in sheet.tables:
                if tbl.name.lower() == table_name.lower():
                    return tbl
        return None


class TextFile:
    """TextFile connection class for standard text files

    Use as a Context Manager.

    reads text file into a pandas dataframe, which is set to TextFile().df

    Additional arguments are passed to a pandas.read_csv
    See https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html

    Examples:
        >>> with TextFile('C:/data.csv', delim='\t', header=('col1','col2')) as Obj:  # noqa
        >>>     my_pandas_dataframe = Obj.df
        >>>     print(Obj.df[1])
    """

    def __init__(self, fname, delim=',', header=0, **args):
        """(class:ConfigTextFile, args)->None

        args are passed to the panda's read_csv func call.
        """
        self._header = header
        self._delim = delim

        self.fname = _path.normpath(fname)
        self._args = args
        self.df = None  # type: [None, _pd.DataFrame]
        self.refresh()

    def __enter__(self):
        """enter"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """exit"""
        self.close()

    def refresh(self):
        """refresh data"""
        self.df = _pd.read_csv(self.fname, header=self._header, delimiter=self._delim, **self._args)

    def close(self):
        """close connection"""
        with _fuckit:
            del self.df  # not really necessary but stops pylint moaning


class _ESRIFile(_BaseFileSource):
    """Base class for ESRI file data sources, including layers in
    filesystem geodatabases and shapefiles

    Args:
        Config (str, ConfigESRIShp, ConfigESRIGeoDBTableOrFeatureClass, ConfigESRISDE) : An instance of a Config class in this module.
        Also accepts a string and just tries it!
        cursor_type: Type of cursor top open, currently only supports SearchCursor
        cols (tuple, list): List of cols to include in dataset
        exclude_cols (tuple, list): List of cols to exclude from dataset
        where_clause (str): Filter records returned with this where clause
        col_rename_func (any): A function to apply to the column names, defaults to str.lower

    Raies:
        ValueError: If incorrect class type passed to Config. Config should be an instance of [ConfigESRIShp, ConfigESRIGeoDBTableOrFeatureClass or ConfigESRISDE]

    Notes:
        Converts all column names to lower case. This is because ESRI geodatabases are not case sensitive to field names, but pandas
        is, which causes a hell of a lot of niggling issues. Pass col_rename_func = lambda x:x to override thie behaviour
    """

    def __init__(self, Config, cursor_type=ESRICursorType.SearchCursor, cols=(), exclude_cols=('Shape',), where_clause='', col_rename_func=str.lower, **kwargs):

        self.Config = Config  # type: [ConfigESRIShp, ConfigESRIGeoDBTableOrFeatureClass]

        if isinstance(Config, (ConfigESRIGeoDBTableOrFeatureClass, ConfigESRIShp)):
            self._fqn = Config.fname
        elif isinstance(Config, str):
            self._fqn = _path.normpath(Config)
        else:
            raise ValueError('Expected Config class instance of type ConfigESRIShp, ConfigESRIGeoDBTableOrFeatureClass or ConfigESRISDE')

        self._col_rename_func = col_rename_func

        self._cursor_type = cursor_type  # type: ESRICursorType
        self._where_clause = where_clause
        self._kwargs = kwargs
        self._exclude_cols = exclude_cols
        self.df = None  # type: [None, _pd.DataFrame]

        self.SearchCursor = None
        self.UpdateCursor = None
        self.InsertCursor = None

        if isinstance(cols, str):
            self._cols = (cols,)
        else:
            self._cols = cols

        super().__init__(self._fqn)
        self.refresh()

    def __enter__(self):
        """enter"""
        return self

    def refresh(self) -> None:
        """
        retrieve values with search cursor
        """
        # TODO Implement sort and support other cursors - See CRUD.py and ORM.py
        self.close()
        if self._cursor_type == ESRICursorType.SearchCursor:
            self.SearchCursor = _arcpy.da.SearchCursor(self._fqn, fields=self._cols, where_clause=self._where_clause, **self._kwargs)
        elif self._cursor_type == ESRICursorType.InsertCursor:
            raise NotImplementedError
        elif self._cursor_type == ESRICursorType.UpdateCursor:
            raise NotImplementedError
        elif self._cursor_type == ESRICursorType.PandasDataframe:
            # table_as_pandas errors on date types with nulls, hence replaced
            # self.df = _data.table_as_pandas(self._fqn, cols=self._cols, where=self._where_clause, **self._kwargs)
            self.df = _data.table_as_pandas2(self._fqn, cols=self._cols, exclude_cols=self._exclude_cols, where=self._where_clause, **self._kwargs)
            self.df.columns = list(map(self._col_rename_func, self.df.columns))
        else:
            raise NotImplementedError

    def __exit__(self, exc_type, exc_val, exc_tb):
        """exit"""
        self.close()

    def close(self):
        """close connections"""
        with _fuckit:
            del self.SearchCursor
            del self.UpdateCursor
            del self.InsertCursor

    def delete(self):
        """delete"""
        raise NotImplementedError


#  Note the inheritance here. Let the base class do the work
# But lets implent as two different classes to make it more
# obvious what being read when see it in code that is working
# with these connection types
class ESRIShp(_ESRIFile):  # noqa
    """
    Open layer
    See https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/searchcursor.htm

    Use pypika to generate complex where statements:
    https://github.com/kayak/pypika

    Args:
        cols: tuple/list of columns to include in the conncetion  # noqa  # noqa
        cursor_type: type of datasource to open. See the connections.ESRICursorType enumeration  # noqa
        args: passed to the relevant connection call, e.g. arcpy.da.SearchCursor  # noqa
    """


# See comment against ESRIShp
class ESRIGeoDBFeatureClassOrTable(_ESRIFile):  # noqa
    """Open geodatabase feature layer
    See https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/searchcursor.htm

    Use pypika to generate complex where statements:
    https://github.com/kayak/pypika


    Args:
        Config (connections.ConfigESRIGeoDBTableOrFeatureClass): Instance of ConfigESRIGeoDBTableOrFeatureClass  # noqa
        cols: tuple/list of columns to include in the connetion  # noqa
        cursor_type: type of datasource to open. See the connections.ESRICursorType enumeration  # noqa
        args: passed to the relevant connection call, e.g. arcpy.da.SearchCursor  # noqa
    """



class Oracle:
    """Oracle tables.

    An oracle connection, independent of ESRI enterprise geodb
    """

    def __init__(self):
        raise NotImplementedError
