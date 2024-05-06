from otree.api import *
from typing import List

from cancel_culture_game.trading_classes import TradeSession, Trader, TraderType, Market, SessionStatus, Security

c = Currency

doc = """
Dollar auction
"""


class Constants(BaseConstants):
    name_in_url = 'cancel_culture_game'
    instructions_template = 'cancel_culture_game/instructions.html'
    players_per_group = None
    num_rounds = 4
    # jackpot = 100 # не 
    # instrum_num = 2


# model classes

class Subsession(BaseSubsession):
    pass


# распределить типы по игрокам
def get_types(subsession, types_num):
    return [(i + subsession.round_number) % types_num for i in range(subsession.session.num_participants)]


# здесь инициализация всех параметров
def create_round(subsession):
    print('session id', id(subsession.session))

    # TODO - сделать загрузку из файла
    if subsession.round_number == 1:

        # словарь всех параметров которые нужно изменить по сравнению с дефолтными
        ses_params = {
            'NumPeriodsPerTrial': 1,
            'PeriodLength': 360,
            'TimerEnabled': True,
            'NumScenarios': 4,
            'ScenarioNames': ['1', '2', '3', '4'],
            'ScenarioDeterminationPeriod': 1,
            'ScenarioList': [1, 2, 3, 4],
            'TimeMessagesEnabled': True,
            'TimeMessages': [[[[0, 'Эксперты предсказывают падение акций компании 4'], [30, 'Ожидается падение рынка'],
                               [60, 'Наблюдается снижение спроса на услуги компании 1'],
                               [90, 'Значительно вырос  спрос на услуги компании 5'],
                               [120, 'Возможны знаительные скачки цен на акции компании 5'],
                               [150, 'Наблюдается рост спроса на услуги компании 1'],
                               [180, 'Снижение спроса на услуги компании 5'], [210, 'Ожидается падение рынка'],
                               [240, 'Ожидаются знаительные скачки цен на акции компании 4'],
                               [270, 'Ожидаются знаительные скачки цен на акции'],
                               [300, 'Рынок акций сильно переоценен'],
                               [330, 'Продолжается рост спроса на услуги компании 5'], [360, 'Нет новостей']]],
                             [[[0, 'Эксперты предсказывают падение акций компании 4'], [30, 'Ожидается падение рынка'],
                               [60, 'Ожидается снижение спроса на услуги компании 1'],
                               [90, 'Увеличивается спрос на услуги компании 5'],
                               [120, 'Ожидаются знаительные скачки цен на акции компании 5'],
                               [150, 'Произошел рост спроса на услуги компании 1'],
                               [180, 'Наблюдается снижение спроса на услуги компании 5'],
                               [210, 'Ожидается падение рынка'],
                               [240, 'Ожидаются знаительные скачки цен на акции компаний 3, 5'],
                               [270, 'Ожидаются знаительные скачки цен на акции'],
                               [300, 'На рынке акций сильный рирост частных инвесторов'],
                               [330, 'Продолжается рост спроса на услуги компании 5'], [360, 'Нет новостей']]],
                             [[[0, 'Ожидается падение акций компании 4'], [30, 'Ожидается падение рынка'],
                               [60, 'Наблюдается снижение спроса на услуги компании 1'],
                               [90, 'Увеличивается спрос на услуги компании 5'],
                               [120, 'Возможны знаительные скачки цен на акции компании 5'],
                               [150, 'Произошел рост спроса на услуги компании 1'],
                               [180, 'Снижение спроса на услуги компании 5'], [210, 'Ожидается падение рынка'],
                               [240, 'Ожидаются знаительные скачки цен на акции компании 3'],
                               [270, 'Ожидаются знаительные скачки цен на акции'],
                               [300, 'На рынке акций сильный рирост частных инвесторов'],
                               [330, 'Продолжается рост спроса на услуги компании 5'], [360, 'Нет новостей']]],
                             [[[0, 'Вероятно падение акций компании 4'], [30, 'Ожидается падение рынка'],
                               [60, 'Ожидается снижение спроса на услуги компании 1'],
                               [90, 'Наблюдается увеличение спроса на услуги компании 5'],
                               [120, 'Ожидаются знаительные скачки цен на акции комании 3'],
                               [150, 'Наблюдается рост спроса на услуги компании 1'],
                               [180, 'Наблюдается снижение спроса на услуги компании 5'],
                               [210, 'Ожидается падение рынка'],
                               [240, 'Ожидаются знаительные скачки цен на акции компании 4'],
                               [270, 'Ожидаются знаительные скачки цен на акции'],
                               [300, 'Рынок акций сильно переоценен'],
                               [330, 'Продолжается рост спроса на услуги компании 5'], [360, 'Нет новостей']]]]
        }
        trd_ses = TradeSession(ses_params)

        securities_params = [
            {
                'Name': 'Cash',
                'Type': 'Currency',
                'Rates': [[-1], [-1], [-1], [-1]]
            },
            {
                'Name': 'Co. 1',
                'Type': 'Stock',
                'StartPeriod': 1,
                'PeriodCounts': 1,
                'PriceBounds': (0, 10000),
                'Exogeneous': True,
                'MaxQtyBound': 10000,
                'Payouts': [38.2, 40.38, 41.47, 40.67],
                'ExogeneousPrices': [[[[0, 54.55, 55.35], [30, 45.01, 45.81], [60, 27.73, 28.53], [90, 24.51, 25.31],
                                       [120, 24.41, 25.21], [150, 27.25, 28.05], [180, 24.17, 24.97],
                                       [210, 30.05, 30.85], [240, 29.78, 30.58], [270, 29.84, 30.64],
                                       [300, 39.45, 40.25], [330, 39.41, 40.21], [360, 38.2, 38.2]]],
                                     [[[0, 56.37, 57.21], [30, 56.68, 57.52], [60, 45.04, 45.88], [90, 21.41, 22.25],
                                       [120, 20.84, 21.68], [150, 33.31, 34.15], [180, 26.17, 27.01],
                                       [210, 26.34, 27.18], [240, 31.7, 32.54], [270, 31.31, 32.15],
                                       [300, 30.58, 31.42], [330, 41.5, 42.34], [360, 40.38, 40.38]]],
                                     [[[0, 60.2, 61], [30, 57.69, 58.49], [60, 37.56, 38.36], [90, 23.74, 24.54],
                                       [120, 18.57, 19.37], [150, 29.65, 30.45], [180, 25.31, 26.11],
                                       [210, 28.15, 28.95], [240, 32.01, 32.81], [270, 30.96, 31.76],
                                       [300, 35.65, 36.45], [330, 39.88, 40.68], [360, 41.47, 41.47]]],
                                     [[[0, 59.12, 59.92], [30, 57.06, 57.86], [60, 20.55, 21.35], [90, 22.3, 23.1],
                                       [120, 22.35, 23.15], [150, 28.5, 29.3], [180, 25.63, 26.43], [210, 26.47, 27.27],
                                       [240, 29.01, 29.81], [270, 30.7, 31.5], [300, 36.33, 37.13], [330, 39.33, 40.13],
                                       [360, 40.67, 40.67]]]]
            },
            {
                'Name': 'Co. 2',
                'Type': 'Stock',
                'StartPeriod': 1,
                'PeriodCounts': 1,
                'PriceBounds': (0, 10000),
                'Exogeneous': True,
                'MaxQtyBound': 10000,
                'Payouts': [88.76, 90.2, 92.58, 87.9],
                'ExogeneousPrices': [[[[0, 96.76, 98.46], [30, 84.34, 86.04], [60, 61.09, 62.79], [90, 52.13, 53.83],
                                       [120, 50.31, 52.01], [150, 52.37, 54.07], [180, 46.42, 48.12],
                                       [210, 48.56, 50.26], [240, 47.69, 49.39], [270, 57.22, 58.92],
                                       [300, 79.14, 80.84], [330, 84.06, 85.76], [360, 88.76, 88.76]]],
                                     [[[0, 93.48, 95.2], [30, 99.64, 101.36], [60, 72.61, 74.33], [90, 53.87, 55.59],
                                       [120, 46.6, 48.32], [150, 60.59, 62.31], [180, 51.82, 53.54],
                                       [210, 48.96, 50.68], [240, 46.91, 48.63], [270, 48.33, 50.05],
                                       [300, 62.46, 64.18], [330, 84.43, 86.15], [360, 90.2, 90.2]]],
                                     [[[0, 93.34, 95.04], [30, 99.66, 101.36], [60, 60.38, 62.08], [90, 53.1, 54.8],
                                       [120, 43.37, 45.07], [150, 55.55, 57.25], [180, 52.79, 54.49],
                                       [210, 51.04, 52.74], [240, 47, 48.7], [270, 52.4, 54.1], [300, 71.68, 73.38],
                                       [330, 84.21, 85.91], [360, 92.58, 92.58]]],
                                     [[[0, 90.42, 92.12], [30, 95.08, 96.78], [60, 49.86, 51.56], [90, 49.54, 51.24],
                                       [120, 49.54, 51.24], [150, 53.97, 55.67], [180, 54.05, 55.75],
                                       [210, 48.27, 49.97], [240, 48.59, 50.29], [270, 56.37, 58.07],
                                       [300, 75.72, 77.42], [330, 83.82, 85.52], [360, 87.9, 87.9]]]]
            },
            {
                'Name': 'Co. 3',
                'Type': 'Stock',
                'StartPeriod': 1,
                'PeriodCounts': 1,
                'PriceBounds': (0, 10000),
                'Exogeneous': True,
                'MaxQtyBound': 10000,
                'Payouts': [220.52, 208.53, 209.29, 221.03],
                'ExogeneousPrices': [[[[0, 161.13, 165.49], [30, 153.14, 157.5], [60, 149.38, 153.74],
                                       [90, 170.34, 174.7], [120, 174.28, 178.64], [150, 194.58, 198.94],
                                       [180, 196.05, 200.41], [210, 216.11, 220.47], [240, 201.75, 206.11],
                                       [270, 194.04, 198.4], [300, 205.41, 209.77], [330, 214.16, 218.52],
                                       [360, 220.52, 220.52]]],
                                     [[[0, 148.99, 153.19], [30, 174.57, 178.77], [60, 153.3, 157.5],
                                       [90, 155.17, 159.37], [120, 174.78, 178.98], [150, 178.79, 182.99],
                                       [180, 199.37, 203.57], [210, 203.51, 207.71], [240, 194.38, 198.58],
                                       [270, 201.41, 205.61], [300, 215.02, 219.22], [330, 206.33, 210.53],
                                       [360, 208.53, 208.53]]],
                                     [[[0, 153.41, 157.61], [30, 175.99, 180.19], [60, 150.63, 154.83],
                                       [90, 165.12, 169.32], [120, 171.78, 175.98], [150, 180.49, 184.69],
                                       [180, 199.47, 203.67], [210, 200.01, 204.21], [240, 197.08, 201.28],
                                       [270, 212.22, 216.42], [300, 207.96, 212.16], [330, 206.24, 210.44],
                                       [360, 209.29, 209.29]]],
                                     [[[0, 157.5, 161.86], [30, 169.73, 174.09], [60, 129.53, 133.89],
                                       [90, 159.23, 163.59], [120, 174.95, 179.31], [150, 191.7, 196.06],
                                       [180, 199.7, 204.06], [210, 204.38, 208.74], [240, 194.11, 198.47],
                                       [270, 206.12, 210.48], [300, 202.34, 206.7], [330, 214.33, 218.69],
                                       [360, 221.03, 221.03]]]]
            },
            {
                'Name': 'Co. 4',
                'Type': 'Stock',
                'StartPeriod': 1,
                'PeriodCounts': 1,
                'PriceBounds': (0, 10000),
                'Exogeneous': True,
                'MaxQtyBound': 10000,
                'Payouts': [250.22, 251.99, 281.66, 281.66],
                'ExogeneousPrices': [[[[0, 38.67, 43.37], [30, 39.83, 44.53], [60, 30.23, 34.93], [90, 47.42, 52.12],
                                       [120, 50.97, 55.67], [150, 67.28, 71.98], [180, 90.68, 95.38],
                                       [210, 161.4, 166.1], [240, 138.3, 143], [270, 124.64, 129.34],
                                       [300, 184.49, 189.19], [330, 230.52, 235.22], [360, 250.22, 250.22]]],
                                     [[[0, 27.01, 31.27], [30, 45.61, 49.87], [60, 42.63, 46.89], [90, 32.1, 36.36],
                                       [120, 47.74, 52], [150, 54.78, 59.04], [180, 88.39, 92.65], [210, 92.58, 96.84],
                                       [240, 105.8, 110.06], [270, 137.5, 141.76], [300, 139.05, 143.31],
                                       [330, 209.65, 213.91], [360, 251.99, 251.99]]],
                                     [[[0, 31.6, 35.86], [30, 49.07, 53.33], [60, 32.18, 36.44], [90, 43.06, 47.32],
                                       [120, 49.29, 53.55], [150, 61.79, 66.05], [180, 96.86, 101.12],
                                       [210, 105.78, 110.04], [240, 135.61, 139.87], [270, 149.5, 153.76],
                                       [300, 131.9, 136.16], [330, 209.01, 213.27], [360, 281.66, 281.66]]],
                                     [[[0, 32.15, 36.47], [30, 55.74, 60.06], [60, 24.18, 28.5], [90, 41.46, 45.78],
                                       [120, 50.85, 55.17], [150, 61.96, 66.28], [180, 100.23, 104.55],
                                       [210, 132.34, 136.66], [240, 145.47, 149.79], [270, 136.56, 140.88],
                                       [300, 158.88, 163.2], [330, 212.29, 216.61], [360, 281.66, 281.66]]]]
            },
            {
                'Name': 'Co. 5',
                'Type': 'Stock',
                'StartPeriod': 1,
                'PeriodCounts': 1,
                'PriceBounds': (0, 10000),
                'Exogeneous': True,
                'MaxQtyBound': 10000,
                'Payouts': [300.32, 344.41, 383.23, 382.8],
                'ExogeneousPrices': [[[[0, 69.63, 76.3], [30, 98.33, 105], [60, 139.45, 146.12], [90, 128.49, 135.16],
                                       [120, 172.8, 179.47], [150, 246.86, 253.53], [180, 247.24, 253.91],
                                       [210, 318.43, 325.1], [240, 463.43, 470.1], [270, 454.24, 460.91],
                                       [300, 471.68, 478.35], [330, 330.65, 337.32], [360, 300.32, 300.32]]],
                                     [[[0, 63.76, 71.9], [30, 80.49, 88.63], [60, 106.17, 114.31], [90, 105.61, 113.75],
                                       [120, 149.66, 157.8], [150, 199.46, 207.6], [180, 253.96, 262.1],
                                       [210, 250.59, 258.73], [240, 342.74, 350.88], [270, 472.46, 480.6],
                                       [300, 491.96, 500.1], [330, 399.71, 407.85], [360, 344.41, 344.41]]],
                                     [[[0, 65.16, 73.16], [30, 82.94, 90.94], [60, 99.47, 107.47], [90, 133.88, 141.88],
                                       [120, 159.91, 167.91], [150, 231.02, 239.02], [180, 252.01, 260.01],
                                       [210, 236.91, 244.91], [240, 395.51, 403.51], [270, 501.25, 509.25],
                                       [300, 395.57, 403.57], [330, 387.98, 395.98], [360, 383.23, 383.23]]],
                                     [[[0, 68.73, 76.73], [30, 93.76, 101.76], [60, 122.55, 130.55],
                                       [90, 135.27, 143.27], [120, 164.02, 172.02], [150, 243.27, 251.27],
                                       [180, 252.44, 260.44], [210, 281.67, 289.67], [240, 460.47, 468.47],
                                       [270, 505.19, 513.19], [300, 431.6, 439.6], [330, 400.97, 408.97],
                                       [360, 382.8, 382.8]]]]
            },
        ]
        instruments = Security.GetSecurities(securities_params, trd_ses)
        trader_params = [
            {
                'Name': "1",
                'PositionBounds': None,
                'MinScoreLevel': 0,
                'InitialPositions': [83000, 38, 0, 40, 0, 24],
                'MaxScore': 10000,
                'Params': {'a': 0.001, 'b': 0.0000025},
                'MinQtyBound': [0, 0, 0, 0, 0, 0],
                'MaxQtyBound': [None, None, None, None, None, None]

            },
            {
                'Name': "2",
                'PositionBounds': None,
                'MinScoreLevel': 0,
                'InitialPositions': [44000, 0, 0, 31, 190, 0],
                'MaxScore': 10000,
                'Params': {'a': 0.001, 'b': 0.0000025},
                'MinQtyBound': [0, 0, 0, 0, 0, 0],
                'MaxQtyBound': [None, None, None, None, None, None]
            },
            {
                'Name': "3",
                'PositionBounds': None,
                'MinScoreLevel': 0,
                'InitialPositions': [5000, 0, 0, 0, 359, 0],
                'MaxScore': 10000,
                'Params': {'a': 0.001, 'b': 0.0000025},
                'MinQtyBound': [0, 0, 0, 0, 0, 0],
                'MaxQtyBound': [None, None, None, None, None, None]
            },
            {
                'Name': "4",
                'PositionBounds': None,
                'MinScoreLevel': 0,
                'InitialPositions': [28000, 543, 215, 0, 5, 87],
                'MaxScore': 10000,
                'Params': {'a': 0.001, 'b': 0.0000025},
                'MinQtyBound': [0, 0, 0, 0, 0, 0],
                'MaxQtyBound': [None, None, None, None, None, None]
            },
        ]
        trader_types = TraderType.GetFromList(trader_params, trd_ses, instruments)
        traders = [Trader(trader_types[tt]) for tt in get_types(subsession, len(trader_types))]
        subsession.session.vars['traders_types'] = trader_types
        subsession.session.vars['instruments'] = instruments
        subsession.session.vars['trade_session'] = trd_ses
        subsession.session.vars['traders'] = traders
        subsession.session.vars['market'] = Market(trd_ses, instruments, traders)

    else:
        trader_types = subsession.session.vars['traders_types']
        traders = subsession.session.vars['traders']
        for i, tt in enumerate(get_types(subsession, len(trader_types))):
            traders[i].ChangeType(trader_types[tt])
    for p in subsession.get_players():
        p.isAdmin = (p.participant.label == 'admin')


