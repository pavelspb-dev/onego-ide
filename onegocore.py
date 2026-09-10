class Invalid15bits(ValueError):
    pass

class InvalidRegister(ValueError):
    pass

class Core:
    def __init__(self, cpu):
        self.r0 = "000000000000000"
        self.r1 = "000000000000000"
        self.r2 = "000000000000000"
        self.r3 = "000000000000000"
        self.r4 = "000000000000000"
        self.r5 = "000000000000000"
        self.r6 = "000000000000000"
        self.r7 = "000000000000000"
        self.r8 = "000000000000000"
        self.r9 = "000000000000000"
        self.r10 = "000000000000000"
        self.r11 = "000000000000000"
        self.r12 = "000000000000000"
        self.r13 = "000000000000000"
        self.asi = "000000000000000"
        self.lz = "000000000000000"

        self.cmd = "000000000000000"
        self.step = 0
        self.cpu = cpu

    def handle_cmd(self):
        self.step += 1
        match self.cmd[:3]:
            case "000":
                return self.execute_add()
            case "001":
                return self.execute_sub()
            case "010":
                return self.execute_mul()
            case "011":
                return self.execute_if()
            case "100":
                return self.execute_rw()
            case "101":
                return self.execute_push()
            case "110":
                return self.execute_eq()
            case "111":
                return self.execute_gt()

    def get_reg(self, reg):
        match reg:
            case "0000":
                return self.r0
            case "0001":
                return self.r1
            case "0010":
                return self.r2
            case "0011":
                return self.r3
            case "0100":
                return self.r4
            case "0101":
                return self.r5
            case "0110":
                return self.r6
            case "0111":
                return self.r7
            case "1000":
                return self.r8
            case "1001":
                return self.r9
            case "1010":
                return self.r10
            case "1011":
                return self.r11
            case "1100":
                return self.r12
            case "1101":
                return self.r13
            case "1110":
                return self.asi
            case "1111":
                return self.lz
            case _:
                raise InvalidRegister(f"Регистра \"{reg}\" не существует")

    def set_reg(self, reg, value):
        if not type(reg) is str or len(reg) != 4:
            raise InvalidRegister(f"Имя регистра - четыре бита. \"{reg}\"({type(reg)}) - невалидно.")
        if not type(value) is str or len(value) != 15:
            raise Invalid15bits(f"Данные - строка из 15 бит(0/1). \"{value}\"({type(value)}) - невалидно")

        match reg:
            case "0000":
                return None
            case "0001":
                self.r1 = value
            case "0010":
                self.r2 = value
            case "0011":
                self.r3 = value
            case "0100":
                self.r4 = value
            case "0101":
                self.r5 = value
            case "0110":
                self.r6 = value
            case "0111":
                self.r7 = value
            case "1000":
                self.r8 = value
            case "1001":
                self.r9 = value
            case "1010":
                self.r10 = value
            case "1011":
                self.r11 = value
            case "1100":
                self.r12 = value
            case "1101":
                self.r13 = value
            case "1110":
                self.asi = value
            case "1111":
                self.lz = value

    def _reg_value(self, reg_code: str) -> int:
        bits = self.get_reg(reg_code)
        if reg_code == "1110":
            if bits[0] == '1':
                return -(int(bits[1:], 2))
            else:
                return int(bits[1:], 2)
        else:
            return self.cpu.num_from_15bit(bits)

    def _value_to_reg(self, reg_code: str, value: int) -> str:
        if reg_code == "1110":
            if value < 0:
                value = 0x4000 | (-value)
            else:
                value = value & 0x7FFF
            return format(value, '015b')
        else:
            return self.cpu.num_to_15bit(value)

    def execute_add(self):
        reg1 = self._reg_value(self.cmd[3:7])
        reg2 = self._reg_value(self.cmd[7:11])
        result = reg1 + reg2
        self.set_reg(self.cmd[11:15], self._value_to_reg(self.cmd[11:15], result))

    def execute_sub(self):
        reg1 = self._reg_value(self.cmd[3:7])
        reg2 = self._reg_value(self.cmd[7:11])
        result = reg1 - reg2
        self.set_reg(self.cmd[11:15], self._value_to_reg(self.cmd[11:15], result))

    def execute_mul(self):
        reg1 = self._reg_value(self.cmd[3:7])
        reg2 = self._reg_value(self.cmd[7:11])
        result = reg1 * reg2
        self.set_reg(self.cmd[11:15], self._value_to_reg(self.cmd[11:15], result))

    def execute_if(self):
        if self.cmd[3] == '1':
            # if yes
            if self.lz != "111111111111111":
                self.asi = format((int(self.asi, 2) + 1) & 0x7FFF, '015b')
        else:
            # if not
            if self.lz == "111111111111111":
                self.asi = format((int(self.asi, 2) + 1) & 0x7FFF, '015b')

    def execute_rw(self):
        if self.cmd[3] == '1':
            addr = self.get_reg(self.cmd[4:8])
            data = self.get_reg(self.cmd[8:12])
            self.cpu.memwrite(addr, data)
        else:
            addr = self.get_reg(self.cmd[4:8])
            self.set_reg(self.cmd[8:12], self.cpu.memread(addr))

    def execute_push(self):
        self.set_reg(self.cmd[3:7], self.cmd[7:].zfill(15))

    def execute_eq(self):
        reg1 = self._reg_value(self.cmd[3:7])
        reg2 = self._reg_value(self.cmd[7:11])
        self.lz = "111111111111111" if reg1 == reg2 else "000000000000000"

    def execute_gt(self):
        reg1 = self._reg_value(self.cmd[3:7])
        reg2 = self._reg_value(self.cmd[7:11])
        self.lz = "111111111111111" if reg1 > reg2 else "000000000000000"
