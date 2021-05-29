from bokeh.embed import json_item
from json import dumps
from . import TestStreamer, SenseStreamer, EEGStreamer


def get_layout(info):
    """
    Retrieves or creates the appropriate Bokeh Layout object
    <info> dictionary of attributes associated with this stream
    """
    # TODO: Not hard-code the various stream types here.
    #  It should be able to look through /boheh_layouts and find the right layout
    name = info['name']
    if name == 'TestStreamer' or name == 'TestAnalyzer':
        layout = TestStreamer.create_layout(info)
    elif name == 'SenseStreamer':
        layout = SenseStreamer.create_layout(info)
    elif name == 'EEGStreamer':
        layout = EEGStreamer.create_layout(info)
    else:
        raise Exception("Layout for {} not found".format(info['name']))

    # TODO: Allow option to quickly construct a basic layout from a few parameters
    #  like a list of column ids and a graph title.

    # convert Bokeh layout object to JSON string
    return dumps(json_item(layout))
