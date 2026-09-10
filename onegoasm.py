class ASMSyntaxError(ValueError):
    pass

class InstructionError(ValueError):
    pass

reg_dict = {
    "р0":  "0000",
    "р1":  "0001",
    "р2":  "0010",
    "р3":  "0011",
    "р4":  "0100",
    "р5":  "0101",
    "р6":  "0110",
    "р7":  "0111",
    "р8":  "1000",
    "р9":  "1001",
    "р10": "1010",
    "р11": "1011",
    "р12": "1100",
    "р13": "1101",
    "аси": "1110",
    "лз":  "1111"
}

opcodes_dict = {v: k for k, v in reg_dict.items()}


def compile_line(line: str):
    splited = [x for x in line.split() if x]

    if not splited:
        return None

    match splited[0]:
        case "сложи":
            return add_compile(line)
        case "вычти":
            return sub_compile(line)
        case "умножь":
            return mul_compile(line)
        case "если":
            return if_compile(line)
        case "запиши":
            return write_compile(line)
        case "прочитай":
            return read_compile(line)
        case "положи":
            return push_compile(line)
        case _:
            if len(splited) < 2 or (splited[1] != "больше" and splited[1] != "равно"):
                raise ASMSyntaxError(f"Я не понимаю эту строку:\n >> {line}\nВозможно, в ней есть опечатка.")

            if not splited[2].endswith('?'):
                raise ASMSyntaxError(f"Сравнение должно заканчиваться знаком '?':\n >> {line}")

            r1 = reg_dict[splited[0]]
            r2 = reg_dict[splited[2].rstrip('?')]
            if splited[1] == "равно":
                return f"110{r1}{r2}1111"
            else:
                return f"111{r1}{r2}1111"


def add_compile(line: str):
    splited = [x for x in line.split() if x]
    if splited[2] != "и" or splited[4] != "результат" or splited[5] != "положи" or splited[6] != "в":
        raise ASMSyntaxError(f"Я не понимаю эту строку:\n >> {line}\nВозможно, в ней есть опечатка.")
    r1 = reg_dict[splited[1]]
    r2 = reg_dict[splited[3][:-1]]
    rr = reg_dict[splited[7]]
    return f"000{r1}{r2}{rr}"


def mul_compile(line: str):
    splited = [x for x in line.split() if x]
    if splited[2] != "на" or splited[4] != "результат" or splited[5] != "положи" or splited[6] != "в":
        raise ASMSyntaxError(f"Я не понимаю эту строку:\n >> {line}\nВозможно, в ней есть опечатка.")
    r1 = reg_dict[splited[1]]
    r2 = reg_dict[splited[3][:-1]]
    rr = reg_dict[splited[7]]
    return f"010{r1}{r2}{rr}"


def sub_compile(line: str):
    splited = [x for x in line.split() if x]
    if splited[2] != "из" or splited[4] != "результат" or splited[5] != "положи" or splited[6] != "в":
        raise ASMSyntaxError(f"Я не понимаю эту строку:\n >> {line}\nВозможно, в ней есть опечатка.")
    r_x = reg_dict[splited[1]]
    r_y = reg_dict[splited[3][:-1]]
    rr  = reg_dict[splited[7]]
    return f"001{r_y}{r_x}{rr}"


def if_compile(line: str):
    splited = [x for x in line.split() if x]
    if splited[2] != "то" or (splited[1][:2] != "да" and splited[1][:3] != "нет"):
        raise ASMSyntaxError(f"Я не понимаю эту строку:\n >> {line}\nВозможно, в ней есть опечатка.")
    if splited[1][:2] == "да":
        return "011100000000000"
    else:
        return "011000000000000"

def write_compile(line: str):
    splited = [x for x in line.split() if x]
    if len(splited) != 4 or splited[2] != "в":
        raise ASMSyntaxError(f"Я не понимаю эту строку:\n >> {line}\nВозможно, в ней есть опечатка.")
    data_reg, addr_reg = splited[1], splited[3]
    if data_reg not in reg_dict:
        raise ASMSyntaxError(f"Неизвестный регистр: {data_reg}")
    if addr_reg not in reg_dict:
        raise ASMSyntaxError(f"Неизвестный регистр: {addr_reg}")
    return f"1001{reg_dict[addr_reg]}{reg_dict[data_reg]}000"

def read_compile(line: str):
    splited = [x for x in line.split() if x]
    if len(splited) != 5 or splited[1] != "из" or splited[3] != "в":
        raise ASMSyntaxError(f"Я не понимаю эту строку:\n >> {line}\nВозможно, в ней есть опечатка.")
    addr_reg, res_reg = splited[2], splited[4]
    if addr_reg not in reg_dict:
        raise ASMSyntaxError(f"Неизвестный регистр: {addr_reg}")
    if res_reg not in reg_dict:
        raise ASMSyntaxError(f"Неизвестный регистр: {res_reg}")
    return f"1000{reg_dict[addr_reg]}{reg_dict[res_reg]}000"

