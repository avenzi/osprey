from lib import Streamer


class TestAnalyzer(Streamer):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'TestAnalyzer'  # display name
        self.type = 'plot'
        self.raw_streamer = 'TestStreamer'  # name of data column in redis to analyze

    def loop(self):
        """ Maine execution loop """
        # get most recent data from raw data stream
        data = self.database.read_data(self.raw_streamer)

        # perform some operation on the data
        for key in data.keys():
            for i in range(len(data[key])):
                data[key][i] *= 10

        # output processed data to new stream
        self.database.write_data(self.name, data)


