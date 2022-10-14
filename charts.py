# Unaltered from the original source in repo
# https://github.com/NERC-CEH/arcapi
# This is currently broken and needs a full update



import arcpy as _arcpy
import numpy as _np

from arcproapi.errors import MapNotFound, MapFrameNotFound, LayoutNotFound  # noqa


def create_pie_chart(fig, table, case_field, data_field='', fig_title='', x=8.5, y=8.5, rounding=0):
    """Create a pie chart based on a case field and data field.

    If no data_field is specified, the pie chart slices reflect frequency
    of value in the case_field.

    WARNING: although this tool successfully creates a pie chart .png,
             it throws a C++ runtime error.  TODO: Need to investigate this.

    Required:
    fig -- output png file for pie chart
    table -- table for data to create pie chart
    case_field -- field that will be used to summarize values,
                  and also will provide the labels for the legend.

    Optional:
    data_field -- field with values for pie chart.  If no field is
                  specified, count of each value in case_field will be used
    fig_title -- title for the pie chart figure
    x --  size for y-axis side (in inches)
    y --  size for y-axis side (in inches)
    rounding -- rounding for pie chart legend labels.  Default is 0.

    Example:
    >>> wards = r'C:\Temp\Voting_Wards.shp'
    >>> figure = r'C:\Temp\Figures\Election_results.png'
    >>> create_pie_chart(figure, wards, 'CANDIDATE', 'NUM_VOTES', 'Election Results')
    """

    import pylab, numpy, re

    # make sure figure is .png or .jpg
    if not re.findall('.png', fig, flags=re.IGNORECASE):
        out_file += '.png'

    # rounding nested function, (rounding value of 0 from built in round does not return integer)
    def rnd(f, t, rounding):
        return round((f/float(t))*100, rounding) if rounding > 0 else int((f/float(t))*100)

    # Grab unique values
    with _arcpy.da.SearchCursor(table, [case_field]) as rows:
        cases = sorted(list(set(r[0] for r in rows)))

    # if not data_field
    tmp_fld = 'cnt_xx_xx_'
    fields = [case_field, data_field]
    if not data_field:
        _arcpy.AddField_management(table, tmp_fld, 'SHORT')
        with _arcpy.da.UpdateCursor(table, [tmp_fld]) as rows:
            for r in rows:
                r[0] = 1
                rows.updateRow(r)
        fields = [case_field, tmp_fld]

    # vals for slices
    vals=[]

    # sum values
    sum_table = str(_arcpy.Statistics_analysis(table, r'in_memory\sum_tab_xxx',
                                              [[fields[1], 'SUM']],
                                              fields[0]).getOutput(0))
    fields[1] = 'SUM_{0}'.format(fields[1])
    with _arcpy.da.SearchCursor(sum_table, fields) as rows:
        for r in rows:
            vals.append([r[0],r[1]])

    # clean up tmp_fld if necessary
    if not data_field:
        if tmp_fld in [f.name for f in _arcpy.ListFields(table)]:
            try:
                _arcpy.DeleteField_management(table, tmp_fld)
            except:
                pass

    # Create Pie Charts
    the_fig = pylab.figure(figsize=(x, y))
    pylab.axes([0.1, 0.1, 0.8, 0.8])
    label = [v[0] for v in vals]
    fracs = [v[1] for v in vals]
    tot = [sum(fracs)] * len(fracs)
    if len(label) == len(fracs):
        cmap = pylab.plt.cm.prism
        color = cmap(numpy.linspace(0., 1., len(fracs)))
        pie_wedges = pylab.pie(fracs,colors=color,pctdistance=0.5, labeldistance=1.1)
        for wedge in pie_wedges[0]:
            wedge.set_edgecolor('white')
        pylab.legend(map(lambda x, f, t: '{0} ({1}, {2}%)'.format(x, f, rnd(f, t, rounding)),
                         label, fracs, tot),
                     loc=(0,0), prop={'size':8})
        pylab.title(fig_title)
        pylab.savefig(fig)
        msg('Created: %s' %fig)
    _arcpy.Delete_management(sum_table)
    return fig


