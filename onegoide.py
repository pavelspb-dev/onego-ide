import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QTextEdit, QAction,
    QFileDialog, QMessageBox, QSplitter, QVBoxLayout, QWidget, QToolBar,
    QListWidget, QListWidgetItem, QTextBrowser, QPushButton, QHBoxLayout, QDockWidget,
    QLabel, QFrame, QSizePolicy
)
from PyQt5.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QTextCursor,
    QKeySequence, QIcon, QPixmap, QPainter, QBrush, QPen
)
from PyQt5.QtCore import Qt, QRegularExpression, QEventLoop, QTimer, QSize

import onegoasm
import onegocpu
import onegocore
import onegobios
import onegoram
import onegossd

DATA_DIR = os.path.join(os.path.expanduser("~"), ".onego-ide")

class AsmHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#c586c0"))
        keyword_format.setFontWeight(QFont.Bold)

        register_format = QTextCharFormat()
        register_format.setForeground(QColor("#4ec9b0"))
        register_format.setFontWeight(QFont.Bold)

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#d19a66"))

        char_format = QTextCharFormat()
        char_format.setForeground(QColor("#ce9178"))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#8a9a5b"))
        comment_format.setFontItalic(True)

        keywords = [
            "сложи", "вычти", "умножь", "если", "запиши", "прочитай", "положи",
            "да", "нет", "больше", "равно"
        ]
        for word in keywords:
            pattern = QRegularExpression(
                "\\b" + word + "\\b",
                QRegularExpression.UseUnicodePropertiesOption
            )
            self.highlighting_rules.append((pattern, keyword_format))

        registers = ["р0", "р1", "р2", "р3", "р4", "р5", "р6", "р7",
                     "р8", "р9", "р10", "р11", "р12", "р13", "аси", "лз"]
        for reg in registers:
            pattern = QRegularExpression(
                "\\b" + reg + "\\b",
                QRegularExpression.UseUnicodePropertiesOption
            )
            self.highlighting_rules.append((pattern, register_format))

        pattern = QRegularExpression(
            "\\b\\d+\\b",
            QRegularExpression.UseUnicodePropertiesOption
        )
        self.highlighting_rules.append((pattern, number_format))

        pattern = QRegularExpression("'[^']'")
        self.highlighting_rules.append((pattern, char_format))

        pattern = QRegularExpression("--[^\n]*")
        self.highlighting_rules.append((pattern, comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

class Keyboard:
    def __init__(self):
        self.buffer = []
        self.loop = None

    def add_char(self, char):
        self.buffer.append(char)
        if self.loop and self.loop.isRunning():
            self.loop.quit()

    def read_char(self):
        if self.buffer:
            return self.buffer.pop(0)
        return None

    def wait_read_char(self):
        if self.buffer:
            return self.buffer.pop(0)
        self.loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(self.loop.quit)
        timer.start(10000)
        self.loop.exec_()
        if self.buffer:
            return self.buffer.pop(0)
        return None

    def listen(self):
        pass

class ExecutionLogger:
    def __init__(self, settings):
        self.settings = settings
        self.steps = []
        self.prev_registers = {
            'r0': "000000000000000", 'r1': "000000000000000", 'r2': "000000000000000", 'r3': "000000000000000",
            'r4': "000000000000000", 'r5': "000000000000000", 'r6': "000000000000000", 'r7': "000000000000000",
            'r8': "000000000000000", 'r9': "000000000000000", 'r10': "000000000000000", 'r11': "000000000000000",
            'r12': "000000000000000", 'r13': "000000000000000", 'asi': "1" + format(5000, '014b'), 'lz': "000000000000000"
        }

    def log_step(self, cpu, core):
        step_num = len(self.steps) + 1
        cmd = core.cmd
        try:
            disasm = onegoasm.disassemble_line(cmd)
        except:
            disasm = "?"
        opcode = cmd[:3]

        changed = self.get_changed_registers(core)

        if changed:
            del changed["asi"]

        step_data = {
            'num': step_num,
            'cmd': cmd,
            'disasm': disasm,
            'changed': changed,
            'show_registers': self.settings.get('show_registers', True)
        }
        self.steps.append(step_data)
        self.prev_registers = self.get_all_registers(core)

    def get_all_registers(self, core):
        return {
            'r0': core.r0, 'r1': core.r1, 'r2': core.r2, 'r3': core.r3,
            'r4': core.r4, 'r5': core.r5, 'r6': core.r6, 'r7': core.r7,
            'r8': core.r8, 'r9': core.r9, 'r10': core.r10, 'r11': core.r11,
            'r12': core.r12, 'r13': core.r13, 'asi': core.asi, 'lz': core.lz
        }

    def get_changed_registers(self, core):
        if not self.prev_registers:
            return {}
        current = self.get_all_registers(core)
        changed = {}
        for name, val in current.items():
            if val != self.prev_registers.get(name):
                changed[name] = val
        return changed

    def render(self):
        if not self.steps:
            return ""

        html = "<table class='log-table'>"
        html += "<tr><th>Шаг</th><th>Команда</th><th>Изменённые регистры</th></tr>"
        for step in self.steps:
            html += "<tr>"
            html += f"<td>{step['num']}</td>"
            html += f"<td>{step['disasm']}</td>"
            if step['show_registers'] and step['changed']:
                changed_str = ", ".join([f"{name}: {val}" for name, val in step['changed'].items()])
                html += f"<td>{changed_str}</td>"
            else:
                html += "<td></td>"
            html += "</tr>"
        html += "</table>"
        return html

class OutputRedirect:
    def __init__(self, text_edit, logger):
        self.text_edit = text_edit
        self.logger = logger
        self.buffer = ""
        self.cpu = None
        self.core = None

    def write(self, text):
        self.buffer += text

        if self.text_edit:
            cursor = self.text_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(text)
            self.text_edit.setTextCursor(cursor)
            QApplication.processEvents()

    def flush(self):
        pass

    def log(self):
        if self.logger and self.cpu and self.core:
            self.logger.log_step(self.cpu, self.core)
        QApplication.processEvents()

class LessonManager:
    def __init__(self):
        self.lessons = self.create_lessons()

    def create_lessons(self):
        lessons = [
            {
                'id': 0,
                'title': 'Мой прогресс',
                'description': '',
                'example_code': '',
                'task': '',
                'hints': [],
                'check': None
            },
            {
                'id': 1,
                'title': 'Что такое Onego-15VA?',
                'description': '''
                    <h2>Добро пожаловать!</h2>
                    <p>Перед тобой учебный компьютер <b>Onego-15VA</b>. Он состоит из:</p>
                    <ul>
                        <li><b>Процессора (CPU)</b> — выполняет команды.</li>
                        <li><b>16 регистров</b> — быстрые ячейки для хранения чисел: <b>р0…р13, аси, лз</b>.</li>
                        <li><b>Оперативной памяти (RAM)</b> — 16384 ячейки, адреса от 0 до 16383. Программа загружается BIOS'ом в RAM, начиная с адреса 5000.</li>
                        <li><b>SSD</b> — диск, хранящий программу в файле <code>onegossd.img</code>.</li>
                        <li><b>BIOS</b> — программа, которая запускается при старте и готовит всё к работе.</li>
                    </ul>
                    <p>Регистр <b>р0</b> всегда равен нулю (запись в него игнорируется).</p>
                    <p>Регистр <b>лз</b> хранит результат последнего сравнения: <code>111111111111111</code> — истина, иначе ложь.</p>
                    <p>Регистр <b>аси</b> (адрес следующей инструкции) указывает, какую команду выполнить следующей. Обычно он увеличивается на 1 после каждой команды.</p>
                    <p><b>Как процессор выполняет программу?</b></p>
                    <ol>
                        <li>Читает команду из памяти по адресу из регистра <b>аси</b>.</li>
                        <li>Увеличивает <b>аси</b> на 1.</li>
                        <li>Выполняет команду.</li>
                        <li>Повторяет, пока не встретит пустую команду (все нули).</li>
                    </ol>
                    <p>Теперь перейдём к первой настоящей программе!</p>
                ''',
                'example_code': '',
                'task': 'Прочитай внимательно теорию и переходи к следующему уроку.',
                'hints': [],
                'check': None
            },
            {
                'id': 2,
                'title': 'Команда "положи"',
                'description': '''
                    <h2>Учимся записывать числа в регистры</h2>
                    <p>Команда <code>положи</code> записывает число или символ в регистр.</p>
                    <p>Синтаксис:</p>
                    <pre>положи 42 в р3</pre>
                    <p>После этой команды в регистре <b>р3</b> будет число 42.</p>
                    <p>Можно использовать символы (в кодировке CP866):</p>
                    <pre>положи 'A' в р5</pre>
                    <p>Регистр <b>р0</b> особенный: запись в него игнорируется, он всегда равен нулю.</p>
                    <p>Проверить значение регистра можно после выполнения программы в таблице «Регистры после выполнения».</p>
                    <p><b>Пример:</b></p>
                    <pre>положи 77 в р2</pre>
                    <p>Этот код поместит 77 в регистр р2.</p>
                ''',
                'example_code': "положи 77 в р2",
                'task': 'Положи число 77 в регистр р2.',
                'hints': [
                    'Используй команду положи.',
                    'Число 77 записывается без кавычек.',
                    'Регистр р2 указывается после "в".'
                ],
                'check': lambda ctx: (ctx['regs']['р2'] == 77, 'Регистр р2 должен содержать 77. Проверь команду положи.')
            },
            {
                'id': 3,
                'title': 'Вывод символа',
                'description': '''
                    <h2>Печатаем символ на экране</h2>
                    <p>Чтобы вывести символ, нужно:</p>
                    <ol>
                        <li>Положить код символа в любой регистр (кроме р0 и аси).</li>
                        <li>Записать данные из этого регистра по адресу <b>0</b> (в регистре р0 всегда 0).</li>
                    </ol>
                    <p>Команда <code>запиши</code> пишет данные из регистра-источника в память по адресу из регистра-адреса.</p>
                    <pre>запиши р1 в р0</pre>
                    <p>Здесь р1 — источник, р0 — адрес (0).</p>
                    <p><b>Пример (выводит 'К'):</b></p>
                    <pre>положи 'К' в р1
запиши р1 в р0</pre>
                    <p><b>Твоя задача:</b> вывести символ 'М' (латинская заглавная).</p>
                ''',
                'example_code': "положи 'К' в р1\nзапиши р1 в р0",
                'task': 'Выведи символ «М» (латинская заглавная).',
                'hints': [
                    'Используй команды положи и запиши.',
                    'Символ записывается в одиночных кавычках: \'М\'',
                    'В качестве регистра-адреса используй р0.'
                ],
                'check': lambda ctx: (ctx['output'] == 'М', 'Выведено не "М". Проверь регистр и команды.')
            },
            {
                'id': 4,
                'title': 'Вывод строки',
                'description': '''
                    <h2>Несколько символов подряд</h2>
                    <p>Чтобы вывести строку, нужно вывести каждый символ по очереди.</p>
                    <p>Пример вывода «Кот»:</p>
                    <pre>положи 'К' в р1
запиши р1 в р0
положи 'о' в р1
запиши р1 в р0
положи 'т' в р1
запиши р1 в р0</pre>
                    <p>Пробел — тоже символ: <code>' '</code>.</p>
                    <p><b>Твоя задача:</b> вывести строку <b>«Привет, мир!»</b> (с запятой, пробелом и восклицательным знаком).</p>
                ''',
                'example_code': "положи 'К' в р1\nзапиши р1 в р0\nположи 'о' в р1\nзапиши р1 в р0\nположи 'т' в р1\nзапиши р1 в р0",
                'task': 'Выведи «Привет, мир!» (с запятой, пробелом и восклицательным знаком).',
                'hints': [
                    'Каждая буква — пара команд: положи и запиши.',
                    'Пробел записывается как \' \' (один пробел между кавычками).',
                    'Следи за порядком символов и регистром букв (строчные/прописные).'
                ],
                'check': lambda ctx: (ctx['output'] == 'Привет, мир!', 'Вывод не совпадает с "Привет, мир!". Проверь все символы и пробел.')
            },
            {
                'id': 5,
                'title': 'Арифметика',
                'description': '''
                    <h2>Считаем на процессоре</h2>
                    <p>Команды:</p>
                    <ul>
                        <li><code>сложи X и Y, результат положи в Z</code> — Z = X + Y</li>
                        <li><code>вычти X из Y, результат положи в Z</code> — Z = Y - X (обрати внимание на порядок!)</li>
                        <li><code>умножь X на Y, результат положи в Z</code> — Z = X * Y</li>
                    </ul>
                    <p>Числа могут быть отрицательными (15-битный дополнительный код).</p>
                    <p>Пример: вычислить (5+3)*2 и результат в р5:</p>
                    <pre>положи 5 в р1
положи 3 в р2
сложи р1 и р2, результат положи в р3
положи 2 в р4
умножь р3 на р4, результат положи в р5</pre>
                    <p>После выполнения в р5 будет 16.</p>
                    <p><b>Твоя задача:</b> вычисли <code>(6 + 4) * 3</code> и сохрани результат в регистре <b>р5</b>. Выводить ничего не нужно.</p>
                ''',
                'example_code': "положи 5 в р1\nположи 3 в р2\nсложи р1 и р2, результат положи в р3\nположи 2 в р4\nумножь р3 на р4, результат положи в р5",
                'task': 'Вычисли (6+4)*3 и положи результат в р5.',
                'hints': [
                    'Сначала сложи 6 и 4 в какой-нибудь регистр.',
                    'Затем умножь сумму на 3.',
                    'Команда вычти: вычти р2 из р1 означает р1 - р2.'
                ],
                'check': lambda ctx: (ctx['regs']['р5'] == 30, 'Регистр р5 должен содержать 30. Проверь порядок операций.')
            },
            {
                'id': 6,
                'title': 'Сравнения',
                'description': '''
                    <h2>Сравниваем значения</h2>
                    <p>Сравнения записываются как вопросы:</p>
                    <pre>р1 больше р2?
р1 равно р2?</pre>
                    <p>Результат попадает в регистр <b>лз</b>:</p>
                    <ul>
                        <li><code>111111111111111</code> — истина (да)</li>
                        <li><code>000000000000000</code> — ложь (нет)</li>
                    </ul>
                    <p>Пример:</p>
                    <pre>положи 10 в р1
положи 5 в р2
р1 больше р2?</pre>
                    <p>После выполнения <b>лз</b> станет истиной (10 > 5).</p>
                    <p><b>Твоя задача:</b> сделай так, чтобы после выполнения программы регистр <b>лз</b> был истиной. Подсказка: сравни 8 и 3.</p>
                ''',
                'example_code': "положи 10 в р1\nположи 5 в р2\nр1 больше р2?",
                'task': 'Сделай так, чтобы флаг лз стал истиной (сравни 8 и 3, вопрос "8 больше 3?").',
                'hints': [
                    'Используй вопрос "больше".',
                    'Положи 8 в один регистр, 3 в другой.',
                    'Сравни первый регистр со вторым.'
                ],
                'check': lambda ctx: (ctx['regs']['лз'] == 1, 'Флаг лз должен быть истиной. Проверь, что сравниваешь 8 > 3.')
            },
            {
                'id': 7,
                'title': 'Условные переходы',
                'description': '''
                    <h2>Ветвление программы</h2>
                    <p>Команда <code>если да, то</code> или <code>если нет, то</code> позволяет пропустить следующую команду, если условие (флаг лз) не выполняется.</p>
                    <p>Если условие <b>истинно</b>, выполняется следующая команда как обычно.<br>
                    Если <b>ложно</b>, следующая команда <b>пропускается</b> (счётчик аси увеличивается на 2 вместо 1).</p>
                    <p>Пример: вывести «1», если 5 > 3.</p>
                    <pre>положи 5 в р1
положи 3 в р2
р1 больше р2?
положи '1' в р3
если да, то
запиши р3 в р0</pre>
                    <p>Если условие ложно, команда <code>положи '1' в р3</code> будет пропущена.</p>
                    <p><b>Твоя задача:</b> напиши программу, которая выводит символ «О», если 5 равно 5 (это истина, поэтому символ должен выводиться).</p>
                ''',
                'example_code': "положи 5 в р1\nположи 3 в р2\nр1 больше р2?\nположи '1' в р3\nесли да, то\nзапиши р3 в р0",
                'task': 'Выведи «О», если 5 равно 5 (условие истинно, символ должен вывестись).',
                'hints': [
                    'Сравни 5 и 5 на равенство.',
                    'Используй "если да, то".',
                    'Поскольку условие истинно, команда вывода выполнится.'
                ],
                'check': lambda ctx: (ctx['output'] == 'О', 'Программа должна вывести "О". Убедись, что условие истинно и команда вывода выполняется.')
            },
            {
                'id': 8,
                'title': 'Циклы',
                'description': '''
                    <h2>Повторяем действия</h2>
                    <p>Цикл позволяет выполнять одни и те же команды несколько раз. Для этого нужно:</p>
                    <ol>
                        <li>Завести счётчик (регистр с числом повторений).</li>
                        <li>Выполнить нужные команды.</li>
                        <li>Уменьшить счётчик на 1.</li>
                        <li>Если счётчик больше нуля, вернуться к началу цикла.</li>
                    </ol>
                    <p>Возврат осуществляется изменением регистра <b>аси</b> (адрес следующей инструкции). Если установить <b>аси</b> на адрес первой команды цикла, то процессор продолжит выполнение с этой команды.</p>
                    <p>Важно: программа загружается в RAM с адреса 5000, поэтому адрес команды = 5000 + её порядковый номер (начиная с 0).</p>
                    <p>Однако команда <code>положи</code> не может загрузить число больше 255. Поэтому адрес 5001 придётся вычислить через арифметику. Например, так:</p>
                    <pre>положи 100 в р5
вычти р5 из р4, результат положи в р4   -- р4 = 0 - 100 = -100 (знак-модуль)
положи 50 в р5
умножь р4 на р5, результат положи в р4   -- р4 = -100 * 50 = -5000
положи 10 в р5
вычти р5 из р4, результат положи в р4   -- р4 = -5000 - 10 = -5010</pre>
                    <p>Теперь в р4 лежит -5010 (бинарно: 1 01001110010010) — это адрес RAM 5010 с установленным старшим битом. Осталось добавить нужное смещение (в нашем случае 1) и записать в <b>аси</b>.</p>
                    <p>Вот рабочий пример цикла, выводящего 'A' три раза:</p>
                    <pre>положи 3 в р2          -- счётчик повторений
положи 'A' в р1        -- символ
положи 1 в р3          -- для декремента
-- вычисляем адрес возврата: -5010
положи 100 в р5
вычти р5 из р4, результат положи в р4
положи 50 в р5
умножь р4 на р5, результат положи в р4
положи 10 в р5
вычти р5 из р4, результат положи в р4
-- сам цикл
запиши р1 в р0         -- вывод (адрес 5008? – но мы переходим на метку ниже)
положи 1 в р4          -- временно
сложи р2 и р3, результат положи в р2   -- счётчик++
р2 равно р13?          -- если счётчик == 3? (р13 предварительно 0? нет)
если нет, то
сложи р0 и р4, результат положи в аси   -- переход</pre>
                    <p>В этом примере много лишнего, но он показывает подход. <b>Для простоты в этом задании мы разрешаем развернуть цикл (повторить команды несколько раз).</b> Поэтому ты можешь просто три раза подряд написать команды вывода.</p>
                    <p><b>Твоя задача:</b> выведи строку «ААА» (три буквы А подряд).</p>
                ''',
                'example_code': '',
                'task': 'Выведи «ААА» (три буквы А подряд).',
                'hints': [
                    'Проще всего написать три пары команд: положи \'А\' в р1 и запиши р1 в р0.',
                    'Если хочешь цикл, аккуратно вычисли адрес возврата.',
                    'В цикле не забудь уменьшать счётчик и проверять его.'
                ],
                'check': lambda ctx: (ctx['output'] == 'ААА', 'Ожидался вывод "ААА". Проверь, что выводится три раза.')
            },
            {
                'id': 9,
                'title': 'Работа с памятью',
                'description': '''
                    <h2>Запись и чтение из RAM</h2>
                    <p>Команды:</p>
                    <ul>
                        <li><code>запиши данные в адрес</code> — пишет 15 бит из регистра данных в ячейку памяти по адресу из регистра адреса.</li>
                        <li><code>прочитай из адрес в регистр</code> — читает 15 бит из памяти по адресу в регистр.</li>
                    </ul>
                    <p>RAM‑адрес задаётся отрицательным числом: например, адрес 200 соответствует -200 (старший бит = 1).</p>
                    <p>Как получить -200:</p>
                    <pre>положи 200 в р1
вычти р1 из р0, результат положи в р1   -- 0 - 200 = -200</pre>
                    <p>Теперь в р1 лежит -200 (бинарно: 1xxxxxxxxxxxxxx), что указывает на RAM‑адрес 200.</p>
                    <p><b>Твоя задача:</b> запиши число 55 в RAM по адресу 150, затем прочитай его в регистр р6.</p>
                ''',
                'example_code': "положи 100 в р1\nвычти р1 из р0, результат положи в р1\nположи 42 в р2\nзапиши р2 в р1",
                'task': 'Запиши 55 в RAM по адресу 150 и прочитай обратно в р6. Адрес получи как отрицательное число: 0 - 150.',
                'hints': [
                    'Сначала положи 150 в р1.',
                    'Вычисли -150: вычти р1 из р0 (р0=0), результат положи в р1.',
                    'Положи 55 в р2, затем запиши р2 в р1.',
                    'Прочитай из р1 в р6 и проверь, что р6=55.'
                ],
                'check': lambda ctx: (ctx['ram'][150] == '000000000110111' and ctx['regs']['р6'] == 55, 'RAM[150] или регистр р6 содержат неверное значение. Проверь вычисление адреса и порядок команд.')
            },
            {
                'id': 10,
                'title': 'Ввод с клавиатуры',
                'description': '''
                    <h2>Читаем символ</h2>
                    <p>Адрес 0 используется не только для вывода, но и для ввода.</p>
                    <p>Команда <code>прочитай из р0 в р1</code> прочитает символ с клавиатуры и положит его код в р1.</p>
                    <p>Если клавиша не нажата, будет прочитан 0.</p>
                    <p><b>Твоя задача:</b> напиши программу, которая читает символ с клавиатуры и выводит его же на экран (эхо).</p>
                    <p><i>Для проверки нажми клавишу во время выполнения программы (окно IDE должно быть в фокусе).</i></p>
                ''',
                'example_code': "прочитай из р0 в р1\nзапиши р1 в р0",
                'task': 'Считай символ с клавиатуры и выведи его обратно.',
                'hints': [
                    'Используй прочитай из р0 в р1.',
                    'Затем запиши р1 в р0 (вывод).',
                    'Программа может завершиться сразу после чтения, если клавиша была нажата заранее.'
                ],
                'check': None
            },
            {
                'id': 11,
                'title': 'Итоговый проект: мини-калькулятор',
                'description': '''
                    <h2>Соединяем всё вместе</h2>
                    <p>Создай программу, которая:</p>
                    <ol>
                        <li>Читает два числа с клавиатуры (одна цифра каждое).</li>
                        <li>Вычитает из первого второе (убедись, что первое больше).</li>
                        <li>Выводит результат как символ цифры (например, 7-3 → '4').</li>
                    </ol>
                    <p>Коды символов цифр в CP866: '0'=48, '1'=49 и т.д. Поэтому после вычитания нужно прибавить 48, чтобы получить код символа.</p>
                    <p>Это сложная задача, но ты уже многое умеешь!</p>
                    <p><i>Проверка ручная – просто запусти программу, введи две цифры и посмотри на вывод.</i></p>
                ''',
                'example_code': '',
                'task': 'Реализуй калькулятор: первая цифра минус вторая, выведи результат.',
                'hints': [
                    'Сначала прочитай две цифры в разные регистры.',
                    'Вычти 48 из каждой, чтобы получить числовое значение.',
                    'Вычти второе число из первого.',
                    'Прибавь 48 к результату и выведи.'
                ],
                'check': None
            },
        ]
        return lessons

class LessonPanel(QWidget):
    def __init__(self, ide):
        super().__init__()
        self.ide = ide
        self.current_lesson_index = 0
        self.hint_index = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.lesson_list = QListWidget()
        self.lesson_list.setObjectName("lessonList")
        self.lesson_list.itemClicked.connect(self.on_lesson_selected)
        self.refresh_lesson_list()
        self.lesson_list.setStyleSheet("""
            QListWidget#lessonList {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: none;
                border-right: 1px solid #3c3c3c;
                padding: 10px 5px;
                font-size: 13px;
                outline: none;
            }
            QListWidget#lessonList::item {
                padding: 8px 10px;
                border-radius: 5px;
                margin: 2px 0;
            }
            QListWidget#lessonList::item:selected {
                background-color: #4a9eff;
                color: white;
            }
            QListWidget#lessonList::item:hover {
                background-color: #3e3e3e;
            }
            QListWidget#lessonList::item[completed="true"] {
                background-color: #2d5a2d;
                color: #a5d6a7;
            }
            QListWidget#lessonList::item[completed="true"]:selected {
                background-color: #4caf50;
                color: white;
            }
            QListWidget#lessonList::item[isProgress="true"] {
                background-color: #3a3a3a;
                color: #ffd54f;
                font-weight: bold;
            }
        """)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        self.lesson_title = QLabel()
        self.lesson_title.setObjectName("lessonTitle")
        self.lesson_title.setWordWrap(True)
        self.lesson_title.setStyleSheet("""
            QLabel#lessonTitle {
                font-size: 18px;
                font-weight: bold;
                color: #ba68c8;
                padding: 5px 10px;
                background-color: #2d2d2d;
                border-radius: 6px;
            }
        """)

        self.lesson_view = QTextBrowser()
        self.lesson_view.setOpenExternalLinks(True)
        self.lesson_view.setStyleSheet("""
            QTextBrowser {
                font-family: 'Segoe UI', 'Arial', sans-serif;
                font-size: 13px;
                line-height: 1.5;
                padding: 10px;
                background-color: #20242a;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                color: #e0e0e0;
            }
            QTextBrowser h2 {
                color: #ba68c8;
                font-size: 16px;
                margin-top: 15px;
                margin-bottom: 5px;
            }
            QTextBrowser h3 {
                color: #4a9eff;
                font-size: 14px;
                margin-top: 10px;
                margin-bottom: 5px;
            }
            QTextBrowser p {
                margin: 8px 0;
            }
            QTextBrowser ul, QTextBrowser ol {
                margin: 8px 0;
                padding-left: 20px;
            }
            QTextBrowser li {
                margin: 4px 0;
            }
            QTextBrowser pre {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px;
                white-space: pre-wrap;
                word-wrap: break-word;
                font-family: 'Consolas', 'Courier New', monospace;
                color: #d4d4d4;
            }
            QTextBrowser code {
                background-color: #2d2d2d;
                padding: 1px 4px;
                border-radius: 3px;
                font-family: 'Consolas', 'Courier New', monospace;
                color: #ce9178;
            }
        """)

        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("← Предыдущий")
        self.btn_next = QPushButton("Следующий →")
        self.btn_prev.setObjectName("navButton")
        self.btn_next.setObjectName("navButton")
        self.btn_prev.clicked.connect(self.prev_lesson)
        self.btn_next.clicked.connect(self.next_lesson)
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)

        btn_layout = QHBoxLayout()
        self.btn_example = QPushButton("📋 Пример")
        self.btn_check = QPushButton("✅ Проверить")
        self.btn_hint = QPushButton("💡 Подсказка")
        self.btn_example.setObjectName("btnExample")
        self.btn_check.setObjectName("btnCheck")
        self.btn_hint.setObjectName("btnHint")
        self.btn_example.clicked.connect(self.insert_example)
        self.btn_check.clicked.connect(self.check_solution)
        self.btn_hint.clicked.connect(self.show_hint)
        btn_layout.addWidget(self.btn_example)
        btn_layout.addWidget(self.btn_check)
        btn_layout.addWidget(self.btn_hint)
        btn_layout.addStretch()

        right_layout.addWidget(self.lesson_title)
        right_layout.addWidget(self.lesson_view, 1)
        right_layout.addLayout(nav_layout)
        right_layout.addLayout(btn_layout)

        splitter.addWidget(self.lesson_list)
        splitter.addWidget(right_panel)
        splitter.setSizes([220, 500])

        layout.addWidget(splitter)

        self.setStyleSheet("""
            QPushButton#navButton {
                background-color: #3a3a3a;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px 12px;
                color: #e0e0e0;
            }
            QPushButton#navButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton#btnExample {
                background-color: #8e24aa;
                border: 1px solid #ab47bc;
                border-radius: 4px;
                padding: 6px 12px;
                color: white;
                font-weight: bold;
            }
            QPushButton#btnExample:hover {
                background-color: #9c27b0;
            }
            QPushButton#btnCheck {
                background-color: #1e88e5;
                border: 1px solid #42a5f5;
                border-radius: 4px;
                padding: 6px 12px;
                color: white;
                font-weight: bold;
            }
            QPushButton#btnCheck:hover {
                background-color: #2196f3;
            }
            QPushButton#btnHint {
                background-color: #fb8c00;
                border: 1px solid #ffa726;
                border-radius: 4px;
                padding: 6px 12px;
                color: white;
                font-weight: bold;
            }
            QPushButton#btnHint:hover {
                background-color: #f57c00;
            }
        """)

        if self.ide.lesson_manager.lessons:
            self.set_current_lesson(0)

    def refresh_lesson_list(self):
        self.lesson_list.clear()
        for i, lesson in enumerate(self.ide.lesson_manager.lessons):
            title = lesson['title']
            is_progress = (lesson['id'] == 0)
            completed = self.ide.is_lesson_completed(lesson['id']) if not is_progress else False
            if completed:
                title = "✔ " + title
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, i)
            item.setData(Qt.UserRole + 1, lesson['id'])
            item.setData(Qt.UserRole + 2, "true" if completed else "false")
            item.setData(Qt.UserRole + 3, "true" if is_progress else "false")
            self.lesson_list.addItem(item)

    def set_current_lesson(self, index):
        if 0 <= index < len(self.ide.lesson_manager.lessons):
            self.current_lesson_index = index
            self.hint_index = 0
            lesson = self.ide.lesson_manager.lessons[index]
            self.lesson_title.setText(lesson['title'])
            self.lesson_list.setCurrentRow(index)
            self.display_lesson()
            self.update_check_button()

    def on_lesson_selected(self, item):
        index = item.data(Qt.UserRole)
        self.set_current_lesson(index)

    def prev_lesson(self):
        self.set_current_lesson(self.current_lesson_index - 1)

    def next_lesson(self):
        self.set_current_lesson(self.current_lesson_index + 1)

    def display_lesson(self):
        lesson = self.ide.lesson_manager.lessons[self.current_lesson_index]
        if lesson['id'] == 0:
            html = self.generate_progress_html()
            self.lesson_view.setHtml(html)
        else:
            html = lesson['description']
            html += f"<h3>Задание</h3><p>{lesson['task']}</p>"
            if lesson.get('example_code'):
                html += "<h3>Пример кода</h3><pre>" + lesson['example_code'] + "</pre>"
            self.lesson_view.setHtml(html)

    def generate_progress_html(self):
        total_lessons = len([l for l in self.ide.lesson_manager.lessons if l['id'] != 0])
        completed = len(self.ide.completed_lessons)
        percent = int(completed / total_lessons * 100) if total_lessons > 0 else 0
        achievements = [
            ("🌟 Начало пути", 1),
            ("🖥️ Первая программа", 2),
            ("📜 Строковый мастер", 4),
            ("➕ Арифметик", 5),
            ("⚖️ Логик", 6),
            ("🔀 Ветвление", 7),
            ("🔄 Циклы", 8),
            ("💾 Память", 9),
            ("⌨️ Клавиатура", 10),
            ("🏆 Итоговый проект", 11)
        ]
        html = f"""
        <h2>Мой прогресс</h2>
        <p>Выполнено уроков: <b>{completed}</b> из <b>{total_lessons}</b></p>
        <div style="background-color:#3c3c3c;border-radius:5px;padding:2px;margin:10px 0;">
            <div style="background-color:#4caf50;width:{percent}%;height:20px;border-radius:5px;text-align:center;color:white;line-height:20px;">{percent}%</div>
        </div>
        <h3>Достижения</h3>
        <ul>
        """
        for name, lesson_id in achievements:
            status = "✅" if lesson_id in self.ide.completed_lessons else "🔒"
            html += f"<li>{status} {name}</li>"
        html += "</ul>"
        return html

    def insert_example(self):
        lesson = self.ide.lesson_manager.lessons[self.current_lesson_index]
        if lesson.get('example_code'):
            self.ide.editor.setPlainText(lesson['example_code'])

    def show_hint(self):
        lesson = self.ide.lesson_manager.lessons[self.current_lesson_index]
        hints = lesson.get('hints', [])
        if not hints:
            QMessageBox.information(self, "Подсказка", "Для этого урока нет подсказок.")
            return
        hint = hints[self.hint_index % len(hints)]
        self.hint_index += 1
        QMessageBox.information(self, "Подсказка", hint)

    def update_check_button(self):
        lesson = self.ide.lesson_manager.lessons[self.current_lesson_index]
        if lesson['id'] == 0:
            self.btn_example.hide()
            self.btn_check.hide()
            self.btn_hint.hide()
            return
        self.btn_example.show()
        self.btn_check.show()
        self.btn_hint.show()
        if lesson.get('check') is None:
            self.btn_check.setText("🏁 Готово")
            try:
                self.btn_check.clicked.disconnect()
            except TypeError:
                pass
            self.btn_check.clicked.connect(self.mark_as_done)
        else:
            self.btn_check.setText("✅ Проверить")
            try:
                self.btn_check.clicked.disconnect()
            except TypeError:
                pass
            self.btn_check.clicked.connect(self.check_solution)

    def mark_as_done(self):
        lesson = self.ide.lesson_manager.lessons[self.current_lesson_index]
        self.ide.complete_lesson(lesson['id'])
        self.refresh_lesson_list()
        self.set_current_lesson(self.current_lesson_index)
        QMessageBox.information(self, "Прогресс", "Отлично! Задание отмечено как выполненное.")

    def check_solution(self):
        lesson = self.ide.lesson_manager.lessons[self.current_lesson_index]
        self.ide.run_program()
        if self.ide.last_core is None:
            return

        ram_dump = {}
        if hasattr(self.ide, 'last_ram'):
            for i, val in enumerate(self.ide.last_ram.dump()):
                ram_dump[i] = val
        else:
            ram_dump = {}
        context = {
            'output': self.ide.last_output_text,
            'core': self.ide.last_core,
            'regs': self.ide.last_regs,
            'ram': ram_dump
        }

        check_func = lesson.get('check')
        if check_func:
            success, message = check_func(context)
            if success:
                self.ide.complete_lesson(lesson['id'])
                self.refresh_lesson_list()
                self.set_current_lesson(self.current_lesson_index)
                QMessageBox.information(self, "Проверка", "🎉 Отлично! Задание выполнено!")
            else:
                QMessageBox.warning(self, "Проверка", message)
        else:
            QMessageBox.warning(self, "Проверка", "Для этого урока нет автоматической проверки. Запусти программу вручную и сравни результат.")

class OnegoIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.log_settings = {
            'show_registers': True
        }
        self.keyboard = Keyboard()
        self.lesson_manager = LessonManager()
        self.last_core = None
        self.last_output_text = ""
        self.last_regs = {}
        self.progress_file = os.path.join(DATA_DIR, "progress.json")
        self.completed_lessons = self.load_progress()

        self.debug_cpu = None
        self.debug_core = None
        self.debug_ram = None
        self.debug_ssd = None
        self.debug_bios = None
        self.debug_logger = None
        self.debug_output_redirect = None
        self.debug_step_count = 0

        self.init_ui()

    def load_progress(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return set(data.get('completed', []))
            except:
                return set()
        return set()

    def save_progress(self):
        data = {'completed': list(self.completed_lessons)}
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except:
            pass

    def is_lesson_completed(self, lesson_id):
        return lesson_id in self.completed_lessons

    def complete_lesson(self, lesson_id):
        self.completed_lessons.add(lesson_id)
        self.save_progress()

    def init_ui(self):
        self.setWindowTitle("Онего IDE")
        self.setGeometry(100, 100, 1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QPlainTextEdit, QTextEdit, QTextBrowser {
                background-color: #20242a;
                color: #e0e0e0;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 5px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                selection-background-color: #4a9eff;
            }
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #3a4a5a, stop:1 #2d2d2d);
                border: none;
                padding: 4px;
                spacing: 4px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                padding: 5px;
                border-radius: 4px;
                color: #d4d4d4;
            }
            QToolButton:hover {
                background: #4a4a4a;
                border: 1px solid #555;
            }
            QToolButton:pressed {
                background: #606060;
            }
            QMenuBar {
                background: #2d2d2d;
                color: #d4d4d4;
                border-bottom: 1px solid #3c3c3c;
            }
            QMenuBar::item {
                background: transparent;
                padding: 4px 8px;
            }
            QMenuBar::item:selected {
                background: #3e3e3e;
                border-radius: 4px;
            }
            QMenu {
                background: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
            QMenu::item:selected {
                background: #4a9eff;
                color: white;
            }
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #1565c0, stop:1 #2196f3);
                color: white;
                font-weight: bold;
                padding-left: 8px;
            }
            QListWidget {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                padding: 5px;
                font-size: 13px;
            }
            QListWidget::item:selected {
                background-color: #4a9eff;
                color: white;
            }
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                    stop:0 #5a5a5a, stop:1 #4a4a4a);
                border-color: #777;
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                                    stop:0 #3a3a3a, stop:1 #2a2a2a);
            }
            QSplitter::handle {
                background: #3c3c3c;
            }
            QSplitter::handle:hover {
                background: #4a9eff;
            }
            QDockWidget::title {
                background: #2d2d2d;
                padding: 6px;
                border-bottom: 1px solid #3c3c3c;
                text-align: left;
            }
            QDockWidget::close-button, QDockWidget::float-button {
                background: transparent;
                border: none;
            }
            QDockWidget::close-button:hover, QDockWidget::float-button:hover {
                background: #4a4a4a;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        self.editor = QPlainTextEdit()
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.highlighter = AsmHighlighter(self.editor.document())

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setHtml("""<html><head><style>
            body { font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; color: #d4d4d4; background-color: #252526; }
            .bios-output { white-space: pre-wrap; margin-bottom: 15px; }
            .log-table { border-collapse: collapse; margin-bottom: 15px; width: 100%; }
            .log-table th, .log-table td { border: 1px solid #3c3c3c; padding: 4px 8px; text-align: left; }
            .log-table th { background-color: #2d2d2d; color: #d4d4d4; }
            .final-table { border-collapse: collapse; margin-top: 10px; }
            .final-table th, .final-table td { border: 1px solid #3c3c3c; padding: 4px 8px; text-align: left; }
            .final-table th { background-color: #2d2d2d; color: #d4d4d4; }
        </style></head><body></body></html>""")

        splitter.addWidget(self.editor)
        splitter.addWidget(self.output)
        splitter.setSizes([800, 600])

        layout.addWidget(splitter)

        self.create_actions()
        self.create_menus()
        self.create_toolbar()

        self.lessons_dock = QDockWidget("📚 Интерактивные уроки", self)
        self.lessons_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.lessons_panel = LessonPanel(self)
        self.lessons_dock.setWidget(self.lessons_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.lessons_dock)

        self.lessons_dock.visibilityChanged.connect(self.on_lessons_visibility_changed)

        self.statusBar().showMessage("Готов")

    def create_actions(self):
        self.new_action = QAction(QIcon.fromTheme("document-new"), "Новый", self)
        self.new_action.setShortcut(QKeySequence.New)
        self.new_action.triggered.connect(self.new_file)

        self.open_action = QAction(QIcon.fromTheme("document-open"), "Открыть...", self)
        self.open_action.setShortcut(QKeySequence.Open)
        self.open_action.triggered.connect(self.open_file)

        self.save_action = QAction(QIcon.fromTheme("document-save"), "Сохранить", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self.save_file)

        self.save_as_action = QAction(QIcon.fromTheme("document-save-as"), "Сохранить как...", self)
        self.save_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_as_action.triggered.connect(self.save_file_as)

        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "Выход", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)

        self.run_action = QAction(QIcon.fromTheme("media-playback-start"), "Запустить", self)
        self.run_action.setShortcut(QKeySequence("F5"))
        self.run_action.triggered.connect(self.run_program)

        self.debug_action = QAction(QIcon.fromTheme("debug-run"), "Отладка", self)
        self.debug_action.setShortcut(QKeySequence("F6"))
        self.debug_action.triggered.connect(self.start_debug)

        self.step_action = QAction(QIcon.fromTheme("debug-step-over"), "Шаг", self)
        self.step_action.setShortcut(QKeySequence("F7"))
        self.step_action.triggered.connect(self.step_debug)

        self.continue_action = QAction(QIcon.fromTheme("media-playback-start"), "Продолжить", self)
        self.continue_action.setShortcut(QKeySequence("F8"))
        self.continue_action.triggered.connect(self.continue_debug)

        self.stop_action = QAction(QIcon.fromTheme("process-stop"), "Стоп", self)
        self.stop_action.setShortcut(QKeySequence("F9"))
        self.stop_action.triggered.connect(self.stop_debug)

        self.show_regs_action = QAction("Показывать регистры", self, checkable=True)
        self.show_regs_action.setChecked(self.log_settings['show_registers'])
        self.show_regs_action.toggled.connect(self.toggle_show_registers)

        self.show_lessons_action = QAction("Показывать уроки", self, checkable=True)
        self.show_lessons_action.setChecked(True)
        self.show_lessons_action.toggled.connect(self.toggle_lessons)

    def create_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction(self.new_action)
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        run_menu = menubar.addMenu("Запуск")
        run_menu.addAction(self.run_action)

        debug_menu = menubar.addMenu("Отладка")
        debug_menu.addAction(self.debug_action)
        debug_menu.addSeparator()
        debug_menu.addAction(self.step_action)
        debug_menu.addAction(self.continue_action)
        debug_menu.addAction(self.stop_action)

        view_menu = menubar.addMenu("Вид")
        view_menu.addAction(self.show_regs_action)
        view_menu.addAction(self.show_lessons_action)

    def create_toolbar(self):
        toolbar = QToolBar("Панель инструментов")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.run_action)
        toolbar.addSeparator()
        toolbar.addAction(self.debug_action)
        toolbar.addAction(self.step_action)
        toolbar.addAction(self.continue_action)
        toolbar.addAction(self.stop_action)

    def toggle_show_registers(self, checked):
        self.log_settings['show_registers'] = checked

    def toggle_lessons(self, checked):
        if checked:
            self.lessons_dock.show()
        else:
            self.lessons_dock.hide()

    def on_lessons_visibility_changed(self, visible):
        self.show_lessons_action.blockSignals(True)
        self.show_lessons_action.setChecked(visible)
        self.show_lessons_action.blockSignals(False)

    def new_file(self):
        if self.maybe_save():
            self.editor.clear()
            self.current_file = None
            self.statusBar().showMessage("Новый файл")
            self.set_status_color("#1565c0")

    def open_file(self):
        if self.maybe_save():
            filename, _ = QFileDialog.getOpenFileName(
                self, "Открыть файл", "", "OnegoASM (*.oasm);;Все файлы (*)"
            )
            if filename:
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        self.editor.setPlainText(f.read())
                    self.current_file = filename
                    self.statusBar().showMessage(f"Открыт: {filename}")
                    self.set_status_color("#1565c0")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")
                    self.set_status_color("#e53935")

    def save_file(self):
        if self.current_file is None:
            return self.save_file_as()
        else:
            return self._save_to_file(self.current_file)

    def save_file_as(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Сохранить файл", "", "OnegoASM (*.oasm);;Все файлы (*)"
        )
        if filename:
            if not filename.endswith('.oasm'):
                filename += '.oasm'
            return self._save_to_file(filename)
        return False

    def _save_to_file(self, filename):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.current_file = filename
            self.statusBar().showMessage(f"Сохранено: {filename}")
            self.set_status_color("#43a047")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")
            self.set_status_color("#e53935")
            return False

    def maybe_save(self):
        if self.editor.document().isModified():
            ret = QMessageBox.question(
                self, "Сохранить изменения?",
                "Документ был изменён. Сохранить изменения?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            if ret == QMessageBox.Save:
                return self.save_file()
            elif ret == QMessageBox.Cancel:
                return False
        return True

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F5:
            self.run_program()
            return
        char = event.text()
        if char:
            self.keyboard.add_char(char)
        super().keyPressEvent(event)

    def set_status_color(self, color):
        self.statusBar().setStyleSheet(f"QStatusBar {{ background-color: {color}; }}")

    def format_asi(self, asi_bits):
        if isinstance(asi_bits, int):
            bits = format(asi_bits, '015b')
        else:
            bits = asi_bits
        if bits[0] == '1':
            return f"RAM-{int(bits[1:], 2)}"
        else:
            return f"SSD-{int(bits[1:], 2)}"

    def get_registers_dict(self, core):
        reg_map = {
            'r0': 'р0', 'r1': 'р1', 'r2': 'р2', 'r3': 'р3',
            'r4': 'р4', 'r5': 'р5', 'r6': 'р6', 'r7': 'р7',
            'r8': 'р8', 'r9': 'р9', 'r10': 'р10', 'r11': 'р11',
            'r12': 'р12', 'r13': 'р13', 'asi': 'аси', 'lz': 'лз'
        }
        regs = {
            'r0': core.r0, 'r1': core.r1, 'r2': core.r2, 'r3': core.r3,
            'r4': core.r4, 'r5': core.r5, 'r6': core.r6, 'r7': core.r7,
            'r8': core.r8, 'r9': core.r9, 'r10': core.r10, 'r11': core.r11,
            'r12': core.r12, 'r13': core.r13, 'asi': core.asi, 'lz': core.lz
        }
        result = {}
        for name, val in regs.items():
            rus_name = reg_map.get(name, name)
            if name == 'asi':
                result[rus_name] = int(val, 2)
            elif name == 'lz':
                result[rus_name] = 1 if val == "111111111111111" else 0
            else:
                num = int(val, 2)
                if val[0] == '1':
                    num -= 32768
                result[rus_name] = num
        return result

    def _compile_program(self):
        asm_text = self.editor.toPlainText()
        if not asm_text.strip():
            QMessageBox.warning(self, "Пустая программа", "Введите программу перед запуском.")
            self.set_status_color("#e53935")
            return None

        try:
            binary = ""
            for line in asm_text.split('\n'):
                stripped = line.strip()
                if not stripped or stripped.startswith('--'):
                    continue
                compiled = onegoasm.compile_line(stripped)
                if compiled is not None:
                    binary += compiled
            if not binary:
                QMessageBox.warning(self, "Пустая программа", "Нет инструкций для компиляции.")
                self.set_status_color("#e53935")
                return None
            if len(binary) % 15 != 0:
                binary = binary.ljust((len(binary) + 14) // 15 * 15, '0')
            return binary
        except Exception as e:
            QMessageBox.critical(self, "Ошибка компиляции", str(e))
            self.set_status_color("#e53935")
            return None

    def _write_ssd_image(self, binary):
        img_path = os.path.join(DATA_DIR, "onegossd.img")
        with open(img_path, 'w') as f:
            f.write(binary)
        return img_path

    def run_program(self):
        self.last_core = None
        self.last_output_text = ""
        self.last_regs = {}
        self.last_ram = None
        self.last_ssd = None

        binary = self._compile_program()
        if binary is None:
            return

        try:
            self._write_ssd_image(binary)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось записать образ SSD:\n{e}")
            self.set_status_color("#e53935")
            return

        self.output.clear()
        self.keyboard.buffer.clear()
        logger = ExecutionLogger(self.log_settings)
        output_redirect = OutputRedirect(self.output, logger)

        original_cwd = os.getcwd()
        try:
            os.chdir(DATA_DIR)
            ram = onegoram.RAM()
            ssd = onegossd.SSD()
            bios = onegobios.BIOS()
            core = onegocore.Core(None)
            cpu = onegocpu.CPU(ram, core, bios, ssd, output=output_redirect, keyboard=self.keyboard)
            core.cpu = cpu
            output_redirect.cpu = cpu
            output_redirect.core = core
            cpu.start()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка выполнения", str(e))
            self.set_status_color("#e53935")
            return
        finally:
            os.chdir(original_cwd)

        self.last_ram = ram
        self.last_ssd = ssd

        bios_output = output_redirect.buffer
        log_html = logger.render()
        regs_html = self.generate_registers_html(core)

        self.last_core = core
        self.last_output_text = bios_output
        self.last_regs = self.get_registers_dict(core)

        self.statusBar().showMessage("Выполнение завершено")
        self.set_status_color("#43a047")

        final_html = f"""
            <html>
            <head>
            <style>
                body {{ font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; color: #d4d4d4; background-color: #252526; }}
                .bios-output {{ white-space: pre-wrap; margin-bottom: 15px; }}
                .log-table {{ border-collapse: collapse; margin-bottom: 15px; width: 100%; }}
                .log-table th, .log-table td {{ border: 1px solid #3c3c3c; padding: 4px 8px; text-align: left; }}
                .log-table th {{ background-color: #2d2d2d; color: #d4d4d4; }}
                .final-table {{ border-collapse: collapse; margin-top: 10px; }}
                .final-table th, .final-table td {{ border: 1px solid #3c3c3c; padding: 4px 8px; text-align: left; }}
                .final-table th {{ background-color: #2d2d2d; color: #d4d4d4; }}
            </style>
            </head>
            <body>
                <div class="bios-output">{bios_output}</div>
                {log_html}
                {regs_html}
            </body>
            </html>
        """
        self.output.setHtml(final_html)

    def start_debug(self):
        self.stop_debug()

        binary = self._compile_program()
        if binary is None:
            return

        try:
            self._write_ssd_image(binary)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось записать образ SSD:\n{e}")
            self.set_status_color("#e53935")
            return

        self.output.clear()
        self.keyboard.buffer.clear()

        self.debug_logger = ExecutionLogger(self.log_settings)
        self.debug_output_redirect = OutputRedirect(self.output, self.debug_logger)

        original_cwd = os.getcwd()
        try:
            os.chdir(DATA_DIR)
            self.debug_ram = onegoram.RAM()
            self.debug_ssd = onegossd.SSD()
            self.debug_bios = onegobios.BIOS()
            self.debug_core = onegocore.Core(None)
            self.debug_cpu = onegocpu.CPU(
                self.debug_ram, self.debug_core, self.debug_bios,
                self.debug_ssd, output=self.debug_output_redirect,
                keyboard=self.keyboard
            )
            self.debug_core.cpu = self.debug_cpu
            self.debug_output_redirect.cpu = self.debug_cpu
            self.debug_output_redirect.core = self.debug_core

            self.debug_cpu.start(mode="step-by-step")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка отладки", str(e))
            self.set_status_color("#e53935")
            self.stop_debug()
            return
        finally:
            os.chdir(original_cwd)

        self.debug_step_count = 0
        self.update_debug_display()
        self.statusBar().showMessage("Отладка: F7 — шаг, F8 — продолжить, F9 — стоп")
        self.set_status_color("#fb8c00")

    def step_debug(self):
        if not self.debug_cpu:
            QMessageBox.information(self, "Отладка", "Сначала нажмите «Отладка» (F6).")
            return

        original_cwd = os.getcwd()
        try:
            os.chdir(DATA_DIR)
            result = self.debug_cpu.step()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка выполнения", str(e))
            self.set_status_color("#e53935")
            self.stop_debug()
            return
        finally:
            os.chdir(original_cwd)

        self.debug_step_count += 1
        self.update_debug_display()

        if result == "END":
            QMessageBox.information(self, "Отладка", "Программа завершена.")
            self.stop_debug()

    def continue_debug(self):
        if not self.debug_cpu:
            QMessageBox.information(self, "Отладка", "Сначала нажмите «Отладка» (F6).")
            return

        original_cwd = os.getcwd()
        try:
            os.chdir(DATA_DIR)
            while True:
                result = self.debug_cpu.step()
                self.debug_step_count += 1
                if result == "END":
                    break
        except Exception as e:
            QMessageBox.critical(self, "Ошибка выполнения", str(e))
            self.set_status_color("#e53935")
            self.stop_debug()
            return
        finally:
            os.chdir(original_cwd)

        self.update_debug_display()
        QMessageBox.information(self, "Отладка", "Программа завершена.")
        self.stop_debug()

    def stop_debug(self):
        self.debug_cpu = None
        self.debug_core = None
        self.debug_ram = None
        self.debug_ssd = None
        self.debug_bios = None
        self.debug_logger = None
        self.debug_output_redirect = None
        self.debug_step_count = 0

    def update_debug_display(self):
        if not self.debug_core:
            return

        core = self.debug_core
        try:
            disasm = onegoasm.disassemble_line(core.cmd)
        except:
            disasm = "?"

        step = self.debug_step_count
        output_text = self.debug_output_redirect.buffer if self.debug_output_redirect else ""
        log_html = self.debug_logger.render() if self.debug_logger else ""
        regs_html = self.generate_registers_html(core)

        html = f"""
        <html><head><style>
            body {{ font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; color: #d4d4d4; background-color: #252526; }}
            .debug-header {{ color: #ffa726; font-size: 15px; font-weight: bold; margin-bottom: 8px; }}
            .info {{ margin: 4px 0; }}
            .cmd {{ color: #ce9178; }}
            .output {{ background-color: #1e1e1e; border: 1px solid #3c3c3c; border-radius: 4px; padding: 6px; white-space: pre-wrap; margin-top: 8px; }}
            .log-table {{ border-collapse: collapse; margin-bottom: 15px; width: 100%; }}
            .log-table th, .log-table td {{ border: 1px solid #3c3c3c; padding: 4px 8px; text-align: left; }}
            .log-table th {{ background-color: #2d2d2d; color: #d4d4d4; }}
            .final-table {{ border-collapse: collapse; margin-top: 10px; }}
            .final-table th, .final-table td {{ border: 1px solid #3c3c3c; padding: 4px 8px; text-align: left; }}
            .final-table th {{ background-color: #2d2d2d; color: #d4d4d4; }}
        </style></head><body>
            <div class="debug-header">🔍 Отладка — шаг {step}</div>
            <div class="info">Выполненная команда: <span class="cmd">{disasm}</span></div>
            <div class="info">аси (следующая инструкция): {self.format_asi(core.asi)}</div>
            <div class="info">Вывод программы:</div>
            <div class="output">{output_text}</div>
            {regs_html}
            {log_html}
        </body></html>
        """
        self.output.setHtml(html)

    def generate_registers_html(self, core):
        html = """
            <table class="final-table">
                <tr><th colspan="2">Регистры после выполнения</th></tr>
        """
        regs = [
            ("р0", core.r0), ("р1", core.r1), ("р2", core.r2), ("р3", core.r3),
            ("р4", core.r4), ("р5", core.r5), ("р6", core.r6), ("р7", core.r7),
            ("р8", core.r8), ("р9", core.r9), ("р10", core.r10), ("р11", core.r11),
            ("р12", core.r12), ("р13", core.r13), ("аси", core.asi), ("лз", core.lz)
        ]
        for name, val in regs:
            if name == 'аси':
                html += f"<tr><td>{name}</td><td>{self.format_asi(val)} ({val})</td></tr>"
            elif name == 'лз':
                if val == "111111111111111":
                    html += f"<tr><td>{name}</td><td>истина ({val})</td></tr>"
                else:
                    html += f"<tr><td>{name}</td><td>ложь ({val})</td></tr>"
            else:
                num = int(val, 2)
                if val[0] == '1':
                    num -= 32768
                html += f"<tr><td>{name}</td><td>{num} ({val})</td></tr>"
        html += "</table>"
        return html

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    QApplication.setDesktopFileName("onego-ide")
    app = QApplication(sys.argv)
    ide = OnegoIDE()
    ide.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
