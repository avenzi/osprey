class Temperature:
    def __init__(self):
        self.roomTemperature = '--.-'
        self.airPressure = '--.-'
        self.airHumidity = '--.-'
        self.status = ''
        self.date = ''

class Audio:

    def __init__(self):
        self.decibels = '--.-'
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
        self.airPressure = 0.0
        self.airHumidity = 0.0