def chart(x, out_file='c:\\temp\\chart.jpg', texts={}, template=None, resolution=95, openit=True):
    """Create and open a map (JPG) showing x and return path to the figure path.

    Required:
    x -- input feature class, raster dataset, or a layer

    Optional:
    out_file -- path to output jpeg file, default is 'c:\\temp\\chart.jpg'
    texts -- dict of strings to include in text elements on the map (by name)
    template -- path to the .mxd to be used, default None points to mxd with
        a single text element called "txt"
    resolution -- output resolution in DPI (dots per inch)
    openit -- if True (default), exported jpg is opened in a webbrowser

    Example:
    >>> chart('c:\\foo\\bar.shp')
    >>> chart('c:\\foo\\bar.shp', texts = {'txt': 'A Map'}, resolution = 300)
    """
    todel = []
    import re
    if template is None: template = _path.join(_path.dirname(_path.realpath(__file__)), 'chart.mxd')
    if not re.findall(".mxd", template, flags=re.IGNORECASE): template += ".mxd"
    if not re.findall(".jpe?g", out_file, flags=re.IGNORECASE): out_file += ".jpg"

    mxd = _arcpy.mapping.MapDocument(template)
    if not _arcpy.Exists(x):
        x = _arcpy.CopyFeatures_management(x, _arcpy.CreateScratchName('tmp', workspace = 'in_memory')).getOutput(0)
        todel = [x]
    dtype = _arcpy.Describe(x).dataType
    df = _arcpy.mapping.ListDataFrames(mxd)[0]

    lr = "chart" + tstamp(tf = "%H%M%S")
    if _arcpy.Exists(lr) and _arcpy.Describe(lr).dataType in ('FeatureLayer', 'RasterLayer'):
        _arcpy.Delete_management(lr)
    if "raster" in dtype.lower():
        _arcpy.MakeRasterLayer_management(x, lr)
    else:
        _arcpy.MakeFeatureLayer_management(x, lr)

    lyr = _arcpy.mapping.Layer(lr)
    _arcpy.mapping.AddLayer(df, lyr)

    # try to update text elements if any requested:
    for tel in texts.keys():
        try:
            texel = _arcpy.mapping.ListLayoutElements(mxd, "TEXT_ELEMENT", tel)[0]
            texel.text = str(texts[tel])
        except Exception as e:
            _arcpy.AddMessage("Error when updating text element " + str(tel) + ": "+ str(e))
    _arcpy.RefreshActiveView()
    _arcpy.mapping.ExportToJPEG(mxd, out_file, resolution=resolution)

    # cleanup
    _arcpy.Delete_management(lr)
    del mxd
    if todel: _arcpy.Delete_management(todel[0])

    # open the chart in a browser if requested
    if openit:
        import webbrowser
        webbrowser.open_new_tab(out_file)

    return _arcpy.Describe(out_file).catalogPath


def plot(x, y=None, out_file="c:\\temp\\plot.png", main="Arcapi Plot", xlab="X", ylab="Y", pch="+", color="r", openit=True):
    """
    Create and display a plot (PNG) showing x (and y).

    Uses matplotlib.pyplot.scatter.

    Required:
    x -- values to plot on x axis

    Optional:
    y -- values to plot on y axis or None (default), then x will be plotted
        on y axis, using index for x axis.
    out_file -- path to output file, default is 'c:\\temp\\plot.png'
    main -- title of the plot
    xlab -- label for x axis
    ylab -- label for y axis
    pch
    color -- color of points:
        'r': red (default), 'b': blue, 'g': green, 'c': cyan, 'm': magenta,
        'y': yellow, 'k': black, 'w': white, hexadecimal code like '#eeefff',
        shades of grey as '0.75', 3-tuple like (0.1, 0.9, 0.5) for (R, G, B).
    pch -- character for matplotlib plot marks, default is '+', can also be:
        +: plus sign, .: dot, o: circle, *: star, p: pentagon, s:square, x: X,
        D: diamond, h: hexagon, ^: triangle
    openit -- if True (default), exported figure is opened in a webbrowser

    Example:
    >>> x = xrange(20)
    >>> plot(x)
    >>> plot(x, out_file='c:\\temp\\pic.png')
    >>> y = xrange(50,70)
    >>> plot(x, y, 'c:\\temp\\pic.png', 'Main', 'X [m]', 'Y [m]', 'o', 'k')
    """
    import re
    if not re.findall(".png", out_file, flags=re.IGNORECASE): out_file += ".png"

    if y is None:
        y = x
        len(x)
        x = xrange(len(y))
    lx = len(x)
    ly = len(y)
    if lx != ly:
        raise ArcapiError('x and y have different length, %s and %s' % (lx, ly))

    from matplotlib import pyplot as plt
    plt.scatter(x, y, c=color, marker=pch)
    plt.title(str(main))
    plt.xlabel(str(xlab))
    plt.ylabel(str(ylab))
    plt.savefig(out_file)
    plt.close()
    if openit:
        import webbrowser
        webbrowser.open_new_tab("file://" + out_file)
    return


