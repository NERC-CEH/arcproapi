"""
Retrieve informtion about databases.

Largely returns pandas dataframes which can be viewed with xlwings.view(dataframe).

Also see arcproapi.structure, which has several functions which retrieve info about
feature classes and tables. This module is intended for the big standalone summary stuff.

Structure on-the-other-hand, has many methods which are consumed directly by other library functions
"""

import os.path as _path  # noqa

import arcpy as _arcpy
from arcpy.da import Describe  # noqa this is the dict version of Describe

import pandas as _pd
import fuckit as _fuckit

import funclite.iolib as _iolib
import funclite.baselib as _baselib

import arcproapi.structure as _struct
from arcproapi.structure import fcs_field_sym_diff as fc_field_sym_diff  # noqa - expose here as well - makes sense
from arcproapi.structure import fcs_schema_compare as fc_schema_compare  # noqa - expose here as well - makes sense
from arcproapi.structure import gdb_find_cols, FieldsDescribe  # noqa - as above

import arcproapi.data as _data
from arcproapi.data import key_info  # noqa - expose here as well - makes sense

import arcproapi.environ as _environ
import arcproapi.errors as _errors
import arcproapi.decs as _arcdecs


@_arcdecs.environ_persist
def domain_usage(db_: str) -> (_pd.DataFrame, None):
    """
    Get a list of domain usage across a geodatabase

    Args:
        db_ (str): Path to the geodatabase, should support enterprise and fGDBs

    Returns:
        Pandas.DataFrame: Pandas dataframe
        None: If there are no domains in db_

    Credit:
        Adapted from https://gis.stackexchange.com/a/413675/197165

    Examples:
        >>> domain_usage('C:/my.gdb')
        feature_class   domain  field_name
                   fc  domain1      field1

    """
    # TODO: DEBUG/TEST domain_usage
    db_ = _path.normpath(db_)
    _arcpy.env.workspace = db_
    domains = _arcpy.da.ListDomains(db_)
    if not domains: return None

    datasets = _arcpy.ListDatasets(feature_type='Feature')

    out = _baselib.DictList()

    for domain in domains:
        for fd in datasets:
            # get the feature classes
            fcs = _arcpy.ListFeatureClasses(feature_dataset=fd)
            for fc in fcs:
                fields = _arcpy.ListFields(fc)
                for field in fields:
                    if field.domain == domain:
                        out['feature_class'] = fc
                        out['domain'] = domain
                        out['field_name'] = field.name
    return _pd.DataFrame(out)


def gdb_row_counts(gdb: str, save_to: (str, None) = None, overwrite_xlsx: bool = False, match: (str, list) = '*', where: (str, None) = None) -> _pd.DataFrame:  # noqa
    """
    Get row counts for all feature classes and tables in a geodatabase.
    Also see gdb_dump_struct.

    Args:
        gdb (str): Path to geodatabase
        save_to (str, None): dump to this excel file if provided. Is normpathed.
        overwrite_xlsx (bool): Overwrite the file given in save_to
        match (str, list, tuple): match names on this, matches all with the default, '*'
        where (str): throw this where into the data.get_row_count2 query

    Returns:
        pandas.DataFrame

    Notes:
        Coded against file geodatabases, should work with other geodatabases, but untested.
        \n
        The where is passed to get_row_count2, against all tables/feature classes that are matched,
        hence it is highly likely to raise an error unless you know what you are querying!
        I possible use is to reduce query time in finding empty tables, by limiting on OBJECTID.
        gdb_dump_struct omits row counts, hence is quicker

    Examples:
        >>> gdb = r'C:\my.gdb'  # noqa
        >>> gdb_row_counts(gdb, match='__ATT')
        full_name           base_name       type                shape_type  row_cnt
        C:/my.gdb/my_ATTACH my_ATTACH       table               n/a         3
        C:/my.gdb/ATTFC     ATTFC           feature class       polygon     10
        ...
    """
    if isinstance(match, str):
        match = [match]

    fcs, tbls = _struct.gdb_tables_and_fcs_list(gdb, full_path=True)

    filt = lambda s: True if not match else _baselib.list_member_in_str(_iolib.get_file_parts2(s)[1], match)
    if not match == ['*']:
        fcs = [s for s in fcs if filt(s)]
        tbls = [s for s in tbls if filt(s)]
    fcs_tbls = fcs + tbls

    dic = {'full_name': [s for s in fcs_tbls]}  # noqa
    dic['base_name'] = [_path.basename(s) for s in fcs_tbls]
    dic['type'] = ['feature class'] * len(fcs) + ['table'] * len(tbls)
    dic['shape_type'] = [_struct.Describe(s)['shapeType'] for s in fcs] + ['n/a'] * len(tbls)  # noqa
    dic['row_cnt'] = [_data.get_row_count2(s, where=where) for s in fcs_tbls]
    df = _pd.DataFrame(data=dic)
    if save_to: _save_to(df, save_to, overwrite_xlsx)
    return df


