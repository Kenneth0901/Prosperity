import json
from typing import Dict, List
from datamodel import TradingState , Order

class DataHandler:
    def __init__(self):
        self.timestamp = 0
        self.market_data = {}
        self.positions = {}
        self.traderData = {}

    def update(self, state: TradingState):
        self.timestamp = state.timestamp
        self.position = state.position
        self.observations = state.observations
        self.own_trades = state.own_trades

        self.market_data = {}
        for symbol, order_depth in state.order_depths.items():
            self.market_data[symbol] = {
                'best_bid': [best_bid := max(order_depth.buy_orders), order_depth.buy_orders[best_bid]],
                'best_ask': [best_ask := min(order_depth.sell_orders), order_depth.sell_orders[best_ask]],
                'mid_price': (best_bid + best_ask) / 2,
                'snap': order_depth,
                'trades': state.market_trades.get(symbol, [])
            }

    def load_trader_data(self, trader_data_str: str):
        if trader_data_str:
            self.traderData = json.loads(trader_data_str)
        else:
            self.traderData = {}

    def dump_trader_data(self) -> str:
        return json.dumps(self.traderData)



class Portfolio:
    def __init__(self, position_limits: Dict[str, int]):
        self.position_limits = position_limits
        self.positions = {}
        self.pnl = {}
        self.volume_traded = {}
        self.cpnl = {}  # 已实现盈亏
        self.total_pnl = 0

    def update_positions_from_trades(self, own_trades: Dict[str, List], timestamp):
        """
        根据实际成交的own_trades更新positions与cpnl。
        """
        for symbol, trades in own_trades.items():
            for trade in trades:
                if trade.timestamp != timestamp - 100:
                    continue
                quantity = trade.quantity
                self.positions[symbol] = self.positions.get(symbol, 0) + quantity
                self.volume_traded[symbol] = self.volume_traded.get(symbol, 0) + abs(quantity)
                if trade.buyer == "SUBMISSION":
                    self.cpnl[symbol] = self.cpnl.get(symbol, 0) - quantity * trade.price
                else:
                    self.cpnl[symbol] = self.cpnl.get(symbol, 0) + quantity * trade.price

    def calculate_pnl(self, market_data):
        """
        根据最新市场价格对未平仓头寸估值。
        """
        self.total_pnl = 0
        for symbol, position in self.positions.items():
            best_sell = market_data[symbol]['best_ask'][0]
            best_buy = market_data[symbol]['best_bid'][0]

            # 根据当前持仓方向进行市价估值
            if position >= 0:
                settled_pnl = position * best_sell
            else:
                settled_pnl = position * best_buy

            # 累计盈亏= 已实现盈亏 + 当前估值
            self.pnl[symbol] = self.cpnl.get(symbol, 0) + settled_pnl
            self.total_pnl += self.pnl[symbol]

    def risk_control(self, symbol, desired_volume):
        current_pos = self.positions.get(symbol, 0)
        limit = self.position_limits[symbol]
        max_buy = limit - current_pos
        max_sell = -limit - current_pos
        if desired_volume > 0:
            allowed_volume = min(desired_volume, max_buy)
        else:
            allowed_volume = max(desired_volume, max_sell)
        return allowed_volume


class RainforestResStrategy:
    def __init__(self, datahandler: DataHandler, symbol: str):
        self.datahandler = datahandler
        self.symbol = symbol

    def cal_signal(self):
        market_data = self.datahandler.market_data[self.symbol]
        mid_price = market_data['mid_price']

        if mid_price < 9995:
            price = market_data['best_ask'][0]
            volume = 10
        elif mid_price > 9995:
            price = market_data['best_bid'][0]
            volume = -10
        else:
            return None

        return Order(self.symbol, price, volume)
    
class KelpStrategy:
    def __init__(self, datahandler: DataHandler, symbol: str):
        self.datahandler = datahandler
        self.symbol = symbol

    def cal_signal(self):
        market_data = self.datahandler.market_data[self.symbol]
        mid_price = market_data['mid_price']

        if mid_price < 2025:
            price = market_data['best_ask'][0]
            volume = 10
        elif mid_price > 2025:
            price = market_data['best_bid'][0]
            volume = -10
        else:
            return None

        return Order(self.symbol, price, volume)




class Trader:
    def __init__(self):
        self.datahandler = DataHandler()
        self.portfolio = Portfolio(position_limits={'RAINFOREST_RESIN': 50, 'KELP': 50})
        self.strategies = {
            'RAINFOREST_RESIN': RainforestResStrategy(self.datahandler, 'RAINFOREST_RESIN'),
            'KELP': KelpStrategy(self.datahandler, 'KELP')
        }

    def run(self, state: TradingState):
        self.datahandler.update(state)
        self.datahandler.load_trader_data(state.traderData)

        # 从traderData恢复历史状态
        self.portfolio.positions = self.datahandler.traderData.get('positions', {})
        self.portfolio.cpnl = self.datahandler.traderData.get('cpnl', {})
        self.portfolio.volume_traded = self.datahandler.traderData.get('volume_traded', {})
        self.portfolio.update_positions_from_trades(self.datahandler.own_trades, self.datahandler.timestamp)

        orders = {}
        for symbol, strategy in self.strategies.items():
            signal_order = strategy.cal_signal()
            # 风控调整交易量
            if signal_order != None:
                allowed_volume = self.portfolio.risk_control(symbol, signal_order.quantity)
                adjusted_order = Order(symbol, signal_order.price, allowed_volume)
                orders[symbol] = [adjusted_order]

     
        self.portfolio.calculate_pnl(self.datahandler.market_data)
        self.datahandler.traderData['positions'] = self.portfolio.positions
        self.datahandler.traderData['cpnl'] = self.portfolio.cpnl
        self.datahandler.traderData['volume_traded'] = self.portfolio.volume_traded
        trader_data_dumped = self.datahandler.dump_trader_data()
        print(f"Timestamp {self.datahandler.timestamp}, Total PNL: {self.portfolio.total_pnl}")
        conversions = 1
        return orders, conversions, trader_data_dumped
