import pandas as pd
import numpy as np
import time

import statsmodels.formula.api as sm
import statsmodels.tsa.stattools as ts
import statsmodels.tsa.vector_ar.vecm as vm

from IPython.display import clear_output

def compute_adf_tests(pathname, hourpath, symbols, filename, lower=10000):
    """computes the adf tests, saves as filename. 
    All files included in test must have greater than lower hours"""

    start = time.time()
    loc = list(pd.read_csv(pathname + symbols, squeeze=True))
    stats = pd.DataFrame(columns=["A", "B", "t", "p", "h"])
    i = 1
    length = len(loc)
    for a in loc:
        print(f"Analyzing {a} ({i}/{length})")
        i += 1
        for b in loc[loc.index(a)+1:]:
            df1 = pd.read_csv(hourpath + a + "-hour.csv", index_col=0, parse_dates=True)
            if len(df1)<lower:
                continue
            df2 = pd.read_csv(hourpath + b + "-hour.csv", index_col=0, parse_dates=True)
            if len(df2)<lower:
                continue
            df = df1.open.rename("A").to_frame()
            df["B"] = df2.open
            df = df.dropna()
            df = df[1000:]
            
            coint_t, pvalue, crit_value = ts.coint(df['B'], df['A'])

            result = vm.coint_johansen(df[['A', 'B']].values, det_order=0, k_ar_diff=1)
            yport = pd.DataFrame(np.dot(df.values, result.evec[:, 0]))  # (net) market value of portfolio
            ylag = yport.shift()
            deltaY = yport - ylag
            df2 = pd.concat([ylag, deltaY], axis=1)
            df2.columns = ['ylag', 'deltaY']
            regress_results = sm.ols(formula="deltaY ~ ylag", data=df2).fit()
            halflife = -np.log(2) / regress_results.params['ylag']
            stats = stats.append({"A":a, "B":b, "t":coint_t, "p":pvalue, "h":halflife}, ignore_index=True)
        clear_output()
    stats.to_csv(pathname+filename, index=False)
    print(f"Operation took {round((time.time() - start)/60, 2)} minutes")