def gdb_dump_tables_and_fcs(gdb: str, save_to: (str, None) = None,
                            overwrite_xlsx: bool = False) -> _pd.DataFrame:  # noqa
    """
    Write out the tables and feature classes of a gdb to excel

    Performs quicker than gdb_row_counts.

    Args:
        gdb (str): the geodatabase, set the environment.
        save_to (str, None): dump to this excel file if provided. Is normpathed.
        overwrite_xlsx (bool): Overwrite the file given in save_to

    Returns:
        pandas.DataFrame: A pandas datafrome of the fcs/tables

    Raises:
        FileExistsError: If save_to is given and the file exists, but overwrite_xlsx is False

    Notes:
        *** This sets the arcpy workspace ***
        All filters are case insensitive

    Examples:
        >>> df_out = gdb_dump_tables_and_fcs('C:/my.gdb', 'C:/struct.xlsx')
    """
    gdb = _path.normpath(gdb)

    out = {'fullname': [],
           'name': [],
           'type': []}

    fcs, tbls = _struct.gdb_tables_and_fcs_list(gdb)

    def _add_fld(fullname: str, name: str, type_: str):
        out['fullname'] += [fullname]
        out['name'] += [name]
        out['type'] += [type_]

    for fc in fcs:
        _add_fld(_iolib.fixp(gdb, fc), fc, 'feature class')

    for tbl in tbls:
        _add_fld(_iolib.fixp(gdb, tbl), tbl, 'table')
    df = _pd.DataFrame(out)
    if save_to: _save_to(df, save_to, overwrite_xlsx)
    return df


