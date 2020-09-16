from bokeh.models import CustomJS, Slider, RangeSlider, Select, Toggle, Spinner

# default values of all widgets
widgets = {'fourier_window': 5,
           'bandpass_toggle': True, 'bandstop_toggle': True,
           'bandpass_range': (5, 62), 'bandstop_center': 60, 'bandstop_width': 0.5,
           'bandpass_order': 3, 'bandstop_order': 3,
           'bandpass_filter': 'Butterworth', 'bandstop_filter': 'Butterworth'}


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

bandstop_toggle = Toggle(label="Bandstop", button_type="success", active=widgets['bandstop_toggle'])
bandstop_toggle.js_on_click(CustomJS(code=js_request('bandstop_toggle', 'active')))

# Range slider and Center/Width sliders
bandpass_range = RangeSlider(title="Range", start=0, end=70, step=1, value=widgets['bandpass_range'])
bandpass_range.js_on_change("value", CustomJS(code=js_request('bandpass_range')))

bandstop_center = Slider(title="Center", start=0, end=60, step=1, value=widgets['bandstop_center'])
bandstop_center.js_on_change("value", CustomJS(code=js_request('bandstop_center')))
bandstop_width = Slider(title="Width", start=0, end=2, step=0.5, value=widgets['bandstop_width'])
bandstop_width.js_on_change("value", CustomJS(code=js_request('bandstop_width')))

# Filter selectors
bandpass_filter = Select(title="Filters:", options=['Butterworth', 'Bessel', 'Chebyshev 1'], value=widgets['bandpass_filter'])
bandpass_filter.js_on_change("value", CustomJS(code=js_request('bandpass_filter')))

bandstop_filter = Select(title="Filters:", options=['Butterworth', 'Bessel', 'Chebyshev 1'], value=widgets['bandstop_filter'])
bandstop_filter.js_on_change("value", CustomJS(code=js_request('bandstop_filter')))

# Order spinners
bandpass_order = Spinner(title="Order", low=1, high=10, step=1, width=80, value=widgets['bandpass_order'])
bandpass_order.js_on_change("value", CustomJS(code=js_request('bandpass_order')))

bandstop_order = Spinner(title="Order", low=1, high=10, step=1, width=80, value=widgets['bandstop_order'])
bandstop_order.js_on_change("value", CustomJS(code=js_request('bandstop_order')))

# To be imported by EEGHandler and used to construct the Bokeh layout of widgets
widgets_row = [[bandpass_toggle, bandpass_range, [bandpass_filter, bandpass_order]],
               [bandstop_toggle, bandstop_center, bandstop_width, [bandstop_filter, bandstop_order]]]
