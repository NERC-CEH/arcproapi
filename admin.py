"""Overarching admin functions, like backups."""
import os.path as _path

import arcpy as _arcpy

import funclite.iolib as _iolib

class BackUps:

    @staticmethod
    def backup_sde(sde_file: str, out_gdb: str, overwrite: bool = False) -> None:
        """   
        Copies files from an SDE database to a GDB or SQLite Database (using
        spatialite for spatial files). SQLite files must end in .sqlite to be
        recognised by ArcGIS. Currently, rasters are only supported for GDB. With
        overwrite set to True, any existing db is deleted and a full copy of the
        SDE is made. If False, files within the database that are not present in
        the output db are copied, and files where the number of features do not
        match are replaced.
    
        Args:
            sde_file (str): Name of the database owner to copy.
            out_gdb (str): Path for the output DB, which is created if it doesn't exist.
            overwrite (bool): Select True to delete any existing GDB and create a new copy
                
        Notes:
            This script adapted from Shaun Astbury's scripts in UKCEH.
            Temporaily changes workspace, then resets it back to the original

        Credit:
            This script was authored by Shaun Astbury who worked for CEH GMEP Project. It has subsequently been edited to run under arcgispro and Python >= 3.7
        """
        # TODO Fix backup_sde up
        sde_file = _path.normpath(sde_file)

        if _arcpy.Exists(out_gdb) and overwrite:
            _arcpy.management.Delete(out_gdb)
    
        # Create new DB
        if not _arcpy.Exists(out_gdb):
            _arcpy.management.CreateFileGDB(dirname(out_gdb), basename(out_gdb))

        current_ws = _arcpy.env.workspace
        _arcpy.env.workspace = sde_file
    
        # Iterate through tables in database, and attempt to copy any which do not
        # already exist.
        tbls = _arcpy.ListTables()
        if tbls:
            for tbl in tbls:
                if tbl.split('.')[0] == owner:
                    path = osjoin(out_gdb, tbl.split('.')[1])
                    if _arcpy.Exists(path):
                        _arcpy.MakeTableView_management(tbl, "tbl")
                        in_count = int(
                            _arcpy.GetCount_management("tbl").getOutput(0))
                        _arcpy.Delete_management("tbl")
                        _arcpy.MakeTableView_management(path, "tbl")
                        out_count = int(
                            _arcpy.GetCount_management("tbl").getOutput(0))
                        _arcpy.Delete_management("tbl")
                        if in_count != out_count:
                            _arcpy.Delete_management(path)

                    if not _arcpy.Exists(path):
                        print(tbl)
                        try:
                            _arcpy.CopyRows_management(tbl, path)
                        except:
                            print('Failed importing {0}'.format(tbl))
    
        # Iterate through rasters in database, and attempt to copy any which do not
        # already exist.
        rasters = _arcpy.ListRasters('*')
        if rasters and not sqlite:
            for raster in rasters:
                if raster.split('.')[0] == owner:
                    path = osjoin(out_gdb, raster.split('.')[1].upper())
                    if not _arcpy.Exists(path):
                        print(raster)
                        try:
                            _arcpy.CopyRaster_management(raster, path)
                        except:
                            print('Failed importing {0}'.format(raster))
    
        # Iterate through feature classes in database, and attempt to copy any
        # which do not already exist.
        feats = _arcpy.ListFeatureClasses()
        if feats:
            for feat in feats:
                if feat.split('.')[0] == owner:
                    path = osjoin(out_gdb, feat.split('.')[1])
                    if _arcpy.Exists(path):
                        _arcpy.MakeTableView_management(feat, "tbl")
                        in_count = int(
                            _arcpy.GetCount_management("tbl").getOutput(0))
                        _arcpy.Delete_management("tbl")
                        _arcpy.MakeTableView_management(path, "tbl")
                        out_count = int(
                            _arcpy.GetCount_management("tbl").getOutput(0))
                        _arcpy.Delete_management("tbl")
                        if in_count != out_count:
                            _arcpy.Delete_management(path)
                    if not _arcpy.Exists(path):
                        print(feat)
                        try:
                            if sqlite:
                                add_sqlite_tbl(feat, out_gdb, True)
                            else:
                                _arcpy.CopyFeatures_management(feat, path)
                        except Exception as e:
                            print('Failed importing {0}:'.format(feat))
                            print('\t', e)
    
        # Iterate through feature datasets in database, and attempt to copy any
        # which do not already exist.
        datasets = _arcpy.ListDatasets('*', 'Feature')
        if datasets:
            for dataset in datasets:
                if dataset.split('.')[0] == owner:
    
                    # Create Feature Dataset if GDB.
                    if not sqlite:
                        path = osjoin(out_gdb, dataset.split('.')[1])
                        if not _arcpy.Exists(path):
                            _arcpy.CreateFeatureDataset_management(dirname(path),
                                                                  basename(path))
    
                    # Set workspace to dataset.
                    _arcpy.env.workspace = osjoin(cnx, dataset)
    
                    # Iterate through feature classes in dataset, and attempt to
                    # copy any which do not already exist.
                    feats = _arcpy.ListFeatureClasses()
                    if feats:
                        for feat in feats:
                            if feat.split('.')[0] == owner:
                                if sqlite:
                                    path = osjoin(out_gdb, feat.split('.')[1])
                                else:
                                    path = osjoin(out_gdb,
                                                  dataset.split('.')[1],
                                                  feat.split('.')[1])
                                if _arcpy.Exists(path):
                                    _arcpy.MakeTableView_management(feat, "tbl")
                                    in_count = int(
                                        _arcpy.GetCount_management(
                                            "tbl").getOutput(0))
                                    _arcpy.Delete_management("tbl")
                                    _arcpy.MakeTableView_management(path, "tbl")
                                    out_count = int(
                                        _arcpy.GetCount_management(
                                            "tbl").getOutput(0))
                                    _arcpy.Delete_management("tbl")
                                    if in_count != out_count:
                                        _arcpy.Delete_management(path)
    
                                try:
    
                                    # SQLite (and most other DBs) doesn't use
                                    # Feature Datasets, so just export the file.
                                    if sqlite:
                                        if not _arcpy.Exists(path):
                                            print(feat)
                                            add_sqlite_tbl(feat, out_gdb, True)
    
                                    # If GDB, include the dataset in the path.
                                    else:
                                        if not _arcpy.Exists(path):
                                            print(feat)
                                            _arcpy.CopyFeatures_management(feat,
                                                                          path)
                                except Exception as e:
                                    print('Failed importing {0}:'.format(feat))
                                    print('\t', e)
    
        # Reset workspace.
        _arcpy.env.workspace = current_ws
