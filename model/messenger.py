import json
import pandas as pd

MESSAGE = 'message.txt'
HISTORY = 'history.txt'

def get_message():
    """reads the message.txt file and returns it"""
    return open_json(MESSAGE)
    
def save_message(message):
    """saves the message to message.txt"""
    save_json(message, MESSAGE)
    
def get_history():
    """reads the message.txt file and returns it"""
    return open_json(HISTORY)
    
def save_history(history):
    """saves the message to message.txt"""
    save_json(history, HISTORY)
        
def open_json(filename):
    """opens json file"""
    with open(filename) as json_file:
        return json.load(json_file)
    
def save_json(file, filename):
    """saves json file"""
    with open(filename, 'w') as outfile:
        json.dump(file, outfile)

def update_trade(trade):
    """saves trade to message.txt for discord manager to post"""
    message = get_message()
    message["trades"].append(trade)
    save_message(message)
    
def update_portfolio_value(pv, usdt, a, b, a_val, b_val):
    """updates portfolio value and saves it"""
    a = a[:-4]
    b = b[:-4]
    message = get_message()
    message["portfolio"] = {'usdt': usdt, 'total': pv}
    message["strategy"][a + b] = {}
    message["strategy"][a + b]["pct"] = (a_val + b_val)/pv
    message["strategy"][a + b]["a"] = a_val
    message["strategy"][a + b]["b"] = b_val
    save_message(message)
    
def keep_track_of_order(order):
    """saves order or transaction to json"""
    message = get_message()
    history = get_history()
    history["order"].append(order)
    history["portfolio"].append(message["portfolio"])
    save_history(history)
