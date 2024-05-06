# класс описывающий базовые свойства торгуемого инструмента
from decimal import Decimal

from .session_status import SessionStatus
from .load_params import LoadParams
from .pos_change import PosChange
from .my_orderbook import MyOrderBook


class Security(LoadParams):
    # внутренние параметры
    Num = 1  # номер инструмента 0 - деньги, остальные следующие
    LastPrice = None  # последняя цена
    ChartHistory = [[], [], []]  # история для графиков
    Changes = []  # изменения вызванные данным инструментом в конце периода
    LastSendChartHistory = [0, 0, 0]  # последняя отправленная история для графиков
    LastBid = None  # посдений бид
    LastAsk = None  # последнй аск
    CurrentExogeneousLevel = 0  # текущий уровень внешних цен
    Active = False  # активен ли инструмент

    # задаваемые параметры
    Name = "test1"  # название
    Type = ""  # тип #Bond / Stock / Currency / Forward / Option
    Exogeneous = False  # если True, то цены задаются из вне в ExogeneousPrices
    ExogeneousPricesFunc = None
    ExogeneousPricesFuncParams = {}
    # заданные внешние цены: формат [время после начала, бид, аск]
    ExogeneousPrices = [[[[0, 100.1, 102.1], [100, 200.1, 202.1]],  # period 1 trial 1
                         [[0, 100.1, 102.1], [100, 200.1, 202.1]]],  # period 2 trial 1
                        [[[0, 100.1, 102.1], [100, 200.1, 202.1]]]]  # period 1 trial 2

    StartPeriod = 1  # стартовый период инструмента (TODO не реализован)
    PeriodCounts = 3  # период в котором инструмент заканчивается
    PriceBounds = (0, 10000)  # ограничение на цены (минимальная, максимальная)
    MinQtyBound = -10000  # TODO не реализовано
    MaxQtyBound = 10000  # TODO не реализовано
    Tradable = True  # если False, то инструмент не торгуется
    # Hidden = False
    BaseCurrency = 0  # номер инструмента в котором идут расчеты за сделки - обычно кэш - 0-й инструмент

    # создать из словаря
    def __init__(self, dictionary, session, num):
        self.PeriodCounts = session.NumPeriodsPerTrial
        self.__dict__.update(dictionary)
        self.Session = session
        self.PriceBounds = self.check_tuple_list_val(self.PriceBounds, self.PeriodCounts, 1, 2, 0)
        self.MaxQtyBound = self.check_list_val(self.MaxQtyBound, self.PeriodCounts)
        self.Num = num
        self.LastPeriod = self.PeriodCounts + self.StartPeriod - 1
        self.LastExogeneousPricesSaved = [None, None]
        if num == 0:
            assert self.Type == "Currency"

    # сделать необходимые линки на другие инструменты - обычно не надо
    def makeInstrumsLinks(self, instrums):
        pass

    # время следующего уровня внешних цен
    def getExogeneousUpdateTime(self):
        if self.CurrentExogeneousLevel < len(
                self.ExogeneousPrices[self.Session.CurrentTrial - 1][self.Session.CurrentPeriod - 1]):
            return self.ExogeneousPrices[self.Session.CurrentTrial - 1][self.Session.CurrentPeriod - 1][
                self.CurrentExogeneousLevel][0]
        return 1000000

    # получить следующий уровень внешних цен
    def getNewExogeneousPrice(self):
        res = self.ExogeneousPrices[self.Session.CurrentTrial - 1][self.Session.CurrentPeriod - 1][
            self.CurrentExogeneousLevel]
        if self.ExogeneousPricesFunc is not None:
            res2 = self.ExogeneousPricesFunc(res[0], self.LastExogeneousPricesSaved, self.ExogeneousPricesFuncParams)
            res[1] = res2[0]
            res[2] = res2[1]
        self.LastExogeneousPricesSaved[0] = res[1]
        self.LastExogeneousPricesSaved[1] = res[2]
        self.CurrentExogeneousLevel += 1
        return res, self.getExogeneousUpdateTime()

    # получить объем (в деньгах) который будет исполнен сразу же
    def getOrderVolumeWithIntersect(self, ordertype, price, size, ord_sgn):
        deal_cash = 0
        deal_vol = 0
        if self.OB is not None:
            if ord_sgn > 0:
                for i in range(len(self.OB.offer_prices)):
                    pr = self.OB.offer_prices[i]
                    if pr > price:
                        break
                    vl = self.OB.offer_sizes[i]
                    deal_vol += vl
                    deal_cash += pr * vl
                    if deal_vol > size:
                        deal_cash -= (deal_vol - size) * pr
                        deal_vol = size
                        break
            else:
                for i in range(len(self.OB.bid_prices)):
                    pr = self.OB.bid_prices[-1 - i]
                    if pr < price:
                        break
                    vl = self.OB.bid_sizes[i]
                    deal_vol += vl
                    deal_cash += pr * vl
                    if deal_vol > size:
                        deal_cash -= (deal_vol - size) * pr
                        deal_vol = size
                        break
        if ordertype == 'limit':
            return deal_cash + (size - deal_vol) * price
        else:
            return deal_cash

    # получить объем (в штуках инструмента) с учетом бюджетного ограничения и исполняетмого объема
    def getOrderVolumeWithCashRestrict(self, ordertype, price, size, ord_sgn, allow_cash):
        deal_cash = 0
        deal_vol = 0
        if self.OB is not None:
            if ord_sgn > 0:
                for i in range(len(self.OB.offer_prices)):
                    pr = self.OB.offer_prices[i]
                    if pr > price:
                        break
                    vl = self.OB.offer_sizes[i]
                    deal_vol += vl
                    deal_cash += pr * vl
                    finished = 0
                    if deal_cash > allow_cash:
                        deal_vol -= (deal_cash - allow_cash) / pr
                        deal_cash = allow_cash
                        finished = 1
                    if deal_vol > size:
                        deal_cash -= (deal_vol - size) * pr
                        deal_vol = size
                        finished = 1
                    if finished == 1:
                        break
            else:
                for i in range(len(self.OB.bid_prices)):
                    pr = self.OB.bid_prices[-1 - i]
                    if pr < price:
                        break
                    vl = self.OB.bid_sizes[i]
                    deal_vol += vl
                    deal_cash += pr * vl
                    finished = 0
                    if deal_cash > allow_cash:
                        deal_vol -= (deal_cash - allow_cash) / pr
                        deal_cash = allow_cash
                        finished = 1
                    if deal_vol > size:
                        deal_cash -= (deal_vol - size) * pr
                        deal_vol = size
                        finished = 1
                    if finished == 1:
                        break

        if ordertype == 'limit':
            left_size = size - deal_vol
            left_cash = allow_cash - deal_cash
            if (left_cash > 0) and (left_size > 0):
                left_cash = min(left_cash, left_size * price)
                left_size = left_cash / price
                return deal_vol + left_size, deal_cash + left_cash
            else:
                return deal_vol, deal_cash
        else:
            return deal_vol, deal_cash

    # ожидаемый выигрыш для сценария scen
    def getProjectedProfit(self, scen):
        return 1

    # сохранить историю для графика, если надо
    def checkSaveChartHistory(self, tm):
        if self.LastBid != self.OB.max_bid:
            self.LastBid = self.OB.max_bid
            self.ChartHistory[0].append([tm, str(self.LastBid)])

        if self.LastAsk != self.OB.min_offer:
            self.LastAsk = self.OB.min_offer
            self.ChartHistory[1].append([tm, str(self.LastAsk)])

    # обработать сделку
    def procTrade(self, trader, Price, Volume, tm):
        if Price != self.LastPrice:  # изменилась последняя цена - обновить график
            self.ChartHistory[2].append([tm, str(Price)])
            self.LastPrice = Price
        self.Transaction(trader, Price, Volume)

    # обработать транзакцию
    def Transaction(self, trader, Price, Volume):
        trader.Position[self.Num] = trader.Position[self.Num] + Volume
        trader.Position[self.BaseCurrency] = trader.Position[self.BaseCurrency] - Volume * Price
        # trader.Cash = trader.Cash - Volume * Price

    # получить обвноление графика
    def get_last_history(self):
        ar = ['bid', 'ask', 'trade']
        res = {}
        for ind, nm in enumerate(ar):
            res[nm] = [[i, self.ChartHistory[ind][i]] for i in
                       range(self.LastSendChartHistory[ind], len(self.ChartHistory[ind]))]
            self.LastSendChartHistory[ind] = len(self.ChartHistory[ind])
        return res

    # получить полные данные для графика
    def get_full_history(self):
        ar = ['bid', 'ask', 'trade']
        res = {}
        for ind, nm in enumerate(ar):
            res[nm] = self.ChartHistory[ind]
        return res

    # обсчитать конец периода
    def CalcPeriodEnd(self):
        self.Changes = []

    # создать инструмент
    @staticmethod
    def GetSecurity(dictionary, session, num):
        tp = dictionary['Type']
        if tp == "Currency":
            return secCurrency(dictionary, session, num)
        if tp == "Stock":
            return secStock(dictionary, session, num)

    # создать инструменты из списка
    @staticmethod
    def GetSecurities(dictionaries, session):
        return [Security.GetSecurity(dictionaries[i], session, i) for i in range(len(dictionaries))]

    # последний ли это был период
    def willExpire(self):
        return self.LastPeriod == self.Session.CurrentPeriod

    # инициализация при начале следующего периода
    def NextPeriod(self):
        self.ChartHistory = [[], [], []]
        self.LastSendChartHistory = [0, 0, 0]
        self.LastBid = None
        self.LastAsk = None
        self.LastPrice = None
        self.Changes = []
        self.Active = (self.Session.CurrentPeriod >= self.StartPeriod) and (
                self.Session.CurrentPeriod <= self.LastPeriod)
        self.CurrentExogeneousLevel = 0
        # if not self.Active:
        #     self.Tradable = False
        if self.Num != 0:
            self.OB = MyOrderBook()
        else:
            self.OB = None

    # инициализация при начале новой игры
    def NewTrial(self):
        self.NextPeriod()

    # завершение периода
    def EndPeriod(self):
        if self.Active:
            self.CalcPeriodEnd()

    # лучший бид
    def get_best_bid(self):
        if (self.OB is None) or (len(self.OB.bid_prices) == 0):
            return None
        return self.OB.max_bid

    # лучший аск
    def get_best_ask(self):
        if (self.OB is None) or (len(self.OB.offer_prices) == 0):
            return None
        return self.OB.min_offer

    # топ 6 лучших бидов
    # def get_bids(self):
    #     if self.OB is None:
    #         return []
    #     b_bids = []
    #
    #     for i in range(6):
    #         if self.OB.bids.depth > i:
    #             b_bid_pr = self.OB.bids.prices[-1 - i]
    #             b_bid_vol = self.OB.bids.price_map[b_bid_pr].volume
    #             b_bids.append({'i': i, 'q': str(b_bid_vol) if b_bid_vol < 100000 else u"\u221e", 'p': str(b_bid_pr)})
    #         else:
    #             break
    #     return b_bids
    #
    # # топ 6 лучших асков
    # def get_asks(self):
    #     if self.OB is None:
    #         return []
    #     b_asks = []
    #     for i in range(6):
    #         if self.OB.asks.depth > i:
    #             b_ask_pr = self.OB.asks.prices[i]
    #             b_ask_vol = self.OB.asks.price_map[b_ask_pr].volume
    #             b_asks.append({'i': i, 'q': str(b_ask_vol) if b_ask_vol < 100000 else u"\u221e", 'p': str(b_ask_pr)})
    #         else:
    #             break
    #     #                b_asks.append({'i':i, 'q': '', 'p': ''})
    #     return b_asks

    # текущая стоимость инструмента
    def GetValue(self):
        return 0