def hist(x, out_file='c:\\temp\\hist.png', openit=True, **args):
    """
    Create and display a plot (PNG) showing histogram of x and return computed
    histogram of values, breaks, and patches.

    Uses matplotlib.pyplot.hist, for details see help(matplotlib.pyplot.hist).
    Draws an empty plot if x is empty.

    Required:
    x -- Input data (not empty!); histogram is computed over the flattened array.

    Optional:
    bins -- int or sequence of scalars defining the number of equal-width bins.
        or the bin edges including the rightmost edge. Default is 10.
    range -- (float, float), the lower and upper range of the bins,
        default is (min(x), max(x))
    normed -- counts normalized to form a probability density if True, default False
    weights -- array_like array of weights for each element of x.
    cumulative -- cumulative counts from left are calculated if True, default False
    histtype -- 'bar'(default)|'barstacked'|'step'|'stepfilled'
    align -- 'left'|'mid'(default)|'right' to align bars to bin edges.
    orientation -- 'horizontal'(default)|'vertical'
    rwidth -- relative width [0.0 to 1.0] of the bars, default is None (automatic)
    log -- if True, empty bins are filtered out and log scale set; default False
    color -- scalar or array-like, the colors of the bar faces:
        'r': red (default), 'b': blue, 'g': green, 'c': cyan, 'm': magenta,
        'y': yellow, 'k': black, 'w': white, hexadecimal code like '#eeefff',
        shades of grey as '0.75', 3-tuple like (0.1, 0.9, 0.5) for (R, G, B).
        Can also be full color and style specification.
    label -- label for legend if x has multiple datasets
    out_file -- path to output file, default is 'c:\\temp\\hist.png'
    main -- string, histogram main title
    xlab -- string, label for the ordinate (independent) axis
    openit -- if True (default), exported figure is opened in a webbrowser

    Example:
    >>> x = numpy.random.randn(10000)
    >>> hist(x)
    >>> hist(x, bins=20, color='r', main='A Title", xlab='Example')
    """
    import matplotlib.pyplot as plt

    # sort out parameters
    extras =  ('main', 'xlab', 'ylab')
    pars = dict([(k,v) for k,v in args.iteritems() if k not in extras])

    h = plt.hist(x, **pars)

    plt.title(str(args.get('main', 'Histogram')))
    xlab = str(args.get('xlab', 'Value'))
    ylab = 'Count'
    if args.get('Density', False):
        ylab = 'Density'

    if args.get('orientation', 'horizontal') == 'vertical':
        lab = xlab
        xlab = ylab
        ylab = lab

    plt.xlabel(str(xlab))
    plt.ylabel(str(ylab))
    plt.savefig(out_file)
    plt.close()
    if openit:
        import webbrowser
        webbrowser.open_new_tab("file://" + out_file)
    return h


