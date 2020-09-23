from bokeh.models import CustomJS, Slider, RangeSlider, Select, Toggle, Spinner

# default values of all widgets
widgets = {'fourier_window': 5,
           'bandpass_toggle': True, 'notch_toggle': True,
           'bandpass_range': (5, 62), 'notch_center': 60,
           'bandpass_order': 3, 'notch_order': 3,
           'bandpass_filter': 'Butterworth'}


def js_request(header, attribute='value'):
    """
    Generates callback JS code to send an HTTPRequest
    'this.value' refers to the new value of the Bokeh object.
        - In some cases (like buttons) Bokeh uses 'this.active'
    <header> is the header to send the information in
    """
    widget_path = 'widgets'  # request path
    code = """
        var req = new XMLHttpRequest();
        url = window.location.pathname
        queries = window.location.search  // get ID of current stream
        req.open("GET", url+'/{path}'+queries, true);
        req.setRequestHeader('{header}', this.{attribute})
        req.send(null);
        console.log('{header}: ' + this.{attribute})
    """
    return code.format(path=widget_path, header=header, attribute=attribute)


# Fourier Window sliders
fourier_window = Slider(title="FFT Window (seconds)", start=0, end=20, step=1, value=widgets['fourier_window'])
fourier_window.js_on_change("value", CustomJS(code=js_request('fourier_window')))

# Toggle buttons
bandpass_toggle = Toggle(label="Bandpass", button_type="success", active=widgets['bandpass_toggle'])
bandpass_toggle.js_on_click(CustomJS(code=js_request('bandpass_toggle', 'active')))

notch_toggle = Toggle(label="Notch", button_type="success", active=widgets['notch_toggle'])
notch_toggle.js_on_click(CustomJS(code=js_request('notch_toggle', 'active')))

# Range slider and Center/Width sliders
bandpass_range = RangeSlider(title="Range", start=0, end=70, step=1, value=widgets['bandpass_range'])
bandpass_range.js_on_change("value", CustomJS(code=js_request('bandpass_range')))

notch_center = Slider(title="Center", start=0, end=60, step=1, value=widgets['notch_center'])
notch_center.js_on_change("value", CustomJS(code=js_request('notch_center')))

# Filter selectors
bandpass_filter = Select(title="Filters:", options=['Butterworth', 'Bessel', 'Chebyshev 1', 'Chebyshev 2', 'Elliptic'], value=widgets['bandpass_filter'])
bandpass_filter.js_on_change("value", CustomJS(code=js_request('bandpass_filter')))

# Order spinners
bandpass_order = Spinner(title="Order", low=1, high=10, step=1, width=80, value=widgets['bandpass_order'])
bandpass_order.js_on_change("value", CustomJS(code=js_request('bandpass_order')))

notch_order = Spinner(title="Order", low=1, high=10, step=1, width=80, value=widgets['notch_order'])
notch_order.js_on_change("value", CustomJS(code=js_request('notch_order')))

# To be imported by EEGHandler and used to construct the Bokeh layout of widgets
widgets_row = [[[bandpass_toggle, bandpass_filter, bandpass_order], bandpass_range,
               [notch_toggle, notch_order], notch_center, fourier_window]]