class secStock(Security):
    Type = "Stock"  # Bond / Stock / Currency / Forward / Option
    Payouts = [0, 0, 0, 0, 0]  # выплаты для каждого их сценариев
    PayoutsEventsVals = []  # выплата по событиям (матрица размерности по числу событий от которых зависит выплата PayoutsEvents)
    Dividends = None  # {1:[0,0,0,0,0]} # дивиденды по событиям
    PaymentByEvents = False  # включены ли выплаты по событиям, если False то по сценариям
    DividendsEvents = {}  # {1:['e1']} # события от которых зависят выплаты
    PayoutsEvents = []  # ['e1', 'e2'] # события от которых зависят финальные выплаты

    def __init__(self, dictionary, session, num):
        super().__init__(dictionary, session, num)
        assert self.Type == "Stock"
        self.Payouts = [Decimal(p) for p in self.Payouts]

    # оценка выигрыша по сценариям
    def getProjectedProfit(self, scen):
        if self.PaymentByEvents:
            return self.getEventVals(self.PayoutsEventsVals, self.PayoutsEvents)
        else:
            return self.Payouts[scen]

    # получить из матрицы выплаты по реализации событий
    def getEventVals(self, mx, events):
        cur_val = mx
        for e in events:
            e_val = self.Session.getEventNumByName(e, self.Session.Events[e])
            cur_val = cur_val[e_val]
        return Decimal(cur_val)

    # обсчитать конец периода - выплаты дивидеднов и финальные по сценарию
    def CalcPeriodEnd(self):
        if (self.Dividends is not None) and (self.Session.CurrentPeriod in self.Dividends):
            self.Changes = [PosChange(0, self.getEventVals(self.Dividends[self.Session.CurrentPeriod],
                                                           self.DividendsEvents[self.Session.CurrentPeriod]))]
        else:
            self.Changes = []
        if not self.willExpire():
            return
        if self.PaymentByEvents:
            money_change = self.getEventVals(self.PayoutsEventsVals, self.PayoutsEvents)
        else:
            money_change = self.Payouts[self.Session.Scenario]
        self.Changes += [PosChange(0, money_change), PosChange(self.Num, -1)]


