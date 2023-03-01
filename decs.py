"""Decorators"""
import arcpy as _arcpy
import fuckit as _fuckit

def environ_persist(func):
    """
    Persists environment settings for overwriteOutput, workspace and transferDomains
    across methods which can alter these settings.

    Notes:
        transferdomains: See https://pro.arcgis.com/en/pro-app/latest/tool-reference/environment-settings/transfer-domain-descriptions.htm
    """
    def persist(*args, **kwargs):
        o = _arcpy.env.overwriteOutput
        ws = _arcpy.env.workspace
        d = _arcpy.env.transferDomains
        try:
            return func(*args, **kwargs)
        finally:
            with _fuckit:
                _arcpy.env.workspace = ws
                _arcpy.env.overwriteOutput = o
                _arcpy.env.transferDomains = d
    return persist
