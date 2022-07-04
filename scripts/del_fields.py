import arcpy

if False:
    with arcpy.EnvManager(scratchWorkspace=r"S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\GIS\erammp_scratch.gdb",
                          workspace=r"S:\SPECIAL-ACL\ERAMMP2 Survey Restricted\2022\data\GIS\erammp_scratch.gdb"):
        arcpy.management.DeleteField("LPIS_merged_sq_2022",
                                     "LPIS_merged_sq_2022.OSSHEET;LPIS_merged_sq_2022.NGFIELD;LPIS_merged_sq_2022.REGIONNO;"
                                     "LPIS_merged_sq_2022.SHARED;LPIS_merged_sq_2022.SETASIDE;LPIS_merged_sq_2022.ELISNCDATE;"
                                     "LPIS_merged_sq_2022.IACSAREA;LPIS_merged_sq_2022.LFA;LPIS_merged_sq_2022.MAXUAREA;"
                                     "LPIS_merged_sq_2022.UCRPAREA;LPIS_merged_sq_2022.WELSHLAND;LPIS_merged_sq_2022.YRESTBLSHD;"
                                     "LPIS_merged_sq_2022.USERNAME;LPIS_merged_sq_2022.IACSYEAR;LPIS_merged_sq_2022.HOLDINGNO;"
                                     "LPIS_merged_sq_2022.COMSGRAZ;LPIS_merged_sq_2022.COMREG;LPIS_merged_sq_2022.CLCounty;"
                                     "LPIS_merged_sq_2022.CLName;LPIS_merged_sq_2022.DecYear;LPIS_merged_sq_2022.MupVisited;"
                                     "LPIS_merged_sq_2022.Supported;LPIS_merged_sq_2022.INELICOM;LPIS_merged_sq_2022.ParcelStatus;"
                                     "LPIS_merged_sq_2022.MMResolveStatus;LPIS_merged_sq_2022.MMResolveDate;"
                                     "LPIS_merged_sq_2022.LANDCHANGETRANSACTIONID;LPIS_merged_sq_2022.LANDCHANGETRANSACTIONTYPE;"
                                     "LPIS_merged_sq_2022.RECORDSTATUS;LPIS_merged_sq_2022.CASEID;LPIS_merged_sq_2022.PARCELVERSION;"
                                     "LPIS_merged_sq_2022.ValidFrom;LPIS_merged_sq_2022.CHANGESOURCE;LPIS_merged_sq_2022.LCTYPE;"
                                     "LPIS_merged_sq_2022.LCAREA;LPIS_merged_sq_2022.ParcelChng;LPIS_merged_sq_2022.MERGE_SRC")
pass
pass
pass
x = 1