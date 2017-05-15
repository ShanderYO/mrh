from mpd import MPDClient

class Client(object):

    def __init__(self):
        self.client = MPDClient()
        self.client.timeout = 20
        self.client.idletimeout = 20

        self.client.consume = 1
        self.client.crossfade = 1
        self.client.mixrampdb = -17
        self.client.mixrampdelay = 2
        self.client.connect("localhost", 6600)

    def load_playlist(self):
    	self.client.load('1')
    	self.client.play()