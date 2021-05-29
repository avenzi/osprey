from lib import Streamer


class TestAnalyzer(Streamer):
    # TODO: make a base class for the Analyzers?
    target_name = 'TestStreamer'  # name of streamer type to analyze

    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'TestAnalyzer'  # display name
        self.type = 'plot'
        self.target_id = None

    def loop(self):
        """ Maine execution loop """
        # get most recent data from raw data stream
        data = self.database.read_data(self.target_id)

        # perform some operation on the data
        for key in data.keys():
            for i in range(len(data[key])):
                data[key][i] *= 10

        # output processed data to new stream
        self.database.write_data(self.id, data)



