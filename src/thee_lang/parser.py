"""
தீ (THEE) — Parser v3.0
Week 1: Try/Catch, Lambda | Week 2: Import/Module | Week 3: Async/Await/Spawn
Week 5: Struct, Match | All dual Tamil/English keywords
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from thee_lang.lexer import Token, TokenType, TheeLexer

# ═══ AST Nodes ═══
@dataclass
class ASTNode:
    line: int = 0; column: int = 0
@dataclass
class NumberLiteral(ASTNode):
    value: float = 0
@dataclass
class StringLiteral(ASTNode):
    value: str = ""
@dataclass
class BooleanLiteral(ASTNode):
    value: bool = False
@dataclass
class AshLiteral(ASTNode):
    pass
@dataclass
class ListLiteral(ASTNode):
    elements: List[ASTNode] = field(default_factory=list)
@dataclass
class DictLiteral(ASTNode):
    pairs: List[tuple] = field(default_factory=list)
@dataclass
class Identifier(ASTNode):
    name: str = ""
@dataclass
class BinaryOp(ASTNode):
    left: ASTNode = None; op: str = ""; right: ASTNode = None
@dataclass
class UnaryOp(ASTNode):
    op: str = ""; operand: ASTNode = None
@dataclass
class FunctionCall(ASTNode):
    callee: ASTNode = None; arguments: List[ASTNode] = field(default_factory=list)
@dataclass
class MemberAccess(ASTNode):
    object: ASTNode = None; member: str = ""
@dataclass
class IndexAccess(ASTNode):
    object: ASTNode = None; index: ASTNode = None
@dataclass
class PipeExpression(ASTNode):
    left: ASTNode = None; right: ASTNode = None
@dataclass
class Assignment(ASTNode):
    target: ASTNode = None; value: ASTNode = None
@dataclass
class LambdaExpression(ASTNode):
    params: List[str] = field(default_factory=list); body: ASTNode = None
@dataclass
class AwaitExpression(ASTNode):
    expression: ASTNode = None
@dataclass
class LetDeclaration(ASTNode):
    name: str = ""; value: ASTNode = None; is_const: bool = False; type_hint: str = None
@dataclass
class LightStatement(ASTNode):
    expression: ASTNode = None
@dataclass
class EmberStatement(ASTNode):
    value: ASTNode = None
@dataclass
class IfStatement(ASTNode):
    condition: ASTNode = None; body: List[ASTNode] = field(default_factory=list)
    elif_clauses: List[tuple] = field(default_factory=list)
    else_body: List[ASTNode] = field(default_factory=list)
@dataclass
class RepeatTimesLoop(ASTNode):
    count: ASTNode = None; body: List[ASTNode] = field(default_factory=list)
@dataclass
class RepeatForLoop(ASTNode):
    variable: str = ""; iterable: ASTNode = None; body: List[ASTNode] = field(default_factory=list)
@dataclass
class WhileLoop(ASTNode):
    condition: ASTNode = None; body: List[ASTNode] = field(default_factory=list)
@dataclass
class BreakStatement(ASTNode):
    pass
@dataclass
class ContinueStatement(ASTNode):
    pass
@dataclass
class ForgeDeclaration(ASTNode):
    name: str = ""; params: List[str] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)
    is_async: bool = False; return_type: str = None
@dataclass
class TryCatchStatement(ASTNode):
    try_body: List[ASTNode] = field(default_factory=list)
    catch_var: str = None; catch_body: List[ASTNode] = field(default_factory=list)
    finally_body: List[ASTNode] = field(default_factory=list)
@dataclass
class ThrowStatement(ASTNode):
    expression: ASTNode = None
@dataclass
class ImportStatement(ASTNode):
    path: str = ""; alias: str = None; names: List[str] = field(default_factory=list)
@dataclass
class ExportStatement(ASTNode):
    declaration: ASTNode = None
@dataclass
class SpawnStatement(ASTNode):
    expression: ASTNode = None
@dataclass
class ChannelCreate(ASTNode):
    name: str = ""
@dataclass
class StructDeclaration(ASTNode):
    name: str = ""; fields: List[Tuple[str, str]] = field(default_factory=list)
    methods: List[ASTNode] = field(default_factory=list)
@dataclass
class MatchStatement(ASTNode):
    expression: ASTNode = None
    cases: List[Tuple[ASTNode, List[ASTNode]]] = field(default_factory=list)
    default_body: List[ASTNode] = field(default_factory=list)
@dataclass
class AgentDeclaration(ASTNode):
    name: str = ""; goal: ASTNode = None; memory_type: str = "ephemeral"
    skills: List = field(default_factory=list); guards: List = field(default_factory=list)
    senses: List = field(default_factory=list); reactions: List = field(default_factory=list)
    properties: Dict[str, ASTNode] = field(default_factory=dict)
@dataclass
class SkillDeclaration(ASTNode):
    name: str = ""; params: List[str] = field(default_factory=list)
    body: List[ASTNode] = field(default_factory=list)
@dataclass
class GuardDeclaration(ASTNode):
    rules: Dict[str, ASTNode] = field(default_factory=dict)
@dataclass
class SenseDeclaration(ASTNode):
    name: str = ""; body: List[ASTNode] = field(default_factory=list)
@dataclass
class ReactDeclaration(ASTNode):
    event: str = ""; body: List[ASTNode] = field(default_factory=list)
@dataclass
class SummonStatement(ASTNode):
    agent_name: str = ""; alias: str = ""; config: Dict[str, ASTNode] = field(default_factory=dict)
@dataclass
class PursueStatement(ASTNode):
    agent: ASTNode = None; goal: ASTNode = None
@dataclass
class EmitStatement(ASTNode):
    event: str = ""; data: ASTNode = None
@dataclass
class SwarmDeclaration(ASTNode):
    name: str = ""; agents: List[ASTNode] = field(default_factory=list)
    strategy: str = "parallel"; goal: ASTNode = None
@dataclass
class KindleStatement(ASTNode):
    module: str = ""
@dataclass
class Program(ASTNode):
    statements: List[ASTNode] = field(default_factory=list)

# ═══ v6.0 — திருமுறை AST Nodes ═══
@dataclass
class ClassDeclaration(ASTNode):
    name: str = ""; parent: str = None
    constructor: ASTNode = None
    methods: List[ASTNode] = field(default_factory=list)
    properties: Dict[str, ASTNode] = field(default_factory=dict)
@dataclass
class NewExpression(ASTNode):
    class_name: str = ""; arguments: List[ASTNode] = field(default_factory=list)
@dataclass
class SuperCall(ASTNode):
    method: str = None; arguments: List[ASTNode] = field(default_factory=list)
@dataclass
class DecoratedDeclaration(ASTNode):
    decorator: ASTNode = None; declaration: ASTNode = None
    decorator_args: List[ASTNode] = field(default_factory=list)
@dataclass
class YieldExpression(ASTNode):
    value: ASTNode = None
@dataclass
class EnumDeclaration(ASTNode):
    name: str = ""; members: Dict[str, ASTNode] = field(default_factory=dict)
@dataclass
class SpreadExpression(ASTNode):
    expression: ASTNode = None
@dataclass
class DestructureAssignment(ASTNode):
    targets: List[str] = field(default_factory=list); value: ASTNode = None
    is_dict: bool = False

# ═══ Parser ═══
class TheeParserError(Exception):
    def __init__(self, message, token):
        self.token = token
        super().__init__(f"\u0001f525 L{token.line}:C{token.column}: {message}")

class TheeParser:
    def __init__(self, tokens):
        self.tokens = tokens; self.pos = 0
    def peek(self): return self.tokens[self.pos]
    def peek_type(self): return self.tokens[self.pos].type
    def peek_ahead(self, n=1):
        p = self.pos + n
        return self.tokens[p].type if p < len(self.tokens) else TokenType.EOF
    def advance(self):
        t = self.tokens[self.pos]; self.pos += 1; return t
    def expect(self, tt):
        t = self.peek()
        if t.type != tt: raise TheeParserError(f"Expected {tt.name}, got {t.type.name} ({t.value!r})", t)
        return self.advance()
    def skip_newlines(self):
        while self.pos < len(self.tokens) and self.peek_type() == TokenType.NEWLINE: self.advance()
    def at_end(self): return self.peek_type() == TokenType.EOF
    def match(self, *types): return self.peek_type() in types

    def parse(self):
        prog = Program(); self.skip_newlines()
        while not self.at_end():
            s = self.parse_statement()
            if s: prog.statements.append(s)
            self.skip_newlines()
        return prog

    def parse_statement(self):
        self.skip_newlines()
        if self.at_end(): return None
        tt = self.peek_type()
        if tt in (TokenType.LET, TokenType.CONST): return self.parse_let()
        if tt == TokenType.LIGHT: return self.parse_light()
        if tt == TokenType.FORGE: return self.parse_forge()
        if tt == TokenType.EMBER: return self.parse_ember()
        if tt == TokenType.IF: return self.parse_if()
        if tt == TokenType.REPEAT: return self.parse_repeat()
        if tt == TokenType.WHILE: return self.parse_while()
        if tt == TokenType.BREAK: self.advance(); return BreakStatement()
        if tt == TokenType.CONTINUE: self.advance(); return ContinueStatement()
        if tt == TokenType.TRY: return self.parse_try_catch()
        if tt == TokenType.THROW: return self.parse_throw()
        if tt == TokenType.IMPORT: return self.parse_import()
        if tt == TokenType.EXPORT: return self.parse_export()
        if tt == TokenType.ASYNC: return self.parse_async()
        if tt == TokenType.SPAWN: return self.parse_spawn()
        if tt == TokenType.CHANNEL: return self.parse_channel_create()
        if tt == TokenType.STRUCT: return self.parse_struct()
        if tt == TokenType.MATCH: return self.parse_match()
        if tt == TokenType.AGENT: return self.parse_agent()
        if tt == TokenType.SUMMON: return self.parse_summon()
        if tt == TokenType.SWARM: return self.parse_swarm()
        if tt == TokenType.EMIT: return self.parse_emit()
        if tt == TokenType.KINDLE: return self.parse_kindle()
        # v6.0 — திருமுறை features
        if tt == TokenType.CLASS: return self.parse_class()
        if tt == TokenType.ENUM: return self.parse_enum()
        if tt == TokenType.YIELD: return self.parse_yield_stmt()
        if tt == TokenType.DECORATOR: return self.parse_decorator()
        return self.parse_expression_stmt()

    def parse_let(self):
        t = self.advance(); is_const = t.type == TokenType.CONST
        # v6.0 — Destructuring: na [a, b, c] = [1, 2, 3]
        if self.match(TokenType.LBRACKET):
            self.advance(); targets = []
            targets.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA): self.advance(); targets.append(self.expect(TokenType.IDENTIFIER).value)
            self.expect(TokenType.RBRACKET); self.expect(TokenType.ASSIGN)
            val = self.parse_expression()
            return DestructureAssignment(targets=targets, value=val, is_dict=False, line=t.line, column=t.column)
        # v6.0 — Dict destructuring: na {x, y} = obj
        if self.match(TokenType.LBRACE):
            self.advance(); targets = []
            targets.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA): self.advance(); targets.append(self.expect(TokenType.IDENTIFIER).value)
            self.expect(TokenType.RBRACE); self.expect(TokenType.ASSIGN)
            val = self.parse_expression()
            return DestructureAssignment(targets=targets, value=val, is_dict=True, line=t.line, column=t.column)
        name = self.expect(TokenType.IDENTIFIER).value
        type_hint = None
        if self.match(TokenType.COLON): self.advance(); type_hint = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN); val = self.parse_expression()
        return LetDeclaration(name=name, value=val, is_const=is_const, type_hint=type_hint, line=t.line, column=t.column)

    def parse_light(self):
        t = self.advance(); return LightStatement(expression=self.parse_expression(), line=t.line, column=t.column)

    def parse_ember(self):
        t = self.advance(); val = None
        if not self.match(TokenType.NEWLINE, TokenType.RBRACE, TokenType.EOF): val = self.parse_expression()
        return EmberStatement(value=val, line=t.line, column=t.column)

    def parse_forge(self, is_async=False):
        t = self.advance(); name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LPAREN); params = self._params(); self.expect(TokenType.RPAREN)
        rt = None
        if self.match(TokenType.ARROW): self.advance(); rt = self.expect(TokenType.IDENTIFIER).value
        body = self._block()
        return ForgeDeclaration(name=name, params=params, body=body, is_async=is_async, return_type=rt, line=t.line, column=t.column)

    def _params(self):
        params = []
        if not self.match(TokenType.RPAREN):
            params.append(self.expect(TokenType.IDENTIFIER).value)
            if self.match(TokenType.COLON): self.advance(); self.expect(TokenType.IDENTIFIER)
            while self.match(TokenType.COMMA):
                self.advance(); params.append(self.expect(TokenType.IDENTIFIER).value)
                if self.match(TokenType.COLON): self.advance(); self.expect(TokenType.IDENTIFIER)
        return params

    def _block(self):
        self.skip_newlines(); self.expect(TokenType.LBRACE); self.skip_newlines()
        stmts = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            s = self.parse_statement()
            if s: stmts.append(s)
            self.skip_newlines()
        self.expect(TokenType.RBRACE); return stmts

    def parse_if(self):
        t = self.advance(); cond = self.parse_expression(); body = self._block()
        elifs, else_body = [], []; self.skip_newlines()
        while self.match(TokenType.ELIF):
            self.advance(); ec = self.parse_expression(); eb = self._block(); elifs.append((ec, eb)); self.skip_newlines()
        if self.match(TokenType.ELSE): self.advance(); else_body = self._block()
        return IfStatement(condition=cond, body=body, elif_clauses=elifs, else_body=else_body, line=t.line, column=t.column)

    def parse_repeat(self):
        t = self.advance()
        if self.match(TokenType.FOR):
            self.advance(); var = self.expect(TokenType.IDENTIFIER).value; self.expect(TokenType.IN)
            return RepeatForLoop(variable=var, iterable=self.parse_expression(), body=self._block(), line=t.line, column=t.column)
        if self.match(TokenType.IDENTIFIER) and self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TokenType.IN:
            var = self.advance().value; self.expect(TokenType.IN)
            return RepeatForLoop(variable=var, iterable=self.parse_expression(), body=self._block(), line=t.line, column=t.column)
        expr = self.parse_expression()
        if self.match(TokenType.TIMES):
            self.advance(); return RepeatTimesLoop(count=expr, body=self._block(), line=t.line, column=t.column)
        return WhileLoop(condition=expr, body=self._block(), line=t.line, column=t.column)

    def parse_while(self):
        t = self.advance(); return WhileLoop(condition=self.parse_expression(), body=self._block(), line=t.line, column=t.column)

    def parse_try_catch(self):
        t = self.advance(); try_body = self._block(); catch_var = None; catch_body = []; finally_body = []
        self.skip_newlines()
        if self.match(TokenType.CATCH):
            self.advance()
            if self.match(TokenType.LPAREN):
                self.advance(); catch_var = self.expect(TokenType.IDENTIFIER).value; self.expect(TokenType.RPAREN)
            elif self.match(TokenType.IDENTIFIER) and not self.match(TokenType.LBRACE):
                # Bare catch variable: pizhai e { ... }
                catch_var = self.advance().value
            catch_body = self._block()
        self.skip_newlines()
        if self.match(TokenType.FINALLY): self.advance(); finally_body = self._block()
        return TryCatchStatement(try_body=try_body, catch_var=catch_var, catch_body=catch_body, finally_body=finally_body, line=t.line, column=t.column)

    def parse_throw(self):
        t = self.advance(); return ThrowStatement(expression=self.parse_expression(), line=t.line, column=t.column)

    def parse_import(self):
        t = self.advance()
        if self.match(TokenType.STRING):
            path = self.advance().value; alias = None
            if self.match(TokenType.AS): self.advance(); alias = self.expect(TokenType.IDENTIFIER).value
            return ImportStatement(path=path, alias=alias, line=t.line, column=t.column)
        mod = self.expect(TokenType.IDENTIFIER).value; alias = None
        while self.match(TokenType.DOT):  # dotted modules: konar python.numpy
            self.advance(); mod += "." + self.expect(TokenType.IDENTIFIER).value
        if self.match(TokenType.AS): self.advance(); alias = self.expect(TokenType.IDENTIFIER).value
        return ImportStatement(path=mod, alias=alias, line=t.line, column=t.column)

    def parse_export(self):
        t = self.advance(); return ExportStatement(declaration=self.parse_statement(), line=t.line, column=t.column)

    def parse_async(self):
        self.advance()
        if self.match(TokenType.FORGE): return self.parse_forge(is_async=True)
        raise TheeParserError("Expected thee/forge after async", self.peek())

    def parse_spawn(self):
        t = self.advance(); return SpawnStatement(expression=self.parse_expression(), line=t.line, column=t.column)

    def parse_channel_create(self):
        t = self.advance(); return ChannelCreate(name=self.expect(TokenType.IDENTIFIER).value, line=t.line, column=t.column)

    def parse_struct(self):
        t = self.advance(); name = self.expect(TokenType.IDENTIFIER).value
        self.skip_newlines(); self.expect(TokenType.LBRACE); self.skip_newlines()
        fields = []; methods = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            self.skip_newlines()
            if self.match(TokenType.RBRACE): break
            if self.match(TokenType.FORGE): methods.append(self.parse_forge())
            else:
                fn = self.expect(TokenType.IDENTIFIER).value; ft = "any"
                if self.match(TokenType.COLON): self.advance(); ft = self.expect(TokenType.IDENTIFIER).value
                fields.append((fn, ft))
                if self.match(TokenType.ASSIGN): self.advance(); self.parse_expression()
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return StructDeclaration(name=name, fields=fields, methods=methods, line=t.line, column=t.column)

    def parse_match(self):
        t = self.advance(); expr = self.parse_expression()
        self.skip_newlines(); self.expect(TokenType.LBRACE); self.skip_newlines()
        cases = []; default_body = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            self.skip_newlines()
            if self.match(TokenType.RBRACE): break
            if self.match(TokenType.DEFAULT):
                self.advance()
                if self.match(TokenType.FAT_ARROW): self.advance()
                default_body = self._block()
            else:
                if self.match(TokenType.CASE): self.advance()
                pattern = self.parse_expression()
                if self.match(TokenType.FAT_ARROW): self.advance()
                body = self._block()
                cases.append((pattern, body))
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return MatchStatement(expression=expr, cases=cases, default_body=default_body, line=t.line, column=t.column)

    def parse_agent(self):
        t = self.advance(); name = self.expect(TokenType.IDENTIFIER).value
        self.skip_newlines(); self.expect(TokenType.LBRACE); self.skip_newlines()
        ag = AgentDeclaration(name=name, line=t.line, column=t.column)
        while not self.match(TokenType.RBRACE) and not self.at_end():
            self.skip_newlines()
            if self.match(TokenType.RBRACE): break
            tt = self.peek_type()
            if tt == TokenType.GOAL: self.advance(); self.expect(TokenType.COLON); ag.goal = self.parse_expression()
            elif tt == TokenType.MEMORY: self.advance(); self.expect(TokenType.COLON); ag.memory_type = self.expect(TokenType.IDENTIFIER).value
            elif tt == TokenType.SKILL:
                tk = self.advance(); n = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.LPAREN); p = self._params(); self.expect(TokenType.RPAREN); b = self._block()
                ag.skills.append(SkillDeclaration(name=n, params=p, body=b, line=tk.line, column=tk.column))
            elif tt == TokenType.GUARD:
                tk = self.advance(); self.skip_newlines(); self.expect(TokenType.LBRACE); self.skip_newlines()
                rules = {}
                while not self.match(TokenType.RBRACE) and not self.at_end():
                    k = self.expect(TokenType.IDENTIFIER).value; self.expect(TokenType.COLON); v = self.parse_expression(); rules[k] = v; self.skip_newlines()
                self.expect(TokenType.RBRACE)
                ag.guards.append(GuardDeclaration(rules=rules, line=tk.line, column=tk.column))
            elif tt == TokenType.SENSE:
                tk = self.advance(); n = self.expect(TokenType.IDENTIFIER).value; b = self._block()
                ag.senses.append(SenseDeclaration(name=n, body=b, line=tk.line, column=tk.column))
            elif tt == TokenType.REACT:
                tk = self.advance(); e = self.expect(TokenType.IDENTIFIER).value; b = self._block()
                ag.reactions.append(ReactDeclaration(event=e, body=b, line=tk.line, column=tk.column))
            elif tt == TokenType.IDENTIFIER:
                pn = self.advance().value; self.expect(TokenType.COLON); ag.properties[pn] = self.parse_expression()
            else: raise TheeParserError(f"Unexpected in agent: {self.peek().type.name}", self.peek())
            self.skip_newlines()
        self.expect(TokenType.RBRACE); return ag

    def parse_summon(self):
        t = self.advance(); name = self.expect(TokenType.IDENTIFIER).value; alias = name.lower()
        self.skip_newlines()
        if self.match(TokenType.AS): self.advance(); alias = self.expect(TokenType.IDENTIFIER).value
        elif self.match(TokenType.IDENTIFIER) and self.peek().value == "as": self.advance(); alias = self.expect(TokenType.IDENTIFIER).value
        return SummonStatement(agent_name=name, alias=alias, line=t.line, column=t.column)

    def parse_swarm(self):
        t = self.advance(); name = self.expect(TokenType.IDENTIFIER).value
        self.skip_newlines(); self.expect(TokenType.LBRACE); self.skip_newlines()
        sw = SwarmDeclaration(name=name, line=t.line, column=t.column)
        while not self.match(TokenType.RBRACE) and not self.at_end():
            self.skip_newlines()
            if self.match(TokenType.RBRACE): break
            prop = self.expect(TokenType.IDENTIFIER).value; self.expect(TokenType.COLON)
            if prop == "agents": sw.agents = self.parse_list_literal().elements
            elif prop == "strategy": sw.strategy = self.parse_expression()
            elif prop == "goal": sw.goal = self.parse_expression()
            self.skip_newlines()
        self.expect(TokenType.RBRACE); return sw

    def parse_emit(self):
        t = self.advance(); event = self.expect(TokenType.IDENTIFIER).value; data = None
        if self.match(TokenType.LPAREN):
            self.advance()
            if not self.match(TokenType.RPAREN): data = self.parse_expression()
            self.expect(TokenType.RPAREN)
        return EmitStatement(event=event, data=data, line=t.line, column=t.column)

    def parse_kindle(self):
        t = self.advance(); mod = self.expect(TokenType.IDENTIFIER).value
        while self.match(TokenType.DOT): self.advance(); mod += "." + self.expect(TokenType.IDENTIFIER).value
        return KindleStatement(module=mod, line=t.line, column=t.column)

    # ═══ Expressions ═══
    def parse_expression(self): return self._assign()
    def _assign(self):
        e = self._pipe()
        if self.match(TokenType.ASSIGN): self.advance(); return Assignment(target=e, value=self.parse_expression())
        return e
    def _pipe(self):
        l = self._or()
        while self.match(TokenType.PIPE) and self.peek().value == "|>": self.advance(); l = PipeExpression(left=l, right=self._or())
        return l
    def _or(self):
        l = self._and()
        while self.match(TokenType.OR): self.advance(); l = BinaryOp(left=l, op="or", right=self._and())
        return l
    def _and(self):
        l = self._not()
        while self.match(TokenType.AND): self.advance(); l = BinaryOp(left=l, op="and", right=self._not())
        return l
    def _not(self):
        if self.match(TokenType.NOT): t = self.advance(); return UnaryOp(op="not", operand=self._not(), line=t.line, column=t.column)
        return self._cmp()
    def _cmp(self):
        l = self._add()
        while self.match(TokenType.EQUALS, TokenType.NOT_EQUALS, TokenType.LESS_THAN, TokenType.GREATER_THAN, TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL):
            op = self.advance().value; l = BinaryOp(left=l, op=op, right=self._add())
        return l
    def _add(self):
        l = self._mul()
        while self.match(TokenType.PLUS, TokenType.MINUS): op = self.advance().value; l = BinaryOp(left=l, op=op, right=self._mul())
        return l
    def _mul(self):
        l = self._pow()
        while self.match(TokenType.MULTIPLY, TokenType.DIVIDE, TokenType.MODULO): op = self.advance().value; l = BinaryOp(left=l, op=op, right=self._pow())
        return l
    def _pow(self):
        l = self._unary()
        if self.match(TokenType.POWER): self.advance(); l = BinaryOp(left=l, op="**", right=self._pow())
        return l
    def _unary(self):
        if self.match(TokenType.MINUS): t = self.advance(); return UnaryOp(op="-", operand=self._unary(), line=t.line, column=t.column)
        if self.match(TokenType.AWAIT): t = self.advance(); return AwaitExpression(expression=self._unary(), line=t.line, column=t.column)
        if self.match(TokenType.SPAWN): t = self.advance(); return SpawnStatement(expression=self._unary(), line=t.line, column=t.column)
        return self._call()
    def _call(self):
        e = self._primary()
        while True:
            if self.match(TokenType.LPAREN):
                self.advance(); args = []
                if not self.match(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA): self.advance(); args.append(self.parse_expression())
                self.expect(TokenType.RPAREN); e = FunctionCall(callee=e, arguments=args)
            elif self.match(TokenType.DOT):
                self.advance()
                # Accept both identifiers and keywords as member names
                t = self.peek()
                if t.type == TokenType.IDENTIFIER:
                    name = self.advance().value
                else:
                    # Keywords can be used as member names (e.g., obj.on, obj.emit, obj.new)
                    name = self.advance().value
                e = MemberAccess(object=e, member=name)
            elif self.match(TokenType.LBRACKET): self.advance(); idx = self.parse_expression(); self.expect(TokenType.RBRACKET); e = IndexAccess(object=e, index=idx)
            else: break
        return e

    def _primary(self):
        t = self.peek()
        if t.type == TokenType.INTEGER: self.advance(); return NumberLiteral(value=t.value, line=t.line, column=t.column)
        if t.type == TokenType.FLOAT: self.advance(); return NumberLiteral(value=t.value, line=t.line, column=t.column)
        if t.type == TokenType.STRING:
            self.advance()
            if "${" in t.value: return self._parse_template(t)
            return StringLiteral(value=t.value, line=t.line, column=t.column)
        if t.type == TokenType.TRUE: self.advance(); return BooleanLiteral(value=True, line=t.line, column=t.column)
        if t.type == TokenType.FALSE: self.advance(); return BooleanLiteral(value=False, line=t.line, column=t.column)
        if t.type == TokenType.ASH: self.advance(); return AshLiteral(line=t.line, column=t.column)
        if t.type == TokenType.IDENTIFIER:
            if self.peek_ahead() == TokenType.FAT_ARROW: return self._parse_lambda_single()
            self.advance(); return Identifier(name=t.value, line=t.line, column=t.column)
        if t.type == TokenType.LPAREN:
            if self._looks_like_lambda(): return self._parse_lambda()
            self.advance(); e = self.parse_expression(); self.expect(TokenType.RPAREN); return e
        if t.type == TokenType.LBRACKET: return self.parse_list_literal()
        if t.type == TokenType.LBRACE: return self.parse_dict_literal()
        if t.type == TokenType.PURSUE: self.advance(); return PursueStatement(agent=None, goal=self.parse_expression(), line=t.line, column=t.column)
        # v6.0 — new/pudhu for class instantiation
        if t.type == TokenType.NEW:
            self.advance()
            class_name = self.expect(TokenType.IDENTIFIER).value
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                if not self.match(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA): self.advance(); args.append(self.parse_expression())
                self.expect(TokenType.RPAREN)
            return NewExpression(class_name=class_name, arguments=args, line=t.line, column=t.column)
        # v6.0 — super/moolam for parent class access
        if t.type == TokenType.SUPER:
            self.advance()
            method = None; args = []
            if self.match(TokenType.DOT):
                self.advance(); method = self.expect(TokenType.IDENTIFIER).value
                if self.match(TokenType.LPAREN):
                    self.advance()
                    if not self.match(TokenType.RPAREN):
                        args.append(self.parse_expression())
                        while self.match(TokenType.COMMA): self.advance(); args.append(self.parse_expression())
                    self.expect(TokenType.RPAREN)
            elif self.match(TokenType.LPAREN):
                self.advance()
                if not self.match(TokenType.RPAREN):
                    args.append(self.parse_expression())
                    while self.match(TokenType.COMMA): self.advance(); args.append(self.parse_expression())
                self.expect(TokenType.RPAREN)
            return SuperCall(method=method, arguments=args, line=t.line, column=t.column)
        # v6.0 — spread operator ...expr
        if t.type == TokenType.SPREAD:
            self.advance(); return SpreadExpression(expression=self.parse_expression(), line=t.line, column=t.column)
        # v6.0 — yield expression
        if t.type == TokenType.YIELD:
            self.advance()
            val = None
            if not self.match(TokenType.NEWLINE) and not self.match(TokenType.RBRACE) and not self.at_end():
                val = self.parse_expression()
            return YieldExpression(value=val, line=t.line, column=t.column)
        raise TheeParserError(f"Unexpected: {t.type.name} ({t.value!r})", t)

    def _parse_template(self, token):
        import re
        parts = re.split(r"\$\{([^}]+)\}", token.value)
        if len(parts) <= 1: return StringLiteral(value=token.value, line=token.line, column=token.column)
        nodes = []
        for i, part in enumerate(parts):
            if i % 2 == 0:
                if part: nodes.append(StringLiteral(value=part, line=token.line, column=token.column))
            else:
                try:
                    sub = TheeParser(TheeLexer(part).tokenize()).parse_expression()
                    nodes.append(sub)
                except: nodes.append(StringLiteral(value=part, line=token.line, column=token.column))
        if not nodes: return StringLiteral(value="", line=token.line, column=token.column)
        result = nodes[0]
        for n in nodes[1:]: result = BinaryOp(left=result, op="+", right=n, line=token.line, column=token.column)
        return result

    def _looks_like_lambda(self):
        saved = self.pos
        try:
            self.advance(); depth = 1
            while depth > 0 and not self.at_end():
                if self.peek_type() == TokenType.LPAREN: depth += 1
                elif self.peek_type() == TokenType.RPAREN: depth -= 1
                if depth > 0: self.advance()
            if self.at_end(): return False
            self.advance(); return self.match(TokenType.FAT_ARROW)
        finally: self.pos = saved

    def _parse_lambda(self):
        t = self.peek(); self.expect(TokenType.LPAREN); params = []
        if not self.match(TokenType.RPAREN):
            params.append(self.expect(TokenType.IDENTIFIER).value)
            while self.match(TokenType.COMMA): self.advance(); params.append(self.expect(TokenType.IDENTIFIER).value)
        self.expect(TokenType.RPAREN); self.expect(TokenType.FAT_ARROW); body = self.parse_expression()
        return LambdaExpression(params=params, body=body, line=t.line, column=t.column)

    def _parse_lambda_single(self):
        t = self.peek(); param = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.FAT_ARROW); body = self.parse_expression()
        return LambdaExpression(params=[param], body=body, line=t.line, column=t.column)

    def parse_list_literal(self):
        t = self.expect(TokenType.LBRACKET); elems = []; self.skip_newlines()
        if not self.match(TokenType.RBRACKET):
            elems.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                self.advance(); self.skip_newlines()
                if self.match(TokenType.RBRACKET): break
                elems.append(self.parse_expression())
        self.skip_newlines(); self.expect(TokenType.RBRACKET)
        return ListLiteral(elements=elems, line=t.line, column=t.column)

    def parse_dict_literal(self):
        t = self.expect(TokenType.LBRACE); pairs = []; self.skip_newlines()
        if not self.match(TokenType.RBRACE):
            k = self.parse_expression(); self.expect(TokenType.COLON); v = self.parse_expression(); pairs.append((k, v))
            while self.match(TokenType.COMMA):
                self.advance(); self.skip_newlines()
                if self.match(TokenType.RBRACE): break
                k = self.parse_expression(); self.expect(TokenType.COLON); v = self.parse_expression(); pairs.append((k, v))
        self.skip_newlines(); self.expect(TokenType.RBRACE)
        return DictLiteral(pairs=pairs, line=t.line, column=t.column)

    def parse_expression_stmt(self):
        return self.parse_expression()

    # ═══ v6.0 — திருமுறை Parsers ═══

    def parse_class(self):
        t = self.advance()  # consume 'class'/'vagu'
        name = self.expect(TokenType.IDENTIFIER).value
        parent = None
        if self.match(TokenType.EXTENDS):
            self.advance(); parent = self.expect(TokenType.IDENTIFIER).value
        self.skip_newlines(); self.expect(TokenType.LBRACE); self.skip_newlines()
        constructor = None; methods = []; properties = {}
        while not self.match(TokenType.RBRACE) and not self.at_end():
            self.skip_newlines()
            if self.match(TokenType.RBRACE): break
            if self.match(TokenType.FORGE):
                fn = self.parse_forge()
                if fn.name in ("init", "pudhu", "constructor", "__init__"):
                    constructor = fn
                else:
                    methods.append(fn)
            elif self.match(TokenType.LET) or self.match(TokenType.CONST):
                prop = self.parse_let()
                properties[prop.name] = prop.value
            else:
                self.advance()  # skip unknown
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return ClassDeclaration(name=name, parent=parent, constructor=constructor,
                               methods=methods, properties=properties, line=t.line, column=t.column)

    def parse_enum(self):
        t = self.advance()  # consume 'enum'/'pirivu'
        name = self.expect(TokenType.IDENTIFIER).value
        self.skip_newlines(); self.expect(TokenType.LBRACE); self.skip_newlines()
        members = {}; idx = 0
        while not self.match(TokenType.RBRACE) and not self.at_end():
            self.skip_newlines()
            if self.match(TokenType.RBRACE): break
            mname = self.expect(TokenType.IDENTIFIER).value
            if self.match(TokenType.ASSIGN):
                self.advance(); val = self.parse_expression()
                members[mname] = val
            else:
                members[mname] = NumberLiteral(value=idx, line=t.line, column=t.column)
            idx += 1
            if self.match(TokenType.COMMA): self.advance()
            self.skip_newlines()
        self.expect(TokenType.RBRACE)
        return EnumDeclaration(name=name, members=members, line=t.line, column=t.column)

    def parse_yield_stmt(self):
        t = self.advance()  # consume 'yield'/'vilai'
        val = None
        if not self.match(TokenType.NEWLINE) and not self.match(TokenType.RBRACE) and not self.at_end():
            val = self.parse_expression()
        return YieldExpression(value=val, line=t.line, column=t.column)

    def parse_decorator(self):
        t = self.advance()  # consume '@'
        dec_name = self.parse_expression()  # decorator name (could be function call)
        dec_args = []
        self.skip_newlines()
        # Next should be a function or class declaration
        tt = self.peek_type()
        if tt == TokenType.FORGE:
            decl = self.parse_forge()
        elif tt == TokenType.CLASS:
            decl = self.parse_class()
        elif tt == TokenType.DECORATOR:
            decl = self.parse_decorator()  # chained decorators
        else:
            decl = self.parse_statement()
        return DecoratedDeclaration(decorator=dec_name, declaration=decl,
                                    decorator_args=dec_args, line=t.line, column=t.column)
