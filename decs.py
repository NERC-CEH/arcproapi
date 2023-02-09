"""Decorators"""
import arcpy as _arcpy


def environ_persist(func):
    """
    Persists the current environment on exit if decorated function.
    i.e. Will reset env.overwriteOutput and env.workspace to the status
    prior to the decorated function executing.

    """
    def persist():
        o = _arcpy.env.overwriteOutput
        ws = _arcpy.env.workspace
        try:
            func()
        finally:
            _arcpy.env.workspace = ws
            _arcpy.env.overwriteOutput = o
    return persist