class Group(BaseGroup):
    CurrentPeriod = models.IntegerField(initial=0)


def get_trade_session(g) -> TradeSession:
    return g.session.vars['trade_session']


def get_market(g) -> Market:
    return g.session.vars['market']


def get_instruments(g) -> List[Security]:
    return g.session.vars['instruments']


def get_traders(g) -> List[Trader]:
    return g.session.vars['traders']


def get_instrument(g, num) -> Security:
    return g.session.vars['instruments'][num]


# def get_state(group: Group):
#     return dict(
#         top_bid=group.top_bid,
#         top_bidder=group.top_bidder,
#         second_bid=group.second_bid,
#         second_bidder=group.second_bidder,
#     )


class Player(BasePlayer):
    isAdmin = models.BooleanField()
    finalCash = models.FloatField()
    score = models.FloatField()


# экспорт данных
def custom_export(players):
    pos_dict = {}
    instr_name = {}
    pos = Positions.filter()
    for p in pos:
        tp = (p.sessioncode, p.trial, p.period, p.pl, p.start)
        if tp not in pos_dict:
            pos_dict[tp] = {}
        instr_name[p.instr] = p.instr_name
        pos_dict[tp][p.instr] = [p.sessioncode, p.trial, p.period, p.time, p.pl, p.start, p.instr, p.quantity]
        # yield pos_dict[tp][p.instr]

    # Export an ExtraModel called "Trial"
    yield ['session.code', 'trial', 'period', 'time', 'instr', 'sender', 'ord_id', 'price', 'quantity', 'bs', 'type',
           'bestBid_bef', 'bestAsk_bef', 'bestBid_aft', 'bestAsk_aft']
    # 'filter' without any args returns everything
    orders = Order.filter()
    for o in orders:
        yield [o.sessioncode, o.trial, o.period, o.time, instr_name.get(o.instr, ''), o.sender.id_in_group, o.ord_id,
               o.price, o.quantity, o.bs, o.tp,
               o.bbid_bef, o.bask_bef, o.bbid_aft, o.bask_aft]
    yield ['session.code', 'trial', 'period', 'time', 'instr', 'trd_init', 'trd_other', 'ord_init', 'ord_other',
           'price', 'quantity', 'bs']
    # 'filter' without any args returns everything
    deals = Deals.filter()
    for d in deals:
        yield [d.sessioncode, d.trial, d.period, d.time, instr_name.get(d.instr, ''),
               d.pl_init, d.pl_other, d.ord_init, d.ord_other, d.price, d.quantity, d.bs]

    instrs = list(instr_name.keys())
    instrs.sort()
    yield ['session.code', 'trial', 'period', 'time', 'trd', 'state'] + [instr_name.get(i, '') for i in instrs]
    for k in pos_dict:
        yield pos_dict[k][0][:-2] + [pos_dict[k][i][-1] for i in instrs]

    payments_dict = {}
    paym = Payments.filter()
    for pm in paym:
        tp = (pm.sessioncode, pm.trial, pm.period)
        if tp not in payments_dict:
            payments_dict[tp] = {}
        payments_dict[tp][pm.instr] = [pm.sessioncode, pm.trial, pm.period, pm.instr, pm.quantity]
        # yield payments_dict[tp][pm.instr]

    yield ['session.code', 'trial', 'period'] + [instr_name.get(i, '') for i in instrs if i >= 0]
    for k in payments_dict:
        yield payments_dict[k][0][:-2] + [payments_dict[k][i][-1] for i in instrs if i >= 0]

    # yield ['trial', 'period', 'trd', 'instr', 'state', 'quantity', 'time']
    # # 'filter' without any args returns everything
    # pos = Positions.filter()
    # for p in pos:
    #     yield [p.trial, p.period, p.pl, p.instr, p.start, p.quantity, p.time]


