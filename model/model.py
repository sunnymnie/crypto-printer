import binance_helpers as bh
from trader import Trader
from trade import Position, Trade
from strategy import Strategy
import schedule
import time

from IPython.display import clear_output #TEMPORARY!!
from datetime import datetime #TEMPORARY!!!!




class Model:
    def __init__(self, strats, min_trade_amt=20, max_slippage=0.1):
        """inits a Model with a list of strategies, minimum trade amount in USDT, and max slippage in %"""
        self.strats = strats #sorted with priority, strats[0] highest priority
        self.min_trade_amt = min_trade_amt
        self.max_slippage = max_slippage
        self.client = bh.new_binance_client()
        
    def update(self):
        """run and forget"""
        print(f"Model: update")
        clear_output() ########TEMPORARY##########TEMPORARY#########TEMPORARY####
        trader = Trader() #Need to init a new one because binance client 'expires'
        self.client = bh.new_binance_client()
        
        print("STARTING STRATS LOOP")
        
        for strat in self.strats:
            print(f"STARTING STRATS LOOP FOR {strat.a} and {strat.b}")            
            p, max_usdt_amt = self.get_position_and_max_trade_value(strat)
            trade = strat.consider_trading(p)
            if trade.to_trade:
                print(f"STRAT IS TO-TRADE")  
                try:
                    if not trade.liquidate: #buy or sell
                        print(f"STRAT IS TO-BUY")  
                        trade_amt = self.get_trade_amt(trade.long, trade.short, max_usdt_amt)
                        trader.go_long_short(trade.long, trade.short, trade_amt)
                        
                    else: #liquidate
                        print(f"STRAT IS TO-LIQUIDATE")  
                        max_long = bh.get_order_book(self.client, trade.long, self.max_slippage, False, True)
                        max_short = bh.get_order_book(self.client, trade.short, self.max_slippage, True, True)
                        trader.liquidate(trade.long, trade.short, max_long, max_short, self.min_trade_amt)
                except ValueError as e:
                    print(f"STRAT IS TO-LOW")  
                    pass
            print(f"ENDING STRATS LOOP FOR {strat.a} and {strat.b}")  
                    
            strat.save_data()
            
    def turn_on(self):
        schedule.clear()
        schedule.every().minute.at(":01").do(self.update)
        while True:
            schedule.run_pending()
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            print("Current Time =", current_time)
            time.sleep(1)

              
    def get_trade_amt(self, long, short, max_usdt_amt):
        """max per-asset trade amount to have slippage within maximum slippage. 
        If below minimum trade amount, throws exception"""
        print(f"Model: get_trade_amt for long:{long}, short{short}, max_usdt_amt:{max_usdt_amt}")
        print("============Trade amount calculation=================")
        mta = max_usdt_amt/2
        print(f"MODEL: mta = {mta}, max trade per side")
        usdt_balance = bh.get_usdt_balance(self.client)/2
        print(f"MODEL: usdt = {usdt_balance}, max usdt available per side")
        max_long = bh.get_order_book(self.client, long, self.max_slippage, True, True)
        print(f"MODEL: max_long = {max_long}, max long {long} from orderbook")
        max_short = bh.get_order_book(self.client, short, self.max_slippage, False, True)
        print(f"MODEL: max_short = {max_short}, max short {short} from orderbook")
        trade_amt = min(usdt_balance, max_long, max_short, mta)
        print(f"MODEL: trade_amt = {trade_amt}, lowest")
        self.assert_above_minimum_trade_amt(trade_amt)
        return trade_amt
    
#     def get_max_liquidate_amt(self, long, short):
#         """returns the max per-asset USDT amount to liquidate without exceeding max slippage.
#         If below minimum trade amount, throws exception"""
#         max_long = bh.get_order_book(self.client, long, self.max_slippage, True, True)
#         max_short = bh.get_order_book(self.client, short, self.max_slippage, False, True)
#         max_amt = min(max_long, max_short)
#         self.assert_above_minimum_trade_amt(max_amt)
#         return max_amt
    
    def assert_above_minimum_trade_amt(self, trade_amt):
        """throws ValueError if less than minimum trade amount"""
        print(f"Model: assert_above_min_trade_amt w/ trade_amt {trade_amt}")
        if trade_amt < self.min_trade_amt:
            raise ValueError(f'Amount to trade ({trade_amt}) below minimum amount ({self.min_trade_amt})')
    
    def get_portfolio_value(self, ima, btc_price):
        """gets the estimated net USDT value of entire portfolio given isolated margin accounts
        REQUIRES: Quote asset in USDT"""
        print(f"Model: get_portfolio_value with btc_price {btc_price} with # of strats: {len(self.strats)}")
        value = 0
        value += bh.get_usdt_balance(self.client)
        for strat in self.strats:
            value += self.get_pair_value(ima, strat.a, btc_price)
            value += self.get_pair_value(ima, strat.b, btc_price)
        return value

    def get_pair_value(self, ima, pair:str, btc_price):
        """returns the total USDT value of the strat given pair. REQUIRES pair have USDT as quote. 
        If strat does not exist or has non USDT as quote, returns 0"""
        print(f"Model: get_pair_value for pair:{pair}")
        try:
            strat_val = self.get_pair_from_ima(ima, pair)
            quote_val = float(strat_val['baseAsset']['netAssetOfBtc']) * btc_price
            usdt_val = float(strat_val['quoteAsset']['netAsset'])
            total_val = quote_val + usdt_val
            return total_val
        except:
            return 0.

    def is_short(self, ima, pair:str):
        """returns True if is short this asset (net asset of base is negative). False if asset doesn't exist"""
        print(f"Model: is_short for pair: {pair}")
        try: 
            strat_val = self.get_pair_from_ima(ima, pair)
            quote_val = float(strat_val['baseAsset']['netAssetOfBtc'])
            return quote_val < 0
        except:
            return False

    def get_pair_from_ima(self, ima, pair:str):
        """returns dictionary of pair from isolated margin accounts list of dictionaries. 
        REQUIRES pair has USDT as quote asset"""
#         print(f"Model: get_pair_from_ima for pair {pair}")
        return list(filter(lambda x: x["baseAsset"]["asset"] == pair[:-4], ima["assets"]))[0]

    def get_position_and_max_trade_value(self, strat):
        """gets the current Position of the strat and the maximum value it can buy/short
        until it crosses over strat's maximum allocation"""
        print(f"Model: get_position_and_max_trade_value")
        ima = self.client.get_isolated_margin_account()
        btc_price = bh.get_price(self.client, "BTCUSDT")
        pv = self.get_portfolio_value(ima, btc_price)   #portfolio value
        sv = self.get_pair_value(ima, strat.a, btc_price) + self.get_pair_value(ima, strat.b, btc_price) #Strat value
        print(f"MODEL: pv={pv}, sv={sv}")
        mta = (pv * strat.max_portfolio) - sv      #Max trade amount

        position = None

        if self.is_short(ima, strat.a):
            if mta > self.min_trade_amt:
                position = Position.B_PARTIAL
            elif mta <= self.min_trade_amt:
                position = Position.B
        elif self.is_short(ima, strat.b):
            if mta > self.min_trade_amt:
                position = Position.A_PARTIAL
            elif mta <= self.min_trade_amt:
                position = Position.A
        else:
            position = Position.NONE

        return position, max(0, mta)


