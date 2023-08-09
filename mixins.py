"""Mixins for all uses"""
import os.path as _path
import string

import numpy as _np
import fuckit as _fuckit

import arcpy as _arcpy
import bs4 as _bs4
import pandas as _pd
import xlwings as _xlwings

from arcproapi import structure as _struct, conversion as conversion

from funclite import pandaslib as pandaslib
import funclite.baselib as _baselib
from funclite.baselib import classproperty as _classproperty
import funclite.stringslib as _stringslib

import arcproapi.conversion as conversion  # noqa

class MetadataBaseInfo:
    """ Get metadata given a layer name, returning it as a string
    Or get as a metadata object for further manipulation and querying

    Examples:
        # Instantiate a class, which inherits from this mixin
        >>> class MyClass(MetadataBaseInfo):
        >>>     pass
        >>> MC = MyClass()
        # Call the static metadata method on class instance of MC of MyClass
        >>> MC.metadata('C:/my.gdb/lyr')
        'This is the description and summary for layer lyr'
        >>> M = MC.metadata('C:/my.gdb/lyr', as_obj=True)
        >>> M.summary = 'My Summary'
        >>> M.save()  # noqa
    """

    @staticmethod
    def metadata(fname: str, as_obj: bool = False, return_on_error: str = '') -> (str, _arcpy.metadata.Metadata):  # noqa
        """
        Get a  cleaned concatenation of the layers summary and description metadata
        Or the class instance of Metadata for the layer.

        Args:
            fname (str): Layer or table
            as_obj (bool): If true returns the actual metadata instance for the layer, else just returns the string
            return_on_error (str): Return this on error.

        Returns:
            str: A cleaned concatenation of the layers summary and description metadata
            arcpy.metadata.Metadata: Class instance for fname, if as_obj is True

        Examples:
            >>> MetadataBaseInfo.metadata('C:/my.gdb/lyr')
            'This is the description and summary for layer lyr'

        Notes:
            All errors are suppressed, if an error occurs and empty string is returned.
        """
        try:
            fname = _path.normpath(fname)
            if as_obj:
                return _arcpy.metadata.Metadata(fname)  # noqa
            else:
                with _arcpy.metadata.Metadata(fname) as M:
                    return '%s\n\n%s' % (M.summary, _strip_html(M.description))
        except:  # lets not fall in a heap if we bug out, this is just a convieniance function
            return return_on_error


class MixinEnumHelper:
    """
    Mixin property for enums declared in this module.
    Primarily to retreive a list of the texts retreived from as_text
    which is written to backend spatial dbs.

    Inheriting class should implement method as_text

    Methods:
        text_values list[str]: List of all text values, as retrieved from as_text()
        names list[str]: List of all member names, as retrieved from member.name
    """

    @classmethod
    def domain_create(cls, geodb: str, update_option='REPLACE'):
        """
        Import as a domain into a geodatabase

        Args:
            geodb (str): The geodatabase
            update_option (str): Either 'APPEND' or 'REPLACE'. See https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/table-to-domain.htm

        Returns:

        """
        try:
            x = cls.domain_name  # noqa
        except:
            raise NotImplementedError('Cannot create domain.\nClass does not define domain_name. Define this in the enumeration in enums.py.')

        geodb = _path.normpath(geodb)
        code_desc = [(v, v) for v in cls.text_values]
        sdef = 'S%s' % max([len(v) for v in _baselib.list_flatten(code_desc)])
        array = _np.array(code_desc, dtype=[('code', sdef), ('value', sdef)])

        table = 'memory/%s' % _stringslib.rndstr(from_=string.ascii_lowercase)
        try:
            _arcpy.da.NumPyArrayToTable(array, table)
            # NB: You have to close and reopon any active client sessions before this appears as at ArcGISPro 3.0.1. Refreshing the geodb doesnt even work.
            _arcpy.management.TableToDomain(table, 'code', 'value', geodb, cls.domain_name, cls.domain_name, update_option=update_option)  # noqa
        finally:
            with _fuckit:
                _arcpy.management.Delete(table)

    @_classproperty
    def text_values(cls) -> list[str]:  # noqa
        """
        Get a list of all the as_text values.
        The list is ordered before being returned.

        Returns:
            list[str]: List of all text values, as retrieved from as_text()
        """
        lst = [cls.as_text(e) for e in cls]  # noqa
        lst.sort()
        return lst  # noqa

    @_classproperty
    def names(cls) -> list[str]:  # noqa
        """
        Get list of enum member names

        Returns:
            list[str]: List of all member names, as retrieved from member.name

        Examples:
            >>> from enum import Enum
            >>> class EnumSurveyType(Enum, MixinEnumHelper): a=1;b=2  # noqa
            >>> EnumSurveyType.names
            ['birds', 'botany', ...]
        """
        return [e.name for e in cls]  # noqa

    @staticmethod
    def as_text(enum) -> (str, None):
        """
        Default behaviour, override as necessary in inheriting classes.

        Args:
            enum: Class member enum

        Returns:
            str: the class member.name
            None: If any error occurs, e.g. if enum does not support the .name property
        """
        try:
            return enum.name
        except:
            pass
        return None  # noqa


class MixinPandasHelper:
    """Provides several quality of life functions when we have a class instance
    that exposes its underlying table or feature class as a pandas dataframe.

    The inheriting class must support the following properties which return a pandas dataframe:
        <instance>.df and <instance>.df_lower

    For an rather complicated example of use, see data.ResultsAsPandas.
    """

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

        return pandaslib.GroupBy(self.df_lower, groupflds=groupflds, valueflds=valueflds, *funcs, **kwargs).result  # noqa

    def view(self) -> None:
        """Open self.df in excel"""
        _xlwings.view(self.df)  # noqa

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
        lst = self.df_lower.query(expr=where, **kwargs)['shape_area'].to_list()  # noqa
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
            return len(self.df_lower.query(expr=query, **kwargs))  # noqa
        return len(self.df_lower)  # noqa

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

        lst = self.df_lower.query(expr=where, **kwargs)['shape_length'].to_list()  # noqa
        if lst:
            return conv_func(sum(lst))
        return 0





# region local helper funcs
def _strip_html(s: str) -> str:
    """
    Strip html, returning only the text
    Args:
        s (str): the string

    Returns:
        str: the cleaned string
    """
    # https://stackoverflow.com/questions/328356/extracting-text-from-html-file-using-python
    if not s: return ''
    return ' '.join(_bs4.BeautifulSoup(s, "html.parser").stripped_strings)
# endregion