@_arcdecs.environ_persist
def gdb_dump_struct(gdb: str, save_to: (str, None) = None,
                    layer_match: (str, list, None) = None, field_match: (str, list, None) = None,
                    field_type_match: (str, list, None) = None,
                    overwrite_xlsx: bool = False,
                    show_progress: bool = True) -> _pd.DataFrame:  # noqa
    """
    Write the struture of a gdb
    May also work with SDE connection, but untested.

    Args:
        gdb (str): the geodatabase, set the environment.
        save_to (str, None): dump to this excel file if provided. Is normpathed.
        layer_match (str, None, list): Case insensitive wildcard match on layer name
        field_match (str, None, list): Case insensitive wildcard match on field name

        field_type_match (str, None, list): Case insensitive wildcard match on field type.
        \nCommon ones are: 'string', 'single', 'smallinteger', 'integer', 'guid', 'double', 'globalid', 'geometry.
        \nSee https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/field.htm

        overwrite_xlsx (bool): Overwrite the file given in save_to
        show_progress (bool): Print progress messages to the console.

    Returns:
        pandas.DataFrame: A pandas datafrome of the structure

    Raises:
        FileExistsError: If save_to is given and the file exists, but overwrite_xlsx is False

    Notes:
        All filters are case insensitive

    Examples:
        Print all layers matching "*count*" (e.g. country, county), of field type "*int*" with name matching "*popula*" or "*people_*"
        >>> df_out = gdb_dump_struct('C:/my.gdb', 'C:/struct.xlsx', 'count', ['popula', 'people_'], 'int')
    """
    gdb = _path.normpath(gdb)

    if show_progress:
        print('Setting arcpy workspace to %s' % gdb)

    _environ.workspace_set(gdb)

    out = {'fullname': [],
           'name': [],
           'type': [],
           'fld': [],
           'alias': [],
           'fld_type': [],
           'length': [],
           'nullable': [],
           }

    if isinstance(layer_match, str):
        layer_match = [layer_match]
    if isinstance(field_match, str):
        field_match = [field_match]
    if isinstance(field_type_match, str):
        field_type_match = [field_type_match]

    def _add_fld(fullname: str, name: str, type_: str, fld: _arcpy.Field):  # noqa
        out['fullname'].append(fullname)
        out['name'].append(name)
        out['type'].append(type_)
        out['fld'].append(fld.name)
        out['alias'].append(fld.aliasName)
        out['fld_type'].append(str(fld.type))
        out['length'].append(str(fld.length))
        out['nullable'].append(str(fld.isNullable))

    if show_progress:
        print('Scanning geodatabase for tables and feature classes...')
    fcs, tbls = _struct.gdb_tables_and_fcs_list(gdb)

    if show_progress:
        PP = _iolib.PrintProgress(iter_=fcs + tbls, init_msg='Reading feature classes and tables...')

    for fc in fcs:
        if layer_match and not _baselib.list_member_in_str(fc, layer_match, ignore_case=True):
            continue

        for fld in _struct.fields_get(fc, as_objs=True):
            if field_match and not _baselib.list_member_in_str(fld.name, field_match, ignore_case=True):
                continue

            if field_type_match and not _baselib.list_member_in_str(str(fld.type), field_type_match, ignore_case=True):
                continue

            _add_fld(_iolib.fixp(gdb, fc), fc, 'feature class', fld)

        if show_progress:
            PP.increment()  # noqa

    for tbl in tbls:
        if layer_match and not _baselib.list_member_in_str(tbl, layer_match, ignore_case=True):
            continue

        for fld in _struct.fields_get(tbl, as_objs=True):
            if field_match and not _baselib.list_member_in_str(fld.name, field_match, ignore_case=True):
                continue

            if field_type_match and not _baselib.list_member_in_str(str(fld.type), field_type_match, ignore_case=True):
                continue

            _add_fld(_iolib.fixp(gdb, tbl), tbl, 'table', fld)

        if show_progress:
            PP.increment()  # noqa

    df = _pd.DataFrame(out)
    if save_to: _save_to(df, save_to, overwrite_xlsx)
    return df


