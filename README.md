# Crypto-printer
Experimental build. Theoretically, a full-fledged trading program that:
- fetches latest price data for multiple strategies, with capacity for up to ~10
- considers trading opportunities
- if there is an opportunity from a strategy and there is enough capital, sends trade order to Binance
- capable of monitoring a single posiiton for each strategy
- auto balances position after liquidation, generates report for analysis of its trades
- discord capabilities: notifies user when trades and liquidations

## Strategy
The strategy this models uses is based on two cointegrating price-series and buying when the z-score is sufficiently deviated from the mean. Profit is taken when cointegrating series mean-reverts. There are no price or percent take-profits or stop-losses

## Result
The model works as expected, runs through each strategy every minute and performs necessary trades if necessary. In the history of trades, most of the trades were small gains, until one day when not having a stop-loss came back and bit because the model got margin-called. 

## Current state
Current progress is halted because of the difficulty of implementing a stop-loss with mean-reverting assets. (ie, when theoretical mean-revering assets have large immediate price discrepancies, it is the best time to trade, and the worst time to liquidate). 

## Past notes
https://sunnynie.notion.site/Bitcoin-Printer-e81d160556814bbe94d008511ce6ddcb

## Current dependencies:

- conda install -c conda-forge statsmodels
- conda install -c conda-forge nest-asyncio
- python-binance (from pip)
