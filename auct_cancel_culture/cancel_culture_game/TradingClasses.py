from enum import Enum
import numpy as np
import time
from typing import List, Dict
from decimal import Decimal, ROUND_FLOOR
import random

from my_orderbook import MyOrderBook


# вспомогательный класс для загрузки параметров (все остальные наследуются от него)
class LoadParams:
    def check_list_val(self, val, num):
        if not isinstance(val, list):
            return [val for _ in range(num)]
        assert len(val) == num
        return val

    def check_tuple_list_val(self, val, num, defi, count, defVal):
        if not isinstance(val, list):
            if not isinstance(val, tuple):
                val = tuple((val if defi == i else defVal) for i in range(count))
            return self.check_list_val(val, num)
        assert len(val) == num
        return val


# статус торговой сессии
class SessionStatus(Enum):
    INIT = 0
    START = 1
    END = 2
    FINISHED = 3


# параметры торговой сессии
class TradeSession(LoadParams):
    # внутренние параметры
    CurrentTrial = 1  # текущий номер игры (начинается с 1)
    CurrentPeriod = 1  # текущий период внутри игры (начинается с 1)
    PeriodEndTime = None  # время окончания периода
    Status = SessionStatus.INIT  # текущий статус
    PausedTime = None  # время когда поставили на паузу
    Paused = False  # игра на паузе
    Scenario = None  # номер реализовавшегося сценария
    Events = {}  # произошедшие события
    EventMessages = []  # сообщения посланные игрокам от событий
    MessagesToSend = []  # сообщения которые нужно отправить
    CurrentTimeMessagesNum = 0  # текущий номер сообщения по времени (если они включены)

    # настраиваемые параметры
    NumPeriodsPerTrial = 3  # число периодов в одной игре
    PeriodLength = 240  # длительность одного периодов в секундах (или число - тогда одинаково для всех периодов, или список с указанием для каждого)
    TimerEnabled = True  # TODO (не реализовано) включить обратный отсчет (можно указать списком по периодам или одним значением)
    ScenarioList = None  # заданный список реализации сценариев (по играм, если задан то реализуется сценарий из списка, если нет то случайны)
    NumScenarios = 1  # число сценариев
    ScenarioNames = ['']  # имена сценариев (каждый сценарий должен быть назван)
    ScenarioDeterminationPeriod = 1  # период в котором определяется сценарий

    # словарь возможных событий и их настройки
    # ключ элемента - кодовое название события
    # элемент - словарь содержащий три элемента
    # period - номер периода, в конце которого происходит это событие
    # variants - список возможных событий
    # messages - список сообщений, которое рассылается игрокам (для каждого события одно сообщение)
    EventSettings = {'e1': {'period': 1, 'variants': ['a', 'b', 'c'], 'messages': ['', '', '']},
                     'e2': {'period': 1, 'variants': ['a', 'b', 'c'], 'messages': ['', '', '']}, }

    # список реализаций событий - элемент это словарь где для каждого события указывается его вариант реализации
    EventSettingsPredetermined = [{'e1': 'a', 'e2': 'b'},  # игра 1
                                  {'e1': 'c', 'e2': 'c'}]  # игра 2 и т.д.

    TimeMessagesEnabled = False  # включены ли сообщения по времени
    KeepMessages = False  # сохранять ли сообщения между периодами одной игры
    # список сообщений формат [время с начала периода, текст сообщения]
    TimeMessages = [[[[0, "msg 1"], [100, "msg 2"]],  # period 1 trial 1
                     [[0, "msg 1"], [100, "msg 2"]]],  # period 2 trial 1
                    [[[0, "msg 1"], [100, "msg 2"]]]]  # period 1 trial 2

    # если цены указаны экзогенно, то очищать ли заявки игроков перед изменением или исполнять
    ClearOrdersExogeniousPriceChange = True

    # создание TradeSession из словаря параметров
    def __init__(self, dictionary):
        self.__dict__.update(dictionary)
        self.PeriodLength = self.check_list_val(self.PeriodLength, self.NumPeriodsPerTrial)
        self.TimerEnabled = self.check_list_val(self.TimerEnabled, self.NumPeriodsPerTrial)
        self.LastPeriod = self.NumPeriodsPerTrial

    # следующий период
    def NextPeriod(self):
        self.CurrentPeriod += 1
        self.PeriodEndTime = time.time() + self.getPeriodLength()
        self.Status = SessionStatus.START
        self.Paused = False
        self.CurrentTimeMessagesNum = 0

    # новая игра
    def NewTrial(self, trial):
        self.CurrentTrial = trial
        self.CurrentPeriod = 0
        self.NextPeriod()
        self.PauseContinue(True)

    #        self.PeriodEndTime = time.time() + self.getPeriodLength()
    #        self.Status = SessionStatus.START

    # узнать когда слать следующее сообщение по времени
    def getNextMessageTime(self):
        if self.CurrentTimeMessagesNum < len(self.TimeMessages[self.CurrentTrial - 1][self.CurrentPeriod - 1]):
            return self.TimeMessages[self.CurrentTrial - 1][self.CurrentPeriod - 1][self.CurrentTimeMessagesNum][0]
        return 1000000

    # получить следующее сообщение по времени
    # возвращает: сообщение (формат [время с начала периода, текст сообщения]), время следующего сообщения
    def getNewMessage(self):
        res = self.TimeMessages[self.CurrentTrial - 1][self.CurrentPeriod - 1][self.CurrentTimeMessagesNum]
        self.CurrentTimeMessagesNum += 1
        return res, self.getNextMessageTime()

    # в этом ли периоде определяется сценарий
    def is_deter_period(self):
        if isinstance(self.ScenarioDeterminationPeriod, list):
            return (self.CurrentPeriod in self.ScenarioDeterminationPeriod)
        else:
            return (self.CurrentPeriod == self.ScenarioDeterminationPeriod)

    # определить сценарий (запускается в конце периода)
    def DefineScenario(self):
        if self.is_deter_period():
            # если список реализаций сценариев не задан или он закончился
            if (self.ScenarioList is None) or (len(self.ScenarioList) < self.CurrentTrial):
                # то рандом
                self.Scenario = random.randrange(self.NumScenarios)
            else:
                # иначе берем из списка
                self.Scenario = self.ScenarioList[self.CurrentTrial - 1] - 1

    # получить номер варианта события по его названию
    # e - название события
    # nm - название интересуемого варианта
    # возвращает номер варианта
    def getEventNumByName(self, e, nm):
        for i, n in enumerate(self.EventSettings[e]['variants']):
            if n == nm:
                return i

    # проверка нет ли сейчас событий (запускается в конце периода)
    def CheckEvents(self):
        for e in reversed(list(self.EventSettings.keys())):
            if self.EventSettings[e]['period'] == self.CurrentPeriod:
                if (self.EventSettingsPredetermined is None) or (
                        len(self.EventSettingsPredetermined) < self.CurrentTrial):
                    self.Events[e] = random.choice(self.EventSettings[e]['variants'])
                else:
                    self.Events[e] = self.EventSettingsPredetermined[self.CurrentTrial - 1][e]
                self.MessagesToSend.append(self.EventSettings[e]['messages'][self.getEventNumByName(e, self.Events[e])])

    # конец периода
    def EndPeriod(self):
        self.Status = SessionStatus.END
        self.DefineScenario()
        self.CheckEvents()

    # поставить игру на паузу / продолжить
    def PauseContinue(self, pause):
        print('PauseContinue', pause, self.Paused, self.Status)
        if pause:
            if (self.Status != SessionStatus.START) or self.Paused:
                return
            self.Paused = True
            self.PausedTime = time.time()
        else:
            if not self.Paused:
                return
            self.PeriodEndTime += time.time() - self.PausedTime
            self.Paused = False

    # последний ли период
    def isLast(self):
        return self.CurrentPeriod >= self.LastPeriod

    # длительность текущего периода
    def getPeriodLength(self):
        return self.PeriodLength[self.CurrentPeriod - 1]  # периоды нумеруются от 1 поэтому -1

    # не используется
    def getTrialLength(self):
        return sum(self.PeriodLength)

    # оставшееся время до конца периода
    def getLeftPeriodTime(self):
        if self.PeriodEndTime is None:
            return None
        if self.Paused:
            return self.PeriodEndTime - self.PausedTime
        return self.PeriodEndTime - time.time()

    # текущий статус
    def getStatus(self) -> str:
        if (self.Paused) and (self.Status != SessionStatus.END) and (self.Status != SessionStatus.FINISHED):
            return 'PAUSE'
        return self.Status.name


