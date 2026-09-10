class InvalidDataError(ValueError):
    pass

class OverflowError(ValueError):
    pass

class InvalidNumError(ValueError):
    pass

class DeviceError(ValueError):
    pass

class CPU_Error(ValueError):
    pass

class CPU:
    def __init__(self, ram, core, bios, ssd, keyboard = None, output = None) -> None:
        """Initializes CPU"""
        self.cmd = ""
        self.ram = ram
        self.core = core
        self.bios = bios
        self.ssd = ssd
        self.keyboard = keyboard
        self.output = output

        self.stepmode = False

        self.check_devices()

        self._setup_write()

    def check_devices(self) -> None:
        if not callable(getattr(self.bios, "start", None)):
            raise DeviceError("BIOS невозможно запустить!!")

        if not callable(getattr(self.core, "handle_cmd", None)):
            raise CPU_Error("Ядро процессора неработоспособно!!")

        # Checking registers
        if not all((hasattr(self.core, "asi"), hasattr(self.core, "lz"),
                   hasattr(self.core, "r0"), hasattr(self.core, "r1"),
                   hasattr(self.core, "r2"), hasattr(self.core, "r3"),
                   hasattr(self.core, "r4"), hasattr(self.core, "r5"),
                   hasattr(self.core, "r6"), hasattr(self.core, "r7"),
                   hasattr(self.core, "r8"), hasattr(self.core, "r9"),
                   hasattr(self.core, "r10"), hasattr(self.core, "r11"),
                   hasattr(self.core, "r12"), hasattr(self.core, "r13"))):
            raise CPU_Error("Необходимый(-е) регистр(-ы) отсутствует(-ют)!")

        if not callable(getattr(self.ram, "read", None)):
            raise DeviceError("ОЗУ не поддерживает метод чтения")

        if not callable(getattr(self.ram, "write", None)):
            raise DeviceError("ОЗУ не поддерживает метод записи")

        if not callable(getattr(self.ram, "dump", None)):
            raise DeviceError("ОЗУ не реализует метод dump()")

        if not callable(getattr(self.ssd, "write", None)):
            raise DeviceError("ЖД не реализует метод записи")

        if not callable(getattr(self.ssd, "read", None)):
            raise DeviceError("ЖД не реализует метод чтения")

        if not callable(getattr(self.ssd, "dump", None)):
            raise DeviceError("ЖД не реализует метод dump()")

        if self.keyboard:
            if not callable(getattr(self.keyboard, "listen", None)):
                raise DeviceError("Клавиатура неработоспособна")

    def _setup_write(self) -> None:
        if self.output and callable(getattr(self.output, "write", None)):
            self.write = lambda text: self.output.write(text)
        else:
            self.write = lambda text: print(text, end="")

    def start(self, mode: str = "normal") -> None:
        """Starts CPU, if not quiet, outputs messages about connected devices"""
        # Starting BIOS
        self.bios.start(self)

        # We can start CPU-loop
        match mode:
            case "normal":
                self.core.asi = "1" + format(5000, '014b')

                self.core.cmd = ""

                while self.core.cmd != "000000000000000":
                    if self.core.asi[0] == '1':
                        self.core.cmd = self.ram.read(int(self.core.asi[1:], 2))
                    else:
                        self.core.cmd = self.ssd.read(int(self.core.asi[1:], 2))

                    self.core.asi = format((int(self.core.asi, 2) + 1) & 0x7FFF, '015b')

                    self.core.handle_cmd()

                    if callable(getattr(self.output, "log", None)):
                        self.output.log()

            case "step-by-step":
                self.core.asi = "1" + format(5000, '014b')

                self.core.cmd = ""

                self.stepmode = True
            case _:
                raise CPU_Error(f"Процессор не реализует режим работы \"{mode}\". Проверьте, нет ли ошибок в названии, при надобности обратитесь к документации.")

    def step(self) -> str | None:
        if not self.stepmode:
            raise ValueError("Пошаговый режим не включён!")

        if self.core.cmd == "000000000000000":
            return "END"

        if self.core.asi[0] == '1':
            self.core.cmd = self.ram.read(int(self.core.asi[1:], 2))
        else:
            self.core.cmd = self.ssd.read(int(self.core.asi[1:], 2))

        self.core.asi = format((int(self.core.asi, 2) + 1) & 0x7FFF, '015b')

        self.core.handle_cmd()

        if callable(getattr(self.output, "log", None)):
            self.output.log()

        return None
    def connect(self, ram = None, ssd = None, keyboard = None, output = None, bios = None) -> None:
        """Connects device to CPU"""
        if ram:
            self.ram = ram

        if ssd:
            self.ssd = ssd

        if keyboard:
            self.keyboard = keyboard

        if output:
            self.output = output

        if bios:
            self.bios = bios

        self.check_devices()

        self._setup_write()

    def memread(self, addr: str) -> str:
        if not isinstance(addr, str) or len(addr) != 15:
            raise InvalidNumError(f"Адрес должен быть строкой из 15 бит, получено: {addr!r}")
        if not all(ch in '01' for ch in addr):
            raise InvalidNumError(f"Адрес содержит недопустимые символы: {addr!r}")

        device_bit = addr[0]
        raw_addr = int(addr[1:], 2)

        if addr == "000000000000000":
            if self.keyboard:
                read_method = getattr(self.keyboard, 'wait_read_char', None) or getattr(self.keyboard, 'read_char', None)
                if callable(read_method):
                    char = read_method()
                    if char is not None:
                        try:
                            value = char.encode('cp866')[0]
                            return format(value & 0xFF, '08b').zfill(15)
                        except:
                            pass
            return "000000000000000"

        if device_bit == '1':
            return self.ram.read(raw_addr)
        else:
            return self.ssd.read(raw_addr)

    def memwrite(self, addr: str, data: str) -> None:
        if not isinstance(addr, str) or len(addr) != 15:
            raise InvalidNumError(f"Адрес должен быть строкой из 15 бит, получено: {addr!r}")
        if not isinstance(data, str) or len(data) != 15:
            raise InvalidDataError(f"Данные должны быть строкой из 15 бит, получено: {data!r}")
        if not all(ch in '01' for ch in addr) or not all(ch in '01' for ch in data):
            raise InvalidNumError("Адрес и данные должны состоять только из '0' и '1'")

        device_bit = addr[0]
        raw_addr = int(addr[1:], 2)

        if addr == "000000000000000":
            value = int(data, 2) & 0xFF
            try:
                char = bytes([value]).decode('cp866')
                self.write(char)
            except:
                pass
            return

        if device_bit == '1':
            self.ram.write(raw_addr, data)
        else:
            self.ssd.write(raw_addr, data)

    def num_to_15bit(self, num: int) -> str:
        if not (type(num) is int):
            raise TypeError(f"Аргумент num, при передаче в метод CPU.num_to_15bit(), должен быть целым числом(int), а не {type(num)}")

        if not (-16383 <= num <= 16383):
            raise OverflowError(f"Число {num} не входит в поддерживаемые пределы:\n-16383..16383\n")

        sign_bit = '1' if num < 0 else '0'
        magnitude = abs(num)
        magnitude_bits = format(magnitude, '014b')
        return sign_bit + magnitude_bits


    def num_from_15bit(self, bits: str) -> int:
        if not (type(bits) is str):
            raise TypeError(f"Аргумент bits, при передаче в метод CPU.num_from_15bit(), должен быть строкой(str), а не {type(bits)}")

        if len(bits) != 15:
            raise InvalidNumError(f"Некорректное число: \"{bits}\". Длина должна быть 15 бит!")

        if not all(ch in '01' for ch in bits):
            raise InvalidNumError(f"Некорректное число: \"{bits}\". Двоичное число должно состоять ТОЛЬКО из \"1\" и \"0\".")

        sign = -1 if bits[0] == '1' else 1
        magnitude = int(bits[1:], 2)
        return sign * magnitude
