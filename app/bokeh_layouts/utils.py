from bokeh.models import DatetimeTickFormatter

time_formatter = DatetimeTickFormatter(
    years=["%Y"],
    months=["%m/%d %Y"],
    days=["%m/%d"],
    hours=["%m/%d %H:%M"],
    hourmin=["%H:%M"],
    minutes=["%H:%M"],
    minsec=["%H:%M"],
    seconds=["%S"],
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