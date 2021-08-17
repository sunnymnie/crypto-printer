import pandas as pd
import numpy as np
from binance.client import Client
from datetime import datetime
import json
import time
from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from IPython.display import clear_output

def filter_by_cmc_rank(pathname, filename, cmc_rank=200):
    """filters file to only contain assets above cmc_rank"""
    df = pd.read_csv(pathname + filename, squeeze=True)
    string = ""
    for i in df:
        string += "," + i[:-4]
    string = string[1:]
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest'
    parameters = {
        'symbol':string,
        'skip_invalid':True
    }
    headers = {
      'Accepts': 'application/json',
      'X-CMC_PRO_API_KEY': get_api_keys("coinmarketcap", "api")
    }
    session = Session()
    session.headers.update(headers)

    try:
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        print(e)
        
    new = []
    for i in df:
        try:
            if data["data"][i[:-4]]["cmc_rank"] < cmc_rank:
                new.append(i)
        except:
            pass
    pd.Series(new).to_csv(pathname + filename, index=False)
    print(f"Successfully filtered {len(df)-len(new)} assets out, only {len(new)} remain")

def download_all_minutely_data(restart, cont, pathname, minutepath, do, cdo):
    if restart == cont:
        raise ValueError("Do you want to restart or continue from last left off?")
        
    if restart:
        order = pd.read_csv(pathname + do, squeeze=True)
        pd.Series(order).to_csv(pathname + cdo, index=False)
        
    order = pd.read_csv(pathname + cdo, squeeze=True)
    
    while len(order)>0:
        try:
            pair = order.iloc[0]
            print(f"Currently downloading {pair}, {len(order)} remaining")
            binance_download_minute(pair, minutepath)
            order = order[1:]
            pd.Series(order).to_csv(pathname + cdo, index=False)
            time.sleep(30)
            clear_output()
        except:
            try:
                print(f"Error in downloading {pair}, resting 5 minutes. Kill kernal again to quit")
                time.sleep(300)
            except:
                print("Successfully quit")
                return




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

def get_download_order(pathname, adf_stat, filename):
    """saves the download order"""
    df = pd.read_csv(pathname + adf_stat)
    symbols = []
    for row in range(df.shape[0]):
        symbols.append(df.iloc[row].A)
        symbols.append(df.iloc[row].B)

    seen = set()
    seen_add = seen.add
    symbols = [x for x in symbols if not (x in seen or seen_add(x))]
    pd.Series(symbols).to_csv(pathname + filename, index=False)



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
    
def binance_download_minute(pair:str, path:str, start=1000000000000):
    """
    downloads binance data 
    """
    client = new_binance_client()
    start_date = datetime.utcfromtimestamp(start/1000).strftime("%d %b %Y %H:%M:%S")
    klines = client.get_historical_klines(pair, client.KLINE_INTERVAL_1MINUTE, start_date, limit=1000)
    data = get_filtered_minute_dataframe(klines)
    data.to_csv(path + pair + "-minute.csv", index=False)

def get_filtered_dataframe(klines):
    """filters columns and converts columns to floats and ints respectively"""
    df = pd.DataFrame(klines, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
    df = df[['timestamp', 'open']]
    df = df.astype(np.float64)
    df["timestamp"] = df.timestamp.astype(np.int64)
    return df

def get_filtered_minute_dataframe(klines):
    """filters columns and converts columns to floats and ints respectively"""
    df = pd.DataFrame(klines, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
    df = df[['timestamp', 'open', 'high', 'low']]
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
