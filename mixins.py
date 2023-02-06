"""Mixins for all uses"""
import os.path as _path
import arcpy as _arcpy
import bs4 as _bs4


class MetadataBaseInfo:
    """ Get metadata given a layer name, returning it as a string
    Or get as a metadata object for further manipulation and querying

    Examples:
        >>> class MyClass(MetadataBaseInfo):
        >>>     pass
        >>> MC = MyClass()
        >>> MC.metadata('C:/my.gdb/lyr')
        'This is the description and summary for layer lyr'
        >>> M = MC.metadata('C:/my.gdb/lyr', as_obj=True)
        >>> M.summary = 'My Summary'
        >>> M.save()
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





def _strip_html(s:str) -> str:
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