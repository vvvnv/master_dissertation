import time
import random

from .load_params import LoadParams
from .session_status import SessionStatus


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
    # messages - список сообщений, которые рассылается игрокам (для каждого события одно сообщение)
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
        if self.Paused and (self.Status != SessionStatus.END) and (self.Status != SessionStatus.FINISHED):
            return 'PAUSE'
        return self.Status.name
