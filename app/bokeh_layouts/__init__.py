from bokeh.embed import json_item
from json import dumps
from . import test_stream, sense_stream, eeg_stream


def get_layout(info):
    """
    Retrieves or creates the appropriate Bokeh Layout object
    <info> dictionary of attributes associated with this stream
    """
    # TODO: Not hard-code the various stream types here.
    #  Maybe send the info about which one to pick in the info dictionary
    name = info['name']
    if name == 'TestStreamer':
        layout = test_stream.create_layout(info)
    elif name == 'SenseStreamer':
        layout = sense_stream.create_layout(info)
    elif name == 'EEGStreamer' or name == 'SynthEEGStreamer':
        layout = eeg_stream.create_layout(info)
    else:
        raise Exception("Layout for {} not found".format(info['name']))

    # TODO: Allow option to quickly construct a basic layout from a few parameters
    #  like a list of column ids and a graph title.

    # convert Bokeh layout object to JSON string
    return dumps(json_item(layout))