def push_compile(line: str):
    if line.startswith("положи ' ' в"):
        return f"101{reg_dict[line.split()[-1]]}{format(' '.encode('cp866')[0], '08b')}"
    splited = [x for x in line.split() if x]
    if len(splited) < 4 or splited[2] != "в":
        raise ASMSyntaxError(f"Я не понимаю эту строку:\n >> {line}\nВозможно, в ней есть опечатка.")
    reg = splited[3]
    if reg not in reg_dict:
        raise ASMSyntaxError(f"Неизвестный регистр: {reg}")
    operand = splited[1]
    if operand.startswith("'") and operand.endswith("'"):
        if len(operand) != 3:
            raise ASMSyntaxError(f"Символьный литерал должен содержать ровно один символ: {operand}")
        char = operand[1]
        try:
            value = char.encode('cp866')[0]
        except Exception:
            raise ASMSyntaxError(f"Невозможно закодировать символ '{char}' в cp866")
    else:
        try:
            value = int(operand)
        except ValueError:
            raise ASMSyntaxError(f"Операнд должен быть числом или символом в кавычках: {operand}")
    if not (0 <= value <= 255):
        raise ASMSyntaxError(f"Непосредственное значение должно быть от 0 до 255, получено: {value}")
    imm_bits = format(value, '08b')
    return f"101{reg_dict[reg]}{imm_bits}"


def compile_file(filename: str, outfile: str):
    with open(filename, "r") as f:
        asmcode = f.read()

    result = ""
    for line in asmcode.split("\n"):
        if line and not line.startswith("--"):
            compiled = compile_line(line)
            if compiled is not None:
                result += compiled

    if result:
        with open(outfile, "w") as f:
            f.write(result)


# disasm

def reg_from_bin(bin4: str) -> str:
    if bin4 not in opcodes_dict:
        raise InstructionError(f"Неизвестный код регистра: {bin4}")
    return opcodes_dict[bin4]


def disassemble_line(bits: str) -> str:
    if len(bits) != 15 or not all(c in '01' for c in bits):
        raise InstructionError(f"Некорректная бинарная строка: {bits}")

    opcode = bits[0:3]
    rest = bits[3:]

    if opcode == '000':          # add
        r1 = reg_from_bin(rest[0:4])
        r2 = reg_from_bin(rest[4:8])
        rr = reg_from_bin(rest[8:12])
        return f"сложи {r1} и {r2}, результат положи в {rr}"

    elif opcode == '001':        # sub
        r1 = reg_from_bin(rest[0:4])
        r2 = reg_from_bin(rest[4:8])
        rr = reg_from_bin(rest[8:12])
        return f"вычти {r2} из {r1}, результат положи в {rr}"

    elif opcode == '010':        # mul
        r1 = reg_from_bin(rest[0:4])
        r2 = reg_from_bin(rest[4:8])
        rr = reg_from_bin(rest[8:12])
        return f"умножь {r1} на {r2}, результат положи в {rr}"

    elif opcode == '011':        # if
        if rest[0] == '1':
            return "если да, то"
        else:
            return "если нет, то"

    elif opcode == '100':        # rw
        mode = rest[0]
        addr = reg_from_bin(rest[1:5])
        data = reg_from_bin(rest[5:9])
        if mode == '1':
            return f"запиши {data} в {addr}"
        else:
            return f"прочитай из {addr} в {data}"

    elif opcode == '101':        # push
        reg = reg_from_bin(rest[0:4])
        imm_bits = rest[4:12]
        imm_val = int(imm_bits, 2)
        return f"положи {imm_val} в {reg}"

    elif opcode == '110':        # eq
        r1 = reg_from_bin(rest[0:4])
        r2 = reg_from_bin(rest[4:8])
        if rest[8:12] != '1111':
            raise InstructionError(f"Некорректный формат сравнения: {bits}")
        return f"{r1} равно {r2}?"

    elif opcode == '111':        # gt
        r1 = reg_from_bin(rest[0:4])
        r2 = reg_from_bin(rest[4:8])
        if rest[8:12] != '1111':
            raise InstructionError(f"Некорректный формат сравнения: {bits}")
        return f"{r1} больше {r2}?"

    else:
        raise InstructionError(f"Неизвестный опкод: {opcode}")


def disassemble_binary(binary: str) -> list:
    binary = ''.join(binary.split())
    if len(binary) % 15 != 0:
        raise InstructionError("Длина бинарной строки не кратна 15 битам")
    lines = []
    for i in range(0, len(binary), 15):
        chunk = binary[i:i+15]
        lines.append(disassemble_line(chunk))
    return lines


def disassemble_file(infile: str, outfile: str):
    with open(infile, 'r') as f:
        binary = f.read()
    lines = disassemble_binary(binary)
    with open(outfile, 'w') as f:
        f.write('\n'.join(lines) + ('\n' if lines else ''))
