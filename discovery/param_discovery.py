import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import math
from IPython.display import clear_output
import matplotlib.pyplot as plt
import time

import statsmodels.formula.api as sm
import statsmodels.tsa.stattools as ts
import statsmodels.tsa.vector_ar.vecm as vm

import scipy.stats as st
import math

def brute_force_search(restart, cont, pathname, adf, cadf, results):
    """brute force search. cadf is current adf"""
    if restart == cont:
        raise ValueError("Do you want to restart or continue from last left off?")
        
    if restart:
        pairs = pd.read_csv(pathname + adf)
        pairs.to_csv(pathname + cadf, index=False)
        pair_results = pd.DataFrame(columns=["A", "B", "lookback", "thres", "sell_thres", 
                                             "sharpe", "winrate", "avg_winloss", "trades"])
        pair_results.to_csv(pathname + results, index=False)
        
    pairs = pd.read_csv(pathname + cadf)
    pair_results = pd.read_csv(pathname + results)
        
    while len(pairs)>0:
        print(f"Remaining: {len(pairs)}")
#     for i in range(pairs.shape[0]):
#         try:
        a = pairs.A.iloc[0]
        b = pairs.B.iloc[0]
        cutoff = 86400

        can_read = False
        while not can_read:
            try:
                pd.read_csv(f"../data/minute/{a}-minute.csv", index_col=0, parse_dates=True)
                pd.read_csv(f"../data/minute/{b}-minute.csv", index_col=0, parse_dates=True)
                can_read = True
            except: 
                print(f"Failure to read {a} or {b}, sleeping for 5 minutes")
                time.sleep(300)
                
#         try: 

        hedge_ratio, hr_index, df, df1, df2 = get_hedge_ratio_and_index(a, b)

        d = do_backtest_for_loop(a, b, hedge_ratio, hr_index, df, df1, df2,
                                 [3000, 4000, 5000, 6000], [2., 3., 4.], [-0.5, 0, 0.5]) 

        lookbacks, threses, sell_threses, preliminary_sharpe_df = get_best_sharpe_params(d)

        preliminary_sharpe_df.to_csv(f"../data/generated/backtests/{a}-{b}-sharpe.csv", index=False)

        d = do_backtest_for_loop(a, b, hedge_ratio, hr_index, df, df1, df2, lookbacks, threses, sell_threses)

        _, _, _, main_sharpe_df = get_best_sharpe_params(d)

        plot_results(main_sharpe_df, "backtest-graphs", a, b)
        main_sharpe_df.to_csv(f"../data/generated/backtests/{a}-{b}-sharpe-narrowed.csv", index=False)

        lookbacks = list(set(list(main_sharpe_df.lookback)))
        threses = list(set(list(main_sharpe_df.thres)))
        sell_threses = list(set(list(main_sharpe_df.sell_thres)))

        hedge_ratio, hr_index, df, df1, df2 = get_hedge_ratio_and_index(a, b, test_future=True)
        d = do_backtest_for_loop(a, b, hedge_ratio, hr_index, df, df1, df2, lookbacks, threses, sell_threses, cutoff)

        _, _, _, d = get_best_sharpe_params(d)
        d = d.sort_values("sharpe", ascending=False)
        plot_results(d, "forwardtest-graphs", a, b)
        d.to_csv(f"../data/generated/forwardtests/{a}-{b}-forward-test.csv", index=False) 

        pair_results = update_pair_results(pair_results, a, b, d.iloc[0])
#         except:
#             try:
#                 print(f"Error in processing {a} and {b}, kill kernal again to quit")
#                 time.sleep(300)
#             except:
#                 print(f"Successfully quit")
#                 return
        pair_results.to_csv(pathname + results, index=False)
        pair_results = pd.read_csv(pathname + results)
        pairs[1:].to_csv(pathname + cadf, index=False)
        pairs = pd.read_csv(pathname + cadf)
    

def update_pair_results(pair_results, a, b, row):
    pair_results = pair_results.append({"A":a, 
                                        "B":b, 
                                        "lookback":row.lookback, 
                                        "thres":row.thres,
                                        "sell_thres":row.sell_thres,
                                        "sharpe":row.sharpe, 
                                        "winrate":row.winrate,
                                        "avg_winloss":row.avg_winloss,
                                        "trades":row.trades}, ignore_index=True)
    return pair_results
    


def get_hedge_ratio_and_index(a, b, ds=1000, cutoff=86400, test_future=False):
    """gets hedgeratio. a and b must include USDT. ds is downsample, cutoff is in minutes"""
    df1 = pd.read_csv(f"../data/minute/{a}-minute.csv", index_col=0, parse_dates=True)
    df2 = pd.read_csv(f"../data/minute/{b}-minute.csv", index_col=0, parse_dates=True)
    df = df1.open.rename("A").to_frame()
    df["B"] = df2.open
    df = df[1000:] if test_future else df[1000:-cutoff]
    
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
    

def get_spread(lookback, hedge_ratio, hr_index, df, df1, df2, length=700_000):
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

    spread["A"] = df1["open"].reindex(spread.index)
    spread["Ah"] = df1["high"].reindex(spread.index)
    spread["Al"] = df1["low"].reindex(spread.index)

    spread["B"] = df2["open"].reindex(spread.index)
    spread["Bh"] = df2["high"].reindex(spread.index)
    spread["Bl"] = df2["low"].reindex(spread.index)
    return spread[-length:]

