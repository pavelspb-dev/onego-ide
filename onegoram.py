class AddressError(ValueError):
    """Address is not valid"""
    pass

class InvalidDataError(ValueError):
    """Data is not valid"""
    pass

class RAM:
    def __init__(self) -> None:
        """Initializes RAM"""
        self.size = 16384
        self.memory = ["000000000000000" for _ in range(self.size)]

    def read(self, addr: int) -> str:
        """Returns data from address addr"""

        if not (type(addr) is int):
            raise AddressError(f"Адрес должен быть целым числом, а не \"{addr}\"({type(addr)}).")

        try:
            return self.memory[addr]
        except IndexError:
            raise AddressError(f"Адреса \"{addr}\" нет в RAM, чтение невозможно.")

    def write(self, addr, data: str) -> None:
        """Writes data to address addr"""

        if not (type(addr) is int):
            raise AddressError(f"Адрес должен быть целым числом(int), а не \"{addr}\"({type(addr)}).")

        if not (type(data) is str):
            raise InvalidDataError(f"Данные для записи должны быть строкой(str), а не \"{data}\"({type(data)}).")

        if len(data) != 15:
            raise InvalidDataError(f"Длина данных должна быть 15 бит. Данные \"{data}\" невалидны.")

        for bit in data:
            if bit != "0" and bit != "1":
                raise InvalidDataError(f"Данные должны состоять только из символов \"1\" и/или \"0\". Данные \"{data}\" невалидны.")

        try:
            self.memory[addr] = data
        except IndexError:
            raise AddressError(f"Адреса \"{addr}\" нет в RAM, запись невозможна.")

    def dump(self) -> list:
        """Returns dump of memory"""
        return self.memory
