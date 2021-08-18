from lib.lib import Base
from server.analyzers import FunctionAnalyzer
from server.bokeh_layouts import unknown_layout


class Interface(Base):
    def __init__(self):
        super().__init__()
        self.pages = {}  # Page objects indexed by name

    def add_pages(self, *args):
        """ Add the given pages to this interface """
        self.pages += list(args)


class Page(Base):
    def __init__(self, name, expected, layout=None, html=None):
        """
        <name>
        <expected> List of expected stream names
        <layout> Function that accepts a dictionary and returns a Bokeh layout object. (html should not be specified with this)
        <html> The name of an html document to be displayed for this stream (layout should not be specified with this)
        """
        super().__init__()
        self.name = name
        assert type(expected) == list, "argument 'expected' must be a list of expected stream names"
        self.streams = expected
        self.pipeline = []  # list of streams in the pipeline

        if layout and html:
            raise Exception("Specify only a bokeh Layout object or an html filename, not both")
        elif not (layout or html):  # assumes default bokeh layout
            self.layout = unknown_layout.create_layout
        elif layout:
            self.layout = layout
            self.html = 'bokeh.html'
        else:
            self.html = html

    def pipeline(self, name):
        """
        Add a pipeline (and associated interface) to this page for the specified stream
        """
        if name not in self.streams:
            raise Exception("'{}' is not an expected stream name.".format(name))
        self.pipeline.append(name)
