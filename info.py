"""
Retrieve informtion about databases

Largely returns pandas dataframes which can be viewed with xlwings.view(dataframe)
"""
import os.path as _path  # noqa

import pandas as _pd
import xlwings  # noqa

import funclite.iolib as _iolib
import funclite.baselib as _baselib

import arcproapi.structure as _struct
import arcproapi.data as _data


def gdb_row_counts(gdb: str, match: (str, list), where: (str, None) = None) -> _pd.DataFrame:  # noqa
    """
    Get row counts for all feature classes and tables in a geodatabase.

    Args:
        gdb (str): Path to geodatabase
        match (str, list, tuple): match names on this
        where (str): throw this where into the data.get_row_count2 query

    Returns:
        pandas.DataFrame

    Notes:
        Coded against file geodatabases, should work with other geodatabases, but untested.
        \n
        The where is passed to get_row_count2, against all tables/feature classes that are matched,
        hence it is highly likely to raise an error unless you know what you are querying!
        I possible use is to reduce query time in finding empty tables, by limiting on OBJECTID.

    Examples:
        >>> gdb = r'C:\my.gdb'  # noqa
        >>> gdb_row_counts(gdb, match='__ATT')
        full_name           base_name       type            row_cnt
        C:/my.gdb/my_ATTACH my_ATTACH       table           3
        C:/my.gdb/ATTFC     ATTFC           feature class   10
        ...
    """
    if isinstance(match, str):
        match = [match]

    fcs, tbls = _struct.gdb_tables_and_fcs_list(gdb, full_path=True)

    filt = lambda s: True if not match else _baselib.list_member_in_str(_iolib.get_file_parts2(s)[1], match)
    fcs = [s for s in fcs if filt(s)]
    tbls = [s for s in tbls if filt(s)]
    fcs_tbls = fcs + tbls

    dic = {'full_name': [s for s in fcs_tbls]}  # noqa
    dic['base_name'] = [_path.basename(s) for s in fcs_tbls]
    dic['type'] = ['feature class'] * len(fcs) + ['table'] * len(tbls)
    dic['row_cnt'] = [_data.get_row_count2(s, where=where) for s in fcs_tbls]
    df = _pd.DataFrame(data=dic)
    return df



if __name__ == '__main__':
    # Use for dirty debugging
    db = r'\\nerctbctdb\shared\shared\PROJECTS\WG ERAMMP2 (06810)\2 Field Survey\IT and software\OFFLINE DATA BACKUPS\2022\SOILEROSION_PDS\S123_2dbd6e6ccb9a44cdb63f112811317a61_FGDB\e143cfd3-c9f9-4f7d-b246-ce56727f68a6.gdb'
    dframe = gdb_row_counts(db, match='__ATT')  # all attachment tables
    xlwings.view(dframe)
    pass
    exit()