def bars(x, out_file='c:\\temp\\hist.png', openit=True, **args):
    """
    Create and display a plot (PNG) showing barchart of x.

    Uses matplotlib.plt.bar, draws an empty plot if x is empty.
    Parameter width is always 1.0.

    Use matplotlib colors for coloring;
        'r': red, 'b': blue (default), 'g': green, 'c': cyan, 'm': magenta,
        'y': yellow, 'k': black, 'w': white, hexadecimal code like '#eeefff',
        shades of grey as '0.75', 3-tuple like (0.1, 0.9, 0.5) for (R, G, B).

    Required:
    x -- Input data. list-like of bar heights.

    Optional:
    color -- scalar or array-like, the colors of the bar faces
    edgecolor -- scalar or array-like, the colors of the bar edges
    linewidth -- scalar or array-like, default: None width of bar edge(s).
        If None, use default linewidth; If 0, don't draw edges.
    xerr -- scalar or array-like, use to generate errorbar(s) if not None (default)
    yerr -- scalar or array-like, use to generate errorbar(s) if not None (default)
    ecolor -- scalar or array-like, use as color of errorbar(s) if not None (default)
    capsize -- integer, length of error bar caps in points, default: 3
    orientation -- 'vertical'(default)|'horizontal', orientation of the bars
    log -- boolean, set the axis to be log scale if True, default is False
    # other
    out_file -- path to output file, default is 'c:\\temp\\hist.png'
    labels -- list-like of labels for each bar to display on x axis
    main -- string, histogram main title
    xlab -- string, label for the ordinate (independent) axis
    openit -- if True (default), exported figure is opened in a webbrowser

    Example:
    >>> x = [1,2,3,4,5]
    >>> lb = ['A','B','C','D','E']
    >>> bars(x)
    >>> bars(x, labels=lb, color='r', main='A Title', orientation='vertical')
    """
    import matplotlib.pyplot as plt
    import numpy

    width = 1.0
    # unpack arguments
    bpars = ['width', 'color', 'edgecolor', 'linewidth', 'xerr', 'yerr',
             'ecolor', 'capsize','error_kw', 'orientation', 'log']
    barpars = dict([(i, args.get(i, None)) for i in args if i in bpars])
    barpars['align'] = 'center'
    center = range(len(x))
    labels = args.get('labels', center)
    barpars['width'] = width
    orientation = barpars.get('orientation', 'vertical')

    fig, ax = plt.subplots()
    fig.canvas.draw()

    # the orientation parameter seems to have no effect on pyplot.bar, therefore
    # it is handled by calling barh instead of bar if orientation is horizontal
    if orientation == 'horizontal':
        a = barpars.pop('width', None)
        a = barpars.pop('orientation', None)
        plt.barh(center, x, **barpars)
    else:
        plt.bar(center, x, **barpars)

    xlab = str(args.get('xlab', 'Item'))
    ylab = str(args.get('ylab', 'Value'))
    if orientation == 'horizontal':
        lab = xlab
        xlab = ylab
        ylab = lab
        ax.set_yticks(center)
        ax.set_yticklabels(labels)
    else:
        ax.set_xticks(center)
        ax.set_xticklabels(labels)

    ax.set_xlabel(xlab)
    ax.set_ylabel(str(ylab))
    ax.set_title(str(args.get('main', 'Barplot')))
    plt.savefig(out_file)
    plt.close()
    if openit:
        import webbrowser
        webbrowser.open_new_tab("file://" + out_file)

    return


