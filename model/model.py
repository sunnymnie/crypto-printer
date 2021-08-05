import binance_helpers as bh
from trader import Trader
from trade import Position, Trade
from strategy import Strategy


class Model:
    def __init__(self, strats, min_trade_amt=20, max_slippage=0.1):
        self.strats = list(Strategy) #sorted with priority, strats[0] highest priority
        self.min_trade_amt = min_trade_amt
        self.max_slippage = max_slippage
        self.client = bh.new_binance_client()
        
    def update(self):
        """run and forget"""
        trader = Trader() #Need to init a new one because binance client 'expires'
        self.client = bh.new_binance_client()
        
        for strat in self.strats:
                        
            p, max_usdt_amt = self.get_position_and_max_trade_value(strat)
            trade = strat.consider_trading(p)
            if trade.to_trade:
                try:
                    if not trade.liquidate: #buy or sell
                        trade_amt = self.get_trade_amt(trade.long, trade.short, max_usdt_amt)
                        trader.go_long_short(trade.long, trade.short, trade_amt)
                    else: #liquidate
                        trade_amt = self.get_trade_amt(trade.short, trade.long, max_usdt_amt)
                        trader.liquidate(trade.long, trade.short, trade_amt)
                except ValueError as e:
                    pass
                    
            strat.save_data()
            
    def turn_on(self):
        #🛑
        ## Using schedule, run `update` every minute
        ## schedule.clear()
        ## schedule.every().minute.at(":01").do(printer)

              
    def get_trade_amt(self, long, short, max_usdt_amt):
        """max trade to have slippage within maximum slippage. If below minimum
        trade amount, throws exception"""
        max_long = bh.get_order_book(self.client, long, self.max_slippage, True, True)
        max_short = bh.get_order_book(self.client, short, self.max_slippage, False, True)
        trade_amt = min(max_long, max_short, max_usdt_amt)
        if trade_amt < self.min_trade_amt:
            raise ValueError(f'Amount to trade ({trade_amt}) below minimum amount ({self.min_trade_amt})')
        return trade_amt
        
    def get_portfolio_value(self):
        """gets the estimated net USDT value of entire portfolio"""
        value = 0
        for strat in self.strats:
            #🛑
            #value += x
        return value
    
    def get_position_and_max_trade_value(self, strat):
        """gets the current Position of the strat and the maximum value it can buy/short
        until it crosses over strat's maximum allocation"""
        #🛑
        # Calculation: sees if start's current assets above % portfolio allocated
        # etc. 
        return Position.NONE, 0
        
        
        