""" ArcGIS Online Backup Script. Primary intended target are feature services.

Notes:
    This supports basic authentication as well as authentication using arcgispro defaults.

    If you wish to enhance the scripts to cater for additional security models see here:
    https://developers.arcgis.com/python/guide/working-with-different-authentication-schemes/

Examples:
    Backup agol feature layer with itemid 02175a673764470883ed8a1514eb7dfa to  C:/TEMP/AGOL_BACKUP_TEST using arcgispro authentication.
    > python agol_feature_layer_backup.py C:/TEMP/AGOL_BACKUP_TEST -itemid 02175a673764470883ed8a1514eb7dfa
"""
import os.path as path
import time  # noqa
import argparse

import arcgis.gis
import fuckit

import funclite.iolib as iolib


def main():
    cmdline = argparse.ArgumentParser(description=__doc__)  # use the module __doc__
    cmdline.add_argument('saveto', type=path.normpath, help='Local/network Folder to backup to. The file name is automatically created and date-time stamped.')
    cmdline.add_argument('-url', '--url', help='URL to your organisations AGOL site when not authenticating with ArcGISPro. e.g. https://ceh.maps.arcgis.com', required=False)
    cmdline.add_argument('-user', '--user', help='User name', required=False, default='pro')
    cmdline.add_argument('-password', '--password', help='password', required=False, default='')
    cmdline.add_argument('-itemid', '--itemid', help='The AGOL feature layer item identifier', required=True)

    args = cmdline.parse_args()


    print('Authenticating ...')
    if args.user.lower() == 'pro':
        gis = arcgis.GIS('pro')
    else:
        try:
            gis = arcgis.GIS(args.url, args.user, args.password)
        except Exception as e:
            raise Exception('Authentication failed. Did you provide a url, username and password?') from e
    print('Authentication successful....')

    AGOLitem = gis.content.get(args.itemid)


    print("Backing up feature service layers to folder %s..." % args.saveto)
    GDBname = '%s_%s.gdb' % (iolib.pretty_date_now(sep='', with_time=True, time_sep=''), AGOLitem.title)

    try:
        AGOLitem.export(GDBname, 'File Geodatabase', parameters=None, wait='True')

        search_fgb = gis.content.search(query="title:{}".format(GDBname))  # find gdb in ArcGIS online
        fgb_item_id = search_fgb[0].id
        fgb = gis.content.get(fgb_item_id)
        print('Downloading fGDB to %s' % args.saveto)

        iolib.create_folder(args.saveto)
        fgb.download(save_path=args.saveto)  # download file gdb from ArcGIS Online to your computer

    finally:
        with fuckit:
            print("Cleaning up ...")
            fgb.delete()  # noqa

    print('All done')
    iolib.folder_open(args.saveto)



if __name__ == "__main__":
    main()
