"""Decorators"""
import arcpy as _arcpy
import fuckit as _fuckit

def environ_persist(func):
    """
    Persists the current environment on exit.
    i.e. Will reset env.overwriteOutput and env.workspace to the status
    prior to the decorated method executing.
    """
    def persist(*args, **kwargs):
        o = _arcpy.env.overwriteOutput
        ws = _arcpy.env.workspace
        try:
            return func(*args, **kwargs)
        finally:
            with _fuckit:
                _arcpy.env.workspace = ws
                _arcpy.env.overwriteOutput = o
    return persist
