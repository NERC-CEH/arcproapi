"""Mixins for all uses"""
import os.path as _path

import numpy as _np

import arcpy as _arcpy
import bs4 as _bs4

from funclite.baselib import classproperty as _classproperty

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
        array = _np.array(code_desc, dtype=[('code', 'S3'), ('value', 'S50')])
        table = 'in_memory/table'
        _arcpy.da.NumPyArrayToTable(array, table)
        # NB: You have to close and reopon any active client sessions before this appears as at ArcGISPro 3.0.1. Refreshing the geodb doesnt even work.
        _arcpy.management.TableToDomain(table, 'code', 'value', geodb, cls.domain_name, cls.domain_name, update_option=update_option)  # noqa

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
