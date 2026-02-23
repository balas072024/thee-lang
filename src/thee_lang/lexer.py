"""
╔══════════════════════════════════════════════════════════════════════╗
║                    தீ (THEE) LANGUAGE — LEXER                       ║
║          Based on கருவூரார் பலதிரட்டு (Karuvurar Palathirattu)       ║
║                                                                      ║
║  "முதலில் குருவினை மனதால் துதித்து பின்பு                             ║
║   மூலமந்திரத்தை மனதில் உச்சரிக்க வேண்டும்"                           ║
║  — கருவூரார் பலதிரட்டு                                               ║
╚══════════════════════════════════════════════════════════════════════╝

PHILOSOPHICAL FOUNDATION — ஐந்து முகங்கள் (Five Faces of Shiva)
From கருவூரார் பலதிரட்டு 300:

  தத்புருஷம் (East/Gold)     → படைத்தல் → Data & Foundation
  அகோரம் (South/Black)       → அழித்தல் → Functions & Transformation
  வாமதேவம் (North/Red)       → மறைத்தல் → Flow & Navigation
  சத்யோசாதம் (West/White)    → காத்தல் → Agents & Protection
  ஈசானம் (Zenith/Crystal)    → அருளல் → Intelligence & Grace

நமசிவாய: ந=1 ம=2 சி=3 வா=4 ய=5 → 15 → 6 (ஆறுமுகம்)
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List


class TokenType(Enum):
    INTEGER = auto(); FLOAT = auto(); STRING = auto(); IDENTIFIER = auto()
    # தத்புருஷம் — Creation/Foundation
    LET = auto(); CONST = auto(); ASH = auto(); TRUE = auto(); FALSE = auto()
    # அகோரம் — Transformation/Functions
    FORGE = auto(); EMBER = auto(); KINDLE = auto()
    # வாமதேவம் — Flow/Navigation
    IF = auto(); ELIF = auto(); ELSE = auto(); REPEAT = auto(); WHILE = auto()
    FOR = auto(); TIMES = auto(); IN = auto(); BREAK = auto(); CONTINUE = auto()
    # சத்யோசாதம் — Protection/Agents
    LIGHT = auto(); AGENT = auto(); SKILL = auto(); GUARD = auto()
    SUMMON = auto(); SWARM = auto(); EMIT = auto(); SENSE = auto(); REACT = auto()
    # ஈசானம் — Intelligence/Grace
    GOAL = auto(); PURSUE = auto(); MEMORY = auto()
    # Operators
    PLUS = auto(); MINUS = auto(); MULTIPLY = auto(); DIVIDE = auto()
    MODULO = auto(); POWER = auto(); ASSIGN = auto(); EQUALS = auto()
    NOT_EQUALS = auto(); LESS_THAN = auto(); GREATER_THAN = auto()
    LESS_EQUAL = auto(); GREATER_EQUAL = auto()
    AND = auto(); OR = auto(); NOT = auto(); PIPE = auto()
    # Delimiters
    LPAREN = auto(); RPAREN = auto(); LBRACE = auto(); RBRACE = auto()
    LBRACKET = auto(); RBRACKET = auto(); COMMA = auto(); DOT = auto()
    COLON = auto(); ARROW = auto()
    # Week 1: Error Handling
    TRY = auto(); CATCH = auto(); THROW = auto(); FINALLY = auto()
    # Week 1: Lambda
    FAT_ARROW = auto()
    # Week 3: Async/Concurrency
    ASYNC = auto(); AWAIT = auto(); SPAWN = auto(); CHANNEL = auto()
    # Week 5: Struct & Match
    STRUCT = auto(); MATCH = auto(); CASE = auto(); DEFAULT = auto()
    # Week 2: Import
    IMPORT = auto(); FROM = auto(); AS = auto(); EXPORT = auto()
    # Type hints (optional annotations)
    TYPE_ARROW = auto()
    # v6.0 — திருமுறை: Class System, Decorators, Generators, Enums
    CLASS = auto(); NEW = auto(); EXTENDS = auto(); SUPER = auto()
    DECORATOR = auto()  # @
    YIELD = auto()      # Generator yield
    ENUM = auto()       # Enum declaration
    SPREAD = auto()     # ... spread operator
    # Special
    NEWLINE = auto(); EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    column: int


KEYWORDS = {
    # தத்புருஷம் — Creation
    "na": TokenType.LET, "நா": TokenType.LET, "let": TokenType.LET,
    "nirai": TokenType.CONST, "நிரை": TokenType.CONST, "const": TokenType.CONST,
    "sambal": TokenType.ASH, "சாம்பல்": TokenType.ASH, "ash": TokenType.ASH,
    "unmai": TokenType.TRUE, "உண்மை": TokenType.TRUE, "true": TokenType.TRUE,
    "poi": TokenType.FALSE, "பொய்": TokenType.FALSE, "false": TokenType.FALSE,
    # அகோரம் — Transformation
    "thee": TokenType.FORGE, "தீ": TokenType.FORGE, "forge": TokenType.FORGE,
    "kanal": TokenType.EMBER, "கனல்": TokenType.EMBER, "ember": TokenType.EMBER,
    "potri": TokenType.KINDLE, "போற்றி": TokenType.KINDLE, "kindle": TokenType.KINDLE,
    # வாமதேவம் — Flow
    "endral": TokenType.IF, "என்றால்": TokenType.IF, "if": TokenType.IF,
    "allathu": TokenType.ELIF, "அல்லது": TokenType.ELIF, "elif": TokenType.ELIF, "illaiendral": TokenType.ELIF,
    "illai": TokenType.ELSE, "இல்லை": TokenType.ELSE, "else": TokenType.ELSE,
    "ozhugu": TokenType.REPEAT, "ஓழுகு": TokenType.REPEAT, "repeat": TokenType.REPEAT,
    "varai": TokenType.WHILE, "வரை": TokenType.WHILE, "while": TokenType.WHILE,
    "ovvondru": TokenType.FOR, "ஒவ்வொன்று": TokenType.FOR, "for": TokenType.FOR,
    "murai": TokenType.TIMES, "முறை": TokenType.TIMES, "times": TokenType.TIMES,
    "ul": TokenType.IN, "உள்": TokenType.IN, "in": TokenType.IN,
    "niruthu": TokenType.BREAK, "நிறுத்து": TokenType.BREAK, "break": TokenType.BREAK, "nillu": TokenType.BREAK,
    "thodaru": TokenType.CONTINUE, "தொடரு": TokenType.CONTINUE, "continue": TokenType.CONTINUE, "thodu": TokenType.CONTINUE,
    # சத்யோசாதம் — Protection/Agents
    "moochhu": TokenType.LIGHT, "மூச்சு": TokenType.LIGHT, "light": TokenType.LIGHT,
    "uyir": TokenType.AGENT, "உயிர்": TokenType.AGENT, "agent": TokenType.AGENT,
    "thiran": TokenType.SKILL, "திறன்": TokenType.SKILL, "skill": TokenType.SKILL,
    "kaval": TokenType.GUARD, "காவல்": TokenType.GUARD, "guard": TokenType.GUARD,
    "ezhuppu": TokenType.SUMMON, "எழுப்பு": TokenType.SUMMON, "summon": TokenType.SUMMON,
    "koottam": TokenType.SWARM, "கூட்டம்": TokenType.SWARM, "swarm": TokenType.SWARM,
    "kaatru": TokenType.EMIT, "காற்று": TokenType.EMIT, "emit": TokenType.EMIT,
    "unarvu": TokenType.SENSE, "உணர்வு": TokenType.SENSE, "sense": TokenType.SENSE,
    "ethir": TokenType.REACT, "எதிர்": TokenType.REACT, "react": TokenType.REACT,
    # ஈசானம் — Intelligence
    "ilakku": TokenType.GOAL, "இலக்கு": TokenType.GOAL, "goal": TokenType.GOAL,
    "thodar": TokenType.PURSUE, "தொடர்": TokenType.PURSUE, "pursue": TokenType.PURSUE,
    "ninaiv": TokenType.MEMORY, "நினைவு": TokenType.MEMORY, "memory": TokenType.MEMORY,
    # Week 1: முயற்சி — Error Handling (Fire sparks)
    "muyarchi": TokenType.TRY, "முயற்சி": TokenType.TRY, "try": TokenType.TRY,
    "pizhai": TokenType.CATCH, "பிழை_பிடி": TokenType.CATCH, "catch": TokenType.CATCH,
    "eri": TokenType.THROW, "எறி": TokenType.THROW, "throw": TokenType.THROW,
    "iruthi": TokenType.FINALLY, "இறுதி": TokenType.FINALLY, "finally": TokenType.FINALLY,
    # Week 3: ஒத்திசை — Async (Multiple breaths)
    "othisai": TokenType.ASYNC, "ஒத்திசை": TokenType.ASYNC, "async": TokenType.ASYNC,
    "kaathiru": TokenType.AWAIT, "காத்திரு": TokenType.AWAIT, "await": TokenType.AWAIT,
    "uruvakku": TokenType.SPAWN, "உருவாக்கு": TokenType.SPAWN, "spawn": TokenType.SPAWN,
    "kalani": TokenType.CHANNEL, "கலணி": TokenType.CHANNEL, "channel": TokenType.CHANNEL,
    # Week 5: வடிவம் — Struct & Match
    "vadivam": TokenType.STRUCT, "வடிவம்": TokenType.STRUCT, "struct": TokenType.STRUCT,
    "poruthu": TokenType.MATCH, "பொருத்து": TokenType.MATCH, "match": TokenType.MATCH,
    "vazhakku": TokenType.CASE, "வழக்கு": TokenType.CASE, "case": TokenType.CASE,
    "iyalbu": TokenType.DEFAULT, "இயல்பு": TokenType.DEFAULT, "default": TokenType.DEFAULT,
    # Week 2: கொணர் — Import
    "konar": TokenType.IMPORT, "கொணர்": TokenType.IMPORT, "import": TokenType.IMPORT,
    "irunthu": TokenType.FROM, "இருந்து": TokenType.FROM, "from": TokenType.FROM,
    "as": TokenType.AS,
    "veliidu": TokenType.EXPORT, "வெளியீடு": TokenType.EXPORT, "export": TokenType.EXPORT,
    # Logical
    "and": TokenType.AND, "மற்றும்": TokenType.AND,
    "or": TokenType.OR, "அல்": TokenType.OR,
    "not": TokenType.NOT, "அன்று": TokenType.NOT,
    # v6.0 — திருமுறை: OOP, Generators, Enums
    "vagu": TokenType.CLASS, "வகு": TokenType.CLASS, "class": TokenType.CLASS,
    "pudhu": TokenType.NEW, "புது": TokenType.NEW, "new": TokenType.NEW,
    "mirasu": TokenType.EXTENDS, "மிரசு": TokenType.EXTENDS, "extends": TokenType.EXTENDS,
    "moolam": TokenType.SUPER, "மூலம்": TokenType.SUPER, "super": TokenType.SUPER,
    "vilai": TokenType.YIELD, "விளை": TokenType.YIELD, "yield": TokenType.YIELD,
    "pirivu": TokenType.ENUM, "பிரிவு": TokenType.ENUM, "enum": TokenType.ENUM,
}


class TheeLexerError(Exception):
    def __init__(self, message, line, column):
        super().__init__(f"🔥 L{line}:C{column}: {message}")


class TheeLexer:
    def __init__(self, source):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def peek(self):
        return self.source[self.pos] if self.pos < len(self.source) else '\0'

    def peek_next(self):
        return self.source[self.pos + 1] if self.pos + 1 < len(self.source) else '\0'

    def advance(self):
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def add_token(self, tt, value=None):
        self.tokens.append(Token(tt, value, self.line, self.column))

    def tokenize(self):
        while self.pos < len(self.source):
            self._scan()
        self.add_token(TokenType.EOF)
        return self.tokens

    def _scan(self):
        ch = self.peek()
        if ch in ' \t\r':
            self.advance(); return
        if ch == '\n':
            self.advance()
            if not self.tokens or self.tokens[-1].type != TokenType.NEWLINE:
                self.add_token(TokenType.NEWLINE, '\\n')
            return
        if ch == '/' and self.peek_next() == '/':
            while self.pos < len(self.source) and self.peek() != '\n': self.advance()
            return
        if ch == '#':
            while self.pos < len(self.source) and self.peek() != '\n': self.advance()
            return
        if ch == '/' and self.peek_next() == '*':
            self.advance(); self.advance()
            while self.pos < len(self.source):
                if self.peek() == '*' and self.peek_next() == '/':
                    self.advance(); self.advance(); return
                self.advance()
            return
        if ch.isdigit():
            self._number(); return
        if ch in '"\'`':
            self._string(); return
        if ch.isalpha() or ch == '_' or ord(ch) > 127:
            self._identifier(); return
        self._operator()

    def _number(self):
        start = self.pos
        is_float = False
        while self.pos < len(self.source) and (self.peek().isdigit() or self.peek() == '.'):
            if self.peek() == '.':
                if is_float: break
                is_float = True
            self.advance()
        text = self.source[start:self.pos]
        self.add_token(TokenType.FLOAT if is_float else TokenType.INTEGER,
                       float(text) if is_float else int(text))

    def _string(self):
        quote = self.advance()
        result = []
        while self.pos < len(self.source) and self.peek() != quote:
            ch = self.advance()
            if ch == '\\' and self.pos < len(self.source):
                esc = self.advance()
                result.append({'n': '\n', 't': '\t', '\\': '\\', quote: quote}.get(esc, '\\' + esc))
            elif ch == '{' and quote == '`' and self.pos < len(self.source):
                # Template literal interpolation: `hello {name}`
                expr = []
                depth = 1
                while self.pos < len(self.source) and depth > 0:
                    c2 = self.advance()
                    if c2 == '{': depth += 1
                    elif c2 == '}': depth -= 1
                    if depth > 0: expr.append(c2)
                result.append('${' + ''.join(expr) + '}')
            else:
                result.append(ch)
        if self.pos >= len(self.source):
            raise TheeLexerError("Unterminated string", self.line, self.column)
        self.advance()
        self.add_token(TokenType.STRING, ''.join(result))

    def _identifier(self):
        start = self.pos
        while self.pos < len(self.source):
            ch = self.peek()
            if ch.isalnum() or ch == '_' or ord(ch) > 127:
                self.advance()
            else:
                break
        text = self.source[start:self.pos]
        self.add_token(KEYWORDS.get(text, TokenType.IDENTIFIER), text)

    def _operator(self):
        ch = self.advance()
        if ch == '+': self.add_token(TokenType.PLUS, '+')
        elif ch == '-':
            if self.peek() == '>': self.advance(); self.add_token(TokenType.ARROW, '->')
            else: self.add_token(TokenType.MINUS, '-')
        elif ch == '*':
            if self.peek() == '*': self.advance(); self.add_token(TokenType.POWER, '**')
            else: self.add_token(TokenType.MULTIPLY, '*')
        elif ch == '/': self.add_token(TokenType.DIVIDE, '/')
        elif ch == '%': self.add_token(TokenType.MODULO, '%')
        elif ch == '=':
            if self.peek() == '=': self.advance(); self.add_token(TokenType.EQUALS, '==')
            elif self.peek() == '>': self.advance(); self.add_token(TokenType.FAT_ARROW, '=>')
            else: self.add_token(TokenType.ASSIGN, '=')
        elif ch == '!':
            if self.peek() == '=': self.advance(); self.add_token(TokenType.NOT_EQUALS, '!=')
            else: self.add_token(TokenType.NOT, '!')
        elif ch == '<':
            if self.peek() == '=': self.advance(); self.add_token(TokenType.LESS_EQUAL, '<=')
            else: self.add_token(TokenType.LESS_THAN, '<')
        elif ch == '>':
            if self.peek() == '=': self.advance(); self.add_token(TokenType.GREATER_EQUAL, '>=')
            else: self.add_token(TokenType.GREATER_THAN, '>')
        elif ch == '|':
            if self.peek() == '>': self.advance(); self.add_token(TokenType.PIPE, '|>')
            else: self.add_token(TokenType.PIPE, '|')
        elif ch == '(': self.add_token(TokenType.LPAREN, '(')
        elif ch == ')': self.add_token(TokenType.RPAREN, ')')
        elif ch == '{': self.add_token(TokenType.LBRACE, '{')
        elif ch == '}': self.add_token(TokenType.RBRACE, '}')
        elif ch == '[': self.add_token(TokenType.LBRACKET, '[')
        elif ch == ']': self.add_token(TokenType.RBRACKET, ']')
        elif ch == ',': self.add_token(TokenType.COMMA, ',')
        elif ch == '.':
            if self.pos < len(self.source) and self.peek() == '.' and self.pos + 1 < len(self.source) and self.source[self.pos + 1] == '.':
                self.advance(); self.advance()
                self.add_token(TokenType.SPREAD, '...')
            else:
                self.add_token(TokenType.DOT, '.')
        elif ch == ':': self.add_token(TokenType.COLON, ':')
        elif ch == '@': self.add_token(TokenType.DECORATOR, '@')
        else: raise TheeLexerError(f"Unexpected character: {ch!r}", self.line, self.column)
