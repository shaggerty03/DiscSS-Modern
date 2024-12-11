from enum import Enum


class Endpoints(Enum):
    STATUS = 'status'
    PLAY = 'play'
    PAUSE = 'pause'
    STOP = 'stop'
    RESUME = 'resume'
    DISCONNECT = 'disconnect'
