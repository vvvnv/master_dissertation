# вспомогательная структура описывающая изменение позиций
class PosChange:
    def __init__(self, id, delta):
        self.id = id  # номер инструмента
        self.delta = delta  # изменение
