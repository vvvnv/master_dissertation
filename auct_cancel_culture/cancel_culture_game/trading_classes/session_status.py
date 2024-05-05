from enum import Enum


# статус торговой сессии
class SessionStatus(Enum):
    INIT = 0
    START = 1
    END = 2
    FINISHED = 3
