from strategy import Strategy
from model import Model

#🛑 DO NOT RUN UNTIL ALL CODE IS FINISHED
strats = [
    Strategy("ARDRUSDT", "LSKUSDT", 4, 0, 3000, 0.7),
    Strategy("CELRUSDT", "FETUSDT", 3, 0, 4000, 0.3)
]
printer = Model(strats)
printer.turn_on()