def pie(x, y=None, **kwargs):
    """
    Create and display a plot (PNG) showing pie chart of x.

    Uses matplotlib.pyplot.pie, draws an empty plot if x is empty.
    The fractional area of each wedge is given by x/sum(x).  If sum(x) <= 1,
    then the values of x will be used as the fractional area directly.

    Use matplotlib colors for coloring;
        'r': red, 'b': blue, 'g': green, 'c': cyan, 'm': magenta,
        'y': yellow, 'k': black, 'w': white, hexadecimal code like '#eeefff',
        shades of grey as '0.75', 3-tuple like (0.1, 0.9, 0.5) for (R, G, B).

    Required:
    x -- Input data. list-like of bar heights.

    Optional keyword arguments (see matplotlib.pyplot.pie for further details):
    y -- Groupping data - list of factor values, len(x) == len(y),
       values of x will be groupped by y and before the pie chart is plotted.
       If y is specified, labels will include the relevant y value.
    out_file -- output file, default is 'c:\\temp\\hist.png'
    color -- scalar or array-like, the colors of the bar faces
    labels -- list-like of labels for each wedge, or None for default labels
    explode -- scalar or array like for offsetting wedges, default None (0.0)
    main -- string, main title of the plot
    openit -- Open exported figure in a webbrowser? True(default)|False.
    autopct -- None, format string or function for labelling wedges.
    pctdistance -- scalar or array like for fine tuning placment of text
    labeldistance -- labels will be drawn this far from the pie (default is 1.1)
    shadow -- Shadow beneath the pie? False(default)|True.
    mainbox -- bbox properties of the main title, ignored if main is None
    tight -- Apply tight layout? True(default)|False

    Example:
    >>> x = [1,2,3,4,5]
    >>> lb = ['A','B','C','D','E']
    >>> pie(x)
    >>> pie(x, labels=lb, main='A Title')
    >>> pie([1,2,3,4,5,6,7], y=[1,1,2,2,3,3,3], autopct='%1.1f%%')
    >>> pie([1,2,3,4,5,6], y=[(1,'a'),(1,'a'),2,2,'b','b'], autopct='%1.1f%%')
    """
    import matplotlib.pyplot as plt

    # unpack arguments
    #y = kwargs.get('y', None) # more convenient to get as a named argument
    out_file =kwargs.get('out_file', 'c:\\temp\\hist.png')
    openit = kwargs.get('openit', True)
    #
    explode = kwargs.get('explode', None)
    labels = kwargs.get('labels', None)
    colors = kwargs.get('colors', ('b', 'g', 'r', 'c', 'm', 'y', 'k', 'w'))
    autopct = kwargs.get('autopct', None)
    pctdistance = kwargs.get('pctdistance', 0.6)
    labeldistance = kwargs.get('labeldistance', 1.1)
    shadow = kwargs.get('shadow', False)
    startangle = kwargs.get('startangle', 90)
    #
    main = kwargs.get('main', None)
    mainbox = kwargs.get('mainbox', None)
    legend = kwargs.get('legend', True)
    legloc = kwargs.get('legloc', 'best')
    tight = kwargs.get('tight', True)

    # handle the cases when y parameter is supplied
    # i.e. summarize x by y, construct labels etc.
    n = len(x)
    if y is not None:
        if n != len(y):
            raise ArcapiError("Lenghts of x and y must match, %s != %s" %
                              (n, len(y))
                              )

        freqs = {}
        for xi,yi in zip(x,y):
            if yi in freqs:
                freqs[yi] += xi
            else:
                freqs[yi] = xi

        x,y = [],[]
        for k,v in freqs.iteritems():
            x.append(v)
            y.append(k)
        labels = y

    # expand explode, labels, colors, etc. to the right length
    n = len(x)
    if explode is not None:
        if isinstance(explode, list) or isinstance(explode, tuple):
            if len(explode) != n:
                explode = ( explode * n )[0:n]
        else:
            explode = [explode] * n
    if labels is not None:
        if isinstance(labels, list) or isinstance(labels, tuple):
            if len(labels) != n:
                labels = ( labels * n )[0:n]
        else:
            labels = [labels] * n
    if colors is not None:
        if isinstance(colors, list) or isinstance(colors, tuple):
            if len(colors) != n:
                colors = ( colors * n )[0:n]
        else:
            colors = [colors] * n

    plt.figure(1)
    plt.subplot(1,1,1)
    pieresult = plt.pie(
        x,
        explode=explode,
        labels=labels,
        colors=colors,
        autopct=autopct,
        pctdistance=pctdistance,
        shadow=shadow,
        labeldistance=labeldistance
    )
    patches = pieresult[0]
    texts = pieresult[1]

    # add title
    if main is not None:
        plt.title(main, bbox=mainbox)

    # add legend
    if legend:
        if labels is None:
            labels = map(str, x)
            plt.legend(patches, labels, loc=legloc)

    # make output square and tight
    plt.axis('equal')
    if tight:
        plt.tight_layout()

    # save and display
    plt.savefig(out_file)
    plt.close()
    if openit:
        import webbrowser
        webbrowser.open_new_tab("file://" + out_file)

    return


