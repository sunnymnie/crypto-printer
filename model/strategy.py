#import binance client
from downloader import Downloader
from magic import Magic
from trade import Position, Trade

class Strategy:
    def __init__(self, a, b, thres, sell_thres, lookback, max_portfolio):
        self.a = a                          # FETUSDT
        self.b = b                          # CELRUSDT
        self.thres = thres                  # 3.4
        self.sell_thres = sell_thres        # 0.25
        self.max_portfolio = max_portfolio  # 0.8
        self.m = Magic(lookback)
        self.long = Position
        self.dl = Downloader()
        
        self.df_a = self.dl.read_df(self.a)
        self.df_b = self.dl.read_df(self.b)
        self.time_of_last_save = self.df_a.iloc[-1].timestamp
        self.z = self.m.get_z_score(self.df_a, self.df_b)
        
    def update_data(self):
        """updates df_a, and df_b"""
        self.df_a = dl.update_data(self.a, self.df_a)
        self.df_b = dl.update_data(self.b, self.df_b)
        
    def consider_trading(self, p):
        """If trading opportunity, returns trade object, does not tell how much to trade"""
        self.update_data()
        self.z = self.m.get_z_score(self.df_a, self.df_b)
        trade = Trade(False)
        if p == long.A or p == long.B:
            trade = self.consider_liquidating()
        elif p == long.A_PARTIAL or p == long.B_PARTIAL:
            trade = self.consider_liquidating()
            trade = self.consider_long_short() if not trade.to_trade else trade
        else: #p == long.NONE
            trade = self.consider_long_short()
        return trade
        
            
    def consider_long_short():
        """consider a long trade or a short trade"""
        if self.z > self.thres:
            return Trade(True, False, self.a, self.b)
        elif self.z < -self.thres:
            return Trade(True, False, self.b, self.a)
        return Trade(False)
    
    def consider_liquidating():
        if self.z < -self.sell_thres:
            return Trade(True, True, self.a, self.b)
        elif self.z > self.sell_thres:
            return Trade(True, True, self.b, self.a)
        return Trade(False)
        
        
    def save_data(self):
        """saves dfs and sets time of last save"""
        last_save = self.dl.save_df_fast(self.a, self.df_a, self.time_of_last_save)
        last_save = self.dl.save_df_fast(self.b, self.df_b, self.time_of_last_save)
        self.time_of_last_save = last_save #Do not change this (watch out for using new last_save)
        
        