# валюта или деньги
from decimal import Decimal

from auct_cancel_culture.cancel_culture_game.trading_classes import SessionStatus, PosChange
from auct_cancel_culture.cancel_culture_game.trading_classes.security import Security


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
