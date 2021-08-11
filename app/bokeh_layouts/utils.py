from bokeh.models import DatetimeTickFormatter, CustomJS


def time_format():
    """
    Generate a new DatetimeTickFormatter to view data at different scales.
    Usage:
        fig = bokeh.plotting.figure()
        fig.xaxis.formatter = time_format()
    """
    return DatetimeTickFormatter(
        years=["%Y"],
        months=["%b %Y"],
        days=["%b %d"],
        hours=["%H:00"],
        hourmin=["%H:%M"],
        minutes=["%H:%M"],
        minsec=["%H:%M %Ss"],
        seconds=["%Ss"],
        milliseconds=['%S.%3Ns'],
        microseconds=['%S.%fs']
    )


def js_request(ID, key, attribute='value'):
    """
    Generates callback JS code to send an HTTPRequest.
    <ID> is the ID to send this request to.
    <key> is the key in the JSON string being sent to associate with this value
    <attribute> is the attribute of the JS object to send.
    'this.value' refers to the new value of the Bokeh object.
        - In some cases (like buttons) Bokeh uses 'this.active'
    """

    code = """
        var req = new XMLHttpRequest();
        url = window.location.pathname;
        req.open("POST", url+'/widgets'+'?id={ID}', true);
        req.setRequestHeader('Content-Type', 'application/json');
        var json = JSON.stringify({{{key}: this.{attribute}}});
        req.send(json);
        console.log('{key}: ' + this.{attribute});
    """
    return code.format(ID=ID, key=key, attribute=attribute)


def plot_sliding_js(figure, source):
    """
    Configures a JS callback for the given AjaxDataSource and Figure
        to make the incoming data appear to slide into the viewing window instead of in large chunks.
    Whenever the AjaxDataSource data changes, incrementally slide x_range over the length of the
        new incoming data to give smooth appearance.
    Incoming data must have a 'time' data column.
    """
    figure.x_range = [0, 1]
    source.js_on_change('data',
        CustomJS(
            args=dict(figure=figure, source=source),
            code="""
var duration = source.polling_interval

var start = source.data['time'][0]
var current_start = figure.x_range.start
var start_diff = start - current_start

var end = source.data['time'][source.data['time'].length-1]
var current_end = figure.x_range.end
var end_diff = end - current_end

if (end_diff > 0 && end_diff < end-start) {
    console.log("figstart: "+figure.x_range.start+"  datastart: "+start+"   figend: "+figure.x_range.end+"  dataend: "+end)
    console.log("startdiff: "+start_diff+"   enddiff: "+end_diff)
    var slide = setInterval(function(){
        if (figure.x_range.start < start) {
            figure.x_range.start += start_diff/30
        }
        if (figure.x_range.end < end) {
            figure.x_range.end += end_diff/30
        }
    }, duration/30);

    setTimeout(function(){
        clearInterval(slide)
    }, duration)
} else {
    //console.log('caught up')
    //figure.x_range.start = start
    //figure.x_range.end = end
}
"""
    ))
    return


def plot_priority_js(figure, back_source, front_source):
    """
    Configures a JS callback for the given AjaxDataSource and Figure
        to make one AjaxDataSource have visual priority over the other.
    Whenever the front_source receives data and is plotted, back_source becomes more transparent.
    """
    front_source.js_on_change('data',
        CustomJS(
            args=dict(figure=figure, back_source=back_source, front_source=front_source),
            code="""
if (front_source.data['time'].length == 0) {  // no data in source
    var alpha = 1.0
} else {  // data in source
    var alpha = 0.1
}

for (let renderer of figure.renderers) {
    // from the low-priority source
    if (renderer.data_source == back_source) {
        renderer.glyph.line_alpha = alpha
        renderer.glyph.fill_alpha = alpha
    }
}
"""))
    return
