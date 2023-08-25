"""Export operations"""

import os.path as _path
from os import path as _path
from warnings import warn as _warn

import fuckit as _fuckit
import arcpy as _arcpy
import xlwings as _xlwings

import arcproapi.structure as _struct
import arcproapi.decs as _arcdecs
import arcproapi.common as _common


import funclite.baselib as _baselib
from funclite import iolib as _iolib


def gdb_to_csv(gdb: str, export_root: str, match: (str, list[str], tuple[str]) = '*', overwrite: bool = False, clean_extras: (list, None) = ('.xml', '.ini'), show_progress=False, **kwargs) -> list:
    """
    Export all tables and fcs to folder export_root.

    Args:
        gdb (str): The geodatabase, support other formats (see link below), but these are currently untested.
        export_root (str): Root file system folder to export the csv files to
        match (str, list[str], tuple[str]): wildcard match on tables/fcs
        overwrite (bool): Overwrite files without warning
        clean_extras (list, None): If nome, leaves the xml and ini file info in place, else delete files that match the extensions passed
        show_progress (bool): print progress to terminal

        kwargs:
            passed to arcpy.conversion.ExportTable.
            Useful kwargs are where_clause (str), use_field_alias_as_name (bool)
            See https://pro.arcgis.com/en/pro-app/latest/tool-reference/conversion/export-table.htm

    Returns:
        list: list of exported files

    Raises:
        FileExistsError: If a target export file exists and overwrite is false. This validation occurs before any files are exported

    Examples:
        >>> gdb_to_csv('c:/my.gdb', 'C:/temp')
        ['C:/temp/countries.csv', 'C:/temp/states.csv', ...]
    """
    if isinstance(match, str):
        match = [match]
    if match == ['*']: match = None

    fcs, ts = _struct.gdb_tables_and_fcs_list(gdb, full_path=True)
    fcs = _baselib.list_filter_by_list(fcs, match)
    ts = _baselib.list_filter_by_list(ts, match)

    all_in = []
    all_out = []
    success = []


    if show_progress:
        PP = _iolib.PrintProgress(iter_=fcs + ts, init_msg='Collating file names....')  # noqa

    # First loop does the check and builds the in/out lists
    for fname in fcs + ts:
        all_in += [_path.normpath(fname)]
        _, s, _ = _iolib.get_file_parts(fname)
        fout = _iolib.fixp(export_root, '%s.csv' % s)

        if _iolib.file_exists(fout) and not overwrite:
            raise FileExistsError('Export file %s already exists. No files were exported.' % fout)
        _iolib.file_delete(fout)
        all_out += [fout]
        if show_progress:
            PP.increment()  # noqa

    # now do the work using the lists weve built
    if show_progress:
        print('Now doing the export...')
        PP.reset()

    _iolib.create_folder(_path.normpath(export_root))
    for i, fname in enumerate(all_in):
        _arcpy.conversion.ExportTable(fname, all_out[i], **kwargs)
        success += [all_out[i]]
        if show_progress:
            PP.increment()  # noqa

    for f in _iolib.file_list_generator1(_path.normpath(export_root), clean_extras, recurse=False):
        _iolib.file_delete(f)

    return success