# вспомогательнся структура описывающая изменение позиций
class PosChange():
    def __init__(self, id, delta):
        self.id = id  # номер инструмента
        self.delta = delta  # изменение


# класс описывающий базовые свойства торгуемого инструмента
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
    Exogeneous = False  # если True то цены задаются из вне в ExogeneousPrices
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
    Tradable = True  # если False то инструмент не торгуется
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

    # получить объем (в деньгах) который будет иполнен сразу же
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

    # создать инструмент
    @staticmethod
    def GetSecurity(dictionary, session, num):
        tp = dictionary['Type']
        if tp == "Bond":
            return secBond(dictionary, session, num)
        if tp == "Currency":
            return secCurrency(dictionary, session, num)
        if tp == "Stock":
            return secStock(dictionary, session, num)
        if tp == "Forward":
            return secForward(dictionary, session, num)
        if tp == "Option":
            return secOption(dictionary, session, num)

    # создать инструменты из списка
    @staticmethod
    def GetSecurities(dictionaries, session):
        return [Security.GetSecurity(dictionaries[i], session, i) for i in range(len(dictionaries))]

    # последний ли это был период
    def willExpire(self):
        return self.LastPeriod == self.Session.CurrentPeriod

    # инициализация при начале начале следующего периода
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
            self.OB = OrderBook()
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


