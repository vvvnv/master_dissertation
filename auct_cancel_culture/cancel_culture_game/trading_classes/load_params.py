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