def fgdb_to_fgdb(source_gdb: str, dest_gdb: str, recreate: bool = True, show_progress: bool = True) -> int:
    """
    Export a fGDB to another fGDB

    Args:
        source_gdb (str): Source
        dest_gdb (str): Dest
        recreate (bool): Delete dest_gdb if it exists
        show_progress (bool): Show progress

    Returns:
        int: Nr of entities exported

    TODO:
        Test this
    """
    orig = _arcpy.env.workspace
    source_gdb = _path.normpath(source_gdb)
    dest_gdb = _path.normpath(dest_gdb)
    _arcpy.env.workspace = source_gdb

    try:
        src_fld, src_fname, src_ext = _iolib.get_file_parts2(source_gdb)  # noqa Not used at mo - but leave for now
        dest_fld, dest_fname, dest_ext = _iolib.get_file_parts2(dest_gdb)

        if dest_fname[-4:] != '.gdb':
            raise ValueError('dest_gdb did not end with .gdb')

        if recreate:
            print('Deleting the destination GDB...')
            _iolib.folder_delete(dest_gdb)

        if not _iolib.folder_exists(dest_gdb):
            if show_progress:
                print('Creating a destination fGDB "%s" ...' % dest_gdb)
            _arcpy.CreateFileGDB_management(dest_fld, dest_fname)

        # FCs
        if show_progress:
            PP = _iolib.PrintProgress(iter_=_arcpy.ListFeatureClasses(), init_msg='Exporting feature classes...')
        j = 0
        for fc in _arcpy.ListFeatureClasses():
            try:
                _arcpy.management.Copy(fc, _iolib.fixp(dest_gdb, fc))
                j += 1
            except Exception as e:
                _warn('Import of %s failed.\nThe error was:%s' % (fc, e))

            if show_progress:
                PP.increment()  # noqa

        # Tables
        if show_progress:
            PP = _iolib.PrintProgress(iter_=_arcpy.ListTables(), init_msg='Exporting tables...')

        for tbl in _arcpy.ListTables():
            try:
                _arcpy.management.Copy(tbl, _iolib.fixp(dest_gdb, tbl))
                j += 1
            except Exception as e:
                _warn('Import of %s failed.\nThe error was:%s' % (tbl, e))

            if show_progress:
                PP.increment()  # noqa
    finally:
        with _fuckit:
            _arcpy.env.workspace = orig

    return j


@_arcdecs.environ_persist
def fgdb_to_sde_oracle(source_gdb: str, OracleSDE, match_layers: (None, list) = None, exclude_layers: (None, list) = None, show_progress: bool = True) -> dict[str:list, str:list]:
    """
    Export a fGDB to another an oracle enterprise geodb

    Args:
        source_gdb (str): Source
        OracleSDE (OracleSDE): An instance of connections.OracleSDE
        match_layers (None, list): list of partial names to match
        exclude_layers (None, list): list of partial names to match
        show_progress (bool): Show progress

    Returns:
        dict[str:list, str:list]: List of successful and failed exports, {'good':['lyr1', 'lyr2', ...], 'bad':['lyrA', 'lyrB', ...]}

    TODO:
        Test this
    """
    raise NotImplementedError
    source_gdb = _path.normpath(source_gdb)
    _arcpy.env.workspace = _common.workspace_from_fname(source_gdb)
    out = _baselib.DictKwarg()

    src_fld, src_fname, src_ext = _iolib.get_file_parts2(source_gdb)  # noqa Not used at mo - but leave for now
    dest_fld, dest_fname, dest_ext = _iolib.get_file_parts2(OracleSDE.feature_path)
    # TODO: test here for valid sde


    if not _iolib.folder_exists(OracleSDE.feature_path):
        if show_progress:
            print('Creating a destination fGDB "%s" ...' % OracleSDE.feature_path)
        _arcpy.CreateFileGDB_management(dest_fld, dest_fname)

    # FCs
    if show_progress:
        PP = _iolib.PrintProgress(iter_=_arcpy.ListFeatureClasses(), init_msg='Exporting feature classes...')

    for fc in _arcpy.ListFeatureClasses():
        try:
            _arcpy.management.Copy(fc, _iolib.fixp(OracleSDE.feature_path, fc))
            out['good'] = fc
        except Exception as e:
            _warn('Import of %s failed.\nThe error was:%s' % (fc, e))
            out['bad'] = fc
        if show_progress:
            PP.increment()  # noqa

    # Tables
    if show_progress:
        PP = _iolib.PrintProgress(iter_=_arcpy.ListTables(), init_msg='Exporting tables...')

    for tbl in _arcpy.ListTables():
        try:
            _arcpy.management.Copy(tbl, _iolib.fixp(OracleSDE.feature_path, tbl))
            out['good'] = tbl
        except Exception as e:
            _warn('Import of %s failed.\nThe error was:%s' % (tbl, e))
            out['bad'] = tbl

        if show_progress:
            PP.increment()  # noqa

    return dict(out)


