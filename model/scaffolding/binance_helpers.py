from binance.client import Client
import math
from keys import key

def binance_ceil(x:float, dp:float):
    """returns the ceil to dp decimal places (to payback borrowed amounts). Includes 0.1% trading fee"""
    return math.ceil(x*1.001*(10 ** dp))/(10 ** dp)

def binance_floor(x:float, dp:float):
    """returns the floor to dp decimal places amount not including trading fee. (for liquidating)"""
    return math.floor(x*(10 ** dp))/(10 ** dp)

def get_isolated_margin_account(client, asset: str):
    """Returns dict for isolated margin account for base_asset. Enter base_asset as 'FET'. Do NOT include USDT"""
    c = client.get_isolated_margin_account()
    return list(filter(lambda x: x["baseAsset"]["asset"] == asset, c["assets"]))[0]

def get_margin_asset(client, asset:str, isolated=True):
    """No USDT. returns a dictionary with:
    - asset name
    - free
    - locked
    - borrowed
    - interest
    - netAsset"""
    if isolated:
        return get_isolated_margin_account(client, asset)["baseAsset"]
    else:
        return list(filter(lambda x: x['asset'] == asset, client.get_margin_account()["userAssets"]))[0]

def get_price(client, pair:str):
    """returns the price as float. pair MUST include USDT, ie ZECUSDT"""
    return float(client.get_recent_trades(symbol=pair, limit=1)[0]["price"])


def trade_amt(client, asset:str, total:float, precision:float, base="USDT"):
    """returns the amount of asset to trade to be total. DONT include USDT"""
    p = get_price(client, asset + base)
    return binance_floor(total/p, precision)

def new_binance_client():
    """resets the client to prevent 'read operation timed out'"""

    return Client(api_key=key("binance", "api"), api_secret=key("binance", "secret"))

