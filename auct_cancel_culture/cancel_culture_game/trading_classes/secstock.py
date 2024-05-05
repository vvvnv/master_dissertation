# акции

from decimal import Decimal

from auct_cancel_culture.cancel_culture_game.trading_classes import PosChange
from auct_cancel_culture.cancel_culture_game.trading_classes.security import Security


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
