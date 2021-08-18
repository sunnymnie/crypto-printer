from strategy import Strategy
from model import Model

strats = [
    Strategy("ARDRUSDT", "LSKUSDT", 4, 0.2, 6100, 0.7),
    Strategy("CELRUSDT", "FETUSDT", 3, 0.2, 4000, 0.4),
    Strategy("", "", 3, 0, 4000, 0.5)
]
printer = Model(strats)
printer.turn_on()