# трейдер - класс для каждого игрока, где хранятся всего его данные (позиции, сделки и т.п.)
# не имеет внешних настроек (все настройки в типах)

from decimal import Decimal, ROUND_FLOOR

from .pos_change import PosChange
from .trader_type import TraderType


class Trader:
    PrivateMessages = []

    def __init__(self, tp: TraderType):
        self.Type = tp

    # изменить тип игрока на другой - не используется
    def ChangeType(self, tp: TraderType):
        self.Type = tp

    # Кэш - получить - не используется
    @property
    def Cash(self):
        return self.Position[0]

    # Кэш - изменить - не используется
    @Cash.setter
    def Cash(self, value):
        self.Position[0] = value

    # инициализации перед новой игрой
    def NewTrial(self):
        # позиции по инструментам
        self.Position = [Decimal(p) for p in self.Type.InitialPositions]
        # изменения в позициях в конце периода
        self.Changes = [[] for _ in self.Position]
        # заблокированный в заявках объем на покупку
        self.OrderLockBuy = [Decimal(0) for _ in self.Type.InitialPositions]
        # заблокированный в заявках объем на продажу
        self.OrderLockSell = [Decimal(0) for _ in self.Type.InitialPositions]
        # активные заявки трейдера
        self.Orders = [{} for _ in self.Position]
        # история сделок
        self.Trades = []
        # сколько сделок было отправлено для отображения (чтобы отправлять только новые)
        self.LastSendTrades = 0
        # отправленные приватные сообщения
        self.PrivateMessages = []

    # инициализации перед новым периодом
    def NextPeriod(self):
        self.PrivateMessages = []
        # pass

    # отправить приватное сообщение  игроку
    def SendPrivateMessage(self, tm, msg):
        self.PrivateMessages.append([tm, msg])

    # провести расчеты в конце периода
    def EndPeriod(self):
        # get changes in positions at the end of period
        # print('trader', [[c.id, c.delta] for ch in self.Changes for c in ch])
        for idx, pos in enumerate(self.Position):
            if pos != 0:
                # print('tr', idx, pos, [[c.id, c.delta] for c in self.Type.Instruments[idx].Changes])
                self.Changes[idx] = [PosChange(p.id, (p.delta * pos).quantize(Decimal('0.01'), rounding=ROUND_FLOOR))
                                     for p in self.Type.Instruments[idx].Changes]
            else:
                self.Changes[idx] = []
        # apply changes
        # print('trader', [[c.id, c.delta] for ch in self.Changes for c in ch])
        for changes in self.Changes:
            for chn in changes:
                self.Position[chn.id] += chn.delta
        # clear orders
        self.OrderLockBuy = [Decimal(0) for _ in self.Type.InitialPositions]
        self.OrderLockSell = [Decimal(0) for _ in self.Type.InitialPositions]
        for p in self.Orders:
            p.clear()

    # разрешенные позиции по инструменту instr на покупку если bs=1 или на продажу если bs=-1
    def getAllowedPos(self, instr, bs):
        if bs > 0:
            if instr >= len(self.Type.MaxQtyBound):
                return self.Type.MaxQtyBound[-1]
            else:
                return self.Type.MaxQtyBound[instr]
        else:
            if instr >= len(self.Type.MinQtyBound):
                return self.Type.MinQtyBound[-1]
            else:
                return self.Type.MinQtyBound[instr]

    # check position limits
    def getOrderQntAllowed(self, instr, bs, qnt):
        pos_limit = self.getAllowedPos(instr, bs)
        if pos_limit is None:
            return qnt
        # cash_limit = self.getAllowedPos(0, -bs)
        if bs > 0:
            left_pos = pos_limit - self.OrderLockBuy[instr] - self.Position[instr]
            # left_cash = self.Position[0] - cash_limit - self.OrderLockBuy[0]
        else:
            left_pos = self.Position[instr] - pos_limit - self.OrderLockSell[instr]
            # left_cash = cash_limit - self.OrderLockSell[0] - self.Position[0]
        if left_pos < 0:
            left_pos = 0
        # if left_cash < 0:
        # left_cash = 0
        return min(left_pos, qnt)  # , min(cash, left_cash)

    # возращает список из 0 и 1 где для каждого инструмента указано 0 - нельзя торгова, 1 - можно торговать
    def getForbidInstrsState(self):
        return [1 if (i in self.Type.ForbidInstrs) else 0 for i, _ in enumerate(self.Position)]

    # оценка стоимости текущего портфеля по сценарию scen
    def getProjectedScore(self, scen):
        cash = sum(self.Type.Instruments[i].getProjectedProfit(scen) * pos for i, pos in enumerate(self.Position))
        return self.Type.CalcScore(cash)

    # расчет выигрыша
    def getProfit(self):
        return sum([self.Type.Instruments[i].GetValue() * pos for i, pos in enumerate(self.Position)])

    # добавление заявки в активные заявки
    def addOrder(self, instr_id, base_instr_id, order_id, order, global_order_id):
        if order['side'] == 'bid':
            self.OrderLockBuy[instr_id] += order['quantity']
            self.OrderLockSell[base_instr_id] += order['quantity'] * order['price']
        else:
            self.OrderLockSell[instr_id] += order['quantity']
            self.OrderLockBuy[base_instr_id] += order['quantity'] * order['price']
        self.Orders[instr_id][order_id] = {'side': order['side'], 'qnt': order['quantity'], 'price': order['price'],
                                           'global_order_id': global_order_id}

    # очистка всех заявок по инструменту instr с номером instr_id (должны быть согласованы)
    # по направлению side: 'bid' - все заявки на покупку, 'ask' - все заявки на продажу, 'all' - все заявки
    def clear_orders_i(self, instr_id, instr, side):
        ob = instr.OB
        base_instr_id = instr.BaseCurrency
        orders = self.Orders[instr_id]
        num = 0
        for order_id in list(orders.keys()):

            order_val = orders[order_id]
            print('order_id', order_id, order_val, side)
            if (side is None) or (side == 'all') or (side == order_val['side']):
                print('cancel', order_id)
                if order_val['side'] == 'bid':
                    self.OrderLockBuy[instr_id] -= order_val['qnt']
                    self.OrderLockSell[base_instr_id] -= order_val['qnt'] * order_val['price']
                else:
                    self.OrderLockSell[instr_id] -= order_val['qnt']
                    self.OrderLockBuy[base_instr_id] -= order_val['qnt'] * order_val['price']
                ob.cancel_order(order_val['side'], order_id)
                del orders[order_id]
                num += 1
        return num

    # получить из локального номера заявки игрока order_id глобальный идентификатор заявки
    def getGlobalOrderID(self, instr_id, order_id):
        return self.Orders[instr_id][order_id]['global_order_id']

    # изменить оставшееся количество в заявке order_id, если количество 0 Или None то заявка удаляется
    def updateOrder(self, instr_id, order_id, qnt):
        if (qnt is None) or (qnt == 0):
            del self.Orders[instr_id][order_id]
        else:
            self.Orders[instr_id][order_id]['qnt'] = qnt

    # получить список всех активных заявок по инструменту с номером instr_id
    def getOrders(self, instr_id):
        return [{'q': int(self.Orders[instr_id][i]['qnt']), 'p': str(self.Orders[instr_id][i]['price'])} for i in
                self.Orders[instr_id]]

    # обработать сделку
    def procTrade(self, period, instr_id, base_instr_id, side, qnt, price, order_id, new_qnt, tm):
        print('procTrade', instr_id, side, qnt, price, order_id, new_qnt)
        tr_sgn = 1 if side == 'bid' else -1
        self.Type.Instruments[instr_id].procTrade(self, price, tr_sgn * qnt, tm)
        self.Trades.append({'instr': instr_id, 'period': period, 'time': tm, 'p': str(price), 'q': int(tr_sgn * qnt)})
        #        self.Type.Instruments[instr_id].Transaction(self, price, tr_sgn * qnt)
        if order_id is not None:
            if tr_sgn > 0:
                self.OrderLockBuy[instr_id] -= qnt
                self.OrderLockSell[base_instr_id] -= qnt * price
            else:
                self.OrderLockSell[instr_id] -= qnt
                self.OrderLockBuy[base_instr_id] -= qnt * price
            self.updateOrder(instr_id, order_id, new_qnt)

    # получить сделки которые еще не были отправлены клиенту
    def get_trades_update(self):
        ls = self.LastSendTrades
        self.LastSendTrades = len(self.Trades)
        return [[i, self.Trades[i]] for i in range(ls, len(self.Trades))]

    # получить прогноз портфеля по сценариям то 0 до numSc-1
    # формат для каждого сценария: [скор, цвет (1 или 2)]
    def get_score_data(self, numSc):

        sc = [self.getProjectedScore(s) for s in range(numSc)]
        return [[str(s), 1 if s >= self.Type.MinScoreLevel else 2] for s in sc]
