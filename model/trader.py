import binance_helpers as bh
class Trader:
    
    def __init__(self, strats):
        self.client = bh.new_binance_client()
        
    def go_long_short(long, short, usdt_amt):
        """places a market order to go long and takes a loan to go short"""
        # implementation
        
    def liquidate(long, short, usdt_amt):
        """liquidates current long and short position and return loan. Will liquidate all if 
        remaining is less than $20"""
        # implementation
        
    def update_client():
        self.client = bh.new_binance_client()
        