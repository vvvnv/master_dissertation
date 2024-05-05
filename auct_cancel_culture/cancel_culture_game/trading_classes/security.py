# класс описывающий базовые свойства торгуемого инструмента
from auct_cancel_culture.cancel_culture_game.trading_classes import LoadParams
from my_orderbook import MyOrderBook


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
                for i in range(self.OB.asks.depth):
                    pr = self.OB.asks.prices[i]
                    if pr > price:
                        break
                    vl = self.OB.asks.price_map[pr].volume
                    deal_vol += vl
                    deal_cash += pr * vl
                    if deal_vol > size:
                        deal_cash -= (deal_vol - size) * pr
                        deal_vol = size
                        break
            else:
                for i in range(self.OB.bids.depth):
                    pr = self.OB.bids.prices[-1 - i]
                    if pr < price:
                        break
                    vl = self.OB.bids.price_map[pr].volume
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
                for i in range(self.OB.asks.depth):
                    pr = self.OB.asks.prices[i]
                    if pr > price:
                        break
                    vl = self.OB.asks.price_map[pr].volume
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
                for i in range(self.OB.bids.depth):
                    pr = self.OB.bids.prices[-1 - i]
                    if pr < price:
                        break
                    vl = self.OB.bids.price_map[pr].volume
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
        if self.LastBid != self.OB.get_best_bid():
            self.LastBid = self.OB.get_best_bid()
            self.ChartHistory[0].append([tm, str(self.LastBid)])

        if self.LastAsk != self.OB.get_best_ask():
            self.LastAsk = self.OB.get_best_ask()
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

    # # # создать инструмент
    # # @staticmethod
    # # def GetSecurity(dictionary, session, num):
    # #     tp = dictionary['Type']
    # #     if tp == "Currency":
    # #         return secCurrency(dictionary, session, num)
    # #     if tp == "Stock":
    # #         return secStock(dictionary, session, num)
    #
    # # создать инструменты из списка
    # @staticmethod
    # def GetSecurities(dictionaries, session):
    #     return [Security.GetSecurity(dictionaries[i], session, i) for i in range(len(dictionaries))]

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
        # print('instrum', [[ch.id, ch.delta] for ch in self.Changes])

    # лучший бид
    def get_best_bid(self):
        if (self.OB is None) or (self.OB.bids.depth == 0):
            return None
        return self.OB.bids.prices[-1]

    # лучший аск
    def get_best_ask(self):
        if (self.OB is None) or (self.OB.asks.depth == 0):
            return None
        return self.OB.asks.prices[0]

    # топ 6 лучших бидов
    def get_bids(self):
        if self.OB is None:
            return []
        b_bids = []

        for i in range(6):
            if self.OB.bids.depth > i:
                b_bid_pr = self.OB.bids.prices[-1 - i]
                b_bid_vol = self.OB.bids.price_map[b_bid_pr].volume
                b_bids.append({'i': i, 'q': str(b_bid_vol) if b_bid_vol < 100000 else u"\u221e", 'p': str(b_bid_pr)})
            else:
                break
        #                b_bids.append({'i':i, 'q': '', 'p': ''})
        return b_bids

    # топ 6 лучших асков
    def get_asks(self):
        if self.OB is None:
            return []
        b_asks = []
        for i in range(6):
            if self.OB.asks.depth > i:
                b_ask_pr = self.OB.asks.prices[i]
                b_ask_vol = self.OB.asks.price_map[b_ask_pr].volume
                b_asks.append({'i': i, 'q': str(b_ask_vol) if b_ask_vol < 100000 else u"\u221e", 'p': str(b_ask_pr)})
            else:
                break
        #                b_asks.append({'i':i, 'q': '', 'p': ''})
        return b_asks

    # текущая стоимость инструмента
    def GetValue(self):
        return 0