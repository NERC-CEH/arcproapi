"""Export operations"""

import os.path as _path

import arcpy as _arcpy

import arcproapi.structure as _struct
import funclite.iolib as _iolib


def gdb_to_csv(gdb: str, export_root: str, overwrite: bool = False, clean_extras: (list, None) = ['.xml', '.ini'], show_progress=False, **kwargs) -> list:
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



if __name__ == '__main__':
    # simple debugging
    gdb_to_csv('C:/GIS/erammp_local/submission/curated_raw/botany_curated_raw_local.gdb', 'C:/GIS/erammp_local/submission/curated_raw/csv', overwrite=True, show_progress=True)