def summary(tbl, cols=['*'], modes=None, maxcats=10, w='', verbose=True):
    """Summary statistics about columns of a table.

    Required:
    tbl -- table

    Optional:
    cols -- list of columns to look at or ['*'] for all columns (default).
    modes -- list of columns of the same length of cols.
        allowed values are "NUM", "CAT", "IGNORE"
        mode_i indicates if column_i should be treated as numeric value,
        categorical variable, or if it should be ignored.
        Default is None, if which case mode is determined as follows:
            CAT for columns of type TEXT or STRING
            NUM for SHORT, SMALLINTEGER, LONG, INTEGER, DOUBLE, FLOAT
            IGNORE for all other types.
    maxcats -- maximum number of categories to keep track of for CAT columns
        Records of superfluous categories are counted together as ('...').
    w -- where clause to limit the rows of tbl considered, default is ''
    verbose -- suppress printing if False, default is True

    Example:
    >>> summary('c:\\foo\\bar.shp')
    >>> summary('c:\\foo\\bar.shp', ['smap', 'eggs'], ['NUM', 'CAT'])
    """
    cattypes = ('TEXT', 'STRING')
    numtypes = ('SHORT', 'SMALLINTEGER', 'LONG', 'INTEGER', 'DOUBLE', 'FLOAT')
    modetypes = ("NUM", "CAT", "IGNORE")
    fields = _arcpy.ListFields(tbl)
    fields = dict([(f.name, f) for f in fields])
    if cols in([], ['*'], None):
        cols = fields.keys()

    if modes is None:
        modes = []
        for c in cols:
            fld = fields.get(c, None)
            if fld is None:
                raise ArcapiError("Column %s not found." % (c))
            fldtype = fld.type.upper()
            if fldtype in numtypes:
                modes.append("NUM")
            elif fldtype in cattypes:
                modes.append("CAT")
            else:
                modes.append("IGNORE")
    else:
        modes = [str(m).upper() for m in modes]
        if not set(modes).issubset(set(modetypes)):
            raise ArcapiError("modes can only be one of %s" % (str(modetypes)))

    nc = len(cols)
    cixs = range(nc)
    stats = {}
    for ci in cixs:
        colname = cols[ci]
        stats[ci] = {
            "col": colname,
            "type": getattr(fields.get(colname, None), 'type', None),
            "cats": {}, "min":None, "max":None, "n": 0, "na": 0
        }

    with _arcpy.da.SearchCursor(tbl, cols, where_clause = w) as sc:
        for row in sc:
            for ci in cixs:
                mode = modes[ci]
                statsci = stats[ci]
                v = row[ci]
                if mode == "CAT":
                    cats = statsci["cats"]
                    if cats is not None:
                        ncats = len(cats)
                        if v in cats:
                            cats[v] += 1
                        else:
                            if ncats < maxcats:
                                cats[v] = 1
                            else:
                                cats[('...')] = cats.get(('...'), 0) + 1
                elif mode == "NUM":
                    if v is None:
                        statsci["na"] += 1
                    else:
                        statsci["n"] += 1
                        m = statsci["min"]
                        if m is None or v < m:
                            statsci["min"] = v
                        m = statsci["max"]
                        if m is None or v > m:
                            statsci["max"] = v
                        statsci["sum"] = statsci.get("sum", 0) + v
                else:
                    # mode is IGNORE
                    pass

        # calculate means
        for i in cixs:
            sm = stats[i].get('sum', None)
            n = stats[i]['n']
            if n > 0 and sm is not None:
                stats[i]['mean'] = sm / n

        if verbose:
            width = 10
            fulline = '-' * 40
            print(fulline)
            print(str(tbl))
            print(str(_arcpy.Describe(tbl).catalogPath))
            print(fulline)
            for j,i in stats.iteritems():
                mode = modes[j]
                print('COLUMN'.ljust(width) + ": " + str(i.get('col', None)))
                print('type'.ljust(width) + ": "+ str(i.get('type', None)))
                if mode == "NUM":
                    print('min'.ljust(width) + ": " + str(i.get('min', None)))
                    print('max'.ljust(width) + ": " + str(i.get('max', None)))
                    print('mean'.ljust(width) + ": " + str(i.get('mean', None)))
                    print('sum'.ljust(width) + ": " + str(i.get('sum', None)))
                    print('n'.ljust(width) + ": " + str(i.get('n', None)))
                    print('na'.ljust(width) + ": " + str(i.get('na', None)))
                elif mode == "CAT":
                    cats = i["cats"]
                    if len(cats) > 0:
                        print("CATEGORIES:")
                        catable = sorted(zip(cats.keys(), cats.values()), key = lambda a: a[1], reverse = True)
                        print_tuples(catable)
                else:
                    pass
                print(fulline)
    return stats


def frequency(x):
    """Return a dict of counts of each value in iterable x.

    Values in x must be hashable in order to work as dictionary keys.

    Required:
    x -- input iterable object like list or tuple

    Example:
    >>> frequency([1,1,2,3,4,4,4]) # {1: 2, 2: 1, 3: 1, 4: 3}
    >>> frequency(values('c:\\foo\\bar.shp', 'STATE'))
    """
    x.sort()
    fq = {}
    for i in x:
        if i in fq: #has_key deprecated in 3.x
            fq[i] += 1
        else:
            fq[i] = 1
    return fq


