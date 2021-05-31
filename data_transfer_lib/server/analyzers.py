from lib import Streamer
import time

"""
Analyzer streams in Redis are indexed like so:
stream:string_identifier:target_stream_id
Note that it is identified by the original stream's ID, not by it's own.
However, the info hash is still identified by it's own ID per usual.
"""


class TestAnalyzer(Streamer):
    target_name = 'TestStreamer'  # name of streamer type to analyze

    def __init__(self, *args):
        super().__init__(*args)
        self.type = 'plot'
        self.show = 'false'
        self.target_id = None

    def loop(self):
        """ Maine execution loop """
        time.sleep(1)
        # get most recent data from raw data stream
        data = self.database.read_data(self.id, self.target_id)

        # perform some operation on the data
        for key in data.keys():
            for i in range(len(data[key])):
                if key == 'time':
                    continue
                data[key][i] *= 10

        # output processed data to new stream
        self.database.write_data('multiplied:'+self.target_id, data)



