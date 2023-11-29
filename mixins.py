"""Mixins for all uses"""
from warnings import warn as _warn
import os.path as _path
import string as _string

import numpy as _np
import fuckit as _fuckit
import dateutil as _dateutil

import arcpy as _arcpy
import bs4 as _bs4
import pandas as _pd
import xlwings as _xlwings

import arcproapi.conversion as conversion  # noqa - for convieniance

from funclite import pandaslib as pandaslib
import funclite.baselib as _baselib
from funclite.baselib import classproperty as _classproperty
import funclite.stringslib as _stringslib
import funclite.iolib as _iolib


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

    Class Properties and Class Members:
        code_description_dict:
            Define a dictionary to use to create code descriptions for coded values
            For example,

            @_classproperty
            def code_description_dict(cls) -> dict[str:str]:  # noqa
                return {cls.as_text(cls.A): 'The letter A', cls.as_text(cls.B): 'The letter B'}
    """
    domain_name = ''  # stop pycharm moaning

    @classmethod
    def domain_create(cls, geodb: str, update_option='REPLACE'):
        """
        Import as a domain into a geodatabase. Also see domain_create2.

        Args:
            geodb (str): The geodatabase
            update_option (str): Either 'APPEND' or 'REPLACE'. See https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/table-to-domain.htm

        Returns:
            None

        Notes:
            Only supports text field types. Use domain_create2 to autodetect text, integer, float and date values and create the domain accordingly.
        """
        _warn('domain_create2 should be used instead of domain_create. domain_create may be depreciated.', DeprecationWarning, stacklevel=2)
        try:
            x = cls.domain_name  # noqa
        except:
            raise NotImplementedError('Cannot create domain.\nClass does not define domain_name. Define this in the enumeration in enums.py.')

        geodb = _path.normpath(geodb)
        code_desc = [(v, v) for v in cls.text_values if v]

        isint = all([_baselib.is_int(x) for x in cls.text_values])
        isfloat = all([_baselib.is_float(x) for x in cls.text_values])

        sdef = 'S%s' % max([len(v) for v in map(str, _baselib.list_flatten(code_desc))])

        if isint:
            array = _np.array(code_desc, dtype=[('code', sdef), ('value', 'int32')])
        elif isfloat:
            array = _np.array(code_desc, dtype=[('code', sdef), ('value', 'float32')])
        else:
            array = _np.array(code_desc, dtype=[('code', sdef), ('value', sdef)])

        table = 'memory/%s' % _stringslib.rndstr(from_=_string.ascii_lowercase)
        try:
            _arcpy.da.NumPyArrayToTable(array, table)
            # NB: You have to close and reopon any active client sessions before this appears as at ArcGISPro 3.0.1. Refreshing the geodb doesnt even work.
            _arcpy.management.TableToDomain(table, 'code', 'value', geodb, cls.domain_name, cls.domain_name, update_option=update_option)  # noqa
        finally:
            with _fuckit:
                _arcpy.management.Delete(table)

    @classmethod
    def domain_create2(cls, geodb: str, **kwargs) -> None:
        """
        Create the enum as a coded domain in the geodatabase gdb
        Range domains not yet supported.

        This is an enhancemoent over domain_create as it autodetects the field type. domain_create add as 'TEXT' field type.

        Args:
            geodb (str): The geodatabase

            kwargs:
                Passed to arcpy.management.CreateDomain.
                See https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/create-domain.htm#

        Returns:
            None

        Notes:
            Will undoubtedly error if the domain is assigned to a field.
            Integer types have field type arcpy LONG, float types are set to arcpy FLOAT.
            Code will need revising if these types are of insufficient size.
            See https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/create-domain.htm
        """
        try:
            x = cls.domain_name  # noqa
        except:
            raise NotImplementedError('Cannot create domain.\nClass does not define domain_name. Define this for the relevant class in enums.py.')

        geodb = _path.normpath(geodb)
        isint = all([_baselib.is_int(x) for x in cls.text_values_for_domain])
        isfloat = all([_baselib.is_float(x) for x in cls.text_values_for_domain])
        isdate = all([_baselib.is_date(x) for x in cls.text_values_for_domain])

        if isint:
            vals = map(int, [x for x in cls.text_values_for_domain])
            ft = 'LONG'
        elif isfloat:
            vals = map(float, [x for x in cls.text_values_for_domain])
            ft = 'FLOAT'
        elif isdate:
            vals = map(_dateutil.parser.parse, [x for x in cls.text_values_for_domain])  # noqa
            ft = 'DATE'
        else:
            vals = map(str, [x for x in cls.text_values_for_domain])
            ft = 'TEXT'

        if not vals: return

        with _fuckit:
            _arcpy.management.DeleteDomain(geodb, cls.domain_name)
        # domain description is at the domain level and NOT the values for the domain - they are set in the for v in vals loop below
        _arcpy.management.CreateDomain(geodb, domain_name=cls.domain_name,
                                       domain_description=kwargs['domain_description'] if kwargs.get('domain_description', None) else cls.domain_name,
                                       field_type=ft, domain_type='CODED')

        for v in vals:
            _arcpy.management.AddCodedValueToDomain(geodb, cls.domain_name, v, cls.code_description_dict.get(v, v))


    @classmethod
    def domain_assign(cls, fname: str, flds: (str, list[str]), error_on_failure: bool = True) -> dict[str:list[str]]:
        """
        Assign a domain.
        Now creates the domain in the workspace if it does not already exist.

        This call can be a little slow because it first checks if the domain exists in the gdb

        Returns:
               dict[str:list[str]]: A dictionary of successes and failues {'success':[...], 'fail':[...]}
               Dont let the colon in the return lists confuse you - it isnt a dict of dicts but a dict of lists.

        Examples:

            Assign domain to a single field in layer

            >>> MixinEnumHelper.domain_assign('C:/my.gdb/lyr', 'country')
            {'success': ['EnumMyDomainEnum:country'], 'fail':[]}

            Couple of fields (yes a bit odd, but not impossible)

            >>> MixinEnumHelper.domain_assign('C:/my.gdb/lyr', ['country_asia', 'country_europe'])
            {'success': 'EnumMyDomainEnum:country_asia', 'EnumMyDomainEnum:country_europe', 'fail': []}
        """

        # first try and create the domain if it does not exist
        from arcproapi.common import gdb_from_fname as _get_gdb  # dont risk circular import
        from arcproapi.structure import gdb_domain_exists as _chkdom
        if isinstance(flds, str): flds = [flds]
        gdb = _get_gdb(fname)
        if not _chkdom(gdb, cls.domain_name): # noqa
            cls.domain_create2(gdb)  # noqa
        from arcproapi.structure import domains_assign  # import here, otherwise get circular import reference
        return domains_assign(fname, {cls.domain_name: flds}, error_on_failure=error_on_failure)


    @_classproperty
    def text_values(cls) -> list[str]:  # noqa
        """
        Get a list of all the as_text values.
        The list is ordered before being returned.

        Returns:
            list[str]: List of all text values, as retrieved from as_text()
        """
        lst = [cls.as_text(e) for e in cls if cls.as_text(e) is not None]  # noqa
        lst.sort()
        return lst  # noqa


    @_classproperty
    def text_values_for_domain(cls) -> list[str]:  # noqa
        """
        Get a list of all the as_text values, excluding Nones as empty strings.
        The list is ordered before being returned.

        Returns:
            list[str]: List of all text values, as retrieved from as_text()

        Notes:
            Domain values cannot be created from Nones and empty strings, hence this property is provided.
        """
        lst = [cls.as_text(e) for e in cls if  cls.as_text(e) not in (None, '')]  # noqa
        lst.sort()
        return lst  # noqa


    @_classproperty
    def code_description_dict(cls) -> dict[str:str]:  # noqa
        """
        Get default code descriptions. Where more verbose code descriptions are required for self-documentation
        overwrite this method in the inheriting class.

        The should return a dictionary where the key is the domain code and the dict value for the key is the description.


        Returns:
            dict[str:str]:
                The text values with the description of the value, this default method simply returns all values with the values also as descriptions,
                 with the intent of overriding this method in inheriting classes to allow for a mechanis to provide implicit lookup metadata descriptions.

        Notes:
            It constructs the dictionary purely from the cls.text_values_for_domain class property

        Examples:

            overridden code_description_dict providing custom descriptions, then write as a domain to a geodatabase.
            Note that the chainging of classmethod and class property will be depreciated in Python 3.11.
            You can use the alternative decorator .... >>> from funclite.baselib import classproperty

            >>> class MyDomain(MixinEnumHelper):
            >>>    blue = 0: red = 1
            >>>    @classmethod
            >>>    @property
            >>>    def code_description_dict(cls): return {'blue':'the colour blue', 'red': 'the color red'}  # noqa
            >>> MyDomain.domain_create2('c:/my.gdb')
        """
        return {v: v for v in cls.text_values_for_domain}


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
    def __init__(self, *args, **kwargs):
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

        return pandaslib.GroupBy(self.df_lower, groupflds=groupflds, valueflds=valueflds, *funcs, **kwargs).result  # noqa


    def export(self, fname_xlsx: str, silent: bool = False, **kwargs) -> str:
        """
        Handles exporting <instance>.df to an excel file. This should be sufficient in
        most instances, but you can ofcourse override if needed.

        Importantly, it also handles creating a backup if the file already exists in subfolder "_archive" which is created if it does not exist

        Args:
            fname_xlsx (str): Excel file name, include the extension!
            silent (bool): Suppress console status messages
            kwargs: keyword args to pass to pandas.DataFrame.to_excel

        Raises:
            NotImplementedError: If df is not an instance of pandas.DataFrame
            ValueError: If extension to fname is not .xlsx

        Returns:
            str: The backup file name

        Notes:
            Works with a copy of the dataframe, whether or not it is passed as an argument, or a property of cls.df

        Examples:

            ResultsAsPandas inherits this mixin, this is an example of using this mixins export method

            >>> from arcproapi.data import ResultsAsPandas; import arcpy
            >>> ResultsAsPandas(arcpy.analysis.Clip, 'C:/my.shp', 'C:/clip.shp').export('c:/my_results.xlsx')  # noqa
            'C:/temp/archive/my/2023-03-21 1233_my.xlsx'
        """
        df_target = None  # noqa
        if isinstance(self.df, _pd.DataFrame):  # noqa
            df_target = self.df.copy()  # noqa
        else:
            raise NotImplementedError('The inheriting class does not appear to support "df" as a pandas DataFrame.\nPerhaps the instance has not been fully initialised?')
        df_target: _pd.DataFrame  # noqa autocomplete please

        fname_xlsx = _path.normpath(fname_xlsx)
        root, bn, ext = _iolib.get_file_parts2(fname_xlsx)
        bn_noext = _iolib.get_file_parts(fname_xlsx)[1]
        if ext.lower() != '.xlsx':
            raise ValueError('arg "fname" should have file extension .xlsx')

        archive = _iolib.fix(root, '_archive/%s' % bn_noext, mkdir=True)
        out = ''
        if _iolib.file_exists(fname_xlsx):
            out = _iolib.fixp(archive, '%s_%s' % (_iolib.pretty_date(_iolib.file_modification_date(fname_xlsx), with_time=True, time_sep=''), bn))
            _iolib.file_copy(fname_xlsx,
                             out,
                             dest_is_folder=False
                             )
            if not silent: print('Backed up file %s to %s before exporting current dataframe.' % (fname_xlsx, out))

        _iolib.file_delete(fname_xlsx)

        df_target.to_excel(fname_xlsx, **kwargs)
        if not silent: print('Exported dataframe to %s' % fname_xlsx)

        return out


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
        from arcproapi.structure import fc_fields_get  # import here, otherwise get circular import err
        return fc_fields_get(self.fname_output, as_objs=as_objs)  # noqa

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
            Assumed that layers have BNG spatial reference, hence Shape_Area is square meters.
            If this is not the case, then use a custom conversion function, otherwise the returned area will be wrong.
            Note that mixins exposes the conversion module, which provides other conversion functions

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
