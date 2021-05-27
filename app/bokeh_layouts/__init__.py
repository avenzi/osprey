from bokeh.embed import json_item
from json import dumps
from . import TestStreamer, SenseStreamer


def get_layout(name):
    """ Retrieves or creates the appropriate Bokeh Layout object """
    # TODO: Not hard-code the various stream types here.
    #  It should be able to look through /boheh_layouts and find the right layout
    if name == 'TestStreamer' or name == 'TestAnalyzer':
        layout = TestStreamer.create_layout(name)
    elif name == 'SenseStreamer':
        layout = SenseStreamer.create_layout(name)
    else:
        raise Exception("Layout for {} not found".format(name))

    # TODO: Allow option to quickly construct a basic layout from a few parameters
    #  like a list of column names and a graph title.

    # convert Bokeh layout object to JSON string
    return dumps(json_item(layout))