def get_a_b(al, ac, ah, bl, bc, bh):
#     return ac-abs(ac-al)/2, ac+abs(ac-ah)/2, bc-abs(bc-bl)/2, bc+abs(bc-bh)/2
    return ac, ac, bc, bc

def run_backtest(spread, thres, sell_thres, fee=0.002, interest=0.002):
    total, p_total = 0, 0 #Previous total
    returns = []
    price_a, price_b, long = None, None, None #Values: None, "A", "B"
    long_a, long_b,  dd_indices= [], [], [] #Drawdown indicies
    dd_i = True
    spread = spread.reset_index(drop=True)
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
    return returns, drawdowns
        
def liquidate_assets(x1, x2, y1, y2, fee, d1, d2, interest):
    interest = ((d2-d1)/(60*24)) * interest
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

# def convert_timedelta_to_seconds(td):
#     """converts timedelta to seconds"""
#     return td.days*24*60*60 + td.seconds

def do_backtest_for_loop(a, b, hedge_ratio, hr_index, df, df1, df2, lookbacks, thress, sell_thress, length=700_000):
    """Does the backtest forloop and returns the df generated (and saves df)"""
    d = {"lookback":[], "thres":[], "sell_thres":[], "returns":[], "drawdowns":[]}
    for lookback in lookbacks:                          #Don't change this
        spread = get_spread(lookback, hedge_ratio, hr_index, df, df1, df2, length)

        for thres in thress:                               #Don't change this

            for sell_thres in sell_thress:                    #Don't change this 
                    
                print(f"Now doing a: {a}, b: {b}")
                print(f"Now doing lookback: {lookback}, thres: {thres}, sell_thres: {sell_thres}, safe to kill kernel")
                
                returns, drawdowns = run_backtest(spread, thres, sell_thres)

                d["lookback"].append(lookback)
                d["thres"].append(thres)
                d["sell_thres"].append(sell_thres)
                d["returns"].append(list(map(lambda x: round(x, 5), returns)))
                d["drawdowns"].append(list(map(lambda x: x*60, drawdowns)))

                clear_output()

    d = pd.DataFrame(d)
    return d

def plot_results(result, folder, a, b):
    result = result.nlargest(10,'sharpe')
    fig, ax = plt.subplots(figsize=(20, 10))
    for index, row in result.iterrows():
        pd.Series(pd.Series(row['returns']).cumsum()).plot(legend=True)
    ax.legend(result.index)
    plt.close()
    fig.savefig(f'../data/generated/{folder}/{a}-{b}.png') #For final round
    
def get_best_sharpe_params(d):
    """
    returns three lists of floats and the resulting dataframe: 
        1. first list has 3 lookbacks, ie [4500, 5000, 5500]
        2. second list has 3 thres, ie [3.3, 3.6, 3.9]
        3. third list has 2 sell_thres, ie [0, 0.24]
        4. resulting dataframe without cusum, including mxdd and sharpe (i don't think d has cusum...)
        
        List (1) values MUST be separated by 500 each
            - Middle value should be the mean of the top N strats ordered by highest sharpe
            - Must be of type int
            - Can be something like [3346, 3846, 4346]
        List (2) values MUST be separated by 0.3
            - Find the mean thres for top N strats orderd by highest sharpe
        List (3) same logic as above, but find mean sell_thres of top N, 
            then -0.12 from it and +0.12 the other to get the two values
            
        Note: The above criteria is my thoughts, if you think your idea is better, implement that instead
        NOTE: d HAS ALL THREE OF THE LOOKBACKS UNLIKE IN pairs-discovery WHERE IT HAD THE SAME LOOKBACK
        """
    results = pd.DataFrame({"lookback":[], 
                            "thres":[],
                            "sell_thres":[],
                            "returns":[],
                            "drawdowns":[],
                            "mxdd":[],
                            "sharpe":[], 
                            "dd_filtered":[], 
                            "winrate":[],
                            "avg_winloss":[],
                            "trades":[]
                           })

    results["lookback"] = d['lookback'].copy()
    results["thres"] = d['thres'].copy()
    results["sell_thres"] = d['sell_thres'].copy()
    results["returns"] = d['returns'].copy()
    results["drawdowns"] = d['drawdowns'].copy()

    mxdd = []
    sharpe = []
    dd_filtered = []
    winrate = []
    avg_winloss = []
    trades = []
    
    for _, row in results.iterrows():
        r = row['returns']
        mxdd.append(max(row['drawdowns']+[0]))
        sharpe.append(np.sqrt(len(r)) * np.nanmean(r) / np.nanstd(r))
        dd_filtered.append((row['mxdd'] > 2592000*2) and (min(r) < -0.2*2))
        winrate.append(sum(i > 0 for i in r)/len(r))
        avg_winloss.append(np.mean([i for i in r if i > 0]))
        trades.append(len(r))
        
    results['mxdd'] = mxdd
    results['sharpe'] = sharpe
    results['dd_filtered'] = dd_filtered
    results['winrate'] = winrate
    results['avg_winloss'] = avg_winloss
    results['trades'] = trades

#     results = results.sort_values(['dd_filtered', 'sharpe'], ignore_index=True)
    results = results.sort_values('sharpe', ascending=False, ignore_index=True)
    
    top = results.head(3)

    lb = int(top['lookback'].mean())
    ts = round(top['thres'].mean(), 2)
    sts = round(top['sell_thres'].mean(), 2)
        
    return [lb-500, lb, lb+500], [ts-0.3, ts, ts+0.3], [sts-0.25, sts, sts+0.25], results