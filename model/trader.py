import binance_helpers as bh
from binance.enums import * #https://github.com/sammchardy/python-binance/blob/master/binance/enums.py

class Trader:
    
    def __init__(self, strats):
        """inits a new trader that can fulfill trade obligations given by Model"""
        self.client = bh.new_binance_client()
        
    def go_long_short(long, short, usdt_amt):
        """places a market order to go long and takes a loan to go short"""
        # implementation
        
        l_asset = long[:-4]
        s_asset = short[:-4]
        
        usdt_amt = binance_floor(0.99*usdt_amt, 6)
        
        client.transfer_spot_to_isolated_margin(asset='USDT', symbol=long, amount=str(usdt_amt))
        client.transfer_spot_to_isolated_margin(asset='USDT', symbol=short, amount=str(usdt_amt))
        
        l_dp = bh.get_decimal_place(long)
        s_dp = bh.get_decimal_place(short)
        
        l_asset_price = bh.get_price(self.client, long)
        s_asset_price = bh.get_price(self.client, short)
        
        l_amt = bh.binance_floor(usdt_amt*0.97, l_dp)
        s_amt = bh.binance_floor(usdt_amt*0.97, s_dp) 
        
        self.go_short(self, short, s_asset, s_amt)
        self.go_long(self, long, l_asset, l_amt)
        
    def go_long(self, long, l_asset, amt):
        """goes long amt amount of long"""
        order = client.create_margin_order(
            symbol=long,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=amt,
            newOrderRespType = "FULL",
            isIsolated='TRUE')
        return order
    
    def go_short(self, short, s_asset, amt):
        """goes short amt amount of short"""
        transaction = client.create_margin_loan(asset=s_asset, amount=str(amt), isIsolated='TRUE', symbol=short)
        order = client.create_margin_order(
            symbol=short,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=amt,
            newOrderRespType = "FULL",
            isIsolated='TRUE')
        return transaction, order

    
        
    def liquidate(long, short, max_long, max_short, min_trade_amt):
        """liquidates current long and short position but under max_usdt_amt. If remaining 
        short position or long position is less than min_trade_amt, liquidate function ignores max_usdt_amt
        and liquidates all"""
        # implementation
        
        l_asset = long[:-4]
        s_asset = short[:-4]
        
        l_asset_price = bh.get_price(self.client, long)
        s_asset_price = bh.get_price(self.client, short)
        
        l_dp = bh.get_decimal_place(long)
        s_dp = bh.get_decimal_place(short)
        
        l_amt_base = bh.binance_floor(float(get_margin_asset(l_asset)["free"]), l_dp)
        s_amt_base = bh.binance_ceil(abs(float(get_margin_asset(s_asset)["netAsset"])), s_dp) #Positive
        
        l_usdt_amt = l_amt_base * l_asset_price
        s_usdt_amt = s_amt_base * s_asset_price
        
        l_pct = max_long/l_usdt_amt  # % of long position you can sell
        s_pct = max_short/s_usdt_amt # % of short position you can sell
        max_pct = min(l_pct, s_pct)  # max % to sell for both assets
        r_pct = max((1.-max_pct), 0.) # % of portfolio left if sold max_pct for both
        
        
        l_amt = bh.binance_floor(max_pct*l_usdt_amt, l_dp) #long position to sell
        l_r_amt = r_pct*l_usdt_amt #long position remaining
        s_amt = bh.binance_ceil(max_pct*s_usdt_amt, s_dp) #long position to sell
        s_r_amt = r_pct*s_usdt_amt #long position remaining
        
        sell_all = False
        
        if (l_amt > min_trade_amt) and (l_r_amt > min_trade_amt):
            #sell that much long position
            self.liquidate_long_position(long, l_amt)
        elif (l_r_amt > min_trade_amt): # $100 left but current max of buying $5, sell $20
            self.liquidate_long_position(long, bh.binance_floor(min_trade_amt/l_asset_price, l_dp))
        else: #only $30 left, sell $10, or sell $25
            #attempt to sell all
            sell_all = True
            
        if (s_amt > min_trade_amt) and (s_r_amt > min_trade_amt):
            #sell that much long position
            self.liquidate_short_position(short, s_asset, s_amt)
        elif (s_r_amt > min_trade_amt): # $100 left but current max of buying $5, sell $20
            self.liquidate_short_position(short, s_asset, bh.binance_floor(min_trade_amt/s_asset_price, s_dp))
        elif sell_all: #only $30 left, sell $10, or sell $25
            #attempt to sell all
            # Assumes there's enough to sell (ie not $5 left)
            self.liquidate_long_position(long, l_amt_base)
            self.liquidate_short_position(short, s_asset, s_amt_base)
            
        self.repay_loan(short, s_asset)
        
        if sell_all:
            self.move_money_to_spot(self, long, short, l_asset, s_asset)

        
    def liquidate_long_position(self, pair, amt):
        """liquidate the long position"""
        order = self.client.create_margin_order(
            symbol=pair,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=amt,
            newOrderRespType = "FULL",
            isIsolated='TRUE')
        return order
            
    def liquidate_short_position(self, pair, asset, amt):
        """liquidates short position and repays loan"""
        order = self.client.create_margin_order(
            symbol=pair,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=amt,
            newOrderRespType = "FULL",
            isIsolated='TRUE')
        return order
        
    def repay_loan(self, short, s_asset):
        """repays loan"""
        rp = str(abs(float(bh.get_margin_asset(short)["free"])))
        transaction = self.client.repay_margin_loan(asset=s_asset, amount=rp, isIsolated='TRUE', symbol=short)
        return transaction
        
    def move_money_to_spot(self, long, short, l_asset, s_asset):
        """moves all money to spot. Assumes finished closing out of trade"""
        l_usdt = str(bh.binance_floor(float(get_isolated_margin_account(l_asset)["quoteAsset"]["free"]), 6))
        s_usdt = str(bh.binance_floor(float(get_isolated_margin_account(s_asset)["quoteAsset"]["free"]), 6))

        self.client.transfer_isolated_margin_to_spot(asset='USDT', symbol=long, amount=l_usdt)
        self.client.transfer_isolated_margin_to_spot(asset='USDT', symbol=short, amount=s_usdt)

        
    def update_client(self):
        self.client = bh.new_binance_client()
        