# облигации
class secBond(Security):
    Type = "Bond"  # Bond / Stock / Currency / Forward / Option
    Payouts = [0, 0, 100]  # выплаты по периодам

    def __init__(self, dictionary, session, num):
        super().__init__(dictionary, session, num)
        assert self.Type == "Bond"

    # обсчитать конец периода - выплаты по облигации
    def CalcPeriodEnd(self):
        money_change = Decimal(self.Payouts[self.Session.CurrentPeriod - 1])
        self.Changes = [PosChange(0, money_change)]
        if self.willExpire():
            self.Changes.append(PosChange(self.Num, -1))


# валюта или деньги
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


# форвард/фьючерс
class secForward(Security):
    Type = "Forward"  # Bond / Stock / Currency / Forward / Option
    BaseInstrum = 1  # базовый инструмент по которому идет поставка
    Deliverable = True  # поставочный ли форвард

    def __init__(self, dictionary, session, num):
        super().__init__(dictionary, session, num)
        assert self.Type == "Forward"

    # оценка выигрыша по сценариям (работает только для одного периода)
    def getProjectedProfit(self, scen):
        return self.BaseInstrumObj.getProjectedProfit(scen)

    # сделать линк на инстурмент - на базовый инструмент
    def makeInstrumsLinks(self, instrums):
        self.BaseInstrumObj = instrums[self.BaseInstrum]

    # обсчитать конец периода - если конец то поставка/расчет по форварду
    def CalcPeriodEnd(self):
        if self.willExpire():
            if self.Deliverable:
                self.Changes = [PosChange(self.BaseInstrum, 1), PosChange(self.Num, -1)]
            else:
                self.Changes = [PosChange(self.BaseInstrumObj.BaseCurrency,
                                          self.BaseInstrumObj.getProjectedProfit(self.Session.Scenario)),
                                PosChange(self.Num, -1)]


