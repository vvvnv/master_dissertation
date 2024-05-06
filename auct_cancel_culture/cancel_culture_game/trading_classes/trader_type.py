# класс типа трейдера
from .load_params import LoadParams


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
        self.Params = {k: float(self.Params[k]) for k in self.Params}
        if (self.Params.get('calcMaxCash', 0) == 1) and (self.Params['b'] > 0):
            self.Params['maxCash'] = 1 / (self.Params['b'] * 2)

    # рапсределить типы по игрокам
    @staticmethod
    def GetFromList(dictionaries, session, instrs):
        return [TraderType(dictionaries[i], session, instrs) for i in range(len(dictionaries))]

    # посчитать баллы из денег (без учета Min и Max Score)
    def CalcScore(self, profit):
        if self.Params.get('maxCash', None) is not None:
            pr = min(float(profit), self.Params['maxCash'])
        else:
            pr = float(profit)
        return (pr * (1 - pr * self.Params['b']) * self.Params['a'])

    # учет  Min и Max Score в баллах
    def LimitScore(self, unlimScore):
        if unlimScore < self.MinScoreLevel:
            return self.MinScore
        return max(min(self.MaxScore, unlimScore), self.MinScore)
