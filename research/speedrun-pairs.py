import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import math
from IPython.display import clear_output
import time

import statsmodels.formula.api as sm
import statsmodels.tsa.stattools as ts
import statsmodels.tsa.vector_ar.vecm as vm

import scipy.stats as st
import math
# from tqdm import tqdm

pairs = pd.read_csv("../crypto-printer/data/pairs/coint-stats-filtered.csv")
pairs = pairs[:4]


def get_hedge_ratio_and_index(a, b, ds=100):
    """gets hedgeratio. a and b must include USDT. ds is downsample"""
    df1 = pd.read_csv(f"data/hour/{a}-hour.csv", index_col=0, parse_dates=True)
    df2 = pd.read_csv(f"data/hour/{b}-hour.csv", index_col=0, parse_dates=True)
    df = df1.open.rename("A").to_frame()
    df["B"] = df2.open
    df = df[100:]
    df = df.dropna()

    hedge_ratio = np.full(df.shape[0], np.nan)
    l = math.floor(len(hedge_ratio)/ds)
    index = []
    for t in np.arange(l):
        clear_output()
        print(f"{t} < {l}")
        regress_results = sm.ols(formula="B ~ A",
                                 data=df[:t*ds+1]).fit()  # Note this can deal with NaN in top row
        hedge_ratio[t] = regress_results.params[1]
        index.append(df.index[t*ds+1])
    return hedge_ratio, index, df, df1, df2


def get_spread(lookback, length=700_000):
    """returns the spread. Lookback is for mean and std. length is [-length:] of spread"""
    hr = pd.Series(hedge_ratio).dropna().rename("hr").to_frame()

    hr["index"] = hr_index
    hr.set_index("index", inplace=True)

    spread = pd.DataFrame(hr.hr, index=df.index)

    spread.ffill(inplace=True)

    spread = pd.Series((df['B'] - spread["hr"] * df['A'])).rename("spread").to_frame()
    spread["mean"] = spread.spread.rolling(lookback).mean()
    spread["std"] =  spread.spread.rolling(lookback).std()
    spread["zscore"] = pd.Series((spread["spread"]-spread["mean"])/spread["std"])

    spread = spread.dropna()

    spread["A"] = df1["close"].reindex(spread.index)
    spread["Ah"] = df1["high"].reindex(spread.index)
    spread["Al"] = df1["low"].reindex(spread.index)

    spread["B"] = df2["close"].reindex(spread.index)
    spread["Bh"] = df2["high"].reindex(spread.index)
    spread["Bl"] = df2["low"].reindex(spread.index)
    return spread[-length:]

def get_a_b(al, ac, ah, bl, bc, bh):
#     return ac-abs(ac-al)/2, ac+abs(ac-ah)/2, bc-abs(bc-bl)/2, bc+abs(bc-bh)/2
    return ac, ac, bc, bc

def run_backtest(spread, thres, sell_thres, fee=0.000, interest=0.001):
    total, p_total = 0, 0 #Previous total
    cusum, returns = [], []
    price_a, price_b, long = None, None, None #Values: None, "A", "B"
    long_a, long_b, liquidate,  dd_indices= [], [], [], [] #Drawdown indicies
    dd_i = True
    for i in range(spread.shape[0]):
        z = spread.zscore[i]
        if long == None: # Looking to buy
            if z>thres or z<-thres:
                al, ah, bl, bh = get_a_b(spread.Al[i], spread.A[i], spread.Ah[i], spread.Bl[i], spread.B[i], spread.Bh[i])
                price_a = ah if z > thres else al
                price_b = bl if z > thres else bh
                long = "A" if z > thres else "B"
                long_a.append(spread.index[i]) if z > thres else long_b.append(spread.index[i])
        if (long == "A" and z<-sell_thres) or (long == "B" and z>sell_thres): #Liquidate positions
            al, ah, bl, bh = get_a_b(spread.Al[i], spread.A[i], spread.Ah[i], spread.Bl[i], spread.B[i], spread.Bh[i])
            gain = 0
            if long=="A":
                gain = liquidate_assets(price_b, bh, al, price_a, fee, long_a[-1], spread.index[i], interest)
            else:
                gain = liquidate_assets(price_a, ah, bl, price_b, fee, long_b[-1], spread.index[i], interest)
            returns.append(gain)
            total += gain
            price_a, price_b, long = None, None, None
            liquidate.append(spread.index[i])
        cusum.append(total)

        if total < p_total:
            if dd_i:
                dd_indices.append(spread.index[i])
                dd_i = False
        else:
            if not dd_i:
                dd_indices.append(spread.index[i])
                dd_i = True
            p_total = total
    if total < p_total:
        dd_indices.append(spread.index[i])
    drawdowns = get_drawdowns(dd_indices)
    return long_a, long_b, liquidate, cusum, returns, drawdowns

