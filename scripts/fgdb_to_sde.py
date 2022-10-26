"""
Export a file geodatabase to another file geodatabase.

Uses management.Copy, so should copy all relationships
"""
import os  # noqa
import os.path as path  # noqa
from os.path import normpath as np
import argparse

import fuckit

import arcpy
from tqdm import tqdm

import funclite.iolib as iolib


def main():
    """main"""
    cmdline = argparse.ArgumentParser(description=__doc__)  # use the module __doc__

    cmdline.add_argument('source_gdb', type=np, help='The source file-geodatabase')
    cmdline.add_argument('dest_sde', type=np, help='A valid SDE file connection')
    cmdline.add_argument('-overwrite', '--overwrite', help='Allow overwriting in the destination schema. This does a precheck.', action='store_true')

    args = cmdline.parse_args()
    arcpy.env.workspace = args.source_gdb
    arcpy.env.overwriteOutput = args.overwrite

    src_fld, src_fname, src_ext = iolib.get_file_parts2(args.source_gdb)  # noqa Not used at mo - but leave for now
    dest_fld, dest_fname, dest_ext = iolib.get_file_parts2(args.dest_gdb)

    if dest_fname[-4:].lower() != '.sde':
        raise ValueError('dest_sde did not end with .sde')



    print('Exporting feature classes....')
    for fc in tqdm(arcpy.ListFeatureClasses()):
        try:
            arcpy.management.Copy(fc, iolib.fixp(args.dest_sde, fc))
        except:

    print('Exporting tables....')
    for tbl in tqdm(arcpy.ListTables()):
        with fuckit:
            arcpy.management.Copy(tbl,  iolib.fixp(args.dest_sde, tbl))

    print('All done.')
    iolib.folder_open(dest_fld)


if __name__ == '__main__':
    main()
