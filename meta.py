"""work with metadata"""
import os as _os
import os.path as _path

import arcpy as _arcpy

import arcapi as _arcapi

import arcapi.common as _common
from arcapi.errors import *  # noqa


def meta(datasource, mode="PREPEND", **args):
    """Read/write metadata of ArcGIS Feature Class, Raster Dataset, Table, etc.

    Returns a dictionary of all accessible (if readonly) or all editted entries.

    *** This function may irreversibly alter metadata, see details below! ***

    The following entries (XML elements) can be read or updated:
    Title ("dataIdInfo/idCitation/resTitle")
    Purpose ("dataIdInfo/idPurp")
    Abstract ("dataIdInfo/idAbs")

    This function exports metadata of the datasource to XML file using template
    'Metadata\Stylesheets\gpTools\exact copy of.xslt' from ArcGIS installation
    directory. Then it loads the exported XML file into memory using Pythons
    xml.etree.ElementTree, modifies supported elements, writes a new XML file,
    and imports this new XML file as metadata to the datasource.
    If the content of exported metada does not contain element dataInfo,
    it is assumend the metadata is not up to date with current ArcGIS version
    and UpgradeMetadata_conversion(datasource, 'ESRIISO_TO_ARCGIS') is applied!
    Try whether this function is appropriate for your work flows on dummy data.

    Required:
    datasource -- path to the data source to update metadata for
    mode -- {PREPEND|APPEND|OVERWRITE}, indicates whether new entries will be
        prepended or appended to existing entries, or whether new entries will
        overwrite existing entries. Case insensitive.
    **args, keyword arguments of type string indicating what entries to update:
        title, string to use in Title
        purpose, string to use in Purpose
        abstract, string to use in Abstract
        If no keyword argument is specifed, metadata are read only, not edited.

    Example:
    >>> fc = 'c:\\foo\\bar.shp'
    >>> meta(fc) # reads existing entries
    >>> meta(fc, 'OVERWRITE', title="Bar") # updates title
    >>> meta(fc, 'append', purpose='example', abstract='Column Spam means eggs')
    """
    raise NotImplementedError
    #https://github.com/Esri/arcgis-pro-metadata-toolkit
    # Need to convert so compatible with arcpro

    import xml.etree.ElementTree as ET
    xslt = None  # metadata template, could be exposed as a parameter
    sf = _arcpy.env.scratchFolder
    tmpmetadatafile = _arcpy.CreateScratchName('tmpmetadatafile', workspace=sf)

    # checks
    if xslt is None:
        template = 'Metadata\Stylesheets\gpTools\exact copy of.xslt'
        arcdir = _arcpy.GetInstallInfo()['InstallDir']
        xslt = _path.join(arcdir, template)
    if not _path.isfile(xslt):
        raise ArcapiError("Cannot find xslt file " + str(xslt))
    mode = mode.upper()

    lut_name_by_node = {
        'dataIdInfo/idCitation/resTitle': 'title',
        'dataIdInfo/idPurp': 'purpose',
        'dataIdInfo/idAbs': 'abstract'
    }

    # work
    r = _arcpy.XSLTransform_conversion(datasource, xslt, tmpmetadatafile)
    tmpmetadatafile = r.getOutput(0)
    with open(tmpmetadatafile, "r") as f:
        mf = f.read()
    tree = ET.fromstring(mf)

    # check if read-only access requested (no entries supplied)
    readonly = True if len(args) == 0 else False
    reader = {}
    if readonly:
        args = {'title': '', 'purpose': '', 'abstract': ''}
    else:
        # Update the metadata version if it is not up to date
        if tree.find('dataIdInfo') is None:
            _arcpy.conversion.UpgradeMetadata(datasource, 'ESRIISO_TO_ARCGIS')
            _os.remove(tmpmetadatafile)
            r = _arcpy.XSLTransform_conversion(datasource, xslt, tmpmetadatafile)
            tmpmetadatafile = r.getOutput(0)
            with open(tmpmetadatafile, "r") as f:
                mf = f.read()
            tree = ET.fromstring(mf)

    # get what user wants to update
    entries = {}
    if args.get('title', None) is not None:
        entries.update({'dataIdInfo/idCitation/resTitle': args.get('title')})
    if args.get('purpose', None) is not None:
        entries.update({'dataIdInfo/idPurp': args.get('purpose')})
    if args.get('abstract', None) is not None:
        entries.update({'dataIdInfo/idAbs': args.get('abstract')})

    # update entries
    for p, t in entries.iteritems():
        el = tree.find(p)
        if el is None:
            if not readonly:
                wm = "Element %s not found, creating it from scratch." % str(p)
                _arcpy.AddWarning(wm)
                pparent = "/".join(p.split("/")[:-1])
                parent = tree.find(pparent)
                if parent is None:
                    em = "Could not find parent %s as parent of %s in %s " % \
                         (pparent, p, str(datasource))
                    raise ArcapiError(em)
                subel = ET.SubElement(parent, p.split("/")[-1])
                subel.text = str(t)
                el = subel
                del subel
        else:
            if not readonly:
                pre, mid, post = ('', '', '')
                if mode != "OVERWRITE":
                    # remember existing content if not overwrite
                    mid = '' if el.text is None else el.text
                    joiner = '&lt;br/&gt;'
                else:
                    mid = str('' if t is None else t)
                    joiner = ''
                if mode == 'APPEND': post = str('' if t is None else t)
                if mode == 'PREPEND': pre = str('' if t is None else t)
                el.text = joiner.join((pre, mid, post))
        reader.update({lut_name_by_node[p]: getattr(el, 'text', None)})

    # write a new xml file to be imported
    mf = ET.tostring(tree, encoding='utf-8')
    with open(tmpmetadatafile, "w", encoding='utf-8') as f:
        f.write(mf)

    # import new xml file as metadata
    _arcapi.ImportMetadata_conversion(tmpmetadatafile, datasource) # noqa


    _common.msg("Updated metadata for " + str(datasource))

    # try to clean up
    try:
        _os.remove(tmpmetadatafile)
    except:
        pass

    return reader
