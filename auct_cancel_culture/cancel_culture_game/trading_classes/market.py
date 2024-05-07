from typing import List, Dict

import numpy as np

from .traiding_session import TradeSession
from .trader import Trader
from .session_status import SessionStatus
from .security import Security


# market
class Market:
    def __init__(self, ts: TradeSession, instrs: List[Security], trds: List[Trader]):
        self.ts = ts
        self.instrs = instrs
        self.trds = trds
        self.cur_ord_id = 0
        self.Messages = []
        for i in instrs:
            i.makeInstrumsLinks(instrs)

    # получить класс trader по его trader_id
    def GetTrader(self, trader_id) -> Trader:
        return self.trds[trader_id - 1]

    # начать новую игру
    def StartNewTrial(self, trial):
        self.ts.NewTrial(trial)
        for i in self.instrs:
            i.NewTrial()
        for t in self.trds:
            t.NewTrial()
        self.wasChanged = np.zeros((len(self.trds), len(self.instrs)), dtype=bool)
        self.ExogeneousInstrs = [i for i, instr in enumerate(self.instrs) if instr.Exogeneous]
        self.hasExogeneous = (len(self.ExogeneousInstrs) > 0)
        self.nextTimeUpdate = 0
        self.Messages = []
        if len(self.ts.EventMessages) > 0:
            msg_nums = len(self.ts.EventMessages[self.ts.CurrentTrial - 1])
            for j, t in enumerate(self.trds):
                for m in self.ts.EventMessages[self.ts.CurrentTrial - 1][j % msg_nums]:
                    t.SendPrivateMessage(0, m)

    # начать новый период внутри игры
    def StartNextPeriod(self):
        self.ts.NextPeriod()
        for i in self.instrs:
            i.NextPeriod()
        for t in self.trds:
            t.NextPeriod()
        self.nextTimeUpdate = 0
        if not self.ts.KeepMessages:
            self.Messages = []
        if len(self.ts.EventMessages) > 0:
            msg_nums = len(self.ts.EventMessages[self.ts.CurrentTrial - 1])
            for j, t in enumerate(self.trds):
                for m in self.ts.EventMessages[self.ts.CurrentTrial - 1][j % msg_nums]:
                    t.SendPrivateMessage(0, m)

    # завершить период
    def EndPeriod(self):
        self.ts.EndPeriod()
        for i in self.instrs:
            i.EndPeriod()
        for t in self.trds:
            t.EndPeriod()
        self.CheckEventMessages()

    # проверить сообщения от событий
    def CheckEventMessages(self):
        if len(self.ts.MessagesToSend) > 0:
            for m in self.ts.MessagesToSend:
                self.Messages.append([int(self.ts.getPeriodLength() - self.ts.getLeftPeriodTime()), m])
            self.ts.MessagesToSend = []

    # получить новый глобальный номер заявки
    def get_new_order_id(self):
        self.cur_ord_id += 1
        return self.cur_ord_id

    # получить лучший bid и ask по инструменту с номером instr_id
    def GetBestBidAsk(self, instr_id):
        instr = self.instrs[instr_id]
        if instr.OB is not None:
            instr.OB.book_summary()
        if not (instr.Active and instr.Tradable):
            return None, None
        return instr.get_best_bid(), instr.get_best_ask()

    # получить новый объем заявки с учетом ограничений трейдера на позиции
    def updateOrderSize(self, trader_id, instr_id, ordertype, price, size, ord_sgn):
        for instr in self.instrs:
            if instr.OB is not None:
                instr.OB.book_summary()
        instr = self.instrs[instr_id]
        trader = self.trds[trader_id - 1]
        bc_id = instr.BaseCurrency
        cash = instr.getOrderVolumeWithIntersect(ordertype, price, size, ord_sgn)
        allow_size = trader.getOrderQntAllowed(instr_id, ord_sgn, size)
        allow_cash = trader.getOrderQntAllowed(bc_id, -ord_sgn, cash)
        res = instr.getOrderVolumeWithCashRestrict(ordertype, price, allow_size, ord_sgn, allow_cash)[0]
        print("RES = ", res)
        return res

    # новая заявка
    def NewOrder(self, trader_id, instr_id, ordertype, price, size, buysell, ord_sgn, isAdmin=False):
        instr = self.instrs[instr_id]
        trader = self.trds[trader_id - 1]
        if not isAdmin:
            if not (instr.Active and instr.Tradable and (instr_id not in trader.Type.ForbidInstrs)):
                return None, None

            if ordertype == 'limit':
                pr = float(price)
            elif ord_sgn > 0:
                pr = float(1000000)
            else:
                pr = float(0)
            new_size = self.updateOrderSize(trader_id, instr_id, ordertype, pr, size, ord_sgn)
            if new_size < 0:
                return None, None
        else:
            new_size = size

        tm = self.ts.getLeftPeriodTime()
        period = self.ts.CurrentPeriod
        ob = instr.OB
        default_price = '100000' if buysell == 'bid' else '0'
        order = {'type': ordertype,
                 'side': buysell,
                 'quantity': int(min(new_size, size)),
                 'price': default_price if price == '' else price,
                 'trade_id': trader_id}
        trades, order_in_book = ob.process_order(order)
        self.wasChanged[trader_id - 1, instr_id] = True
        global_order_id = self.get_new_order_id()
        base_instr_id = instr.BaseCurrency
        if order_in_book is not None:
            trader.addOrder(instr_id, base_instr_id, order_in_book['order_id'], order_in_book, global_order_id)
        if not isAdmin:
            instr.checkSaveChartHistory(tm)

        trds_res = []
        for tr in trades:
            print('trade', instr_id, tr)
            ord_id1 = global_order_id if tr['party1'][2] is None else self.trds[tr['party1'][0] - 1].getGlobalOrderID(
                instr_id, tr['party1'][2])
            ord_id2 = global_order_id if tr['party2'][2] is None else self.trds[tr['party2'][0] - 1].getGlobalOrderID(
                instr_id, tr['party2'][2])

            trds_res.append(
                {'trd': tr['party1'][0], 'trd2': tr['party2'][0], 'side': tr['party1'][1], 'q': tr['quantity'],
                 'p': tr['price'], 'ord1': ord_id1, 'ord2': ord_id2})
            self.trds[tr['party1'][0] - 1].procTrade(period, instr_id, base_instr_id, tr['party1'][1], tr['quantity'],
                                                     tr['price'], tr['party1'][2], tr['party1'][3], tm)
            self.wasChanged[tr['party1'][0] - 1, instr_id] = True
            self.wasChanged[tr['party1'][0] - 1, base_instr_id] = True
            self.trds[tr['party2'][0] - 1].procTrade(period,
                                                     instr_id,
                                                     base_instr_id,
                                                     tr['party2'][1],
                                                     tr['quantity'],
                                                     tr['price'],
                                                     tr['party2'][2],
                                                     tr['party2'][3],
                                                     tm)
            self.wasChanged[tr['party2'][0] - 1, instr_id] = True
            self.wasChanged[tr['party2'][0] - 1, base_instr_id] = True
        return global_order_id, trds_res

    # внутренняя функция
    # очистить все заявки трейдера с номером trader_id по инструменту instr_id
    def clear_orders_i(self, trader_id, instr_id, side):
        trader = self.trds[trader_id - 1]
        instr = self.instrs[instr_id]
        num = trader.clear_orders_i(instr_id, instr, side)
        if num > 0:
            self.wasChanged[trader_id - 1, instr_id] = True
            self.instrs[instr_id].checkSaveChartHistory(self.ts.getLeftPeriodTime())

    # внешняя функция
    # очистить все заявки трейдера с номером trader_id по инструменту с номером instr
    # или по списку инструментов instr
    # или если instr == None по всем инструментам
    def ClearOrders(self, trader_id, instr, side):
        if instr is None:
            for idx, x in enumerate(self.instrs):
                self.clear_orders_i(trader_id, idx, side)
        elif isinstance(instr, list):
            for idx in instr:
                self.clear_orders_i(trader_id, idx, side)
        else:
            self.clear_orders_i(trader_id, instr, side)

    # обновление времени
    def CheckTimeUpdate(self, tm, admin_id):
        full_update = False
        if self.nextTimeUpdate <= tm:
            new_NextTime = 1000000
            if self.hasExogeneous:
                full_update = True
                for i in self.ExogeneousInstrs:
                    cur_upd_time = self.instrs[i].getExogeneousUpdateTime()
                    if cur_upd_time <= tm:
                        res, new_time = self.instrs[i].getNewExogeneousPrice()
                        if self.ts.ClearOrdersExogeniousPriceChange:
                            for trader in self.trds:
                                trader.clear_orders_i(i, self.instrs[i], 'all')
                        else:
                            self.trds[admin_id - 1].clear_orders_i(i, self.instrs[i], 'all')
                        self.NewOrder(admin_id, i, 'limit', str(res[1]), 1000000, 'bid', 1,
                                      True)  # fixme вот тут тонкое место
                        self.NewOrder(admin_id, i, 'limit', str(res[2]), 1000000, 'ask', -1, True)
                        self.instrs[i].checkSaveChartHistory(self.ts.getLeftPeriodTime())
                        new_NextTime = min(new_NextTime, new_time)
                    else:
                        new_NextTime = min(new_NextTime, cur_upd_time)

            if self.ts.TimeMessagesEnabled:
                cur_upd_time = self.ts.getNextMessageTime()
                if cur_upd_time <= tm:
                    full_update = True
                    res, new_time = self.ts.getNewMessage()
                    self.Messages.append(res)
                    new_NextTime = min(new_NextTime, new_time)
                else:
                    new_NextTime = min(new_NextTime, cur_upd_time)
        if full_update:
            self.wasChanged.fill(False)
        return full_update

    # получить обновления которые надо отправить клиентам
    def GetUpdates(self) -> Dict[int, dict]:
        changes = np.transpose(np.nonzero(self.wasChanged))
        res = {0: {}}
        for c in changes:
            trader = self.trds[c[0]]
            trd_id = int(c[0] + 1)
            if trd_id not in res:
                res[trd_id] = {'cash': str(trader.Cash), 'pos': [str(p) for p in trader.Position], 'orders': {},
                               'trades': trader.get_trades_update(),
                               'scorePr': trader.get_score_data(self.ts.NumScenarios)}
            instr_id = int(c[1])
            instr = self.instrs[instr_id]
            if instr.Tradable:  # skip non tradable
                res[trd_id]['orders'][instr_id] = trader.getOrders(instr_id)
                if instr_id not in res[0]:
                    res[0][instr_id] = {'last_p': str(instr.LastPrice),
                                        'bid': instr.get_bids(),
                                        'ask': instr.get_asks(),
                                        'history': instr.get_last_history()}

        self.wasChanged.fill(False)

        return res

    # получить полное обновление рынков (стаканы, цены, графики)
    def GetFullMarketState(self) -> dict:

        res = {}
        for i, instr in enumerate(self.instrs):
            if instr.OB is not None:
                instr.OB.book_summary()
            if (instr.Type != 'Currency') or instr.Tradable:  # skip non tradable
                res[i] = {'last_p': str(instr.LastPrice), 'active': instr.Active, 'tradable': instr.Tradable,
                          'bid': instr.get_bids(), 'ask': instr.get_asks(),
                          'history': instr.get_full_history()}
                if self.ts.Status == SessionStatus.END:
                    res[i]['changes'] = [[str(p.id), "{:0.2f}".format(p.delta)] for p in instr.Changes]

        return res

    # список позиций трейдера
    def GetTraderPos(self, trader_id) -> list:
        trader = self.trds[trader_id - 1]
        return trader.Position

    # позиции всех трейдеров (в виде словаря)
    def GetAllTradersPos(self):
        return {i + 1: trader.Position for i, trader in enumerate(self.trds)}

    # изенение денег вызванное инструментами
    def GetInstrumentsCashChange(self):
        return [sum(ch.delta for ch in s.Changes if ch.id == 0) for s in self.instrs]

    # все сообщения
    def GetAllMessages(self):
        return {i + 1: self.GetMessages(t) for i, t in enumerate(self.trds)}

    # все сообщения отправленные трейдеру trader
    def GetMessages(self, trader):
        # trader = self.trds[trader_id-1]
        return [{'time': self.ts.getPeriodLength() - m[0], 'msg': m[1]} for m in trader.PrivateMessages] + \
            [{'time': self.ts.getPeriodLength() - m[0], 'msg': m[1]} for m in reversed(self.Messages)]

    # полное обновление по трейдеру: позиции, заявки, сделки, сообщения
    def GetFullTraderState(self, trader_id) -> dict:
        trader = self.trds[trader_id - 1]
        res = {'cash': str(trader.Cash), 'rate': "{:.2f}".format(self.instrs[0].GetRate()),
               'pos': [str(p) for p in trader.Position],
               'lockPosB': [str(p) for p in trader.OrderLockBuy],
               'lockPosS': [str(p) for p in trader.OrderLockSell],
               'forbid': trader.getForbidInstrsState(), 'scorePr': trader.get_score_data(self.ts.NumScenarios)}
        res['orders'] = {i: trader.getOrders(i) for i in range(1, len(self.instrs))}
        res['trades'] = trader.Trades
        all_msgs = self.GetMessages(trader)
        if len(all_msgs) > 0:
            res['messages'] = all_msgs
        if self.ts.Status == SessionStatus.END:
            res['changes'] = {i: [[str(p.id), str(p.delta)] for p in trader.Changes[i]] for i in
                              range(len(self.instrs))}
        return res

    # поставить игру на паузу или снять с паузы
    def PauseStart(self, pause):
        print('PauseStart', self.ts.Status.name, pause)
        if self.ts.Status == SessionStatus.START:
            self.ts.PauseContinue(pause)
