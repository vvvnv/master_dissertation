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
            'PeriodLength': 5,
            'TimerEnabled': True,
            'NumScenarios': 4,
            'ScenarioNames': ['1', '2', '3', '4'],
            'ScenarioDeterminationPeriod': 1,
            'ScenarioList': [1, 2, 3, 4],
            'TimeMessagesEnabled': True,
            'TimeMessages': [[[[0, 'Компания 2 загрязняет окружающую среду, что привело к массовым протестам', True],
                               [180, 'Нет новостей', False]]],
                             [[[0, 'Компания 2 использует детский труд, что привело к массовым протестам', True],
                               [180, 'Нет новостей', False]]],
                             [[[0, 'Компания 3 оказалась пирамидой', True],
                               [180, 'Нет новостей', False]]],
                             [[[0, 'Компания 4 производит препараты, вредящие организму человека', True],
                               [180, 'Нет новостей', False]]]],
            'InsiderRatio': [25, 40, 50, 70],
            'BadCompany': [2, 2, 3, 4]
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
                'Exogeneous': False,
                'MaxQtyBound': 10000,
                'Payouts': [110, 110, 110, 110]
            },
            {
                'Name': 'Co. 2',
                'Type': 'Stock',
                'StartPeriod': 1,
                'PeriodCounts': 1,
                'PriceBounds': (0, 10000),
                'Exogeneous': False,
                'MaxQtyBound': 10000,
                'Payouts': [0, 0, 110, 110]
            },
            {
                'Name': 'Co. 3',
                'Type': 'Stock',
                'StartPeriod': 1,
                'PeriodCounts': 1,
                'PriceBounds': (0, 10000),
                'Exogeneous': False,
                'MaxQtyBound': 10000,
                'Payouts': [110, 110, 0, 110]
            },
            {
                'Name': 'Co. 4',
                'Type': 'Stock',
                'StartPeriod': 1,
                'PeriodCounts': 1,
                'PriceBounds': (0, 10000),
                'Exogeneous': False,
                'MaxQtyBound': 10000,
                'Payouts': [110, 110, 110, 0]
            },
            {
                'Name': 'Co. 5',
                'Type': 'Stock',
                'StartPeriod': 1,
                'PeriodCounts': 1,
                'PriceBounds': (0, 10000),
                'Exogeneous': False,
                'MaxQtyBound': 10000,
                'Payouts': [110, 110, 110, 110]
            },
        ]
        instruments = Security.GetSecurities(securities_params, trd_ses)
        trader_params = [
            {
                'Name': "1",
                'PositionBounds': None,
                'MinScoreLevel': 0,
                'InitialPositions': [10000, 28, 11, 37, 4, 22],
                'MaxScore': 10000,
                'Params': {'a': 0.001, 'b': 0.0000025},
                'MinQtyBound': [0, 0, 0, 0, 0, 0],
                'MaxQtyBound': [None, None, None, None, None, None]

            },
            {
                'Name': "2",
                'PositionBounds': None,
                'MinScoreLevel': 0,
                'InitialPositions': [20000, 0, 0, 0, 0, 0],
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
            p.score = float(pr)
            p.payoff = float(pr)


class Results(Page):
    timeout_seconds = 20


page_sequence = [WaitToStart, Bid, ResultsWaitPage, Results]
