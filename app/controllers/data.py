class Temperature:
    
    def __init__(self):
        self.roomTemperature = '--.-'
        self.skinTemperatureSub1 = '--.-'
        self.skinTemperatureSub2 = '--.-'
        self.status = ''
        self.date = ''

class Audio:

    def __init__(self):
        self.decibels = '--'
        self.status = ''
        self.date = ''

class EventLog:
    def __init__(self):
        self.temperatureStatus = ''
        self.audioStatus = ''

class TriggerSettingsFormData:
    def __init__(self):
        self.audio = 0
        self.temperature = 0.0