class secCurrency(Security):
    Type = "Currency"  # Bond / Stock / Currency / Forward / Option
    # ставка по периодам
    Rates = [[0.25, 0.25, 0.25],  # trial 1 period 1,2,3
             [0.25, 0.25, 0.25]]  # trial 2 period 1,2,3
    ConvertionRate = 1  # коэффициент конвертации в базовую валюту (актуально для счетов с деньгами будущих периодов)

    # оценка выигрыша по сценариям (работает только для одного периода)
    def getProjectedProfit(self, scen):
        if self.Session.Status == SessionStatus.END:
            return 1
        return 1 * (1 + self.GetRate())

    def __init__(self, dictionary, session, num):
        self.Tradable = False
        self.MinQtyBound = None
        self.MaxQtyBound = None
        super().__init__(dictionary, session, num)
        assert self.Type == "Currency"

    # текущая ставка
    def GetRate(self):
        if self.Session.CurrentTrial > len(self.Rates):
            tr = -1
        else:
            tr = self.Session.CurrentTrial - 1
        return Decimal(self.Rates[tr][self.Session.CurrentPeriod - 1])

    # обсчитать конец периода - конвертация в другую валюту если надо
    def CalcPeriodEnd(self):
        money_change = self.GetRate()
        self.Changes = [PosChange(self.Num, money_change)]
        if self.willExpire():
            if self.Num > 0:
                self.Changes = [PosChange(self.BaseCurrency, (1 + money_change) * self.ConvertionRate),
                                PosChange(self.Num, -1)]

    # текущая стоимость
    def GetValue(self):
        return Decimal(1.0)