# заявки для экспорта
class Order(ExtraModel):
    period = models.IntegerField()
    trial = models.IntegerField()
    ord_id = models.IntegerField()
    sessioncode = models.StringField()
    sender = models.Link(Player)
    group = models.Link(Group)
    instr = models.IntegerField()
    price = models.FloatField()
    quantity = models.IntegerField()
    time = models.FloatField()
    tp = models.StringField()
    bs = models.IntegerField()
    bbid_bef = models.FloatField()
    bask_bef = models.FloatField()
    bbid_aft = models.FloatField()
    bask_aft = models.FloatField()


# сделки для экспорта
class Deals(ExtraModel):
    sessioncode = models.StringField()
    period = models.IntegerField()
    trial = models.IntegerField()
    pl_init = models.IntegerField()
    pl_other = models.IntegerField()
    ord_init = models.IntegerField()
    ord_other = models.IntegerField()
    init = models.BooleanField()
    instr = models.IntegerField()
    bs = models.IntegerField()
    price = models.FloatField()
    quantity = models.IntegerField()
    time = models.FloatField()


# таблица позиций для экспорта
class Positions(ExtraModel):
    sessioncode = models.StringField()
    period = models.IntegerField()
    trial = models.IntegerField()
    start = models.IntegerField()
    pl = models.IntegerField()
    group = models.Link(Group)
    instr = models.IntegerField()
    instr_name = models.StringField()
    quantity = models.FloatField()
    time = models.FloatField()


