"""Export operations"""

import os.path as _path
from warnings import warn as _warn

import fuckit as _fuckit
import arcpy as _arcpy
import xlwings as _xlwings

import arcproapi.structure as _struct

import funclite.iolib as _iolib
import funclite.baselib as _baselib

def gdb_to_csv(gdb: str, export_root: str, overwrite: bool = False, clean_extras: (list, None) = ('.xml', '.ini'), show_progress=False, **kwargs) -> list:
    """
    Export all tables and fcs to folder export_root.

    Args:
        gdb (str): The geodatabase, support other formats (see link below), but these are currently untested.
        export_root (str): Root file system folder to export the csv files to
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
    fcs, ts = _struct.gdb_tables_and_fcs_list(gdb, full_path=True)
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



def excel_sheets_to_gdb(xlsx: str, gdb: str, match_sheet: (list, tuple, str) = (), exclude_sheet: (list, tuple, str) = (), allow_overwrite: bool = False, show_progress: bool = False) -> list:
    """
    Import worksheets from excel file fname into file geodatabase gdb.

    Args:
        xlsx (str): Excel workbook
        gdb ():
        match_sheet (): Case insensitive
        exclude_sheet (): Case insensitive. Overrides match_sheet on clash.
        allow_overwrite (bool): Performs a delete prior to importing into gdb, otherwise raises standard arcpy error
        show_progress (bool): Show progress bar

    Returns:
        list of new gdb tables

    Notes:
        Forces all names to lowercase.
        Does not currently support listobjects

    Examples:
        >>> excel_sheets_to_gdb('C:/temp/my.xlsx', ('countries', 'regions'), 'principalities')
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
        workbook: _xlwings.Book = xl.books.open(_xlwings.Book(xlsx), read_only=True)
        for sheet in workbook.sheets:
            if not _baselib.list_member_in_str(sheet, match_sheet, ignore_case=True):  # always true of match is empty/None
                continue

            if _baselib.list_member_in_str(sheet, exclude_sheet, ignore_case=True):
                continue

            sheets += [sheet.lower()]

    if show_progress:
        PP = _iolib.PrintProgress(iter_=sheets)

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


if __name__ == '__main__':
    pass
    # simple debugging
    # gdb_to_csv('C:/GIS/erammp_local/submission/curated_raw/botany_curated_raw_local.gdb', 'C:/GIS/erammp_local/submission/curated_raw/csv', overwrite=True, show_progress=True)
