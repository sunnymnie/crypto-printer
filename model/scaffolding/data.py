### NOT COMPLETE!!!
def get_filtered_dataframe(df):
    """filters columns and converts columsn to floats and ints respectively"""
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df = df.astype(np.float64)
    df["timestamp"] = df.timestamp.astype(np.int64)
    return df

def get_minutely_data(symbol:str, days=0.5):
    """smart gets minutely data. Enter symbol with USDT"""
    data_past = pd.read_csv(f"../data/{symbol}-past.csv")

    d = datetime.today() - timedelta(days=days)
    start_date = d.strftime("%d %b %Y %H:%M:%S")
    today = datetime.today().strftime("%d %b %Y %H:%M:%S")

    klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, start_date, today, 1000)
    data = pd.DataFrame(klines, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore' ])
    data = get_filtered_dataframe(data)

    index = data_past.index[(data_past['timestamp'] == data.iloc[0].timestamp)].tolist()[0]
    data = pd.concat([data_past[:index], data], ignore_index=True, sort=False)

    klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1MINUTE)
    data_latest = pd.DataFrame(klines, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore' ])
    data_latest = get_filtered_dataframe(data_latest)

    index = data.index[(data['timestamp'] == data_latest.iloc[0].timestamp)].tolist()[0]
    result = pd.concat([data[:index], data_latest], ignore_index=True, sort=False)
    result.to_csv(f"../data/{symbol}-past.csv", index=False)
    return result

def get_z_score(): 
    '''gets the latest z-score, given hedge ratio hr.
    Warning, sometimes it gives nan, just rerun (binance's fault)'''
    a = get_minutely_data(ASSET_A + BASE)
    b = get_minutely_data(ASSET_B + BASE)
    a.set_index("timestamp", inplace=True)
    b.set_index("timestamp", inplace=True)
    
    df = pd.to_numeric(a.open.rename("A")).to_frame()
    df["B"] = pd.to_numeric(b.open)
    
    df.dropna(inplace=True)
    
    results = sm.ols(formula="B ~ A", data=df[['B', 'A']]).fit()
    hr = results.params[1]
    spread = pd.Series((df['B'] - hr * df['A'])).rename("spread").to_frame()
    spread["mean"] = spread.spread.rolling(LOOKBACK).mean()
    spread["std"] =  spread.spread.rolling(LOOKBACK).std()
    spread["zscore"] = pd.Series((spread["spread"]-spread["mean"])/spread["std"])
    
    return spread.iloc[-1].zscore