# таблица платежей для экспорта
class Payments(ExtraModel):
    sessioncode = models.StringField()
    period = models.IntegerField()
    trial = models.IntegerField()
    group = models.Link(Group)
    instr = models.IntegerField()
    instr_name = models.StringField()
    quantity = models.FloatField()


# таблица сообщений для экспорта
class Messages(ExtraModel):
    sessioncode = models.StringField()
    period = models.IntegerField()
    trial = models.IntegerField()
    group = models.Link(Group)
    trader = models.IntegerField()
    time = models.FloatField()
    message = models.StringField()


class Intro(Page):
    pass


class WaitToStart(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        create_round(group.subsession)
        m = get_market(group)
        m.StartNewTrial(group.round_number)
        Bid.save_all_pos(group, m, get_trade_session(group), 0)


# PAGES
class Bid(Page):

    # параметры для передачи java script
    @staticmethod
    def js_vars(player: Player):
        market = get_market(player)
        return {'my_id': player.id_in_group,
                'chart_length': market.ts.getPeriodLength(),
                'instrums': len(market.instrs),
                'trial': player.round_number,
                'instrums_names': [instr.Name for instr in market.instrs],
                'scenario_names': market.ts.ScenarioNames,
                'instrums_pos_only': [0 if ((instr.Type != "Currency") or instr.Tradable) else 1 for i, instr in
                                      enumerate(market.instrs)]}

    # параметры для html
    @staticmethod
    def vars_for_template(player):
        market = get_market(player)
        return {
            'instrums': [{'id': i, 'name': instr.Name} for i, instr in enumerate(market.instrs) if
                         (instr.Type != "Currency") or instr.Tradable],
            'currencies': [{'id': i, 'name': instr.Name} for i, instr in enumerate(market.instrs) if
                           (instr.Type == "Currency") and (not instr.Tradable)],
            'asks_range': [5 - i for i in range(6)],
            'bids_range': [i for i in range(6)],
        }

    # сформировать сообщение для игроков (добавляет вспомогательные поля)
    @staticmethod
    def form_resp(market: Market, ts: TradeSession, tp: str, other: dict):
        tm = ts.getLeftPeriodTime()

        res = {'type': tp, 'timeleft': tm if tm > 0 else 0, 'status': ts.getStatus(), 'period': ts.CurrentPeriod}
        # 'state': ts.Status,
        if other is not None:
            res.update(other)
        return res

    # сформировать сообщение для полного обновления рыночных данных для всех игроков
    @staticmethod
    def form_resp_full(group: Group, msgtype, market: Market, ts: TradeSession):
        print('form_resp_full')
        ms = market.GetFullMarketState()
        resp = dict()
        for p in group.get_players():
            resp[p.id_in_group] = Bid.form_resp(market, ts, 'full', {'msgtype': msgtype, 'market': ms,
                                                                     'player': market.GetFullTraderState(
                                                                         p.id_in_group)})
        return resp

    # сформировать сообщение для полного обновления рыночных данных игрока p
    @staticmethod
    def form_resp_full_player(p: Player, market: Market, ts: TradeSession):
        print('form_resp_full_player')
        ms = market.GetFullMarketState()
        return {p.id_in_group: Bid.form_resp(market, ts, 'full', {'market': ms,
                                                                  'player': market.GetFullTraderState(p.id_in_group)})}

    # сформировать очередное обновление данных для игроков (если требуется)
    @staticmethod
    def form_resp_update(group: Group, market: Market, ts: TradeSession):
        print('form_resp_update')
        upd = market.GetUpdates()
        if len(upd) == 0:
            return None

        ms = upd.get(0, None)
        if ms is not None:
            ms = {'market': ms}

        resp = dict()
        for p in group.get_players():
            resp[p.id_in_group] = Bid.form_resp(market, ts, 'update', ms)
        for u, value in upd.items():
            if u != 0:
                resp[u]['player'] = value
        print(resp)
        return resp

    # отправить обновление времени
    @staticmethod
    def form_resp_timer(market: Market, ts: TradeSession):
        return {0: Bid.form_resp(market, ts, 'timer', None)}

    # сохранить позиции всех игроков в базу
    @staticmethod
    def save_all_pos(group: Group, market: Market, ts: TradeSession, sv_type):
        # print('save_all_pos', 0, time.time())
        tm = ts.getLeftPeriodTime()
        # for p in group.get_players():
        # грязный хак, если использовать group.get_players() то сохраненный класс market копируется 
        # без ранее сделанных изменений 
        res = market.GetAllTradersPos()
        for p in res:
            Positions.create(sessioncode=group.session.code, period=ts.CurrentPeriod, trial=group.round_number,
                             start=sv_type, pl=p,
                             group=group, instr=-1, instr_name='rate', quantity=market.instrs[0].GetRate(), time=tm)
            for i, pos in enumerate(res[p]):
                Positions.create(sessioncode=group.session.code, period=ts.CurrentPeriod, trial=group.round_number,
                                 start=sv_type, pl=p,
                                 group=group, instr=i, instr_name=market.instrs[i].Name, quantity=float(pos), time=tm)
            # pass
        if sv_type == 2:
            cash_change = market.GetInstrumentsCashChange()
            for i, c in enumerate(cash_change):
                Payments.create(sessioncode=group.session.code, period=ts.CurrentPeriod, trial=group.round_number,
                                group=group, instr=i, instr_name=market.instrs[i].Name, quantity=float(c))
        # print('save_all_pos', 1, time.time())

    # сохранение всех сообщений в базу
    @staticmethod
    def save_all_messages(group: Group, market: Market, ts: TradeSession):
        msgs = market.GetAllMessages()
        for t in msgs:
            for m in msgs[t]:
                Messages.create(sessioncode=group.session.code, period=ts.CurrentPeriod, trial=group.round_number,
                                group=group, trader=t, time=m['time'], message=m['msg'])

    # реакция на сообщения от игроков
    # время в игре реализовано через таймер у одного из игроков - администратора
    # у него же управление игрой, также через этого игрока сделаны внешние цены
    @staticmethod
    def live_method(player: Player, data):
        if not (('type' in data) and (data['type'] == 'timer')):
            print(data)
        session = player.session
        group = player.group
        market = get_market(group)
        ts = get_trade_session(group)

        # ошибка в номере периода
        if 'period' in data:
            if data['period'] != ts.CurrentPeriod:
                return

        # сообщение когда игра остановлена
        if ts.Status == SessionStatus.END:
            if 'type' in data:
                if data['type'] == 'control':
                    if player.isAdmin:  # если сообщение от админа о начале новой
                        if (data['command'] == 'start') or (data['command'] == 'start_next'):
                            if ts.isLast():  # то если период последний - завершить игру
                                msgtype = 'TrialEnd'
                                ts.Status = SessionStatus.FINISHED
                            else:  # начать следующий период
                                msgtype = 'NextPeriod'
                                market.StartNextPeriod()
                            # отправить полное обновление всем игрокам
                            return Bid.form_resp_full(group, msgtype, market, ts)
            if len(data) == 0:
                return Bid.form_resp_full_player(player, market, ts)
            return

        # если игра завершена
        if ts.Status == SessionStatus.FINISHED:
            msgtype = 'TrialEnd'
            return Bid.form_resp_full(group, msgtype, market, ts)

        # если время периода вышло или сообщение от админа о досрочном завершении
        if (ts.getLeftPeriodTime() < 0) or (
                ('type' in data) and (data['type'] == 'control') and (data['command'] == 'start_next')):
            # сохранить все позиции
            Bid.save_all_pos(group, market, ts, 1)
            # провести расчеты по инструментам (выплаты, определения сценарияв и т.п.)
            market.EndPeriod()
            # сохранить новые позиции
            Bid.save_all_pos(group, market, ts, 2)
            # сохранить все сообщения
            Bid.save_all_messages(group, market, ts)
            msgtype = 'PeriodEnd'
            # отправить полное обновление всем игрокам
            return Bid.form_resp_full(group, msgtype, market, ts)

        # если идет игра
        if 'type' in data:
            t = data['type']
            if t == 'order':  # пришла новая заявка
                if ts.Paused:  # если пауза - то игнорируется
                    return
                tm = ts.getLeftPeriodTime()
                bid_bef, ask_bef = market.GetBestBidAsk(int(data['instr']))
                ord_sgn = 1 if data['side'] == 'bid' else -1
                # отправляется заявка на рынок
                order_id, trds = market.NewOrder(player.id_in_group, int(data['instr']), data['ordertype'],
                                                 data['price'], int(data['qnt']), data['side'], ord_sgn)
                if order_id is None:  # Ошибка
                    print('error none order_id')
                    return

                bid_aft, ask_aft = market.GetBestBidAsk(int(data['instr']))

                # сохранение заявки в базу данных
                if data['ordertype'] == 'limit':
                    Order.create(sessioncode=player.session.code, period=ts.CurrentPeriod, trial=player.round_number,
                                 ord_id=order_id, sender=player, group=player.group,
                                 instr=int(data['instr']), price=float(data['price']), quantity=int(data['qnt']),
                                 time=tm, tp='L', bs=ord_sgn,
                                 bbid_bef=bid_bef, bask_bef=ask_bef, bbid_aft=bid_aft, bask_aft=ask_aft)
                else:
                    Order.create(sessioncode=player.session.code, period=ts.CurrentPeriod, trial=player.round_number,
                                 ord_id=order_id, sender=player, group=player.group,
                                 instr=int(data['instr']), quantity=int(data['qnt']), time=tm, tp='M', bs=ord_sgn,
                                 bbid_bef=bid_bef, bask_bef=ask_bef, bbid_aft=bid_aft, bask_aft=ask_aft)

                # сохранение всех сделок
                for t in trds:
                    trd_sgn = 1 if t['side'] == 'bid' else -1
                    if trd_sgn == ord_sgn:
                        Deals.create(sessioncode=player.session.code, period=ts.CurrentPeriod,
                                     trial=player.round_number, pl_init=t['trd'], pl_other=t['trd2'], bs=ord_sgn,
                                     instr=int(data['instr']), price=t['p'], quantity=t['q'], ord_init=t['ord1'],
                                     ord_other=t['ord2'], time=tm)
                    else:
                        Deals.create(sessioncode=player.session.code, period=ts.CurrentPeriod,
                                     trial=player.round_number, pl_other=t['trd'], pl_init=t['trd2'], bs=ord_sgn,
                                     instr=int(data['instr']), price=t['p'], quantity=t['q'], ord_other=t['ord1'],
                                     ord_init=t['ord2'], time=tm)
                        # отправка обновлния
                return Bid.form_resp_update(group, market, ts)
            if t == 'cancelall':  # отмена всех заявок
                tm = ts.getLeftPeriodTime()
                bid_bef, ask_bef = market.GetBestBidAsk(int(data['instr']))
                market.ClearOrders(player.id_in_group, int(data['instr']), data['side'])
                bid_aft, ask_aft = market.GetBestBidAsk(int(data['instr']))
                ord_sgn = 1 if data['side'] == 'bid' else (0 if data['side'] == 'all' else -1)
                # сохранение заявки об отмене в базу данных
                Order.create(sessioncode=player.session.code, period=ts.CurrentPeriod, trial=player.round_number,
                             ord_id=market.get_new_order_id(), sender=player, group=player.group,
                             instr=int(data['instr']), time=tm, tp='C', bs=ord_sgn,
                             bbid_bef=bid_bef, bask_bef=ask_bef, bbid_aft=bid_aft, bask_aft=ask_aft)
                # отправка обновлений
                return Bid.form_resp_update(group, market, ts)

            if t == 'timer':  # сообщение об изменении времени от администратора
                if player.isAdmin:
                    if market.CheckTimeUpdate(ts.getPeriodLength() - ts.getLeftPeriodTime(), player.id_in_group):
                        return Bid.form_resp_full(group, 'full', market, ts)
                    return Bid.form_resp_timer(market, ts)
                else:
                    return None
            # управляющее сообщение от администратора (pause/resume)
            if t == 'control':
                if player.isAdmin:
                    market.PauseStart(data['command'] != 'start')
                    return Bid.form_resp_timer(market, ts)
                else:
                    return None
        return Bid.form_resp_full_player(player, market, ts)


class ResultsWaitPage(WaitPage):
    @staticmethod
    def after_all_players_arrive(group: Group):
        print('start profit calc')
        market = get_market(group)
        for p in group.get_players():
            t = market.GetTrader(p.id_in_group)
            pr = t.getProfit()
            p.finalCash = float(pr)
            p.score = float(t.Type.CalcScore(pr))
            p.payoff = 1000 * t.Type.LimitScore(p.score)


class Results(Page):
    timeout_seconds = 20


page_sequence = [WaitToStart, Bid, ResultsWaitPage, Results]
