"""Handle SQL Strings, for generating where clauses etc

Base classes from pypika are imported exposed here
See https://github.com/kayak/pypika
"""

#  from pypika import Query, Table, Schema

from arcproapi.common import columns_delim
from funclite.stringslib import get_between as _getb


def query_where_in(field_name: str, values: (tuple, str, list), datasource: str = '', override_field_delim: str = '', exclude_none: bool = False):
    """(str, iter, str) -> str
    build a simple where IN ( query

    Args:
        field_name (str): name of column to query
        values (tuple, str, list): iterable or single value to match
        datasource (str):
            path to datasource, passed to columns_delim to add delimited for field_name
            see https://desktop.arcgis.com/en/arcmap/10.3/analyze/arcpy-functions/addfielddelimiters.htm
        override_field_delim (str): override the field delim
        exclude_none (bool): Exclude None values from the where. The None value can cause an error to be raised when using the where for da.<Cursor>, with an error that misdirects you to think the columns are invalid.

    Raises:
        UserWarning: If values has no elements. This is because the query will be invalid, and debugging at this stage is easier

    Returns:
            str: the query string

    Notes:
        Consider using pypika for complex queries. https://github.com/kayak/pypika
        Field delims:
            file gdbs & shapefiles = "
            Personal gdbs = []
            ArcSDE = <No delimiters>

    Examples:
        >>> query_where_in('ID', (123,345), 'c:/temp/my.gdb')
        '"ID" IN (123, 345)'
    """
    if not values:
        raise UserWarning('No values passed to query_where_in. The query will be invalid.')

    if isinstance(values, str): values = [values]
    if exclude_none:
        values = [v for v in values if v is not None]

    def _f(v):
        if isinstance(v, str):
            return "'%s'" % v
        return str(v)

    # not currently used
    def _getdelim(v):
        if override_field_delim:
            return '%s%s%s' % (override_field_delim, v, override_field_delim)
        return columns_delim(field_name, datasource)

    if isinstance(values, (int, float, str)):
        values = (values,)

    lst = [_f(s) for s in values]

    sql = '%s IN (%s)' % (field_name, ','.join(lst))
    return sql


def query_where_not_in(field_name: str, values: (tuple, str, list), datasource: str = '', override_field_delim: str = '', exclude_none: bool = False):
    """(str, iter, str) -> str
    build a simple where NOT IN ( query

    Args:
        field_name (str): name of column to query
        values (tuple, str, list): iterable or single value to match
        datasource (str):
            path to datasource, passed to columns_delim to add delimited for field_name
            see https://desktop.arcgis.com/en/arcmap/10.3/analyze/arcpy-functions/addfielddelimiters.htm
        override_field_delim (str): override the field delim
        exclude_none (bool): Exclude None values from the where. The None value can cause an error to be raised when using the where for da.<Cursor>, with an error that misdirects you to think the columns are invalid.

    Returns:
            str: the query string

    Notes:
        Consider using pypika for complex queries. https://github.com/kayak/pypika
        Field delims:
            file gdbs & shapefiles = "
            Personal gdbs = []
            ArcSDE = <No delimiters>

    Examples:
        >>> query_where_in('ID', (123,345), 'c:/temp/my.gdb')
        '"ID" IN (123, 345)'
    """
    if isinstance(values, str): values = [values]
    if exclude_none:
        values = [v for v in values if v is not None]

    def _f(v):
        if isinstance(v, str):
            return "'%s'" % v
        return str(v)

    # not currently used
    def _getdelim(v):
        if override_field_delim:
            return '%s%s%s' % (override_field_delim, v, override_field_delim)
        return columns_delim(field_name, datasource)

    if isinstance(values, (int, float, str)):
        values = (values,)

    lst = [_f(s) for s in values]

    sql = '%s NOT IN (%s)' % (field_name, ','.join(lst))
    return sql


def strip_where(sql):
    """(str)->str
    Get everything after the where clause in a string
    May fail with multiple wheres

    Example:
    >>> strip_where("select * from tbl where cola=1")
    'cola=1'
    """
    sql += '|||||||'
    sql = _getb(sql, 'WHERE', '|||||||')
    return sql


def query_where_and(datasource: str = '', **kwargs) -> str:
    """ Generates an SQL WHERE matching the kwargs passed.

    Args:
        datasource (str): The datasource, can be shapefile path, or path to a database. Used to get the correct column delimiters. Uses current workspace if evaluates to False.
        kwargs: The keyword arguments from which to build the ANDed where.

    Returns:
        str: The query

    Examples:
        >>> query_where_and(a=1, b='here')
        'a=1 AND b="here"'
    """
    sql = list()
    if kwargs:
        sql.append(" 1=1 " + " AND ".join("%s = '%s'" % (columns_delim(k, datasource), v)
                                          for k, v in kwargs.items()))
    sql.append(";")
    return "".join(sql)


def is_not_null(fld: str) -> str:
    """
    More a memory aid for the syntax for now

    Args:
        fld (str): field to get as is not null

    Returns:
        definition query compatible is not null

    Examples:
        >>> is_not_null('CRN')
        'CRN IS NOT NULL'
    """
    return '%s IS NOT NULL' % fld


def is_null(fld: str) -> str:
    """
    More a memory aid for the syntax for now

    Args:
        fld (str): field to get as is not null

    Returns:
        definition query compatible is not null

    Examples:
        >>> is_null('CRN')
        'CRN IS NULL'
    """
    return '%s IS NULL' % fld


def str_starts_with(fld: str, starts_with: str) -> str:
    """
    fld  starts with

    Args:
        fld (str): field
        starts_with (str): what it starts with, e.g. 'A'

    Returns:
        str: the query
    """
    return "%s LIKE '%s%%'" % (fld, starts_with)


def str_not_start_with_digit(fld) -> str:
    """
    fld not start with digit
    
    Args:
        fld (str): field
        
    Returns:
        str: the query
    """
    s = "{0} NOT LIKE '0%' And {0} NOT LIKE '1%' And {0} NOT LIKE '2%' And {0} NOT LIKE '3%' And {0} NOT LIKE '4%' And {0} NOT LIKE '5%' And {0} NOT LIKE '6%' And {0} NOT LIKE '7%' And {0} NOT LIKE '8%' And {0} NOT LIKE '9%'".format(
        fld)
    return s