# опционы
class secOption(Security):
    Type = "Option"  # Bond / Stock / Currency / Forward / Option
    OptionType = "Put"  # Put Или Call
    BaseInstrum = 1  # базовый инструмент по которому идет поставка
    Deliverable = False  # поставочный ли опцион
    American = False  # можно ли исполнить досрочно (TODO не сделано)
    Strike = 10.0  # цена страйка

    def __init__(self, dictionary, session, num):
        super().__init__(dictionary, session, num)
        assert self.Type == "Option"
        self.Strike = Decimal(self.Strike)
        if self.OptionType == "Put":
            self.Direction = -1
        elif self.OptionType == "Call":
            self.Direction = 1
        else:
            assert False

    # оценка выигрыша по сценариям (работает только для одного периода)
    def getProjectedProfit(self, scen):
        return max(0, (self.BaseInstrumObj.getProjectedProfit(scen) - self.Strike) * self.Direction)

    def inMoney(self, price):
        return (price - self.Strike) * self.Direction

    # сделать линк на инстурмент - на базовый инструмент
    def makeInstrumsLinks(self, instrums):
        self.BaseInstrumObj = instrums[self.BaseInstrum]

    # обсчитать конец периода - если конец то поставка/расчет по опциону
    def CalcPeriodEnd(self):
        if self.willExpire():
            if self.inMoney(self.BaseInstrumObj.getProjectedProfit(self.Session.Scenario)):
                if self.Deliverable:
                    self.Changes = [PosChange(self.BaseInstrum, self.Direction), PosChange(self.Num, -1),
                                    PosChange(self.BaseInstrumObj.BaseCurrency,
                                              -self.Strike * self.Direction)]
                else:
                    self.Changes = [PosChange(self.BaseInstrumObj.BaseCurrency,
                                              self.getProjectedProfit(self.Session.Scenario)),
                                    PosChange(self.Num, -1)]


# акции
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


# класс типа трейдера
class TraderType(LoadParams):
    Name = "0"  # название
    PositionBounds = None  # TODO - не используется
    InitialPositions = [1000, 15, 0]  # начальные позиции по каждому инструменту (0-й - деньги)
    MinScore = 0  # минимальный балл игрокам (если игрок получил меньше, то выигрыш будет MinScore)
    MinScoreLevel = 0  # требования необходимого количества баллов (если игрок набрал меньше MinScoreLevel, то его выигрыш будет MinScore)
    MaxScore = 10  # если игрок набрал больше MaxScore, то выигрыш будет MaxScore
    # параметры пересчета денег в полезность, формула:
    # Score = a*(Cash - b * Cash^2)
    # если Cash > maxCash, то для расчета в формуле будет использоваться maxCash
    # если calcMaxCash = 1, то maxCash будет расчитан автоматически по формуле:
    # maxCash = a/(2b)
    Params = {'a': 0.001, 'b': 0.0, 'maxCash': 10000, 'calcMaxCash': 0}

    NotAllowTrade = []  # названия инструментов, которыми игроку нельзя торговать
    # минимальное ограничение по количеству по инструменту: 
    # None - значит нет ограничения
    # например 0 - значит запрещены короткие позиции
    # если инструментов больше чем длина списка, то для оставшихся используется последнее значение в списке
    MinQtyBound = [None,
                   -10000]  # это означает что по деньгам нет ограничений, а по каждому инструменту не меньше -10000
    # максимальное ограничение по количеству по инструменту (все аналогично минимальному):  
    # None - значит нет ограничения
    MaxQtyBound = [None, 10000]

    # получить из списка инструментов номер инструмента с нужным именем
    @staticmethod
    def GetInstrByName(instrs, name):
        for i, instr in enumerate(instrs):
            if instr.Name.lower() == name.lower():
                return i
        assert False

    def __init__(self, dictionary, ses, instrs):
        self.__dict__.update(dictionary)
        self.PositionBounds = self.check_tuple_list_val(self.PositionBounds, len(self.InitialPositions), 1, 2, 0)
        assert len(self.InitialPositions) == len(instrs)
        self.ForbidInstrs = set() if (self.NotAllowTrade is None) else {TraderType.GetInstrByName(instrs, name) for name
                                                                        in self.NotAllowTrade}
        self.Session = ses
        self.Instruments = instrs
        self.Params = {k: Decimal(self.Params[k]) for k in self.Params}
        if (self.Params.get('calcMaxCash', 0) == 1) and (self.Params['b'] > 0):
            self.Params['maxCash'] = 1 / (self.Params['b'] * 2)

    # рапсределить типы по игрокам
    @staticmethod
    def GetFromList(dictionaries, session, instrs):
        return [TraderType(dictionaries[i], session, instrs) for i in range(len(dictionaries))]

    # посчитать баллы из денег (без учета Min и Max Score)
    def CalcScore(self, profit):
        if self.Params.get('maxCash', None) is not None:
            pr = min(Decimal(profit), self.Params['maxCash'])
        else:
            pr = Decimal(profit)
        return (pr * (1 - pr * self.Params['b']) * self.Params['a'])

    # учет  Min и Max Score в баллах
    def LimitScore(self, unlimScore):
        if unlimScore < self.MinScoreLevel:
            return self.MinScore
        return max(min(self.MaxScore, unlimScore), self.MinScore)


