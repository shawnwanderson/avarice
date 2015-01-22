import asyncio
import time

import exchangelayer as el
import genconfig as gc
import genutils as gu
import strategies as st
import trader as trd

FreshOrder = False
LastOrder = {}


def GetTradeAmount(order):
  if order == 'buy':
    ta = gu.RoundIfGreaterThan(
        (el.GetTradeAmount('currency') / el.GetMarketPrice('ask')), 3)
  elif order == 'sell':
    ta = gu.RoundIfGreaterThan(el.GetTradeAmount('asset'), 3)
  else:
    ta = 0
  return ta


@asyncio.coroutine
def TradeWrapper():
  while True:
    if trd.LastOrder:
      if trd.FreshOrder:
        # New order, so just make a standard trade.
        el.Trade(trd.LastOrder['order'], trd.LastOrder[
                 'price'], trd.LastOrder['amount'])
        trd.FreshOrder = False
      elif el.OrderExist():
        el.CancelLastOrderIfExist()
        if trd.LastOrder['order'] == 'sell':
          CurrPrice = el.GetMarketPrice('bid')
        if trd.LastOrder['order'] == 'buy':
          CurrPrice = el.GetMarketPrice('ask')
        Prices = [CurrPrice, trd.LastOrder['price']]
        PriceDelta = max(Prices) - min(Prices)
        TradeAmount = GetTradeAmount(trd.LastOrder['order'])
        if PriceDelta <= (gc.Trader.ReIssueSlippage / 100) * trd.LastOrder['price']:
          if TradeAmount > gc.API.AssetTradeMin:
            el.Trade(trd.LastOrder['order'], CurrPrice, TradeAmount)
            print('Re-', trd.LastOrder['order'].upper(), 'at ', CurrPrice)
          else:
            print('Order Mostly Filled; Leftover Too Small')
            trd.LastOrder = {}
      else:
        # Not a new order, and no existing orders. Stop loop.
        print('Order Successful')
        trd.LastOrder = {}
    yield from asyncio.sleep(gc.Trader.ReIssueDelay)


def TradeFromStrategy():
  # Wait until we have enough data to trade off
  if len(st.Trade_list) >= gc.Trader.TradeDelay:
    if st.Trade_list[-1] == 'Buy':
      trd.FreshOrder = True
      TradeAmount = GetTradeAmount('buy')
      if TradeAmount > gc.API.AssetTradeMin:
        print('BUYING', TradeAmount, gc.API.Asset, 'at',
              el.GetMarketPrice('ask'), gc.API.Currency)
        trd.LastOrder = {
            'order': 'buy', 'price': el.GetMarketPrice('ask'), 'amount': TradeAmount}
        if gc.TradeRecorder.Enabled:
          gu.RecordTrades('BOUGHT', el.GetMarketPrice('ask'),
                          TradeAmount)
      else:
        print('Wanted to BUY', TradeAmount, gc.API.Asset,
              'at', el.GetMarketPrice('bid'), 'but needed more',
              gc.API.Currency)
    elif st.Trade_list[-1] == 'Sell':
      trd.FreshOrder = True
      TradeAmount = GetTradeAmount('sell')
      if TradeAmount > gc.API.AssetTradeMin:
        print('SELLING', TradeAmount, gc.API.Asset,
              'at', el.GetMarketPrice('bid'), gc.API.Currency)
        trd.LastOrder = {
            'order': 'sell', 'price': el.GetMarketPrice('bid'), 'amount': TradeAmount}
        if gc.TradeRecorder.Enabled:
          gu.RecordTrades('SOLD', el.GetMarketPrice('bid'), TradeAmount)
      else:
        print('Wanted to SELL', TradeAmount, gc.API.Asset, 'at',
              el.GetMarketPrice('bid'), 'but needed more', gc.API.Asset)
