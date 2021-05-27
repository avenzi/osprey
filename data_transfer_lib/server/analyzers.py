from lib import Streamer


class TestAnalyzer(Streamer):
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'TestAnalyzer'  # display name
        self.type = 'plot'
        self.raw_streamer = 'TestStreamer'  # name of data column in redis to analyze

    def read_stream(self):
        """
        Reads data from a Redis Stream since last read (if last read data is stored in session).
        Redis returns nested lists in which key-value pairs are consecutive elements.
        Converts this output into dictionary
        """
        stream = self.redis.xread({'stream:'+self.raw_streamer: '$'}, None, 0)  # BLOCK 0

        # get keys, which are every other element in first data list
        keys = stream[0][1][0][1].keys()
        output = {key: [] for key in keys}

        # loop through stream data
        for data in stream[0][1]:
            # data[0] is the timestamp ID
            d = data[1]  # data dict
            for key in keys:
                output[key].append(float(d[key]))  # convert to float and append

        return output

    def loop(self):
        """ Maine execution loop """
        # get most recent data from raw data stream
        data = self.read_stream()

        # perform some operation on the data
        for key in data.keys():
            for i in range(len(data[key])):
                data[key][i] *= 10

        # output processed data to new stream
        pipe = self.redis.pipeline()
        for i in range(len(data['time'])):
            # get slice of each data point as dictionary
            pipe.xadd('stream:'+self.name, {key: data[key][i] for key in data.keys()})
        pipe.execute()


