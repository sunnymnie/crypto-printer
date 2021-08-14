import pandas as pd
import numpy as np
from binance.client import Client
from datetime import datetime
import json
import time
from IPython.display import clear_output

def download_all_hourly_data(pathname, filename, hourpath):
    start = time.time()
    series = pd.read_csv(pathname+filename, squeeze=True)
    i = 1
    length = len(series)
    for pair in series:
        print(f"Currently downloading: {i}/{length}")
        binance_download(pair, hourpath)
        i += 1
        clear_output()
    print(f"Operation took {round((time.time() - start)/60, 2)} minutes to download {length} files")




def binance_download(pair:str, path:str, start=1000000000000):
    """
    downloads binance data 
    """
    print(f"downloading {pair}")
    client = new_binance_client()
    start_date = datetime.utcfromtimestamp(start/1000).strftime("%d %b %Y %H:%M:%S")
    klines = client.get_historical_klines(pair, client.KLINE_INTERVAL_1HOUR, start_date, limit=1000)
    data = get_filtered_dataframe(klines)
    data.to_csv(path + pair + "-hour.csv", index=False)

def get_filtered_dataframe(klines):
    """filters columns and converts columns to floats and ints respectively"""
    df = pd.DataFrame(klines, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
    df = df[['timestamp', 'open']]
    df = df.astype(np.float64)
    df["timestamp"] = df.timestamp.astype(np.int64)
    return df

def download_all_available_margin_assets(pathname, filename):
    client = new_binance_client()
    symbols = client.get_all_isolated_margin_symbols()
    fsymbols = list(filter(lambda x: "USDT" in x["symbol"], symbols))
    pairs = list(map(lambda x: x["symbol"], fsymbols))
    pd.Series(pairs).to_csv(pathname + filename, index=False)

def new_binance_client():
    """inits new binance client"""
    api_key = get_api_keys("binance", "api")
    api_secret = get_api_keys("binance", "secret")
    return Client(api_key=api_key, api_secret=api_secret)


def get_api_keys(site: str, api_type: str)->str:
    """
    gets api keys stored in api-keys/api-keys.txt
    site: 'binance'
    api_type: 'api', 'secret'
    """
    with open('../api-keys/api-keys.txt') as json_file:
        return json.load(json_file)[site][api_type]
