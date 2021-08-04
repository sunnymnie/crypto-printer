from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import math
import statsmodels.formula.api as sm
from binance.client import Client

class Downloader: 
	def __init__(self, client, path):
		self.client = client
		self.path = path
		
	def get_minutely_data(self, pair:str):
		"""smartly downloads and returns minutely data. Enter pair with USDT"""
		df_past = self.get_past_bars(pair)
		df_now = self.binance_download(pair, df_past.iloc[-1].timestamp)
		
		df = df_past[df_past.timestamp < df_now.iloc[0].timestamp]
		df = df.append(df_now, ignore_index=True)
		
		return df
		
	def get_past_bars(self, pair):
		"""returns downloaded data if it exists, else downloads and returns"""
		try:
			return self.read_df(pair)
		except:
			return self.binance_download(pair)
		
	def binance_download(self, pair:str, start=1000000000000):
		"""
		downloads binance data and returns it. Set save to true to save
		pair: BTCUSDT
		start: float date. Leave as is for from the very beginning (2001). 
		"""
		start_date = self.get_str_date(self.get_date_from_int(start))
		klines = self.client.get_historical_klines(pair, self.client.KLINE_INTERVAL_1MINUTE, start_date, limit=1000)
		data = self.get_filtered_dataframe(klines)
		return data
		
	def get_filtered_dataframe(self, klines):
		"""filters columns and converts columns to floats and ints respectively"""
		df = pd.DataFrame(klines, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])
		df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
		df = df.astype(np.float64)
		df["timestamp"] = df.timestamp.astype(np.int64)
		return df
	
	def get_date_from_int(self, date:int, delay=600):
		"""returns datetime object from int minus delay in seconds"""
		return datetime.utcfromtimestamp(date/1000) - timedelta(seconds=delay)
	
	def get_str_date(self, date):
		"""returns the string date given datetime date. Use for getting klines"""
		return date.strftime("%d %b %Y %H:%M:%S")
	
	def save_df(self, df, pair):
		"""saves the dataframe"""
		df.to_csv(f"{self.path + pair}-past.csv", index=False)
		
	def read_df(self, pair):
		"""reads the dataframe"""
		return pd.read_csv(f"{self.path + pair}-past.csv")

class Magic:
	def __init__(self, lookback):
		self.lookback = lookback
		
	def get_z_score(self, a, b):
		"""Returns the latest zscore between dataframes a and b. IF NAN, RETURN PREVIOUS"""
		a = a.set_index("timestamp") #Do not set inplace cause reference
		b = b.set_index("timestamp")

		df = pd.to_numeric(a.open.rename("A")).to_frame()
		df["B"] = pd.to_numeric(b.open)

		df.dropna(inplace=True)

		results = sm.ols(formula="B ~ A", data=df[['B', 'A']]).fit()
		hr = results.params[1]
		spread = pd.Series((df['B'] - hr * df['A'])).rename("spread").to_frame()
		spread["mean"] = spread.spread.rolling(self.lookback).mean()
		spread["std"] = spread.spread.rolling(self.lookback).std()
		spread["zscore"] = pd.Series((spread["spread"]-spread["mean"])/spread["std"])

		return self.get_non_nan_zscore(spread)
	
	def get_non_nan_zscore(self, spread):
		"""loops through spread finding latest non-nan zscore"""
		zscore = spread.iloc[-1].zscore
		i = 2
		while math.isnan(zscore):
			zscore = spread.iloc[-i].zscore
			i += 1
		return zscore