def liquidate_assets(x1, x2, y1, y2, fee, d1, d2, interest):
    interest = ((d2-d1).days + 1) * interest
    total = (x1 - x2)/x1 - 2*fee - interest
    total += (y1 - y2)/y1 - 2*fee - interest
    return total

def get_drawdowns(dd_indices, sort=False):
    a = dd_indices[1::2]
    b = dd_indices[::2]
    a = np.array(a)
    b = np.array(b[:len(a)])
    c = a-b
    if sort:
        c.sort()
        c = c[::-1]
    return c

def convert_timedelta_to_seconds(td):
    """converts timedelta to seconds"""
    return td.days*24*60*60 + td.seconds

# Dictionary that would be saved as dataframe
pair_results = {"A":[],
                "B":[],
                "lookback":[],
                "max_sharpe":[],
                "max_fsharpe":[],
                "max_winrate":[],
                "avg_winloss":[],
                "trades":[]
               }

start_time = time.time()
for i in range(pairs.shape[0]):
    a = pairs.A.iloc[i]
    b = pairs.B.iloc[i]
    hedge_ratio, hr_index, df, df1, df2 = get_hedge_ratio_and_index(a, b)
    for lookback in [int(1000/60), int(2000/60), int(4000/60), int(6000/60)]:                              #Don't change this
        d = {"lookback":[], "thres":[], "sell_thres":[], "cusum":[], "returns":[], "drawdowns":[]}
        spread = get_spread(lookback)

        for thres in [0.5, 1., 1.5, 2., 3.]:                               #Don't change this

            for sell_thres in [-2., -1., -0.5, 0., 0.5, 1., 1.5, 2., 3.]:  #Don't change this
                if sell_thres <= -thres:
                    continue

                print(f"Now doing a: {a}, b: {b}")
                print(f"Now doing lookback: {lookback}, thres: {thres}, sell_thres: {sell_thres}, safe to kill kernel")

                long_a, long_b, liquidate, cusum, returns, drawdowns = run_backtest(spread, thres, sell_thres)

                d["lookback"].append(lookback)
                d["thres"].append(thres)
                d["sell_thres"].append(sell_thres)
                d["cusum"].append(cusum)
                d["returns"].append(list(map(lambda x: round(x, 5), returns)))
                d["drawdowns"].append(list(map(lambda x: convert_timedelta_to_seconds(x), drawdowns)))

                clear_output()

        d = pd.DataFrame(d)

        sharpes = []
        filtered_sharpes = []
        win_rates = []
        avg_wins = []
        avg_losses = []
        trades = []

        for index, row in d.iterrows():
            r = row['returns']
            sharpe = np.sqrt(len(r)) * np.nanmean(r) / np.nanstd(r)
            if (pd.Series(row['drawdowns']).max() < 2592000*2) and (min(r) > -0.2*2):
                filtered_sharpes.append(sharpe)
            sharpes.append(sharpe)
            filtered_sharpes.append(-999.0)
            win_rates.append(sum(i > 0 for i in r)/len(r))
            avg_wins.append(np.mean([i for i in r if i > 0]))
            avg_losses.append(np.mean([i for i in r if i < 0]))
            trades.append(len(returns))

        pair_results["A"].append(a)
        pair_results["B"].append(b)
        pair_results["lookback"].append(lookback)
        pair_results["max_sharpe"].append(max(sharpes))
        pair_results["max_fsharpe"].append(max(filtered_sharpes))
        pair_results["max_winrate"].append(max(win_rates))
        pair_results["avg_winloss"].append((np.mean(avg_wins), np.mean(avg_losses)))
        pair_results["trades"].append(np.mean(trades))

    pd.DataFrame(pair_results).to_csv("data/pairs/pairs.csv", index=False)    #Don't change this

print(time.time()-start_time)