# трейдер - класс для каждого игрока, где хранятся всего его данные (позиции, сделки и т.п.)
# не имеет внешних настроек (все настройки в типах)
class Trader():
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


# класс рынка, вся работа с ним, как и трейдер не имеет настроек, все настройки в TradeSession

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
        self.wasChanged = np.zeros((len(self.trds), len(self.instrs)), dtype=np.bool)
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
        if not (instr.Active and instr.Tradable):
            return None, None
        return instr.get_best_bid(), instr.get_best_ask()

    # получить новый объем заявки с учетом ограничений трейдера на позиции
    def updateOrderSize(self, trader_id, instr_id, ordertype, price, size, ord_sgn):
        instr = self.instrs[instr_id]
        trader = self.trds[trader_id - 1]
        bc_id = instr.BaseCurrency
        cash = instr.getOrderVolumeWithIntersect(ordertype, price, size, ord_sgn)
        allow_size = trader.getOrderQntAllowed(instr_id, ord_sgn, size)
        allow_cash = trader.getOrderQntAllowed(bc_id, -ord_sgn, cash)
        return instr.getOrderVolumeWithCashRestrict(ordertype, price, allow_size, ord_sgn, allow_cash)[0]

    # новая заявка
    def NewOrder(self, trader_id, instr_id, ordertype, price, size, buysell, ord_sgn, isAdmin=False):
        instr = self.instrs[instr_id]
        trader = self.trds[trader_id - 1]
        if not isAdmin:
            if not (instr.Active and instr.Tradable and (instr_id not in trader.Type.ForbidInstrs)):
                return None, None

            if ordertype == 'limit':
                pr = Decimal(price)
            elif ord_sgn > 0:
                pr = Decimal(1000000)
            else:
                pr = Decimal(0)
            new_size = self.updateOrderSize(trader_id, instr_id, ordertype, pr, size, ord_sgn)
            if new_size <= 0:
                return None, None
        else:
            new_size = size

        tm = self.ts.getLeftPeriodTime()
        period = self.ts.CurrentPeriod
        ob = instr.OB
        order = {'type': ordertype, 'side': buysell, 'quantity': int(min(new_size, size)), 'price': price,
                 'trade_id': trader_id}
        trades, order_in_book = ob.process_order(order, False, True)
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
            self.trds[tr['party2'][0] - 1].procTrade(period, instr_id, base_instr_id, tr['party2'][1], tr['quantity'],
                                                     tr['price'], tr['party2'][2], tr['party2'][3], tm)
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
                        self.NewOrder(admin_id, i, 'limit', str(res[1]), 1000000, 'bid', 1, True)
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
        chngs = np.transpose(np.nonzero(self.wasChanged))
        res = {0: {}}
        for c in chngs:
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
                    res[0][instr_id] = {'last_p': str(instr.LastPrice), 'bid': instr.get_bids(),
                                        'ask': instr.get_asks(), 'history': instr.get_last_history()}

        self.wasChanged.fill(False)

        return res

    # получить полное обновление рынков (стаканы, цены, графики)
    def GetFullMarketState(self) -> dict:
        res = {}
        for i, instr in enumerate(self.instrs):
            if (instr.Type != 'Currency') or (instr.Tradable):  # skip non tradable
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
