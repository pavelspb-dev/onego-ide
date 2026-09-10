
class BIOS_Error(ValueError):
    pass

class BIOS:
    def __init__(self) -> None:
        pass

    def start(self, cpu) -> None:
        self.cpu = cpu

        if not callable(getattr(self.cpu, "write", None)):
            raise BIOS_Error("Ошибка BIOS: процессор не поддерживает метод вывода текста в консоль")

        if not hasattr(self.cpu, "ssd"):
            raise BIOS_Error("Ошибка BIOS: не обнаружен ЖД")

        if not callable(getattr(self.cpu.ssd, "init", None)):
            raise BIOS_Error("Ошибка BIOS: ЖД не поддерживает метод инициализации")

        if not callable(getattr(self.cpu.ssd, "read", None)):
            raise BIOS_Error("Ошибка BIOS: ЖД не поддерживает метод чтения")

        if not hasattr(self.cpu, "ram"):
            raise BIOS_Error("Ошибка BIOS: не обнаружено ОЗУ")

        if not callable(getattr(self.cpu.ram, "write", None)):
            raise BIOS_Error("Ошибка BIOS: ОЗУ не поддерживает метод записи")

#        self.cpu.write("OnegoBIOS запущен!\nИнициализация ЖД...\n")
        self.cpu.ssd.init()
 #       self.cpu.write("ЖД инициализирован.\nЗагрузка данных в ОЗУ...\n")

        for addr in range(0, 11384):
            data = self.cpu.ssd.read(addr)
            self.cpu.ram.write(addr + 5000, data)

#        self.cpu.write("Готово.\nOnegoBIOS успешно завершил работу, передаётся управление ЦП.\n")
