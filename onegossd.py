class AddressError(ValueError):
    pass

class InvalidDataError(ValueError):
    pass

class SSD:
    def __init__(self) -> None:
        self.size = 16384
        self.memory = ["000000000000000" for _ in range(self.size)]

    def init(self) -> None:
        with open("onegossd.img", "r") as img:
            data = img.read().strip()

        for index, data_ in enumerate([data[i:i+15] for i in range(0, len(data), 15)], start=0):
            self.memory[index] = data_

    def read(self, addr: int) -> str:
        """Returns data from address addr"""

        if not (type(addr) is int):
            raise AddressError(f"Адрес должен быть целым числом, а не \"{addr}\"({type(addr)}).")

        try:
            return self.memory[addr]
        except IndexError:
            raise AddressError(f"Адреса \"{addr}\" нет на SSD, чтение невозможно.")

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
            raise AddressError(f"Адреса \"{addr}\" нет на SSD, запись невозможна.")

    def dump(self) -> list:
        return self.memory