def excel_sheets_to_gdb(xlsx: str, gdb: str, match_sheet: (list, tuple, str) = (), exclude_sheet: (list, tuple, str) = (), allow_overwrite: bool = False, show_progress: bool = False) -> list:
    """
    Import worksheets from excel file fname into file geodatabase gdb.
    If match_sheet or exlude sheet are unspecified then will try and import all sheets.

    Args:
        xlsx (str): Excel workbook
        gdb (str): Geodatabase to export to
        match_sheet (): Case insensitive
        exclude_sheet (): Case insensitive. Overrides match_sheet on clash.
        allow_overwrite (bool): Performs a delete prior to importing into gdb, otherwise raises standard arcpy error
        show_progress (bool): Show progress bar

    Returns:
        list of new gdb tables

    Notes:
        Forces all names to lowercase.
        Does not currently support listobjects.

    Examples:
        >>> excel_sheets_to_gdb('C:/temp/my.xlsx', 'C:/temp/my.gdb', ('countries', 'regions'), 'principalities')
        ['countries_europe', 'countries_america', 'regions_europe', 'regions_america']

    TODO: Add another function to support listobjects
    """
    xlsx = _path.normpath(xlsx)
    # Lets construct the list of sheets then close excel to avoid any potential "read only/file in use" moans
    if isinstance(match_sheet, str):
        match_sheet = [match_sheet]

    if isinstance(exclude_sheet, str):
        exclude_sheet = [exclude_sheet]

    sheets = []
    with _xlwings.App(visible=False) as xl:
        workbook = xl.books.open(xlsx, read_only=True)
        sheet: _xlwings.Sheet
        for sheet in workbook.sheets:
            if exclude_sheet or match_sheet:
                if not _baselib.list_member_in_str(sheet.name, match_sheet, ignore_case=True):  # always true of match is empty/None
                    continue

                if _baselib.list_member_in_str(sheet.name, exclude_sheet, ignore_case=True):
                    continue

            sheets += [sheet.name]

    if show_progress:
        PP = _iolib.PrintProgress(iter_=sheets, init_msg='Importing worksheets ...')

    added = []
    for sheet in sheets:
        # The out_table is based on the input Excel file name
        # an underscore (_) separator followed by the sheet name
        safe_name = _arcpy.ValidateTableName(sheet, gdb)
        out_table = _iolib.fixp(gdb, safe_name)
        if allow_overwrite:
            _struct.fc_delete2(_iolib.fixp(gdb, out_table))

        _arcpy.conversion.ExcelToTable(xlsx, out_table, sheet)
        added += out_table
        if show_progress:
            PP.increment()  # noqa
    return added


def csv_to_gdb(csv_source: str, gdb_dest: str, **kwargs) -> None:
    """
    Import a csv into a geodatabase. Gets a safename from csv filename using arcpy.ValidateTableName
    Normpaths everything.

    Args:
        csv_source (str): CSV name
        gdb_dest (str): gdb name. Is normpathed
        **kwargs (any): keyword args passed to arcpy.conversion.ExportTable. Supports where_clause, field_info and use_field_alias_as_name.
        See https://pro.arcgis.com/en/pro-app/latest/tool-reference/conversion/export-table.htm

    Returns:
        arcpy Result object, passed from arcpy.conversion.ExportTable.

    Examples:
        >>> csv_to_gdb('C:/my.csv', 'C:/my.gdb')
        <Result '\\ ....>
    """
    csv_source = _path.normpath(csv_source)
    gdb_dest = _path.normpath(gdb_dest)
    fname = _iolib.get_file_parts(csv_source)[1]
    res = _arcpy.conversion.ExportTable(csv_source, _iolib.fixp(gdb_dest, _arcpy.ValidateTableName(fname)), **kwargs)
    return res






if __name__ == '__main__':
    pass
    # simple debugging
    # gdb_to_csv('C:/GIS/erammp_local/submission/curated_raw/botany_curated_raw_local.gdb', 'C:/GIS/erammp_local/submission/curated_raw/csv', overwrite=True, show_progress=True)
    excel_sheets_to_gdb(r'\\nerctbctdb\shared\shared\SPECIAL-ACL\ERAMMP2 Survey Restricted\common\data\2 CEH\land\land_cover_map\code_to_class_all_years.xlsx',
                        r'S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\common\data\GIS\ceh.gdb', show_progress=True)