def sde_fname_struct_as_dict(file_path: str) -> dict:
    """
    Return a dict describing a sde feature class or table details and structure.

    Args:
        file_path (str): Input database file path to read.

    Returns:
        sde_dict (dict): Attributes for the input file, which vary by file type.

    TODO: Debug sde_fname_struct_as_dict
    """

    file_path = _path.normpath(file_path)
    sde_dict = {'file_path': file_path}
    desc = _arcpy.Describe(file_path)

    # Retrieve various describe attributes, path, type, fields etc.
    if desc.catalogPath.split('\\')[-2][-4:] == ".sde":
        sde_dict['path'] = "Root of the GMEP SDE Database"
    else:
        sde_dict['path'] = desc.catalogPath.split('\\')[-2]

    dtype = desc.dataType
    sde_dict['type'] = dtype
    sde_dict['name'] = desc.basename.split('.')[-1]
    sde_dict['owner'] = desc.basename.split('.')[0]
    sde_dict['sde_name'] = desc.basename

    # If file is a feature or table, retrieve  field details and row count.
    if dtype == "FeatureClass" or dtype == "Table":
        sde_dict['oid_field'] = desc.OIDFieldName
        fields = desc.fields
        sde_dict['field_details'] = [[f.name, f.type, f.length] for f in fields]
        _arcpy.MakeTableView_management(sde_dict['file_path'], "Temp")
        sde_dict['count'] = int(_arcpy.GetCount_management("Temp").getOutput(0))
        _arcpy.Delete_management("Temp")

    # If file is a feature or raster, get spatial reference information.
    if dtype == "FeatureClass" or dtype == "RasterDataset":
        e = desc.extent
        sde_dict['projection'] = e.spatialReference.name
        sde_dict['extent'] = [[e.YMin, e.XMin], [e.YMin, e.XMax],
                              [e.YMax, e.XMax], [e.YMin, e.XMax]]

    # If file is a feature, get geometry information.
    if dtype == "FeatureClass":
        sde_dict['feature_type'] = desc.shapeType
        sde_dict['shape_field'] = desc.shapeFieldName

    # If file is a raster, attempt to get metadata.
    elif dtype == "RasterDataset":
        bands = desc.bandCount
        if bands > 1:
            raise _errors.InfoMultiBandRasterNotSupported(_errors.InfoMultiBandRasterNotSupported.__doc__)
        else:
            sde_dict['cell_size'] = (desc.meanCellWidth, desc.meanCellHeight)
            sde_dict['field_details'] = [desc.tableType, desc.pixelType]
            sde_dict['raster_size'] = (desc.width, desc.height)
            sde_dict['count'] = (sde_dict['raster_size'][0] *
                                 sde_dict['raster_size'][1])
    return sde_dict






# region helper methods
def _save_to(df: _pd.DataFrame, dest: str, overwrite_xlsx: bool = False, show_progress: bool = True) -> None:
    """
    Internal helper method
    Args:
        df: the dataframe
        dest: place to save
        overwrite_xlsx: allow overwrite

    Returns: None
    """
    save_to = _path.normpath(dest)
    if overwrite_xlsx:
        _iolib.file_delete(save_to)
    df.to_excel(save_to)
    if show_progress:
        print('Saving to excel file %s' % save_to)
# endregion





if __name__ == '__main__':
    with _fuckit:
        import xlwings  # noqa
    import sys
    sys.path.extend(['C:\\development\\erammp-python'])
    import erammp.config as config  # noqa


    # Use for quick debugging
    # row_counts
    if False:
        db = r'\\nerctbctdb\shared\shared\PROJECTS\WG ERAMMP2 (06810)\2 Field Survey\IT and software\OFFLINE DATA BACKUPS\2022\SOILEROSION_PDS\S123_2dbd6e6ccb9a44cdb63f112811317a61_FGDB\e143cfd3-c9f9-4f7d-b246-ce56727f68a6.gdb'
        dframe = gdb_row_counts(db, match='__ATT')  # all attachment tables
        xlwings.view(dframe)

        # dump struct
        df_ = gdb_dump_struct('C:/GIS/erammp_local/submission/staged/raw/botany/botany.gdb',
                              save_to='C:/GIS/erammp_local/submission/staged/raw/botany/botany_struct.xlsx',
                              field_type_match=['str', 'text'],
                              overwrite_xlsx=True)
        xlwings.view(df_)

        gdb_dump_tables_and_fcs(r'S:\GMEP_Restricted\WP3_Restricted\WG_Data_Handover\EIDC_GMEP_SPATIAL\GMEP_SPATIAL_v2.gdb',
                                save_to=r'S:\GMEP_Restricted\WP3_Restricted\WG_Data_Handover\EIDC_GMEP_SPATIAL\GMEP_SPATIAL_v2_checkout.xlsx')
    pass

    exit()
