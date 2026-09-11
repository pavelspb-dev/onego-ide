class OverflowError(ValueError):
    """Register overflow"""
    pass

class InvalidBinError(ValueError):
    """15-bit bin isn't valid num"""
    pass

class DeviceError(ValueError):
    """Device invalid"""
    pass

class CPU_Error(ValueError):
    """Core isn't work"""
    pass

class CPU:
    def __init__(self, ram, core, bios, ssd, keyboard = None, output = None):
        """Initializes CPU"""

        # Defining instruction str
        self.cmd = ""

        # Connecting devices
        self.ram = ram
        self.core = core
        self.bios = bios
        self.ssd = ssd

        self.keyboard = keyboard
        self.output = output

        # Step-by-step mode is off
        self.stepmode = False

        # Checking connected devices and definiting self.write()
        self.check_devices()

        self.update_write()

    def check_devices(self) -> None:
        """Checks device's efficiency"""

        # BIOS check
        if not callable(getattr(self.bios, "start", None)):
            raise DeviceError("BIOS невозможно запустить!!")

        # Core check
        if not callable(getattr(self.core, "handle_cmd", None)):
            raise CPU_Error("Ядро процессора неработоспособно!!")

        # Core's registers check
        if not all((hasattr(self.core, "asi"), hasattr(self.core, "lz"),
                   hasattr(self.core, "r0"), hasattr(self.core, "r1"),
                   hasattr(self.core, "r2"), hasattr(self.core, "r3"),
                   hasattr(self.core, "r4"), hasattr(self.core, "r5"),
                   hasattr(self.core, "r6"), hasattr(self.core, "r7"),
                   hasattr(self.core, "r8"), hasattr(self.core, "r9"),
                   hasattr(self.core, "r10"), hasattr(self.core, "r11"),
                   hasattr(self.core, "r12"), hasattr(self.core, "r13"))):
            raise CPU_Error("Необходимый(-е) регистр(-ы) отсутствует(-ют)!")

        # RAM check
        if not callable(getattr(self.ram, "read", None)):
            raise DeviceError("ОЗУ не поддерживает метод чтения")

        if not callable(getattr(self.ram, "write", None)):
            raise DeviceError("ОЗУ не поддерживает метод записи")

        if not callable(getattr(self.ram, "dump", None)):
            raise DeviceError("ОЗУ не реализует метод dump()")

        # SSD check
        if not callable(getattr(self.ssd, "write", None)):
            raise DeviceError("ЖД не реализует метод записи")

        if not callable(getattr(self.ssd, "read", None)):
            raise DeviceError("ЖД не реализует метод чтения")

        if not callable(getattr(self.ssd, "dump", None)):
            raise DeviceError("ЖД не реализует метод dump()")

        # Keyboard check(if connected)
        if self.keyboard:
            if not callable(getattr(self.keyboard, "listen", None)):
                raise DeviceError("Клавиатура неработоспособна")

    def update_write(self) -> None:
        """Updates CPU.write()"""

        if self.output and callable(getattr(self.output, "write", None)):
            self.write = lambda text: self.output.write(text)
        else:
            self.write = lambda text: print(text, end="")

    def start(self, mode: str = "standart") -> None:
        """Starts CPU"""

        # Starting BIOS
        self.bios.start(self)

        # Continue, depending on the mode
        match mode:
            case "standart":
                # Setting ASI to address "RAM-5000". It is address of first instruction
                self.core.asi = "1" + format(5000, '014b')

                # Resetting core.cmd to avoid undefined behaviour
                self.core.cmd = ""

                while self.core.cmd != "000000000000000":
                    # Reading cmd
                    # It is RAM or SSD?
                    if self.core.asi[0] == '1':
                        # RAM
                        self.core.cmd = self.ram.read(int(self.core.asi[1:], 2))
                    else:
                        # SSD
                        self.core.cmd = self.ssd.read(int(self.core.asi[1:], 2))

                    # asi += 1
                    self.core.asi = format((int(self.core.asi, 2) + 1) & 0x7FFF, '015b')

                    # Handling instruction
                    self.core.handle_cmd()

                    # Log
                    if callable(getattr(self.output, "log", None)):
                        self.output.log()

            case "step-by-step":
                # ASI = RAM-5000
                self.core.asi = "1" + format(5000, '014b')

                # Resetting, to avoid undefined behaviour
                self.core.cmd = ""

                # It is step-mode, flag "stepmode" must be True
                self.stepmode = True

            case _:
                # Unknown mode
                raise CPU_Error(f"Процессор не реализует режим работы \"{mode}\". Проверьте, нет ли ошибок в названии, при надобности обратитесь к документации.")

    def step(self) -> str | None:
        # Does one step, stepmode must be True

        if not self.stepmode:
            raise ValueError(f"Пошаговый режим не включён! self.stepmode={self.stepmode}")

        # Instructions are over
        if self.core.cmd == "000000000000000":
            return "END"

        # Reading instruction from memory
        # It is RAM or SSD?
        if self.core.asi[0] == '1':
            # RAM
            self.core.cmd = self.ram.read(int(self.core.asi[1:], 2))
        else:
            # SSD
            self.core.cmd = self.ssd.read(int(self.core.asi[1:], 2))

        # asi += 1
        self.core.asi = format((int(self.core.asi, 2) + 1) & 0x7FFF, '015b')

        # Handling cmd
        self.core.handle_cmd()

        # Log
        if callable(getattr(self.output, "log", None)):
            self.output.log()

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

        # Validation and write()-update, to avoid errors
        self.check_devices()

        self._setup_write()

    def memread(self, addr: str) -> str:
        """Reads data from address addr"""

        # Address validation
        if not isinstance(addr, str) or len(addr) != 15:
            raise InvalidBinError(f"Адрес должен быть строкой из 15 бит, получено: {addr!r}")
        if not all(ch in '01' for ch in addr):
            raise InvalidBinError(f"Адрес содержит недопустимые символы: {addr!r}")

        # It is reading from keyboard
        if addr == "000000000000000":
            if self.keyboard:
                read_method = getattr(self.keyboard, 'wait_read_char', None) or getattr(self.keyboard, 'read_char', None)

                # Validating keyboard's read method
                if callable(read_method):
                    char = read_method()

                    if char is str:
                        return format(char.encode('cp866')[0] & 0xFF, '08b').zfill(15)

            return "000000000000000"

        # It is...
        if addr[0] == '1':
            # RAM
            return self.ram.read(int(addr[1:], 2))
        else:
            # SSD
            return self.ssd.read(int(addr[1:], 2))

    def memwrite(self, addr: str, data: str) -> None:
        """Writes data to memory(address=addr)"""

        # Validating arguments
        if not isinstance(addr, str) or len(addr) != 15:
            raise InvalidBinError(f"Адрес должен быть строкой из 15 бит, получено: {addr!r}")
        if not isinstance(data, str) or len(data) != 15:
            raise InvalidBinError(f"Данные должны быть строкой из 15 бит, получено: {data!r}")
        if not all(ch in '01' for ch in addr) or not all(ch in '01' for ch in data):
            raise InvalidBinError("Адрес и данные должны состоять только из '0' и '1'")

        if addr == "000000000000000":
            # Writing char to CPU.write
            self.write(bytes([int(data, 2) & 0xFF]).decode("cp866"))
            return

        # It is...
        if addr[0] == '1':
            # RAM
            self.ram.write(int(addr[1:], 2), data)
        else:
            # SSD
            self.ssd.write(int(addr[1:]. 2), data)

    def num_to_15bit(self, num: int) -> str:
        """Converts num to 15bit"""

        # Validating
        if not (type(num) is int):
            raise TypeError(f"Аргумент num, при передаче в метод CPU.num_to_15bit(), должен быть целым числом(int), а не {type(num)}")

        if not (-16383 <= num <= 16383):
            raise OverflowError(f"Число {num} не входит в поддерживаемые пределы:\n-16383..16383\n")

        return ('1' if num < 0 else '0') + format(abs(num), "014b")


    def num_from_15bit(self, bits: str) -> int:
        """Converts 15bit to num"""

        # Validating arguments
        if not (type(bits) is str):
            raise TypeError(f"Аргумент bits, при передаче в метод CPU.num_from_15bit(), должен быть строкой(str), а не {type(bits)}")

        if len(bits) != 15:
            raise InvalidBinError(f"Некорректное число: \"{bits}\". Длина должна быть 15 бит!")

        if not all(ch in '01' for ch in bits):
            raise InvalidBinError(f"Некорректное число: \"{bits}\". Двоичное число должно состоять ТОЛЬКО из \"1\" и \"0\".")

        return (-1 if bits[0] == '1' else 1) * int(bits[1:], 2)
