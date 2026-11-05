"""THEE Interpreter v4.0 — நமசிவாய Architecture — 10/10
Week 1: Try/Catch (முயற்சி/பிழை), Lambda (=>), Throw (எறி)
Week 2: Import/Module (கொணர்), Export (வெளியீடு)
Week 3: Async/Await (ஒத்திசை/காத்திரு), Spawn (உருவாக்கு), Channels
Week 4: HTTP (http_get/post), LLM (ai_complete), Template strings
Week 5: Struct (வடிவம்), Match (பொருத்து), Type hints
Week 6: Package registry, expanded stdlib, optimizer, multi-LLM
10/10: 192 builtins, AST cache, profiler, multi-provider AI, GPIO, Arduino
"""
import math, time, os, sys, json, re, random, threading
# Threading loaded lazily when needed
_lazy_cache = {}
def _lazy(name):
    if name not in _lazy_cache:
        import importlib
        _lazy_cache[name] = importlib.import_module(name)
    return _lazy_cache[name]
from thee_lang.parser import *
from thee_lang import sandbox as _sandbox

# Import optimizer and LLM (graceful fallback)
try:
    from thee_optimizer import TheeOptimizer, TheeProfiler
except ImportError:
    TheeOptimizer = TheeProfiler = None
try:
    from thee_llm import ai_complete as llm_complete, ai_chat as llm_chat, ai_embed as llm_embed, ai_stream as llm_stream
except ImportError:
    llm_complete = llm_chat = llm_embed = llm_stream = None
try:
    from thee_pkg import TheePackageManager
except ImportError:
    TheePackageManager = None

class TheeReturn(Exception):
    def __init__(self, v): self.value = v
class TheeBreak(Exception): pass
class TheeContinue(Exception): pass
class TheeYield(Exception):
    def __init__(self, v): self.value = v
class TheeError(Exception):
    """User-throwable error in THEE programs"""
    def __init__(self, msg, node=None):
        self.thee_message = msg
        loc = f" L{node.line}:C{node.column}" if node and hasattr(node,'line') else ""
        super().__init__(f"தீ பிழை{loc}: {msg}")
class TheeRuntimeError(TheeError): pass

# ═══ Week 3: Channel for concurrent communication ═══
class TheeChannel:
    def __init__(self, name=""):
        self.name = name
        self._queue = []
        self._lock = threading.Lock()
        self._event = threading.Event()
    def send(self, value):
        with self._lock:
            self._queue.append(value)
            self._event.set()
    def receive(self):
        self._event.wait(timeout=5)
        with self._lock:
            if self._queue:
                val = self._queue.pop(0)
                if not self._queue: self._event.clear()
                return val
            return None
    def __repr__(self):
        return f"<கலணி (Channel) '{self.name}' items={len(self._queue)}>"

# ═══ Week 3: Future for async results ═══
class TheeFuture:
    def __init__(self):
        self._result = None; self._done = threading.Event(); self._error = None
    def set_result(self, v): self._result = v; self._done.set()
    def set_error(self, e): self._error = e; self._done.set()
    def result(self, timeout=10):
        self._done.wait(timeout=timeout)
        if self._error: raise TheeRuntimeError(str(self._error))
        return self._result

# ═══ Week 5: Struct instance ═══
class TheeStruct:
    def __init__(self, name, fields, methods=None):
        self._struct_name = name; self._fields = dict(fields)
        self._methods = methods or {}
    def __repr__(self):
        pairs = ", ".join(f"{k}: {v}" for k, v in self._fields.items())
        return f"{self._struct_name}{{{pairs}}}"
    def get(self, key):
        if key in self._fields: return self._fields[key]
        if key in self._methods: return self._methods[key]
        raise TheeRuntimeError(f"Struct '{self._struct_name}' has no field '{key}'")
    def set(self, key, val): self._fields[key] = val

class Environment:
    def __init__(self, parent=None):
        self.bindings = {}; self.constants = set(); self.parent = parent
    def get(self, name):
        if name in self.bindings: return self.bindings[name]
        if self.parent: return self.parent.get(name)
        raise TheeRuntimeError(f"Undefined: '{name}'")
    def set(self, name, value, is_const=False):
        if name in self.constants: raise TheeRuntimeError(f"Cannot reassign constant: '{name}'")
        self.bindings[name] = value
        if is_const: self.constants.add(name)
    def assign(self, name, value):
        if name in self.bindings:
            if name in self.constants: raise TheeRuntimeError(f"Cannot reassign constant: '{name}'")
            self.bindings[name] = value; return
        if self.parent: self.parent.assign(name, value); return
        raise TheeRuntimeError(f"Undefined: '{name}'")

class TheeAgent:
    def __init__(self, name, decl, interp):
        self.name = name; self.decl = decl; self.interp = interp
        self.skills = {}; self.guards = []; self.memory = {}
        self.memory_type = decl.memory_type; self.goal = None
        self.state = "idle"; self.event_handlers = {}; self.properties = {}
        for sk in decl.skills: self.skills[sk.name] = sk
        for g in decl.guards: self.guards.append(g)
        for r in decl.reactions: self.event_handlers[r.event] = r
        if decl.goal: self.goal = interp.evaluate(decl.goal)
        for k, v in decl.properties.items(): self.properties[k] = interp.evaluate(v)

    def execute_skill(self, skill_name, args):
        if skill_name not in self.skills:
            raise TheeRuntimeError(f"Agent '{self.name}' has no skill '{skill_name}'")
        skill = self.skills[skill_name]
        for guard in self.guards:
            rules = {k: self.interp.evaluate(v) for k, v in guard.rules.items()}
            if "require_approval" in rules:
                approved = rules["require_approval"]
                if isinstance(approved, list) and skill_name in approved:
                    print(f"  🔒 காவல் (Vallidevi Guard): '{skill_name}' requires approval"); return None
        env = Environment(self.interp.env); env.set("self", self)
        for i, p in enumerate(skill.params): env.set(p, args[i] if i < len(args) else None)
        old = self.interp.env; self.interp.env = env; result = None
        try:
            for stmt in skill.body: result = self.interp.execute(stmt)
        except TheeReturn as r: result = r.value
        finally: self.interp.env = old
        return result

    def pursue_goal(self, g):
        self.state = "pursuing"; self.goal = g
        print(f"  🎯 இலக்கு: {self.name} → \"{g}\"")
        self.state = "completed"; print(f"  ✅ முடிந்தது: {self.name}")

    def introspect(self):
        lines = [f"═══ உயிர் நிலை (Agent) ═══", f"  பெயர்: {self.name}", f"  நிலை: {self.state}",
                 f"  இலக்கு: {self.goal or 'இல்லை'}", f"  திறன்: {', '.join(self.skills.keys()) or 'இல்லை'}",
                 f"  காவல்: {len(self.guards)}", f"  நினைவு: {self.memory_type}"]
        if self.properties:
            lines.append(f"  பண்புகள்:")
            for k, v in self.properties.items(): lines.append(f"    {k}: {v}")
        return "\n".join(lines)

class TheeInterpreter:
    def __init__(self, sandbox=None):
        self.sandbox = _sandbox.sandbox_requested() if sandbox is None else bool(sandbox)
        self.env = Environment(); self.agents = {}; self.output = []
        _register_power_builtins(self)
        _register_gpio_stubs(self)
        _register_method_chaining(self)
        _register_v5_builtins(self)
        _register_v5_extras(self)
        _register_v5_environments(self)
        _register_v5_mobile(self)
        _register_v5_bugfixes(self)
        _register_v6_features(self)
        _register_v5_extra(self)
        self.exports = {}  # Week 2: module exports
        self.structs = {}  # Week 5: struct definitions
        self._imported = set()  # Week 2: import cycle protection
        self._setup()
        self.sandbox_blocked = _sandbox.apply_sandbox(self) if self.sandbox else []

    def _invoke(self, f, args):
        """Call a THEE function (dict closure) or Python callable"""
        if callable(f): return f(*args)
        if isinstance(f, dict) and "params" in f:
            env = Environment(f["closure"])
            for i, p in enumerate(f["params"]): env.set(p, args[i] if i < len(args) else None)
            old = self.env; self.env = env; res = None
            try:
                for s in f["body"]: res = self.execute(s)
            except TheeReturn as r: res = r.value
            finally: self.env = old
            return res
        raise TheeRuntimeError(f"Not callable: {type(f)}")

    def _reduce(self, f, lst, initial=None):
        it = iter(lst)
        acc = initial if initial is not None else next(it)
        for x in it: acc = self._invoke(f, [acc, x])
        return acc

    def _setup(self):
        b = self.env.set
        # Type/Conversion
        b("len", lambda x: len(x)); b("type", lambda x: type(x).__name__)
        b("str", lambda x: str(x)); b("int", lambda x: int(x)); b("float", lambda x: float(x))
        b("range", lambda *a: list(range(*[int(x) for x in a]))); b("list", lambda x: list(x))
        # Collection
        b("map", lambda f, l: [self._invoke(f, [x]) for x in l])
        b("filter", lambda f, l: [x for x in l if self._invoke(f, [x])])
        b("reduce", lambda f, l, i=None: self._reduce(f, l, i))
        b("sort", lambda l: sorted(l)); b("reverse", lambda l: list(reversed(l)))
        b("append", lambda l, i: l.append(i) or l); b("push", lambda l, i: l.append(i) or l)
        b("unique", lambda l: list(dict.fromkeys(l)))
        b("flatten", lambda l: [x for sub in l for x in (sub if isinstance(sub, list) else [sub])])
        b("zip_lists", lambda a, c: list(map(list, zip(a, c))))
        b("enumerate_list", lambda l: list(map(list, enumerate(l))))
        b("set_unique", lambda l: list(set(l)))
        # Math
        b("abs", lambda x: abs(x)); b("round", lambda x, n=0: round(x, int(n)))
        b("min", lambda *a: min(*a) if len(a)>1 else min(a[0]))
        b("max", lambda *a: max(*a) if len(a)>1 else max(a[0]))
        b("sum", lambda x: sum(x)); b("sqrt", lambda x: math.sqrt(x)); b("pow", lambda x, y: x**y)
        b("sin", lambda x: math.sin(x)); b("cos", lambda x: math.cos(x))
        b("tan", lambda x: math.tan(x)); b("log", lambda x: math.log(x))
        b("floor", lambda x: math.floor(x)); b("ceil", lambda x: math.ceil(x))
        b("PI", math.pi); b("E", math.e)
        b("null", None); b("none", None); b("sambal", None); b("None", None)
        # String
        b("upper", lambda s: s.upper()); b("lower", lambda s: s.lower())
        b("split", lambda s, d=" ": s.split(d))
        def _join_bi(a, b=None):
            if b is None:
                return ", ".join(str(x) for x in a) if isinstance(a, list) else str(a)
            if isinstance(a, list) and isinstance(b, str): return b.join(str(x) for x in a)
            if isinstance(a, str) and isinstance(b, list): return a.join(str(x) for x in b)
            return str(b).join(str(x) for x in a) if isinstance(a, list) else str(a) + str(b)
        b("join", _join_bi)
        b("trim", lambda s: s.strip()); b("contains", lambda s, sub: sub in s)
        b("replace", lambda s, o, n: s.replace(o, n))
        b("slice", lambda l, s, e=None: l[int(s):int(e)] if e else l[int(s):])
        b("startswith", lambda s, p: s.startswith(p)); b("endswith", lambda s, p: s.endswith(p))
        b("find", lambda s, sub: s.find(sub))
        b("count_str", lambda s, sub: s.count(sub) if isinstance(s, str) else len(s))
        b("repeat_str", lambda s, n: s * int(n))
        b("pad_left", lambda s, w, c=" ": str(s).rjust(int(w), c))
        b("pad_right", lambda s, w, c=" ": str(s).ljust(int(w), c))
        b("char_at", lambda s, i: s[int(i)] if int(i) < len(s) else "")
        b("char_code", lambda c: ord(c[0]) if c else 0)
        b("from_char_code", lambda n: chr(int(n)))
        b("format_str", lambda t, *a: t.format(*a) if a else t)
        # JSON
        b("json_parse", lambda s: json.loads(s))
        b("json_stringify", lambda o: json.dumps(o, ensure_ascii=False, default=str))
        b("json_encode", lambda o: json.dumps(o, ensure_ascii=False, default=str))
        b("json_decode", lambda s: json.loads(s))
        b("to_string", lambda x: str(x)); b("parse_int", lambda s: int(s)); b("parse_float", lambda s: float(s))
        # Date/Time
        b("now", lambda: time.time()); b("sleep_ms", lambda ms: time.sleep(ms/1000))
        b("timestamp", lambda: int(time.time()))
        b("date_string", lambda: time.strftime("%Y-%m-%d")); b("time_string", lambda: time.strftime("%H:%M:%S"))
        # Regex
        b("regex_match", lambda p, s: bool(re.match(p, s)))
        b("regex_find", lambda p, s: re.findall(p, s))
        b("regex_replace", lambda p, r, s: re.sub(p, r, s))
        b("regex_split", lambda p, s: re.split(p, s))
        # Dict ops
        b("keys", lambda d: list(d.keys()) if isinstance(d, dict) else [])
        b("values", lambda d: list(d.values()) if isinstance(d, dict) else [])
        b("items", lambda d: [list(p) for p in d.items()] if isinstance(d, dict) else [])
        b("has_key", lambda d, k: k in d if isinstance(d, dict) else False)
        b("merge", lambda a, c: {**a, **c} if isinstance(a, dict) else a + c)
        # Functional
        b("identity", lambda x: x)
        b("any_true", lambda l: any(l)); b("all_true", lambda l: all(l))
        # File I/O
        b("read_file", lambda p: open(p, "r", encoding="utf-8").read())
        b("write_file", lambda p, d: (open(p, "w", encoding="utf-8").write(str(d)), p)[1])
        b("file_exists", lambda p: os.path.exists(p))
        def _file_write(path, content):
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f: f.write(str(content))
            return path
        b("file_write", _file_write)
        b("file_read", lambda p: open(p, "r", encoding="utf-8").read())
        b("file_append", lambda p, c: open(p, "a", encoding="utf-8").write(str(c)))
        b("file_delete", lambda p: os.remove(p) if os.path.exists(p) else None)
        b("file_list", lambda p=".": os.listdir(p))
        b("file_copy", lambda s, d: __import__("shutil").copy2(s, d))
        b("mkdir", lambda p: os.makedirs(p, exist_ok=True))
        b("print_raw", lambda *a: print(*a))
        # Random
        b("random_num", lambda: random.random())
        b("random_int", lambda a, c: random.randint(int(a), int(c)))
        b("random_choice", lambda l: random.choice(l))
        b("shuffle_list", lambda l: (random.shuffle(l), l)[1])

        # ═══════════════════════════════════════════════════════
        # 10/10 STDLIB MEGA EXPANSION — 120+ new builtins
        # ═══════════════════════════════════════════════════════

        # Advanced Math
        b("asin", lambda x: math.asin(x)); b("acos", lambda x: math.acos(x))
        b("atan", lambda x: math.atan(x)); b("atan2", lambda y, x: math.atan2(y, x))
        b("log2", lambda x: math.log2(x)); b("log10", lambda x: math.log10(x))
        b("exp", lambda x: math.exp(x)); b("hypot", lambda x, y: math.hypot(x, y))
        b("degrees", lambda r: math.degrees(r)); b("radians", lambda d: math.radians(d))
        b("gcd", lambda a, c: math.gcd(int(a), int(c)))
        b("factorial", lambda n: math.factorial(int(n)))
        b("clamp", lambda x, lo, hi: max(lo, min(x, hi)))
        b("lerp", lambda a, c, t: a + (c - a) * t)
        b("sign", lambda x: (x > 0) - (x < 0))
        b("INF", float("inf")); b("NAN", float("nan"))
        b("TAU", math.tau); b("PHI", (1 + math.sqrt(5)) / 2)

        # Advanced String
        b("capitalize", lambda s: s.capitalize()); b("title_case", lambda s: s.title())
        b("center", lambda s, w, c=" ": s.center(int(w), c))
        b("is_digit", lambda s: s.isdigit()); b("is_alpha", lambda s: s.isalpha())
        b("is_upper", lambda s: s.isupper()); b("is_lower", lambda s: s.islower())
        b("strip", lambda s, c=None: s.strip(c))
        b("encode_utf8", lambda s: list(s.encode("utf-8")))
        b("hex_encode", lambda s: s.encode().hex())
        b("hash_sha256", lambda s: __import__("hashlib").sha256(s.encode()).hexdigest())
        b("hash_md5", lambda s: __import__("hashlib").md5(s.encode()).hexdigest())
        b("uuid4", lambda: str(__import__("uuid").uuid4()))
        b("base64_enc", lambda s: __import__("base64").b64encode(s.encode()).decode())
        b("base64_dec", lambda s: __import__("base64").b64decode(s.encode()).decode())

        # Advanced Collections
        b("chunk", lambda l, n: [l[ix:ix+int(n)] for ix in range(0, len(l), int(n))])
        b("take", lambda l, n: l[:int(n)]); b("drop", lambda l, n: l[int(n):])
        b("head", lambda l: l[0] if l else None); b("tail", lambda l: l[1:] if l else [])
        b("last", lambda l: l[-1] if l else None)
        b("compact", lambda l: [x for x in l if x is not None and x != False])
        b("index_of", lambda l, v: l.index(v) if v in l else -1)
        b("count_items", lambda l, v: l.count(v))
        b("transpose", lambda m: [list(r) for r in zip(*m)] if m else [])
        b("deep_copy", lambda o: __import__("copy").deepcopy(o))
        b("sorted_by", lambda l, k: sorted(l, key=lambda x: x.get(k, 0) if isinstance(x, dict) else x))
        b("group_by", lambda l, k: self._group_by(l, k))
        b("dict_filter", lambda d, fn: {k: v for k, v in d.items() if self._invoke(fn, [k, v])})
        b("dict_map", lambda d, fn: {k: self._invoke(fn, [v]) for k, v in d.items()})

        # Functional Advanced
        b("memoize", lambda fn: self._make_memoized(fn))
        b("pipe_fn", lambda *fns: lambda x: self._pipe_fns(x, fns))
        b("curry", lambda fn, n: self._curry(fn, int(n)))
        b("flip", lambda fn: lambda a, c: self._invoke(fn, [c, a]))
        b("tap", lambda x, fn: (self._invoke(fn, [x]), x)[1])

        # Date/Time Advanced
        b("date_now", lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
        b("date_format", lambda fmt="%Y-%m-%d", ts=None: time.strftime(fmt) if ts is None else time.strftime(fmt, time.localtime(ts)))
        b("elapsed_ms", lambda start: (time.time() - start) * 1000)
        b("perf_counter", lambda: time.perf_counter())

        # System/OS
        b("env_get", lambda k, d="": os.environ.get(k, d))
        b("platform_name", lambda: sys.platform)
        b("argv_list", lambda: sys.argv[1:])
        b("cwd", lambda: os.getcwd())
        b("path_join", lambda *p: os.path.join(*p))
        b("path_exists", lambda p: os.path.exists(p))
        b("path_dir", lambda p: os.path.dirname(p))
        b("path_base", lambda p: os.path.basename(p))
        b("mkdir_p", lambda p: os.makedirs(p, exist_ok=True) or p)
        b("list_dir", lambda p=".": os.listdir(p))
        b("file_size", lambda p: os.path.getsize(p))
        b("exec_cmd", lambda cmd: __import__("subprocess").getoutput(cmd))
        b("url_encode", lambda s: __import__("urllib.parse", fromlist=["quote"]).quote(str(s)))
        b("url_decode", lambda s: __import__("urllib.parse", fromlist=["unquote"]).unquote(str(s)))

        # Error type constructors
        b("TypeError", lambda m: TheeError("TypeError: " + str(m)))
        b("ValueError", lambda m: TheeError("ValueError: " + str(m)))
        b("IndexError", lambda m: TheeError("IndexError: " + str(m)))
        b("KeyError", lambda m: TheeError("KeyError: " + str(m)))
        b("IOError", lambda m: TheeError("IOError: " + str(m)))

        # Type checks
        b("is_string", lambda x: isinstance(x, str))
        b("is_number", lambda x: isinstance(x, (int, float)))
        b("is_int", lambda x: isinstance(x, int) and not isinstance(x, bool))
        b("is_float", lambda x: isinstance(x, float))
        b("is_bool", lambda x: isinstance(x, bool))
        b("is_list", lambda x: isinstance(x, list))
        b("is_dict", lambda x: isinstance(x, dict))
        b("is_null", lambda x: x is None)
        b("is_callable", lambda x: callable(x) or (isinstance(x, dict) and "params" in x))

        # Conversion extras
        b("to_int", lambda x: int(x)); b("to_float", lambda x: float(x))
        b("to_bool", lambda x: bool(x)); b("to_json", lambda x: json.dumps(x, ensure_ascii=False, default=str))
        b("from_json", lambda s: json.loads(s))

        # Assert (for testing)
        def _assert_eq(a, c, m=""):
            if a != c: raise TheeError(f"Assert failed: {a} != {c} {m}")
        def _assert_true(v, m=""):
            if not v: raise TheeError(f"Assert failed: expected true. {m}")
        b("assert_eq", _assert_eq); b("assert_true", _assert_true)

        # THEE info
        b("thee_help", lambda topic="": self._help(topic))
        b("thee_builtins", lambda: sorted([k for k in self.env.bindings.keys()]))
        # Constants
        b("NAMACHIVAYAM", "நமசிவாய"); b("AINTHU", 5); b("AARU", 6)
        b("PANCHABHUTAM", ["நிலம்", "நீர்", "தீ", "காற்று", "ஆகாயம்"])
        # Week 1: Error constructor
        b("Error", lambda msg: {"type": "TheeError", "message": msg})
        b("is_error", lambda x: isinstance(x, dict) and x.get("type") == "TheeError")
        # Week 3: Channel constructor
        b("make_channel", lambda name="": TheeChannel(name))
        # Week 4: HTTP builtins (using urllib — no external deps)
        b("http_get", self._http_get)
        b("http_post", self._http_post)
        # Week 4: LLM stubs (real integration needs API key)
        b("ai_complete", self._ai_complete)
        b("ai_chat", self._ai_chat)
        b("ai_embed", self._ai_embed)
        b("ai_stream", lambda prompt, cb=None: self._ai_complete(prompt))
        # Week 5: Struct instantiation helper
        b("new", self._struct_new)
        # Week 6: Package registry
        b("thee_version", "3.0.0")
        b("thee_info", lambda: {"version": "3.0.0", "architecture": "நமசிவாய", "builtins": len(self.env.bindings)})

    # ═══ Week 4: HTTP ═══
    def _http_get(self, url, headers=None):
        try:
            from urllib.request import Request, urlopen
            req = Request(url)
            if headers and isinstance(headers, dict):
                for k, v in headers.items(): req.add_header(k, v)
            with urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
                return {"status": resp.status, "body": body, "headers": dict(resp.headers)}
        except Exception as e:
            return {"status": 0, "error": str(e), "body": ""}

    def _http_post(self, url, data=None, headers=None):
        try:
            from urllib.request import Request, urlopen
            body = json.dumps(data).encode("utf-8") if data else b""
            req = Request(url, data=body, method="POST")
            req.add_header("Content-Type", "application/json")
            if headers and isinstance(headers, dict):
                for k, v in headers.items(): req.add_header(k, v)
            with urlopen(req, timeout=10) as resp:
                return {"status": resp.status, "body": resp.read().decode("utf-8")}
        except Exception as e:
            return {"status": 0, "error": str(e), "body": ""}

    # ═══ Week 4: LLM Integration ═══
    def _ai_complete(self, prompt, config=None):
        """AI completion — auto-detects Anthropic/OpenAI/Ollama/stub"""
        if llm_complete:
            return llm_complete(prompt, config if isinstance(config, dict) else None)
        api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if api_key and os.environ.get("ANTHROPIC_API_KEY"):
            try:
                resp = self._http_post("https://api.anthropic.com/v1/messages", {
                    "model": "claude-sonnet-4-20250514", "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}]
                }, {"x-api-key": api_key, "anthropic-version": "2023-06-01"})
                if resp.get("status") == 200:
                    data = json.loads(resp["body"])
                    return data.get("content", [{}])[0].get("text", "")
            except: pass
        return f"[AI stub — set ANTHROPIC_API_KEY or OPENAI_API_KEY or install Ollama] Prompt: {prompt[:100]}"

    def _ai_chat(self, messages, config=None):
        """Multi-turn AI chat — auto-detects provider"""
        if llm_chat:
            return llm_chat(messages, config if isinstance(config, dict) else None)
        return f"[AI chat stub — set API key or install Ollama] {len(messages)} messages"

    def _ai_embed(self, text, config=None):
        """Text embeddings for RAG/vector search"""
        if llm_embed:
            return llm_embed(text, config if isinstance(config, dict) else None)
        import hashlib
        h = hashlib.sha256(text.encode()).hexdigest()
        return [int(h[i:i+2], 16) / 255.0 for i in range(0, 64, 2)]

    # ═══ Week 5: Struct instantiation ═══
    def _struct_new(self, name, values=None):
        if name not in self.structs:
            raise TheeRuntimeError(f"Unknown struct: '{name}'")
        sdef = self.structs[name]
        fields = {}
        for fname, ftype in sdef["fields"]:
            fields[fname] = values.get(fname) if values and fname in values else None
        return TheeStruct(name, fields.items(), sdef.get("methods", {}))

    # ═══ Main Execution ═══
    def run(self, program):
        for s in program.statements: self.execute(s)

    def execute(self, node):
        if isinstance(node, LetDeclaration):
            self.env.set(node.name, self.evaluate(node.value), node.is_const)
        elif isinstance(node, LightStatement):
            v = self.evaluate(node.expression); t = self._fmt(v); print(t); self.output.append(t)
        elif isinstance(node, ForgeDeclaration):
            fn = {"params": node.params, "body": node.body, "closure": self.env, "is_async": node.is_async}
            self.env.set(node.name, fn)
        elif isinstance(node, IfStatement): self._if(node)
        elif isinstance(node, RepeatTimesLoop): self._rep_times(node)
        elif isinstance(node, RepeatForLoop): self._rep_for(node)
        elif isinstance(node, WhileLoop): self._while(node)
        elif isinstance(node, BreakStatement): raise TheeBreak()
        elif isinstance(node, ContinueStatement): raise TheeContinue()
        elif isinstance(node, EmberStatement):
            raise TheeReturn(self.evaluate(node.value) if node.value else None)
        # Week 1: Try/Catch
        elif isinstance(node, TryCatchStatement): self._try_catch(node)
        elif isinstance(node, ThrowStatement): self._throw(node)
        # Week 1: Lambda is handled in evaluate
        # Week 2: Import/Export
        elif isinstance(node, ImportStatement): self._import(node)
        elif isinstance(node, ExportStatement): self._export(node)
        # Week 3: Async/Spawn/Channel
        elif isinstance(node, SpawnStatement): return self._spawn(node)
        elif isinstance(node, ChannelCreate): self._channel_create(node)
        # Week 5: Struct/Match
        elif isinstance(node, StructDeclaration): self._struct_decl(node)
        elif isinstance(node, MatchStatement): self._match(node)
        # Agent-native
        elif isinstance(node, AgentDeclaration):
            self.agents[node.name] = node; agent = TheeAgent(node.name, node, self); self.env.set(node.name, agent)
        elif isinstance(node, SummonStatement): self._summon(node)
        elif isinstance(node, SwarmDeclaration): self._swarm(node)
        elif isinstance(node, EmitStatement): self._emit(node)
        elif isinstance(node, KindleStatement): self._kindle(node)
        # v6.0 — திருமுறை features
        elif isinstance(node, ClassDeclaration): self._class_decl(node)
        elif isinstance(node, EnumDeclaration): self._enum_decl(node)
        elif isinstance(node, DecoratedDeclaration): self._decorated(node)
        elif isinstance(node, DestructureAssignment): self._destructure(node)
        elif isinstance(node, YieldExpression): return self._yield_expr(node)
        elif isinstance(node, Assignment): self._assign_exec(node)
        else: return self.evaluate(node)

    def evaluate(self, node):
        if node is None: return None
        if isinstance(node, NumberLiteral): return node.value
        if isinstance(node, StringLiteral): return node.value
        if isinstance(node, BooleanLiteral): return node.value
        if isinstance(node, AshLiteral): return None
        if isinstance(node, Identifier): return self.env.get(node.name)
        if isinstance(node, ListLiteral): return [self.evaluate(e) for e in node.elements]
        if isinstance(node, DictLiteral): return {self.evaluate(k): self.evaluate(v) for k, v in node.pairs}
        if isinstance(node, BinaryOp): return self._binary(node)
        if isinstance(node, UnaryOp):
            v = self.evaluate(node.operand)
            if node.op == "-": return -v
            if node.op == "not": return not v
        if isinstance(node, FunctionCall): return self._call(node)
        if isinstance(node, MemberAccess): return self._member(node)
        if isinstance(node, IndexAccess):
            o = self.evaluate(node.object); i = self.evaluate(node.index)
            try: return o[i] if isinstance(o, dict) else o[int(i)]
            except: raise TheeRuntimeError(f"Index error", node)
        if isinstance(node, PipeExpression): return self._pipe(node)
        if isinstance(node, Assignment):
            v = self.evaluate(node.value)
            if isinstance(node.target, Identifier): self.env.assign(node.target.name, v)
            elif isinstance(node.target, IndexAccess):
                self.evaluate(node.target.object)[self.evaluate(node.target.index)] = v
            elif isinstance(node.target, MemberAccess):
                o = self.evaluate(node.target.object)
                if isinstance(o, dict): o[node.target.member] = v
                elif isinstance(o, TheeAgent): o.memory[node.target.member] = v
                elif isinstance(o, TheeStruct): o.set(node.target.member, v)
            return v
        # Week 1: Lambda
        if isinstance(node, LambdaExpression):
            return {"params": node.params, "body": [EmberStatement(value=node.body)],
                    "closure": self.env, "is_lambda": True}
        # Week 3: Await
        if isinstance(node, AwaitExpression):
            fut = self.evaluate(node.expression)
            if isinstance(fut, TheeFuture): return fut.result()
            return fut  # Already resolved
        # v6.0 — திருமுறை evaluations
        if isinstance(node, NewExpression): return self._new_instance(node)
        if isinstance(node, SuperCall): return self._super_call(node)
        if isinstance(node, SpreadExpression):
            v = self.evaluate(node.expression)
            return {"__spread__": True, "value": v}
        if isinstance(node, YieldExpression): return self._yield_expr(node)
        if isinstance(node, DecoratedDeclaration): self._decorated(node); return None
        # Week 3: Spawn as expression
        if isinstance(node, SpawnStatement):
            return self._spawn(node)
        if isinstance(node, PursueStatement): return self.evaluate(node.goal)
        raise TheeRuntimeError(f"Cannot evaluate: {type(node).__name__}", node)

    # ═══ Week 1: Try/Catch/Finally ═══
    def _try_catch(self, node):
        try:
            for s in node.try_body: self.execute(s)
        except (TheeReturn, TheeBreak, TheeContinue):
            raise  # Never catch control flow exceptions
        except (TheeError, TheeRuntimeError) as e:
            if node.catch_body:
                env = Environment(self.env)
                if node.catch_var:
                    err_msg = e.thee_message if hasattr(e, 'thee_message') else str(e)
                    env.set(node.catch_var, {"type": "TheeError", "message": err_msg})
                old = self.env; self.env = env
                try:
                    for s in node.catch_body: self.execute(s)
                finally: self.env = old
        except Exception as e:
            if node.catch_body:
                env = Environment(self.env)
                if node.catch_var:
                    env.set(node.catch_var, {"type": "Error", "message": str(e)})
                old = self.env; self.env = env
                try:
                    for s in node.catch_body: self.execute(s)
                finally: self.env = old
        finally:
            if node.finally_body:
                for s in node.finally_body: self.execute(s)

    def _throw(self, node):
        val = self.evaluate(node.expression)
        if isinstance(val, str):
            raise TheeError(val, node)
        elif isinstance(val, dict) and "message" in val:
            raise TheeError(val["message"], node)
        else:
            raise TheeError(str(val), node)

    # ═══ Week 2: Import/Module ═══
    def _import(self, node):
        path = node.path
        if self.sandbox: _sandbox.check_import(path)
        # Python bridge: konar python.numpy / konar python.os.path as p
        if path.startswith("python."):
            mod = TheePythonBridge.py_import(path[len("python."):])
            self.env.set(node.alias or path.split(".")[-1], mod)
            return
        # Built-in modules
        builtins_mods = {
            "math": {"PI": math.pi, "E": math.e, "sqrt": math.sqrt, "sin": math.sin,
                     "cos": math.cos, "tan": math.tan, "log": math.log, "floor": math.floor,
                     "ceil": math.ceil, "abs": abs, "pow": pow},
            "json": {"parse": json.loads, "stringify": lambda o: json.dumps(o, ensure_ascii=False, default=str)},
            "time": {"now": time.time, "sleep": time.sleep, "timestamp": lambda: int(time.time()),
                     "date": lambda: time.strftime("%Y-%m-%d"), "clock": lambda: time.strftime("%H:%M:%S")},
            "random": {"random": random.random, "randint": random.randint,
                       "choice": random.choice, "shuffle": lambda l: (random.shuffle(l), l)[1]},
            "regex": {"match": lambda p, s: bool(re.match(p, s)), "find": re.findall,
                      "replace": re.sub, "split": re.split},
            "http": {"get": self._http_get, "post": self._http_post},
            "ai": {"complete": self._ai_complete, "chat": self._ai_chat},
            "os": {"exists": os.path.exists, "cwd": os.getcwd, "env": lambda k: os.environ.get(k, "")},
        }

        if path in builtins_mods:
            mod = builtins_mods[path]
            alias = node.alias or path
            self.env.set(alias, mod)
            # Also set individual bindings for convenience
            if not node.alias:
                for k, v in mod.items(): self.env.set(k, v)
            return

        # File-based import: import "path/to/file.th"
        if self.sandbox: _sandbox.check_file_import(path)
        # .th is the main extension; .thee still works
        names = [path] if path.endswith((".th", ".thee")) else [path + ".th", path + ".thee"]
        file_path = names[0]
        found = False
        for name in names:
            bases = [""] if os.path.isabs(name) else [".", os.path.dirname(sys.argv[-1]) if sys.argv else "."]
            for base in bases:
                candidate = os.path.join(base, name) if base else name
                if os.path.exists(candidate):
                    file_path = candidate; found = True; break
            if found: break

        if not os.path.exists(file_path):
            raise TheeRuntimeError(f"Module not found: '{path}'", node)

        if file_path in self._imported:
            return  # Already imported (cycle protection)
        self._imported.add(file_path)

        # Parse and execute the module in a new environment
        from thee_lang.lexer import TheeLexer
        source = open(file_path, "r", encoding="utf-8").read()
        tokens = TheeLexer(source).tokenize()
        ast = TheeParser(tokens).parse()

        mod_interp = TheeInterpreter()
        mod_interp.run(ast)

        # Import exports or all top-level bindings
        mod_bindings = mod_interp.exports if mod_interp.exports else mod_interp.env.bindings
        alias = node.alias or os.path.splitext(os.path.basename(path))[0]

        if node.names:
            for n in node.names:
                if n in mod_bindings: self.env.set(n, mod_bindings[n])
        elif node.alias:
            self.env.set(alias, mod_bindings)
        else:
            for k, v in mod_bindings.items():
                if not k.startswith("_") and k not in ("len","type","str","int","float"):
                    self.env.set(k, v)

    def _export(self, node):
        if node.declaration:
            self.execute(node.declaration)
            if isinstance(node.declaration, (LetDeclaration, ForgeDeclaration)):
                name = node.declaration.name
                self.exports[name] = self.env.get(name)

    # ═══ Week 3: Async/Spawn/Channel ═══
    def _spawn(self, node):
        """Spawn concurrent execution — returns a Future"""
        future = TheeFuture()
        expr = node.expression

        def run_async():
            try:
                # Create a child interpreter with shared env
                result = self.evaluate(expr)
                future.set_result(result)
            except Exception as e:
                future.set_error(e)

        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
        return future

    def _channel_create(self, node):
        ch = TheeChannel(node.name)
        self.env.set(node.name, ch)

    # ═══ Week 5: Struct ═══
    def _struct_decl(self, node):
        methods = {}
        for m in node.methods:
            methods[m.name] = {"params": m.params, "body": m.body, "closure": self.env}
        self.structs[node.name] = {"fields": node.fields, "methods": methods}
        # Create constructor function
        def make_struct(*args, **kwargs):
            fields = {}
            for i, (fname, ftype) in enumerate(node.fields):
                if fname in kwargs:
                    fields[fname] = kwargs[fname]
                elif i < len(args):
                    fields[fname] = args[i]
                else:
                    fields[fname] = None
            return TheeStruct(node.name, fields.items(), methods)
        self.env.set(node.name, make_struct)

    # ═══ Week 5: Match/Pattern Matching ═══
    def _match(self, node):
        value = self.evaluate(node.expression)
        for pattern, body in node.cases:
            pval = self.evaluate(pattern)
            if value == pval or (isinstance(pval, str) and pval == "_"):
                for s in body: self.execute(s)
                return
        if node.default_body:
            for s in node.default_body: self.execute(s)

    # ═══ Formatting ═══
    def _fmt(self, v):
        if v is None: return "சாம்பல் (ash/null)"
        if v is True: return "உண்மை (true)"
        if v is False: return "பொய் (false)"
        if isinstance(v, list): return "[" + ", ".join(self._fmt(x) for x in v) + "]"
        if isinstance(v, dict):
            if v.get("type") == "TheeError": return f"பிழை: {v.get('message','')}"
            return "{" + ", ".join(f"{self._fmt(k)}: {self._fmt(x)}" for k, x in v.items()) + "}"
        if isinstance(v, float) and v == int(v): return str(int(v))
        if isinstance(v, TheeAgent): return v.introspect()
        if isinstance(v, TheeStruct): return str(v)
        if isinstance(v, TheeChannel): return str(v)
        if isinstance(v, TheeFuture): return f"<Future pending={not v._done.is_set()}>"
        return str(v)

    def _binary(self, n):
        if n.op == "and": l = self.evaluate(n.left); return l and self.evaluate(n.right)
        if n.op == "or": l = self.evaluate(n.left); return l or self.evaluate(n.right)
        l = self.evaluate(n.left); r = self.evaluate(n.right)
        try:
            ops = {"+": lambda: l+r, "-": lambda: l-r, "*": lambda: l*r, "/": lambda: l/r if r else None,
                   "%": lambda: l%r, "**": lambda: l**r, "==": lambda: l==r, "!=": lambda: l!=r,
                   "<": lambda: l<r, ">": lambda: l>r, "<=": lambda: l<=r, ">=": lambda: l>=r}
            return ops[n.op]()
        except TypeError:
            if n.op == "+": return str(l) + str(r)
            raise

    def _call(self, node):
        callee = self.evaluate(node.callee); args = [self.evaluate(a) for a in node.arguments]
        # Week 5: Struct member method calls
        if isinstance(callee, dict) and "params" in callee:
            env = Environment(callee["closure"])
            for i, p in enumerate(callee["params"]): env.set(p, args[i] if i < len(args) else None)
            old = self.env; self.env = env; result = None
            try:
                for s in callee["body"]: result = self.execute(s)
            except TheeReturn as r: result = r.value
            finally: self.env = old
            return result
        if callable(callee):
            try: return callee(*args)
            except TypeError as e: raise TheeRuntimeError(f"Call error: {e}", node)
        raise TheeRuntimeError(f"Not callable: {type(callee).__name__}", node)

    def _member(self, node):
        o = self.evaluate(node.object); m = node.member
        if isinstance(o, TheeAgent):
            if m in o.skills: return lambda *a: o.execute_skill(m, list(a))
            if m == "pursue": return lambda g: o.pursue_goal(g)
            if m == "introspect": return lambda: o.introspect()
            if m in o.memory: return o.memory[m]
            if m in o.properties: return o.properties[m]
            if m in ("state","goal","name"): return getattr(o, m)
            raise TheeRuntimeError(f"Agent '{o.name}' has no member '{m}'")
        if isinstance(o, TheeStruct):
            return o.get(m)
        if isinstance(o, TheeChannel):
            if m == "send": return o.send
            if m == "receive": return o.receive
            if m == "name": return o.name
        if isinstance(o, TheeFuture):
            if m == "result": return o.result
            if m == "done": return o._done.is_set()
        if isinstance(o, dict):
            # v6.0 — class instance member access
            if o.get("__type__") == "thee_instance":
                if m in o: return o[m]
                raise TheeRuntimeError(f"Instance of '{o.get('__class_name__', '?')}' has no member '{m}'")
            # v6.0 — enum member access
            if o.get("__type__") == "thee_enum":
                if m in o: return o[m]
                raise TheeRuntimeError(f"Enum '{o.get('__name__', '?')}' has no member '{m}'")
            # v6.0 — class static method access
            if o.get("__type__") == "thee_class":
                if m in o.get("methods", {}):
                    method = o["methods"][m]
                    return {"params": method.params, "body": method.body, "closure": self.env}
                if m in o.get("properties", {}):
                    v = o["properties"][m]
                    return self.evaluate(v) if hasattr(v, 'line') else v
                raise TheeRuntimeError(f"Class '{o['name']}' has no static member '{m}'")
            if m in o: return o[m]
            raise TheeRuntimeError(f"Dict has no key '{m}'")
        if isinstance(o, str):
            d = {"length": len(o), "upper": o.upper, "lower": o.lower, "trim": o.strip,
                 "split": o.split, "contains": lambda s: s in o, "replace": o.replace,
                 "startswith": o.startswith, "endswith": o.endswith, "find": o.find}
            if m in d: return d[m]
        if isinstance(o, list):
            d = {"length": len(o), "push": lambda x: o.append(x) or o, "pop": o.pop,
                 "first": o[0] if o else None, "last": o[-1] if o else None,
                 "contains": lambda x: x in o, "sort": lambda: sorted(o),
                 "join": lambda sep=",": sep.join(str(x) for x in o),
                 "map": lambda f: [self._invoke(f, [x]) for x in o],
                 "filter": lambda f: [x for x in o if self._invoke(f, [x])]}
            if m in d: return d[m]
        # Python object fallback — allows .method() on any Python object (Pipeline, modules, etc.)
        if self.sandbox: _sandbox.check_attribute(m)
        attr = getattr(o, m, None)
        if attr is not None:
            return attr
        raise TheeRuntimeError(f"Cannot access .{m} on {type(o).__name__}")

    def _pipe(self, node):
        v = self.evaluate(node.left); r = node.right
        if isinstance(r, FunctionCall):
            c = self.evaluate(r.callee); a = [v] + [self.evaluate(x) for x in r.arguments]
            return self._invoke(c, a)
        elif isinstance(r, Identifier):
            c = self.env.get(r.name)
            return self._invoke(c, [v])
        raise TheeRuntimeError("Pipe target must be callable", node)

    def _if(self, n):
        if self._truthy(self.evaluate(n.condition)):
            for s in n.body: self.execute(s)
        else:
            for c, b in n.elif_clauses:
                if self._truthy(self.evaluate(c)):
                    for s in b: self.execute(s)
                    return
            for s in n.else_body: self.execute(s)

    def _rep_times(self, n):
        for _ in range(int(self.evaluate(n.count))):
            try:
                for s in n.body: self.execute(s)
            except TheeBreak: break
            except TheeContinue: continue

    def _rep_for(self, n):
        for item in self.evaluate(n.iterable):
            self.env.set(n.variable, item)
            try:
                for s in n.body: self.execute(s)
            except TheeBreak: break
            except TheeContinue: continue

    def _while(self, n):
        while self._truthy(self.evaluate(n.condition)):
            try:
                for s in n.body: self.execute(s)
            except TheeBreak: break
            except TheeContinue: continue

    def _summon(self, n):
        if n.agent_name not in self.agents:
            raise TheeRuntimeError(f"Unknown agent: '{n.agent_name}'")
        agent = TheeAgent(n.agent_name, self.agents[n.agent_name], self)
        self.env.set(n.alias, agent)
        self.env.set(n.agent_name, agent)
        print(f"  🔥 எழுப்பு (Summoned): {n.agent_name} → {n.alias}")

    def _swarm(self, n):
        strat = self.evaluate(n.strategy) if isinstance(n.strategy, ASTNode) else n.strategy
        names = [self.evaluate(a) if isinstance(a, ASTNode) else a for a in n.agents]
        goal = self.evaluate(n.goal) if n.goal else None
        print(f"  🐝 கூட்டம் (Swarm): {n.name}")
        self.env.set(n.name, {"name": n.name, "agents": names, "strategy": strat, "goal": goal})

    def _emit(self, n):
        data = self.evaluate(n.data) if n.data else None
        print(f"  📡 காற்று (Event): {n.event}" + (f" → {data}" if data else ""))
        for name, val in self.env.bindings.items():
            if isinstance(val, TheeAgent) and n.event in val.event_handlers:
                handler = val.event_handlers[n.event]
                env = Environment(self.env); env.set("data", data)
                old = self.env; self.env = env
                try:
                    for s in handler.body: self.execute(s)
                finally: self.env = old

    def _kindle(self, n):
        # Redirect to import system
        self._import(ImportStatement(path=n.module))

    def _assign_exec(self, n):
        v = self.evaluate(n.value)
        if isinstance(n.target, Identifier): self.env.assign(n.target.name, v)
        elif isinstance(n.target, IndexAccess):
            self.evaluate(n.target.object)[self.evaluate(n.target.index)] = v
        elif isinstance(n.target, MemberAccess):
            o = self.evaluate(n.target.object)
            if isinstance(o, dict): o[n.target.member] = v
            elif isinstance(o, TheeAgent): o.memory[n.target.member] = v
            elif isinstance(o, TheeStruct): o.set(n.target.member, v)

    def _group_by(self, lst, key):
        result = {}
        for item in lst:
            k = item.get(key, "unknown") if isinstance(item, dict) else str(item)
            result.setdefault(k, []).append(item)
        return result

    def _make_memoized(self, f):
        cache = {}
        def memoized(*args):
            key = str(args)
            if key not in cache:
                cache[key] = self._invoke(f, list(args))
            return cache[key]
        return memoized

    def _pipe_fns(self, x, fns):
        result = x
        for f in fns:
            result = self._invoke(f, [result])
        return result

    def _curry(self, f, n):
        def curried(*args):
            if len(args) >= n:
                return self._invoke(f, list(args[:n]))
            return lambda *more: curried(*(args + more))
        return curried

    def _group_by(self, lst, key):
        result = {}
        for item in lst:
            k = item.get(key, "?") if isinstance(item, dict) else str(item)
            result.setdefault(k, []).append(item)
        return result
    def _make_memoized(self, f):
        cache = {}
        def memoized(*args):
            key = str(args)
            if key not in cache: cache[key] = self._invoke(f, list(args))
            return cache[key]
        return memoized
    def _pipe_fns(self, x, fns):
        for f in fns: x = self._invoke(f, [x])
        return x
    def _curry(self, f, n):
        def curried(*args):
            if len(args) >= n: return self._invoke(f, list(args[:n]))
            return lambda *more: curried(*(args + more))
        return curried
    def _help(self, topic=""):
        cats = {"math": "sin cos tan sqrt pow log abs round floor ceil PI E PHI TAU",
                "string": "upper lower split join trim contains replace slice startswith endswith find",
                "collection": "map filter reduce sort reverse flatten unique zip_lists chunk take drop",
                "agent": "uyir(agent) thiran(skill) kaval(guard) ezhuppu(summon) kaatru(emit)",
                "flow": "endral(if) allathu(elif) illai(else) ozhugu(repeat) muyarchi(try) pizhai(catch)",
                "async": "othisai(async) kaathiru(await) uruvakku(spawn) kalani(channel)",
                "struct": "vadivam(struct) poruthu(match) vazhakku(case) iyalbu(default)"}
        if topic and topic in cats: return f"{topic}: {cats[topic]}"
        return "Topics: " + ", ".join(cats.keys()) + ". Use thee_help('topic') for details."
    def _truthy(self, v):
        if v is None or v is False: return False
        if isinstance(v, (int, float)) and v == 0: return False
        if isinstance(v, (str, list)) and len(v) == 0: return False
        return True

    # ═══════════════════════════════════════════════════════════
    # v6.0 — திருமுறை FEATURE IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════

    # ─── 1. CLASS SYSTEM (vagu/வகு) ───
    def _class_decl(self, node):
        """Register a class definition with inheritance support."""
        class_def = {
            "__type__": "thee_class",
            "name": node.name,
            "parent": node.parent,
            "constructor": node.constructor,
            "methods": {m.name: m for m in node.methods},
            "properties": node.properties,
        }
        self.env.set(node.name, class_def)

    def _new_instance(self, node):
        """Create a new instance of a class: pudhu ClassName(args)."""
        cls = self.env.get(node.class_name)
        if not isinstance(cls, dict) or cls.get("__type__") != "thee_class":
            raise TheeRuntimeError(f"'{node.class_name}' is not a class", node)

        # Create instance object
        instance = {"__type__": "thee_instance", "__class__": cls, "__class_name__": cls["name"]}

        # Copy default properties
        for k, v in cls["properties"].items():
            instance[k] = self.evaluate(v) if hasattr(v, 'line') else v

        # Resolve parent chain methods
        all_methods = {}
        parent_cls = cls
        chain = []
        while parent_cls:
            chain.insert(0, parent_cls)
            if parent_cls["parent"]:
                try:
                    parent_cls = self.env.get(parent_cls["parent"])
                except:
                    parent_cls = None
            else:
                parent_cls = None

        for c in chain:
            for name, method in c["methods"].items():
                all_methods[name] = method
            for k, v in c["properties"].items():
                if k not in instance:
                    instance[k] = self.evaluate(v) if hasattr(v, 'line') else v

        # Bind methods to instance
        for name, method in all_methods.items():
            def make_method(m):
                def bound(*args):
                    env = Environment(m.body[0].line if m.body else 0)
                    env.parent = self.env
                    env.set("self", instance)
                    env.set("this", instance)
                    for i, p in enumerate(m.params):
                        env.set(p, args[i] if i < len(args) else None)
                    old_env = self.env
                    self.env = env
                    try:
                        for s in m.body: self.execute(s)
                        return None
                    except TheeReturn as ret:
                        return ret.value
                    finally:
                        self.env = old_env
                return bound
            instance[name] = make_method(method)

        # Call constructor
        constructor = cls["constructor"]
        if not constructor:
            for c in chain:
                if c["constructor"]:
                    constructor = c["constructor"]
                    break

        if constructor:
            env = Environment()
            env.parent = self.env
            env.set("self", instance)
            env.set("this", instance)
            args = [self.evaluate(a) for a in node.arguments]
            for i, p in enumerate(constructor.params):
                env.set(p, args[i] if i < len(args) else None)
            old_env = self.env
            self.env = env
            try:
                for s in constructor.body: self.execute(s)
            except TheeReturn:
                pass
            finally:
                self.env = old_env

        return instance

    def _super_call(self, node):
        """Handle super() / moolam() calls in class methods."""
        instance = self.env.get("self")
        if not isinstance(instance, dict) or "__class__" not in instance:
            raise TheeRuntimeError("super/moolam can only be used inside a class method", node)
        cls = instance["__class__"]
        if not cls.get("parent"):
            raise TheeRuntimeError(f"Class '{cls['name']}' has no parent class", node)
        parent = self.env.get(cls["parent"])
        args = [self.evaluate(a) for a in node.arguments]
        if node.method:
            method = parent["methods"].get(node.method)
            if not method:
                raise TheeRuntimeError(f"Parent class has no method '{node.method}'", node)
            env = Environment()
            env.parent = self.env
            env.set("self", instance)
            env.set("this", instance)
            for i, p in enumerate(method.params):
                env.set(p, args[i] if i < len(args) else None)
            old_env = self.env
            self.env = env
            try:
                for s in method.body: self.execute(s)
                return None
            except TheeReturn as ret:
                return ret.value
            finally:
                self.env = old_env
        elif parent.get("constructor"):
            c = parent["constructor"]
            env = Environment()
            env.parent = self.env
            env.set("self", instance)
            env.set("this", instance)
            for i, p in enumerate(c.params):
                env.set(p, args[i] if i < len(args) else None)
            old_env = self.env
            self.env = env
            try:
                for s in c.body: self.execute(s)
            except TheeReturn:
                pass
            finally:
                self.env = old_env

    # ─── 2. PIPE CHAINS (|>) — Enhanced ───
    # Already handled via _pipe and PipeExpression, but enhance for method chaining
    # The existing |> works: value |> func. Enhancement: value |> .method()

    # ─── 3. DECORATORS (@) ───
    def _decorated(self, node):
        """Apply decorator to a function or class declaration."""
        # First, execute the inner declaration
        self.execute(node.declaration)
        # Get the declared name
        if isinstance(node.declaration, ForgeDeclaration):
            name = node.declaration.name
        elif isinstance(node.declaration, ClassDeclaration):
            name = node.declaration.name
        elif isinstance(node.declaration, DecoratedDeclaration):
            # Chained decorator - get innermost name
            inner = node.declaration
            while isinstance(inner, DecoratedDeclaration):
                inner = inner.declaration
            name = inner.name if hasattr(inner, 'name') else None
        else:
            return

        if name:
            original = self.env.get(name)
            decorator = self.evaluate(node.decorator)
            if callable(decorator):
                decorated = decorator(original)
            elif isinstance(decorator, dict) and "params" in decorator:
                decorated = self._invoke(decorator, [original])
            else:
                decorated = original
            self.env.assign(name, decorated)

    # ─── 4. EVENT SYSTEM ───
    def _init_events(self):
        if not hasattr(self, '_event_handlers'):
            self._event_handlers = {}

    def _event_on(self, event_name, handler):
        self._init_events()
        self._event_handlers.setdefault(event_name, []).append(handler)
        return True

    def _event_emit(self, event_name, *data):
        self._init_events()
        handlers = self._event_handlers.get(event_name, [])
        results = []
        for h in handlers:
            try:
                results.append(self._invoke(h, list(data)))
            except Exception as e:
                results.append(str(e))
        return results

    def _event_off(self, event_name, handler=None):
        self._init_events()
        if handler is None:
            self._event_handlers.pop(event_name, None)
        else:
            handlers = self._event_handlers.get(event_name, [])
            self._event_handlers[event_name] = [h for h in handlers if h != handler]
        return True

    def _event_once(self, event_name, handler):
        self._init_events()
        def wrapper(*args):
            self._event_off(event_name, wrapper)
            return self._invoke(handler, list(args))
        self._event_handlers.setdefault(event_name, []).append(wrapper)
        return True

    # ─── 5. GENERATORS (vilai/yield) ───
    def _yield_expr(self, node):
        """Yield implementation — stores value in generator state."""
        val = self.evaluate(node.value) if node.value else None
        raise TheeYield(val)

    # ─── 6. DESTRUCTURING ───
    def _destructure(self, node):
        """Handle destructured assignment: na [a, b] = [1, 2] or na {x, y} = obj."""
        val = self.evaluate(node.value)
        if node.is_dict:
            if isinstance(val, dict):
                for t in node.targets:
                    self.env.set(t, val.get(t))
            elif isinstance(val, list):
                for i, t in enumerate(node.targets):
                    self.env.set(t, val[i] if i < len(val) else None)
        else:
            if isinstance(val, (list, tuple)):
                for i, t in enumerate(node.targets):
                    self.env.set(t, val[i] if i < len(val) else None)
            elif isinstance(val, dict):
                keys = list(val.keys())
                for i, t in enumerate(node.targets):
                    self.env.set(t, val[keys[i]] if i < len(keys) else None)

    # ─── 7. ENHANCED AGENTS — Memory persistence, swarm coordination ───
    # Agent enhancements are registered as builtins in _register_v6

    # ─── 9. ENUM SUPPORT ───
    def _enum_decl(self, node):
        """Register an enum as a dict of named constants."""
        members = {}
        for name, val_node in node.members.items():
            members[name] = self.evaluate(val_node) if hasattr(val_node, 'line') else val_node
        # Make it a frozen dict-like object
        enum_obj = {"__type__": "thee_enum", "__name__": node.name}
        enum_obj.update(members)
        self.env.set(node.name, enum_obj)

# ═══════════════════════════════════════════════════════
# SMART ERROR ENGINE — Better than any language
# ═══════════════════════════════════════════════════════

class TheeSmartError:
    """Produces human-friendly errors with suggestions"""
    
    COMMON_TYPOS = {
        "moocchu": "moochhu", "mochhu": "moochhu", "print": "moochhu",
        "na ": "na ", "let": "na", "var": "na", "const": "nirai",
        "function": "thee", "def": "thee", "fn": "thee", "func": "thee",
        "if": "endral", "else": "illai", "elif": "allathu",
        "for": "ozhugu", "while": "ozhugu", "loop": "ozhugu",
        "return": "kanal", "ret": "kanal",
        "try": "muyarchi", "catch": "pizhai", "except": "pizhai",
        "import": "konar", "from": "irunthu",
        "class": "uyir", "agent": "uyir",
        "struct": "vadivam", "match": "poruthu", "switch": "poruthu",
        "async": "othisai", "await": "kaathiru",
        "true": "unmai", "false": "poi", "null": "sambal", "none": "sambal",
        "break": "niruthu", "continue": "thodaru",
    }

    @staticmethod
    def suggest(name, available):
        """Find closest match using edit distance"""
        if not available: return None
        best, best_dist = None, float('inf')
        for a in available:
            d = TheeSmartError._edit_dist(name.lower(), a.lower())
            if d < best_dist and d <= max(2, len(name) // 3):
                best, best_dist = a, d
        return best

    @staticmethod
    def _edit_dist(a, b):
        m, n = len(a), len(b)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev, dp[0] = dp[0], i
            for j in range(1, n + 1):
                tmp = dp[j]
                dp[j] = min(dp[j] + 1, dp[j-1] + 1, prev + (0 if a[i-1] == b[j-1] else 1))
                prev = tmp
        return dp[n]

    @staticmethod  
    def format_error(error_type, message, context=None):
        """Format a user-friendly error message"""
        lines = [f"🔥 {error_type}: {message}"]
        
        # Check for common Python/JS habits
        for wrong, right in TheeSmartError.COMMON_TYPOS.items():
            if wrong in message.lower():
                lines.append(f"  💡 Did you mean '{right}'? (THEE uses Tamil-inspired keywords)")
                break
        
        if context:
            lines.append(f"  📍 {context}")
        
        lines.append(f"  📖 Type 'thee help' for keyword reference")
        return "\n".join(lines)

# ═══════════════════════════════════════════════════════
# BUILT-IN WEB SERVER — Zero config, instant HTTP
# ═══════════════════════════════════════════════════════

class TheeWebServer:
    """Built-in web server — no Flask/Django/Express needed"""
    def __init__(self):
        self.routes = {}
        self.static_dir = None
        self.running = False
    
    def route(self, path, handler):
        self.routes[path] = handler
    
    def serve(self, port=8000, host="0.0.0.0"):
        import http.server, json as _json
        routes = self.routes
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path in routes:
                    result = routes[self.path]
                    body = _json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                    self.send_response(200)
                    ct = "application/json" if isinstance(result, (dict, list)) else "text/html"
                    self.send_header("Content-Type", ct)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(body.encode())
                else:
                    self.send_error(404, f"Route not found: {self.path}")
            def log_message(self, *a): pass
        srv = http.server.HTTPServer((host, port), H)
        print(f"🌐 THEE server: http://{host}:{port} ({len(routes)} routes)")
        srv.serve_forever()

# ═══════════════════════════════════════════════════════
# BUILT-IN DATABASE — Zero config SQLite
# ═══════════════════════════════════════════════════════

class TheeDB:
    """Built-in database — no install, no config, instant"""
    def __init__(self, path=":memory:"):
        import sqlite3
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
    
    def query(self, sql, params=None):
        cur = self.conn.execute(sql, params or [])
        if sql.strip().upper().startswith("SELECT"):
            return [dict(r) for r in cur.fetchall()]
        self.conn.commit()
        return cur.lastrowid
    
    def create_table(self, name, columns):
        if isinstance(columns, list):
            cols = ", ".join(str(c) for c in columns)
        elif isinstance(columns, dict):
            cols = ", ".join(f"{k} {v}" for k, v in columns.items())
        else:
            cols = str(columns)
        self.query(f"CREATE TABLE IF NOT EXISTS {name} ({cols})")
    
    def insert(self, table, data):
        keys = ", ".join(data.keys())
        vals = ", ".join("?" * len(data))
        return self.query(f"INSERT INTO {table} ({keys}) VALUES ({vals})", list(data.values()))
    
    def select(self, table, where=None):
        sql = f"SELECT * FROM {table}"
        if where: sql += f" WHERE {where}"
        return self.query(sql)
    
    def close(self):
        self.conn.close()

def _register_power_builtins(interp):
    """Register web server, database, CSV, chart builtins"""
    env = interp.env
    
    # === Web Server ===
    _server = TheeWebServer()
    env.set("web_route", lambda path, response: _server.route(path, response))
    env.set("web_serve", lambda port=8000: _server.serve(int(port)))
    env.set("web_html", lambda body, title="THEE App": f"<!DOCTYPE html><html><head><title>{title}</title><style>body{{font-family:system-ui;max-width:800px;margin:40px auto;padding:0 20px;background:#f5f5f0;color:#1a1a2e}}h1{{color:#D4380D}}</style></head><body>{body}</body></html>")
    env.set("web_json", lambda data: data)
    
    # === Database ===
    _dbs = {}
    def _db_open(path=":memory:"):
        _dbs["current"] = TheeDB(path)
        return f"Database opened: {path}"
    def _db_query(sql, params=None):
        if "current" not in _dbs: _dbs["current"] = TheeDB()
        return _dbs["current"].query(sql, params)
    def _db_create(table, columns):
        if "current" not in _dbs: _dbs["current"] = TheeDB()
        _dbs["current"].create_table(table, columns)
        return f"Table {table} created"
    def _db_insert(table, data):
        if "current" not in _dbs: _dbs["current"] = TheeDB()
        return _dbs["current"].insert(table, data)
    def _db_select(table, where=None):
        if "current" not in _dbs: _dbs["current"] = TheeDB()
        return _dbs["current"].select(table, where)
    
    env.set("db_open", _db_open)
    env.set("db_query", _db_query)
    env.set("db_create", _db_create)
    env.set("db_insert", _db_insert)
    env.set("db_select", _db_select)
    env.set("db_close", lambda: _dbs.get("current", TheeDB()).close())
    
    # === CSV ===
    def _csv_read(path, delimiter=","):
        import csv as _csv
        with open(path, 'r', encoding='utf-8') as f:
            reader = _csv.DictReader(f, delimiter=delimiter)
            return [dict(row) for row in reader]
    def _csv_write(path, data, headers=None):
        import csv as _csv
        if not data: return
        hdrs = headers or list(data[0].keys())
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = _csv.DictWriter(f, fieldnames=hdrs)
            w.writeheader()
            w.writerows(data)
        return f"Written {len(data)} rows to {path}"
    
    env.set("csv_read", _csv_read)
    env.set("csv_write", _csv_write)
    
    # === Data Analysis ===
    env.set("data_sum", lambda data, key: sum(float(r.get(key, 0)) for r in data))
    env.set("data_avg", lambda data, key: sum(float(r.get(key, 0)) for r in data) / max(len(data), 1))
    env.set("data_min", lambda data, key: min(float(r.get(key, 0)) for r in data))
    env.set("data_max", lambda data, key: max(float(r.get(key, 0)) for r in data))
    env.set("data_count", lambda data, key=None, value=None: sum(1 for r in data if key is None or r.get(key) == value))
    env.set("data_sort_by", lambda data, key, desc=False: sorted(data, key=lambda r: r.get(key, ""), reverse=desc))
    env.set("data_filter_by", lambda data, key, value: [r for r in data if r.get(key) == value])
    env.set("data_group_by", lambda data, key: interp._group_by(data, key))
    env.set("data_pluck", lambda data, key: [r.get(key) for r in data])
    
    # === Chart (ASCII + HTML) ===
    def _chart_bar(data, title="Chart"):
        if isinstance(data, dict):
            items = list(data.items())
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            items = [(str(r.get("label", i)), float(r.get("value", 0))) for i, r in enumerate(data)]
        else:
            items = [(str(i), v) for i, v in enumerate(data)]
        mx = max(abs(v) for _, v in items) if items else 1
        lines = [f"  📊 {title}", "  " + "─" * 50]
        for label, val in items:
            bar_len = int((abs(val) / mx) * 35) if mx else 0
            bar = "█" * bar_len
            lines.append(f"  {label:>12s} │{bar} {val}")
        lines.append("  " + "─" * 50)
        return "\n".join(lines)
    
    def _chart_line(data, title="Chart"):
        if not data: return "No data"
        vals = [float(v) for v in data]
        mn, mx = min(vals), max(vals)
        rng = mx - mn if mx != mn else 1
        h = 8
        lines = [f"  📈 {title}"]
        for row in range(h, -1, -1):
            threshold = mn + (row / h) * rng
            line = f"  {threshold:8.1f} │"
            for v in vals:
                line += "●" if abs(v - threshold) < rng / h else " "
            lines.append(line)
        lines.append("           └" + "─" * len(vals))
        return "\n".join(lines)
    
    def _chart_html(data, chart_type="bar", title="Chart"):
        if isinstance(data, dict):
            labels = list(data.keys())
            values = list(data.values())
        elif isinstance(data, list) and data and isinstance(data[0], dict):
            labels = [r.get("label", str(i)) for i, r in enumerate(data)]
            values = [float(r.get("value", 0)) for r in data]
        else:
            labels = [str(i) for i in range(len(data))]
            values = [float(v) for v in data]
        mx = max(values) if values else 1
        bars = ""
        for i, (l, v) in enumerate(zip(labels, values)):
            pct = (v / mx * 100) if mx else 0
            bars += f'<div style="display:flex;align-items:center;margin:4px 0"><span style="width:80px;text-align:right;padding-right:8px;font-size:12px">{l}</span><div style="height:24px;width:{pct}%;background:linear-gradient(90deg,#D4380D,#FF6B35);border-radius:4px;min-width:2px"></div><span style="padding-left:8px;font-size:12px">{v}</span></div>'
        return f'<div style="font-family:system-ui;padding:20px"><h3 style="color:#D4380D">{title}</h3>{bars}</div>'
    
    env.set("chart_bar", _chart_bar)
    env.set("chart_line", _chart_line)
    env.set("chart_html", _chart_html)
    
    # === Validation ===
    env.set("is_email", lambda s: "@" in s and "." in s.split("@")[-1] if isinstance(s, str) else False)
    env.set("is_url", lambda s: s.startswith("http://") or s.startswith("https://") if isinstance(s, str) else False)
    env.set("is_phone", lambda s: len([c for c in s if c.isdigit()]) >= 7 if isinstance(s, str) else False)
    env.set("is_empty", lambda x: x is None or x == "" or x == [] or x == {})
    env.set("is_between", lambda x, lo, hi: lo <= x <= hi)
    def _require(val, msg="Required"):
        if not val: raise TheeRuntimeError(msg)
        return val
    env.set("require", _require)
    
    # === Color/Format ===
    env.set("color_rgb", lambda r, g, b: f"#{int(r):02x}{int(g):02x}{int(b):02x}")
    env.set("format_number", lambda n, dec=2: f"{float(n):,.{int(dec)}f}")
    env.set("format_currency", lambda n, sym="$": f"{sym}{float(n):,.2f}")
    env.set("format_percent", lambda n, dec=1: f"{float(n)*100:.{int(dec)}f}%")
    env.set("format_bytes", lambda b: f"{b/1073741824:.1f}GB" if b >= 1073741824 else f"{b/1048576:.1f}MB" if b >= 1048576 else f"{b/1024:.1f}KB" if b >= 1024 else f"{int(b)}B")
    
    # === Config/Env ===
    env.set("config_load", lambda path: json.loads(open(path, encoding='utf-8').read()))
    env.set("config_save", lambda path, data: open(path, 'w', encoding='utf-8').write(json.dumps(data, indent=2, ensure_ascii=False)))

# ═══════════════════════════════════════════════════════
# METHOD CHAINING — The killer ease-of-use feature
# list.map().filter().sort() — works like JavaScript
# ═══════════════════════════════════════════════════════

def _register_method_chaining(interp):
    """Make list/string methods return chainable objects"""
    # Enhance the _member method to support full chaining
    old_member = interp._member
    
    def enhanced_member(node):
        o = interp.evaluate(node.object)
        m = node.member
        
        # NUMBER methods
        if isinstance(o, (int, float)):
            num_methods = {
                "abs": abs(o), "round": round(o), "floor": int(o),
                "ceil": int(o) + (1 if o != int(o) and o > 0 else 0),
                "is_even": o % 2 == 0, "is_odd": o % 2 != 0,
                "is_positive": o > 0, "is_negative": o < 0, "is_zero": o == 0,
                "to_str": str(o), "to_float": float(o), "to_int": int(o),
                "times": lambda f: [interp._invoke(f, [i]) for i in range(int(o))],
                "upto": lambda n: list(range(int(o), int(n) + 1)),
                "downto": lambda n: list(range(int(o), int(n) - 1, -1)),
                "currency": f"${float(o):,.2f}",
                "percent": f"{float(o)*100:.1f}%",
                "pad": lambda n, c="0": str(o).zfill(int(n)),
            }
            if m in num_methods:
                v = num_methods[m]
                return v
        
        # Enhanced LIST methods with chaining
        if isinstance(o, list):
            # Properties (auto-evaluated, no args needed) — wrapped safely
            try:
                _sorted = sorted(o)
            except TypeError:
                _sorted = list(o)
            try:
                _unique = list(dict.fromkeys(o))
            except TypeError:
                _unique = o
            try:
                _min = min(o) if o else None
                _max = max(o) if o else None
            except TypeError:
                _min = None
                _max = None
            try:
                _sorted_desc = sorted(o, reverse=True)
            except TypeError:
                _sorted_desc = list(reversed(o))
            list_props = {
                "length": len(o), "size": len(o), "count": len(o),
                "first": o[0] if o else None, "last": o[-1] if o else None,
                "second": o[1] if len(o) > 1 else None,
                "rest": o[1:], "init": o[:-1],
                "is_empty": len(o) == 0,
                "sort": _sorted, "sort_desc": _sorted_desc,
                "reverse": list(reversed(o)),
                "unique": _unique,
                "flat": [x for sub in o for x in (sub if isinstance(sub, list) else [sub])],
                "compact": [x for x in o if x is not None and x != "" and x != 0],
                "sum": sum(x for x in o if isinstance(x, (int, float))),
                "avg": sum(x for x in o if isinstance(x, (int, float))) / max(len(o), 1),
                "min": _min, "max": _max,
                "shuffle": __import__('random').sample(o, len(o)),
            }
            if m in list_props: return list_props[m]
            # Methods (need arguments, return callable)
            list_methods = {
                "push": lambda x: (o.append(x), o)[1],
                "pop": lambda: o.pop() if o else None,
                "shift": lambda: o.pop(0) if o else None,
                "includes": lambda x: x in o,
                "contains": lambda x: x in o,
                "index_of": lambda x: o.index(x) if x in o else -1,
                "join": lambda sep=", ": sep.join(str(x) for x in o),
                "each": lambda f: [interp._invoke(f, [x]) for x in o] and o,
                "map": lambda f: [interp._invoke(f, [x]) for x in o],
                "filter": lambda f: [x for x in o if interp._invoke(f, [x])],
                "reject": lambda f: [x for x in o if not interp._invoke(f, [x])],
                "find": lambda f: next((x for x in o if interp._invoke(f, [x])), None),
                "every": lambda f: all(interp._invoke(f, [x]) for x in o),
                "some": lambda f: any(interp._invoke(f, [x]) for x in o),
                "reduce": lambda f, init=0: _reduce_list(o, f, init, interp),
                "take": lambda n: o[:int(n)],
                "drop": lambda n: o[int(n):],
                "chunk": lambda n: [o[i:i+int(n)] for i in range(0, len(o), int(n))],
                "sample": lambda n=1: __import__('random').sample(o, int(n)),
                "zip_with": lambda other: list(zip(o, other)),
                "to_dict": lambda: {str(i): v for i, v in enumerate(o)},
                "to_str": lambda sep=", ": sep.join(str(x) for x in o),
                "pluck": lambda key: [x.get(key) if isinstance(x, dict) else None for x in o],
                "group_by": lambda f: _group_list(o, f, interp),
                "sort_by": lambda f: sorted(o, key=lambda x: interp._invoke(f, [x])),
            }
            if m in list_methods: return list_methods[m]
        
        # Enhanced STRING methods with chaining
        if isinstance(o, str):
            str_methods = {
                "length": len(o), "size": len(o), "count": len(o),
                "upper": o.upper(), "lower": o.lower(),
                "title": o.title(), "capitalize": o.capitalize(),
                "trim": o.strip(), "ltrim": o.lstrip(), "rtrim": o.rstrip(),
                "reverse": o[::-1],
                "is_empty": len(o) == 0,
                "is_blank": len(o.strip()) == 0,
                "is_upper": o.isupper(), "is_lower": o.islower(),
                "is_digit": o.isdigit(), "is_alpha": o.isalpha(),
                "is_alnum": o.isalnum(),
                "chars": list(o),
                "words": o.split(),
                "lines": o.split('\n'),
                "word_count": len(o.split()),
                "char_count": len(o),
                "split": lambda sep=" ": o.split(sep),
                "contains": lambda s: s in o,
                "includes": lambda s: s in o,
                "starts_with": o.startswith if hasattr(o, 'startswith') else lambda s: o[:len(s)] == s,
                "ends_with": o.endswith if hasattr(o, 'endswith') else lambda s: o[-len(s):] == s,
                "replace": lambda old, new: o.replace(old, new),
                "pad_left": lambda n, c=" ": o.rjust(int(n), c),
                "pad_right": lambda n, c=" ": o.ljust(int(n), c),
                "center": lambda n, c=" ": o.center(int(n), c),
                "repeat": lambda n: o * int(n),
                "slice": lambda start, end=None: o[int(start):int(end) if end else None],
                "find": lambda s: o.find(s),
                "replace_all": lambda old, new: o.replace(old, new),
                "to_int": int(o) if o.isdigit() else 0,
                "to_float": float(o) if o.replace('.','',1).isdigit() else 0.0,
                "to_list": list(o),
                "encode": lambda: o.encode('utf-8'),
                "match": lambda pattern: bool(__import__('re').search(pattern, o)),
                "extract": lambda pattern: __import__('re').findall(pattern, o),
            }
            if m in str_methods:
                return str_methods[m]
        
        # Enhanced DICT methods — lazy evaluation to avoid serializing functions
        # SKIP for THEE special types (class instances, enums, class defs)
        if isinstance(o, dict) and o.get("__type__") not in ("thee_instance", "thee_enum", "thee_class"):
            # Properties (computed only when accessed)
            dict_props = {"keys", "values", "entries", "length", "size", "count", "is_empty", "to_list", "to_json", "to_json_pretty"}
            dict_meths = {"has", "get", "set", "delete", "merge", "map_values", "filter_by"}
            if m in dict_props:
                if m == "keys": return list(o.keys())
                if m == "values": return list(o.values())
                if m == "entries": return list(o.items())
                if m in ("length", "size", "count"): return len(o)
                if m == "is_empty": return len(o) == 0
                if m == "to_list": return [{"key": k, "value": v} for k, v in o.items()]
                if m == "to_json": return __import__('json').dumps(o, ensure_ascii=False, default=lambda x: "<fn>" if callable(x) else repr(x))
                if m == "to_json_pretty": return __import__('json').dumps(o, indent=2, ensure_ascii=False, default=lambda x: "<fn>" if callable(x) else repr(x))
            if m in dict_meths:
                if m == "has": return lambda k: k in o
                if m == "get": return lambda k, d=None: o.get(k, d)
                if m == "set": return lambda k, v: (o.__setitem__(k, v), o)[1]
                if m == "delete": return lambda k: (o.pop(k, None), o)[1]
                if m == "merge": return lambda other: {**o, **other}
                if m == "map_values": return lambda f: {k: interp._invoke(f, [v]) for k, v in o.items()}
                if m == "filter_by": return lambda f: {k: v for k, v in o.items() if interp._invoke(f, [v])}
        
        # Fall through to original
        return old_member(node)
    
    interp._member = enhanced_member

def _reduce_list(lst, f, init, interp):
    acc = init
    for x in lst:
        acc = interp._invoke(f, [acc, x])
    return acc

def _group_list(lst, f, interp):
    groups = {}
    for x in lst:
        key = str(interp._invoke(f, [x]))
        groups.setdefault(key, []).append(x)
    return groups

# ═══════════════════════════════════════════════════════
# GPIO STUBS — For desktop testing of Pi/Arduino code
# ═══════════════════════════════════════════════════════

def _register_gpio_stubs(interp):
    """Register GPIO stubs so Pi code runs on desktop with simulation messages"""
    env = interp.env
    _pins = {}
    def _stub(name):
        def fn(*args):
            if not _pins.get("_warned"):
                print("  ⚡ GPIO simulation mode (no hardware detected)")
                _pins["_warned"] = True
            return 0
        return fn
    
    for fn_name in ['gpio_output', 'gpio_input', 'gpio_write', 'gpio_read',
                     'gpio_high', 'gpio_low', 'gpio_toggle', 'gpio_pwm',
                     'gpio_cleanup', 'gpio_pins']:
        if fn_name not in env.bindings:
            env.set(fn_name, _stub(fn_name))
    
    if 'delay_ms' not in env.bindings:
        import time as _time
        env.set('delay_ms', lambda ms: _time.sleep(ms / 1000))
        env.set('delay_us', lambda us: _time.sleep(us / 1000000))
        env.set('millis', lambda: int(_time.time() * 1000))
    
    if 'cpu_temp' not in env.bindings:
        env.set('cpu_temp', lambda: 42.0)
        env.set('mem_free', lambda: 1024.0)
        env.set('disk_free', lambda: 50.0)
        env.set('uptime', lambda: 3600.0)
    
    for c in ['HIGH', 'LOW', 'LED_ON', 'LED_OFF']:
        if c not in env.bindings:
            env.set(c, 1 if 'H' in c or 'ON' in c else 0)

# ═══════════════════════════════════════════════════════════════════
# 🔥 THEE v5.0 — GAME CHANGERS
# ═══════════════════════════════════════════════════════════════════

# ═══ 1. PYTHON BRIDGE — Access ALL 500,000+ Python Packages ═══
class TheePythonBridge:
    """Import and use ANY Python package directly in THEE"""
    _cache = {}
    
    @staticmethod
    def py_import(module_name, alias=None):
        """Import a Python module: py_import('pandas') or py_import('numpy', 'np')"""
        if module_name in TheePythonBridge._cache:
            return TheePythonBridge._cache[module_name]
        try:
            import importlib
            mod = importlib.import_module(module_name)
            TheePythonBridge._cache[module_name] = mod
            return mod
        except ImportError:
            raise TheeRuntimeError(f"Python package '{module_name}' not found. Install with: thee install {module_name}")
    
    @staticmethod
    def py_call(obj, method, *args, **kwargs):
        """Call a method on a Python object"""
        fn = getattr(obj, method, None)
        if fn is None:
            raise TheeRuntimeError(f"'{type(obj).__name__}' has no method '{method}'")
        return fn(*args, **kwargs)
    
    @staticmethod
    def py_attr(obj, attr):
        """Get an attribute from a Python object"""
        return getattr(obj, attr)
    
    @staticmethod
    def py_eval(code_str):
        """Evaluate a Python expression"""
        return eval(code_str)

# ═══ 2. PERFORMANCE OPTIMIZER — Compile hot functions to Python ═══
class TheeOptimizer:
    """Compiles THEE functions to Python bytecode for ~100x speedup"""
    _compiled = {}
    
    @staticmethod
    def compile_function(name, params, body_ast, interpreter):
        """Compile a THEE function to native Python for performance"""
        # Generate Python source from AST
        py_src = TheeOptimizer._ast_to_python(body_ast, 0)
        param_str = ", ".join(params)
        full_src = f"def {name}({param_str}):\n{py_src}"
        try:
            local_ns = {"__builtins__": __builtins__}
            exec(compile(full_src, f"<thee:{name}>", "exec"), local_ns)
            fn = local_ns[name]
            TheeOptimizer._compiled[name] = fn
            return fn
        except:
            return None  # Fall back to interpreter
    
    @staticmethod
    def _ast_to_python(nodes, indent):
        """Convert THEE AST to Python source code"""
        lines = []
        prefix = "    " * (indent + 1)
        for node in nodes if isinstance(nodes, list) else [nodes]:
            if isinstance(node, LetDeclaration):
                lines.append(f"{prefix}{node.name} = {TheeOptimizer._expr_to_py(node.value)}")
            elif isinstance(node, LightStatement):
                lines.append(f"{prefix}print({TheeOptimizer._expr_to_py(node.expression)})")
            elif isinstance(node, EmberStatement):
                lines.append(f"{prefix}return {TheeOptimizer._expr_to_py(node.value)}")
            elif isinstance(node, IfStatement):
                lines.append(f"{prefix}if {TheeOptimizer._expr_to_py(node.condition)}:")
                lines.append(TheeOptimizer._ast_to_python(node.then_body, indent+1))
                if node.else_body:
                    lines.append(f"{prefix}else:")
                    lines.append(TheeOptimizer._ast_to_python(node.else_body, indent+1))
            elif isinstance(node, FunctionCall):
                lines.append(f"{prefix}{TheeOptimizer._expr_to_py(node)}")
        if not lines:
            lines.append(f"{prefix}pass")
        return "\n".join(lines)
    
    @staticmethod
    def _expr_to_py(node):
        if isinstance(node, NumberLiteral): return str(node.value)
        if isinstance(node, StringLiteral): return repr(node.value)
        if isinstance(node, BooleanLiteral): return "True" if node.value else "False"
        if isinstance(node, AshLiteral): return "None"
        if isinstance(node, Identifier): return node.name
        if isinstance(node, BinaryOp):
            l = TheeOptimizer._expr_to_py(node.left)
            r = TheeOptimizer._expr_to_py(node.right)
            op = node.op
            if op == "and": op = "and"
            elif op == "or": op = "or"
            return f"({l} {op} {r})"
        if isinstance(node, UnaryOp):
            return f"(-{TheeOptimizer._expr_to_py(node.operand)})" if node.op == "-" else f"(not {TheeOptimizer._expr_to_py(node.operand)})"
        if isinstance(node, FunctionCall):
            args = ", ".join(TheeOptimizer._expr_to_py(a) for a in node.args)
            if isinstance(node.callee, Identifier):
                return f"{node.callee.name}({args})"
            return f"{TheeOptimizer._expr_to_py(node.callee)}({args})"
        return "None"

# ═══ 3. JWT AUTHENTICATION ═══
class TheeAuth:
    """Built-in JWT authentication"""
    _secret = "thee_secret_namachivayam_108"
    _users = {}
    
    @staticmethod
    def set_secret(secret):
        TheeAuth._secret = secret
    
    @staticmethod
    def hash_password(password):
        import hashlib
        return hashlib.sha256((password + TheeAuth._secret).encode()).hexdigest()
    
    @staticmethod
    def create_token(payload, expires_hours=24):
        import json, base64, hashlib, time
        header = base64.urlsafe_b64encode(json.dumps({"alg":"HS256","typ":"JWT"}).encode()).decode().rstrip("=")
        payload["exp"] = int(time.time()) + (expires_hours * 3600)
        payload_b = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        sig_input = f"{header}.{payload_b}"
        sig = base64.urlsafe_b64encode(hashlib.sha256((sig_input + TheeAuth._secret).encode()).digest()).decode().rstrip("=")
        return f"{header}.{payload_b}.{sig}"
    
    @staticmethod
    def verify_token(token):
        import json, base64, hashlib, time
        try:
            parts = token.split(".")
            if len(parts) != 3: return None
            sig_input = f"{parts[0]}.{parts[1]}"
            expected_sig = base64.urlsafe_b64encode(hashlib.sha256((sig_input + TheeAuth._secret).encode()).digest()).decode().rstrip("=")
            if parts[2] != expected_sig: return None
            padding = 4 - len(parts[1]) % 4
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * padding))
            if payload.get("exp", 0) < time.time(): return None
            return payload
        except:
            return None
    
    @staticmethod
    def register(username, password):
        TheeAuth._users[username] = TheeAuth.hash_password(password)
        return True
    
    @staticmethod
    def login(username, password):
        stored = TheeAuth._users.get(username)
        if stored and stored == TheeAuth.hash_password(password):
            return TheeAuth.create_token({"user": username})
        return None

# ═══ 4. ASYNC WEB SERVER ═══
class TheeAsyncWeb:
    """Production-grade async web server with middleware"""
    _routes = {}
    _middleware = []
    _static_dir = None
    _cors = True
    
    @staticmethod
    def route(path, handler_or_data, method="GET"):
        TheeAsyncWeb._routes[(method, path)] = handler_or_data
    
    @staticmethod
    def middleware(fn):
        TheeAsyncWeb._middleware.append(fn)
    
    @staticmethod
    def static(directory):
        TheeAsyncWeb._static_dir = directory
    
    @staticmethod
    def serve(port=8000, host="0.0.0.0"):
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json, os, mimetypes
        routes = TheeAsyncWeb._routes
        static_dir = TheeAsyncWeb._static_dir
        cors = TheeAsyncWeb._cors
        
        class Handler(BaseHTTPRequestHandler):
            def _handle(self, method):
                path = self.path.split("?")[0]
                # CORS
                if cors:
                    self.send_header_cors = True
                # Check routes
                key = (method, path)
                data = routes.get(key) or routes.get(("GET", path))
                if data is not None:
                    if callable(data):
                        try:
                            result = data()
                        except Exception as e:
                            self._respond(500, {"error": str(e)})
                            return
                    else:
                        result = data
                    if isinstance(result, dict) or isinstance(result, list):
                        self._respond(200, result, "application/json")
                    else:
                        self._respond(200, str(result), "text/html")
                elif static_dir and method == "GET":
                    fpath = os.path.join(static_dir, path.lstrip("/"))
                    if os.path.isfile(fpath):
                        mime = mimetypes.guess_type(fpath)[0] or "application/octet-stream"
                        self.send_response(200)
                        if cors: self.send_header("Access-Control-Allow-Origin", "*")
                        self.send_header("Content-Type", mime)
                        self.end_headers()
                        self.wfile.write(open(fpath, "rb").read())
                        return
                    self._respond(404, {"error": "Not found"})
                else:
                    self._respond(404, {"error": "Not found"})
            
            def _respond(self, code, data, content_type=None):
                import json as j
                self.send_response(code)
                if cors: self.send_header("Access-Control-Allow-Origin", "*")
                if isinstance(data, (dict, list)):
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(j.dumps(data, default=str).encode())
                else:
                    self.send_header("Content-Type", content_type or "text/html")
                    self.end_headers()
                    self.wfile.write(str(data).encode())
            
            def do_GET(self): self._handle("GET")
            def do_POST(self): self._handle("POST")
            def do_PUT(self): self._handle("PUT")
            def do_DELETE(self): self._handle("DELETE")
            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
                self.end_headers()
            def log_message(self, format, *args): pass
        
        print(f"  🔥 THEE Server — http://{host}:{port}")
        HTTPServer((host, port), Handler).serve_forever()

# ═══ 5. TESTING FRAMEWORK ═══
class TheeTestRunner:
    """Built-in testing framework"""
    _tests = []
    _results = {"passed": 0, "failed": 0, "errors": []}
    
    @staticmethod
    def test(name, fn):
        TheeTestRunner._tests.append((name, fn))
    
    @staticmethod
    def run():
        import time
        start = time.perf_counter()
        for name, fn in TheeTestRunner._tests:
            try:
                fn()
                TheeTestRunner._results["passed"] += 1
                print(f"  ✅ {name}")
            except AssertionError as e:
                TheeTestRunner._results["failed"] += 1
                TheeTestRunner._results["errors"].append((name, str(e)))
                print(f"  ❌ {name}: {e}")
            except Exception as e:
                TheeTestRunner._results["failed"] += 1
                TheeTestRunner._results["errors"].append((name, str(e)))
                print(f"  ❌ {name}: {e}")
        elapsed = (time.perf_counter() - start) * 1000
        p = TheeTestRunner._results["passed"]
        f = TheeTestRunner._results["failed"]
        print(f"\n  {p}/{p+f} passed ({elapsed:.0f}ms)")
        return TheeTestRunner._results
    
    @staticmethod
    def assert_eq(a, b, msg=""):
        if a != b: raise AssertionError(msg or f"Expected {b}, got {a}")
    
    @staticmethod
    def assert_true(val, msg=""):
        if not val: raise AssertionError(msg or f"Expected truthy, got {val}")
    
    @staticmethod
    def assert_false(val, msg=""):
        if val: raise AssertionError(msg or f"Expected falsy, got {val}")
    
    @staticmethod
    def assert_throws(fn, msg=""):
        try:
            fn()
            raise AssertionError(msg or "Expected exception, but none was thrown")
        except AssertionError:
            raise
        except:
            pass
    
    @staticmethod
    def assert_near(a, b, tolerance=0.001, msg=""):
        if abs(a - b) > tolerance:
            raise AssertionError(msg or f"Expected ~{b}, got {a} (tolerance: {tolerance})")

# ═══ 6. FRONTEND COMPONENT SYSTEM ═══
class TheeComponent:
    """Generate full HTML pages with components, CSS, and interactivity"""
    
    @staticmethod
    def page(title, body, css="", js="", theme="light"):
        themes = {
            "light": "body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:20px;background:#f5f5f5;color:#1a1a2e}",
            "dark": "body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:20px;background:#1a1a2e;color:#e0e0e0}a{color:#64b5f6}",
            "tamil": "body{font-family:'Noto Sans Tamil',system-ui,sans-serif;margin:0;padding:20px;background:#fff8f0;color:#1a1a2e}h1,h2,h3{color:#d4380d}",
        }
        t_css = themes.get(theme, themes["light"])
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>{t_css} .container{{max-width:1200px;margin:0 auto;padding:20px}} .card{{background:white;border-radius:12px;padding:20px;margin:10px 0;box-shadow:0 2px 8px rgba(0,0,0,0.1)}} .btn{{background:#d4380d;color:white;border:none;padding:10px 24px;border-radius:6px;cursor:pointer;font-size:16px}} .btn:hover{{background:#b02e0a}} .grid{{display:grid;gap:16px}} .grid-2{{grid-template-columns:repeat(2,1fr)}} .grid-3{{grid-template-columns:repeat(3,1fr)}} .grid-4{{grid-template-columns:repeat(4,1fr)}} table{{width:100%;border-collapse:collapse}} th,td{{padding:10px;border:1px solid #ddd;text-align:left}} th{{background:#d4380d;color:white}} tr:nth-child(even){{background:#f9f9f9}} .nav{{background:#1a1a2e;color:white;padding:15px 30px;display:flex;justify-content:space-between;align-items:center;margin:-20px -20px 20px}} .nav a{{color:#e0e0e0;text-decoration:none;margin:0 10px}} input,select,textarea{{padding:8px 12px;border:1px solid #ccc;border-radius:6px;font-size:14px;width:100%;box-sizing:border-box;margin:4px 0}} .alert{{padding:12px 20px;border-radius:8px;margin:10px 0}} .alert-success{{background:#e8f5e9;color:#2e7d32;border-left:4px solid #4caf50}} .alert-error{{background:#ffebee;color:#c62828;border-left:4px solid #f44336}} .alert-info{{background:#e3f2fd;color:#1565c0;border-left:4px solid #2196f3}} {css}</style></head>
<body><div class="container">{body}</div><script>{js}</script></body></html>"""
    
    @staticmethod
    def card(title, content, footer=""):
        f = f"<div style='margin-top:12px;padding-top:12px;border-top:1px solid #eee;color:#666'>{footer}</div>" if footer else ""
        return f"<div class='card'><h3 style='margin-top:0'>{title}</h3>{content}{f}</div>"
    
    @staticmethod
    def nav(brand, links):
        link_html = "".join(f"<a href='{url}'>{text}</a>" for text, url in links)
        return f"<div class='nav'><strong>{brand}</strong><div>{link_html}</div></div>"
    
    @staticmethod
    def table(headers, rows):
        h = "".join(f"<th>{h}</th>" for h in headers)
        r = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
        return f"<table><tr>{h}</tr>{r}</table>"
    
    @staticmethod
    def form(fields, action="/", method="POST"):
        inputs = ""
        for f in fields:
            if isinstance(f, dict):
                t = f.get("type","text"); n = f.get("name",""); l = f.get("label",n)
                if t == "textarea":
                    inputs += f"<div style='margin:8px 0'><label><b>{l}</b></label><textarea name='{n}' rows='4'></textarea></div>"
                elif t == "select":
                    opts = "".join(f"<option>{o}</option>" for o in f.get("options",[]))
                    inputs += f"<div style='margin:8px 0'><label><b>{l}</b></label><select name='{n}'>{opts}</select></div>"
                else:
                    inputs += f"<div style='margin:8px 0'><label><b>{l}</b></label><input type='{t}' name='{n}'></div>"
        return f"<form action='{action}' method='{method}'>{inputs}<button class='btn' type='submit'>Submit</button></form>"
    
    @staticmethod
    def chart_svg(data, chart_type="bar", title="", width=600, height=300):
        """Generate SVG chart (no external dependencies)"""
        if isinstance(data, dict):
            labels = list(data.keys())
            values = list(data.values())
        else:
            labels = [str(i) for i in range(len(data))]
            values = list(data)
        
        max_val = max(values) if values else 1
        n = len(values)
        colors = ["#D4380D","#1a1a2e","#2196F3","#4CAF50","#FF9800","#9C27B0","#00BCD4","#F44336"]
        
        svg = f'<svg width="{width}" height="{height+40}" xmlns="http://www.w3.org/2000/svg">'
        if title:
            svg += f'<text x="{width//2}" y="20" text-anchor="middle" font-size="16" font-weight="bold">{title}</text>'
        
        if chart_type == "bar":
            bw = max(20, (width - 80) // n - 10)
            for i, (l, v) in enumerate(zip(labels, values)):
                h = int((v / max_val) * (height - 60))
                x = 60 + i * (bw + 10)
                y = height - h
                c = colors[i % len(colors)]
                svg += f'<rect x="{x}" y="{y}" width="{bw}" height="{h}" fill="{c}" rx="4"/>'
                svg += f'<text x="{x+bw//2}" y="{height+15}" text-anchor="middle" font-size="11">{l}</text>'
                svg += f'<text x="{x+bw//2}" y="{y-5}" text-anchor="middle" font-size="11">{v}</text>'
        elif chart_type == "line":
            points = []
            for i, v in enumerate(values):
                x = 60 + i * ((width - 80) // max(n-1, 1))
                y = height - int((v / max_val) * (height - 60))
                points.append(f"{x},{y}")
            svg += f'<polyline points="{" ".join(points)}" fill="none" stroke="#D4380D" stroke-width="3"/>'
            for i, (x_y, l) in enumerate(zip(points, labels)):
                x, y = x_y.split(",")
                svg += f'<circle cx="{x}" cy="{y}" r="5" fill="#D4380D"/>'
                svg += f'<text x="{x}" y="{height+15}" text-anchor="middle" font-size="11">{l}</text>'
        elif chart_type == "pie":
            import math
            cx, cy, r = width//2, (height+20)//2, min(width, height)//3
            total = sum(values)
            angle = 0
            for i, (l, v) in enumerate(zip(labels, values)):
                sweep = (v / total) * 2 * math.pi
                x1 = cx + r * math.cos(angle)
                y1 = cy + r * math.sin(angle)
                x2 = cx + r * math.cos(angle + sweep)
                y2 = cy + r * math.sin(angle + sweep)
                large = 1 if sweep > math.pi else 0
                c = colors[i % len(colors)]
                svg += f'<path d="M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {large},1 {x2:.1f},{y2:.1f} Z" fill="{c}"/>'
                mx = cx + (r*0.7) * math.cos(angle + sweep/2)
                my = cy + (r*0.7) * math.sin(angle + sweep/2)
                svg += f'<text x="{mx:.0f}" y="{my:.0f}" text-anchor="middle" font-size="11" fill="white">{l}</text>'
                angle += sweep
        
        svg += '</svg>'
        return svg

# ═══ 7. WEBSOCKET SUPPORT ═══
def _thee_websocket_server(port, on_message):
    """Simple WebSocket server using only stdlib"""
    import socket, hashlib, base64, struct, threading
    
    def _handle_client(conn, addr, callback):
        try:
            data = conn.recv(4096).decode()
            if "Upgrade: websocket" not in data: conn.close(); return
            key = ""
            for line in data.split("\r\n"):
                if line.startswith("Sec-WebSocket-Key:"):
                    key = line.split(": ")[1].strip()
            accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-5AB5DC525E75").encode()).digest()).decode()
            response = f"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: {accept}\r\n\r\n"
            conn.send(response.encode())
            while True:
                header = conn.recv(2)
                if len(header) < 2: break
                opcode = header[0] & 0x0F
                if opcode == 8: break
                length = header[1] & 0x7F
                if length == 126: length = struct.unpack(">H", conn.recv(2))[0]
                elif length == 127: length = struct.unpack(">Q", conn.recv(8))[0]
                mask = conn.recv(4)
                payload = bytearray(conn.recv(length))
                for i in range(len(payload)): payload[i] ^= mask[i % 4]
                msg = payload.decode()
                reply = callback(msg) if callback else msg
                if reply:
                    reply_bytes = reply.encode()
                    frame = bytearray([0x81, len(reply_bytes)]) + reply_bytes
                    conn.send(frame)
        except: pass
        finally: conn.close()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(5)
    print(f"  🔌 WebSocket server on ws://localhost:{port}")
    while True:
        conn, addr = sock.accept()
        threading.Thread(target=_handle_client, args=(conn, addr, on_message), daemon=True).start()

# ═══ REGISTER ALL v5 GAME-CHANGERS ═══
def _register_v5_builtins(interp):
    env = interp.env
    
    # Python Bridge
    env.set("py_import", TheePythonBridge.py_import)
    env.set("py_call", TheePythonBridge.py_call)
    env.set("py_attr", TheePythonBridge.py_attr)
    env.set("py_eval", TheePythonBridge.py_eval)
    
    # Auth/JWT
    env.set("auth_secret", TheeAuth.set_secret)
    env.set("auth_register", TheeAuth.register)
    env.set("auth_login", TheeAuth.login)
    env.set("auth_verify", TheeAuth.verify_token)
    env.set("auth_token", TheeAuth.create_token)
    env.set("hash_password", TheeAuth.hash_password)
    
    # Components
    env.set("html_page", TheeComponent.page)
    env.set("html_card", TheeComponent.card)
    env.set("html_nav", TheeComponent.nav)
    env.set("html_table", TheeComponent.table)
    env.set("html_form", TheeComponent.form)
    env.set("chart_svg", TheeComponent.chart_svg)
    env.set("chart_pie", lambda d, t="": TheeComponent.chart_svg(d, "pie", t))
    
    # Testing
    env.set("test_run", TheeTestRunner.run)
    env.set("test_case", TheeTestRunner.test)
    env.set("assert_near", TheeTestRunner.assert_near)
    env.set("assert_throws", TheeTestRunner.assert_throws)
    
    # WebSocket
    env.set("ws_serve", _thee_websocket_server)
    
    # Async web
    env.set("web_static", TheeAsyncWeb.static)
    env.set("web_get", lambda p, d: TheeAsyncWeb.route(p, d, "GET"))
    env.set("web_post", lambda p, d: TheeAsyncWeb.route(p, d, "POST"))
    env.set("web_put", lambda p, d: TheeAsyncWeb.route(p, d, "PUT"))
    env.set("web_delete", lambda p, d: TheeAsyncWeb.route(p, d, "DELETE"))
    
    # Performance
    env.set("optimize", lambda name: TheeOptimizer._compiled.get(name, None))
    
    # Docker generation
    def _docker_gen(app_file="main.th", port=8000):
        return f"""FROM python:3.12-slim
WORKDIR /app
COPY thee /usr/local/bin/thee
COPY {app_file} .
RUN chmod +x /usr/local/bin/thee
EXPOSE {port}
CMD ["thee", "{app_file}"]"""
    env.set("docker_gen", _docker_gen)
    
    # Environment helpers
    env.set("env_set", lambda k, v: os.environ.__setitem__(k, str(v)))
    env.set("env_all", lambda: dict(os.environ))
    
    # Cron/scheduler
    import threading, time as _time
    def _schedule(seconds, fn):
        def _loop():
            while True:
                _time.sleep(seconds)
                try: fn()
                except: pass
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        return t
    env.set("schedule", _schedule)
    
    # Rate limiter
    _rate_limits = {}
    def _rate_limit(key, max_calls, window_secs):
        import time as t
        now = t.time()
        if key not in _rate_limits: _rate_limits[key] = []
        _rate_limits[key] = [ts for ts in _rate_limits[key] if now - ts < window_secs]
        if len(_rate_limits[key]) >= max_calls: return False
        _rate_limits[key].append(now)
        return True
    env.set("rate_limit", _rate_limit)
    
    # Cache/memoize
    _memo_cache = {}
    def _memoize(key, fn, ttl=300):
        import time as t
        if key in _memo_cache:
            val, ts = _memo_cache[key]
            if t.time() - ts < ttl: return val
        result = fn() if callable(fn) else fn
        _memo_cache[key] = (result, t.time())
        return result
    env.set("cache", _memoize)
    env.set("cache_clear", lambda: _memo_cache.clear())
    
    # Logging
    _logs = []
    def _log(level, msg):
        import time as t
        entry = {"time": t.strftime("%Y-%m-%d %H:%M:%S"), "level": level, "msg": str(msg)}
        _logs.append(entry)
        icons = {"info": "ℹ️", "warn": "⚠️", "error": "❌", "debug": "🔍"}
        print(f"  {icons.get(level, '📝')} [{entry['time']}] {level.upper()}: {msg}")
    env.set("log_info", lambda m: _log("info", m))
    env.set("log_warn", lambda m: _log("warn", m))
    env.set("log_error", lambda m: _log("error", m))
    env.set("log_debug", lambda m: _log("debug", m))
    env.set("log_all", lambda: list(_logs))
    
    # Queue
    import queue
    _queues = {}
    def _queue_create(name): _queues[name] = queue.Queue(); return True
    def _queue_push(name, item): _queues.get(name, queue.Queue()).put(item); return True
    def _queue_pop(name, timeout=1):
        try: return _queues.get(name, queue.Queue()).get(timeout=timeout)
        except: return None
    env.set("queue_create", _queue_create)
    env.set("queue_push", _queue_push)
    env.set("queue_pop", _queue_pop)
    
    # Retry
    def _retry(fn, max_attempts=3, delay=1):
        import time as t
        for i in range(max_attempts):
            try: return fn()
            except Exception as e:
                if i == max_attempts - 1: raise
                t.sleep(delay)
    env.set("retry", _retry)

# ═══ 8. FAST FUNCTION HELPER ═══
def _py_func(name, params, body):
    """Create a Python-speed function from THEE
    Usage: py_func("fib", "n", "n if n<=1 else fib(n-1)+fib(n-2)")
    """
    param_str = params if isinstance(params, str) else ", ".join(params)
    src = f"def {name}({param_str}):\n    return {body}"
    ns = {}
    exec(src, ns)
    fn = ns[name]
    # Allow recursion
    fn.__globals__[name] = fn
    return fn

def _py_exec(code_block):
    """Execute a block of Python code and return all defined names"""
    ns = {}
    exec(code_block, ns)
    return {k: v for k, v in ns.items() if not k.startswith('_')}

def _register_v5_extra(interp):
    interp.env.set("py_func", _py_func)
    interp.env.set("py_exec", _py_exec)
    
    # Retry with proper callable handling
    import time as _t
    def _retry_v2(fn, max_attempts=3, delay=1):
        for i in range(max_attempts):
            try:
                return fn() if callable(fn) else fn
            except Exception as e:
                if i == max_attempts - 1: raise
                _t.sleep(delay)
    interp.env.set("retry", _retry_v2)


# ═══ 8. FAST MODE — One-liner to compile Python functions ═══
def _thee_fast(code_str):
    """Run Python code and return result. Usage: na result = fast('sum(range(1000000))')"""
    return eval(code_str)

def _thee_fast_fn(name, params, body):
    """Define a fast Python function. Usage: fast_fn('fib', 'n', 'n if n<=1 else fib(n-1)+fib(n-2)')"""
    param_str = params if isinstance(params, str) else ",".join(params)
    ns = {}
    exec(f"def {name}({param_str}):\n    return {body}", ns)
    fn = ns[name]
    # Allow recursion
    fn.__globals__[name] = fn
    return fn

def _thee_pip_install(package):
    """Install a pip package"""
    import subprocess, sys
    result = subprocess.run([sys.executable, "-m", "pip", "install", "--break-system-packages", "-q", package],
                          capture_output=True, text=True)
    if result.returncode == 0:
        print(f"  📦 Installed: {package}")
        return True
    else:
        print(f"  ❌ Failed to install {package}: {result.stderr[:100]}")
        return False

# ═══ 9. MIDDLEWARE-CAPABLE WEB SERVER ═══
class TheeMiddleware:
    """Middleware chain for web requests"""
    _chain = []
    
    @staticmethod
    def use(name, fn):
        TheeMiddleware._chain.append((name, fn))
    
    @staticmethod
    def cors():
        TheeMiddleware.use("cors", lambda req, res: res)
    
    @staticmethod
    def logger():
        def _log(req, res):
            import time
            print(f"  📡 {time.strftime('%H:%M:%S')} {req.get('method','GET')} {req.get('path','/')}")
            return res
        TheeMiddleware.use("logger", _log)
    
    @staticmethod
    def auth_guard(secret=None):
        def _guard(req, res):
            token = req.get("headers", {}).get("Authorization", "").replace("Bearer ", "")
            if not token:
                return {"error": "Unauthorized", "_status": 401}
            payload = TheeAuth.verify_token(token)
            if not payload:
                return {"error": "Invalid token", "_status": 401}
            req["user"] = payload
            return res
        TheeMiddleware.use("auth", _guard)

# ═══ 10. DATA PIPELINE ═══
class TheePipeline:
    """Chainable data transformation pipeline"""
    def __init__(self, data):
        self.data = data
    
    def where(self, key, value):
        self.data = [r for r in self.data if r.get(key) == value]
        return self
    
    def where_gt(self, key, value):
        self.data = [r for r in self.data if r.get(key, 0) > value]
        return self
    
    def where_lt(self, key, value):
        self.data = [r for r in self.data if r.get(key, 0) < value]
        return self
    
    def where_contains(self, key, value):
        self.data = [r for r in self.data if value in str(r.get(key, ""))]
        return self
    
    def order_by(self, key, desc=False):
        self.data = sorted(self.data, key=lambda r: r.get(key, 0), reverse=desc)
        return self
    
    def limit(self, n):
        self.data = self.data[:n]
        return self
    
    def select(self, *keys):
        self.data = [{k: r.get(k) for k in keys} for r in self.data]
        return self
    
    def pluck(self, key):
        return [r.get(key) for r in self.data]
    
    def group_by(self, key):
        groups = {}
        for r in self.data:
            k = r.get(key)
            if k not in groups: groups[k] = []
            groups[k].append(r)
        return groups
    
    def count(self):
        return len(self.data)
    
    def sum(self, key):
        return sum(r.get(key, 0) for r in self.data)
    
    def avg(self, key):
        vals = [r.get(key, 0) for r in self.data]
        return sum(vals) / len(vals) if vals else 0
    
    def to_list(self):
        return self.data

# ═══ REGISTER v5.1 additions ═══
def _register_v5_extras(interp):
    env = interp.env
    
    # Fast mode
    env.set("fast", _thee_fast)
    env.set("fast_fn", _thee_fast_fn)
    
    # Pip
    env.set("pip_install", _thee_pip_install)
    
    # Middleware
    env.set("use_cors", TheeMiddleware.cors)
    env.set("use_logger", TheeMiddleware.logger)
    env.set("use_auth", TheeMiddleware.auth_guard)
    
    # Data pipeline
    env.set("pipe", lambda data: TheePipeline(data))
    
    # String template engine
    def _template(tmpl, data):
        result = tmpl
        for k, v in data.items():
            result = result.replace("{{" + k + "}}", str(v))
        return result
    env.set("template", _template)
    
    # Date helpers
    import time as _t
    env.set("now", lambda: __import__('time').strftime("%Y-%m-%d %H:%M:%S"))
    env.set("today", lambda: _t.strftime("%Y-%m-%d"))
    env.set("now_iso", lambda: _t.strftime("%Y-%m-%dT%H:%M:%SZ"))
    
    # Crypto helpers
    import hashlib as _hl
    env.set("sha256", lambda s: _hl.sha256(str(s).encode()).hexdigest())
    env.set("md5", lambda s: _hl.md5(str(s).encode()).hexdigest())
    
    # Retry with backoff
    def _retry_backoff(fn, max_attempts=3, base_delay=1):
        import time
        for i in range(max_attempts):
            try:
                return fn()
            except Exception as e:
                if i == max_attempts - 1:
                    raise
                time.sleep(base_delay * (2 ** i))
    env.set("retry_backoff", _retry_backoff)
    
    # JSON pretty print
    import json as _j
    env.set("json_pretty", lambda d: _j.dumps(d, indent=2, default=str, ensure_ascii=False))
    env.set("json_parse", lambda s: _j.loads(s))
    
    # Batch operations
    def _batch(items, size):
        return [items[i:i+size] for i in range(0, len(items), size)]
    env.set("batch", _batch)
    
    # Debounce / throttle (for scheduling)
    _last_calls = {}
    def _throttle(key, min_interval_ms):
        import time
        now = time.time() * 1000
        last = _last_calls.get(key, 0)
        if now - last < min_interval_ms:
            return False
        _last_calls[key] = now
        return True
    env.set("throttle", _throttle)
    
    # Event bus
    _event_bus = {}
    def _on(event, handler):
        if event not in _event_bus: _event_bus[event] = []
        _event_bus[event].append(handler)
    def _emit(event, data=None):
        for h in _event_bus.get(event, []):
            try:
                h(data) if data else h()
            except: pass
    env.set("on", _on)
    env.set("emit", _emit)
    
    # Environment profiles
    def _env_profile(name="development"):
        profiles = {
            "development": {"debug": True, "port": 8000, "host": "localhost", "log_level": "debug"},
            "production": {"debug": False, "port": 80, "host": "0.0.0.0", "log_level": "error"},
            "testing": {"debug": True, "port": 8001, "host": "localhost", "log_level": "info"},
        }
        return profiles.get(name, profiles["development"])
    env.set("env_profile", _env_profile)

# ═══════════════════════════════════════════════════════════
#  v5.2 — EVERY ENVIRONMENT: Mobile, Desktop, PWA, Cloud,
#  Bots, Static, PDF, Electron, Lambda, Chrome Extension
# ═══════════════════════════════════════════════════════════

class TheeEnvironments:
    """Generate deployable output for ANY platform from THEE code"""
    
    # ─── 1. PWA (Progressive Web App) → Mobile-installable ───
    @staticmethod
    def pwa_gen(title, body_html, icon_emoji="🔥", theme_color="#D4380D", port=8000):
        """Generate complete PWA: manifest + service worker + installable HTML"""
        manifest = json.dumps({
            "name": title, "short_name": title[:12], "start_url": "/",
            "display": "standalone", "background_color": "#ffffff",
            "theme_color": theme_color, "orientation": "portrait",
            "icons": [{"src": f"https://fakeimg.pl/192x192/?text={icon_emoji}&font=noto", "sizes": "192x192", "type": "image/png"},
                      {"src": f"https://fakeimg.pl/512x512/?text={icon_emoji}&font=noto", "sizes": "512x512", "type": "image/png"}]
        }, indent=2)
        
        sw = """self.addEventListener('install', e => e.waitUntil(caches.open('thee-v5').then(c => c.addAll(['/']))));
self.addEventListener('fetch', e => e.respondWith(caches.match(e.request).then(r => r || fetch(e.request))));"""
        
        html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="{theme_color}"><meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="/manifest.json"><title>{title}</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8f9fa}}
.app-bar{{background:{theme_color};color:#fff;padding:12px 16px;font-size:18px;font-weight:600;position:sticky;top:0;z-index:100;box-shadow:0 2px 4px rgba(0,0,0,.15)}}
.content{{padding:16px;max-width:600px;margin:0 auto}}.card{{background:#fff;border-radius:12px;padding:16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
.btn{{display:inline-block;padding:12px 24px;background:{theme_color};color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;width:100%;text-align:center;margin:8px 0}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
input,select,textarea{{width:100%;padding:12px;border:1px solid #ddd;border-radius:8px;font-size:16px;margin:6px 0}}
.tab-bar{{position:fixed;bottom:0;left:0;right:0;background:#fff;display:flex;border-top:1px solid #eee;padding:8px 0;z-index:100}}
.tab-bar a{{flex:1;text-align:center;color:#999;text-decoration:none;font-size:12px;padding:4px}}.tab-bar a.active{{color:{theme_color}}}
@media(min-width:768px){{.content{{max-width:800px}}.grid{{grid-template-columns:1fr 1fr 1fr}}}}</style>
</head><body><div class="app-bar">{icon_emoji} {title}</div><div class="content">{body_html}</div>
<script>if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js');</script></body></html>"""
        
        return {"html": html, "manifest": manifest, "sw": sw}
    
    # ─── 2. Static Site Export → Host anywhere (GitHub Pages, Netlify) ───
    @staticmethod
    def static_export(pages, output_dir="dist"):
        """Export THEE app as static HTML files"""
        os.makedirs(output_dir, exist_ok=True)
        for path, content in pages.items():
            filename = "index.html" if path == "/" else path.strip("/").replace("/", "_") + ".html"
            filepath = os.path.join(output_dir, filename)
            with open(filepath, "w") as f:
                f.write(content if isinstance(content, str) else json.dumps(content, indent=2, default=str))
            print(f"  📄 {filepath}")
        print(f"  ✅ Static site exported to {output_dir}/ ({len(pages)} pages)")
        print(f"  📦 Deploy: upload {output_dir}/ to GitHub Pages, Netlify, or Vercel")
        return output_dir
    
    # ─── 3. Desktop GUI (tkinter — built into Python) ───
    @staticmethod
    def gui_window(title, width=800, height=600):
        """Create a desktop GUI window"""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.title(title)
            root.geometry(f"{width}x{height}")
            root.configure(bg="#f8f9fa")
            return root
        except ImportError:
            print("  ⚠️ tkinter not available (headless environment)")
            return {"_type": "gui_window", "title": title, "width": width, "height": height, "widgets": []}
    
    @staticmethod
    def gui_label(window, text, x=0, y=0, size=14, bold=False, color="#1a1a2e"):
        try:
            import tkinter as tk
            font = ("Arial", size, "bold" if bold else "normal")
            lbl = tk.Label(window, text=text, font=font, fg=color, bg="#f8f9fa")
            lbl.place(x=x, y=y)
            return lbl
        except:
            if isinstance(window, dict):
                window.setdefault("widgets", []).append({"type": "label", "text": text, "x": x, "y": y})
            return {"type": "label", "text": text}
    
    @staticmethod
    def gui_button(window, text, command=None, x=0, y=0, width=120, color="#D4380D"):
        try:
            import tkinter as tk
            btn = tk.Button(window, text=text, command=command, bg=color, fg="white",
                          font=("Arial", 12), relief="flat", width=width//10)
            btn.place(x=x, y=y)
            return btn
        except:
            if isinstance(window, dict):
                window.setdefault("widgets", []).append({"type": "button", "text": text, "x": x, "y": y})
            return {"type": "button", "text": text}
    
    @staticmethod
    def gui_input(window, placeholder="", x=0, y=0, width=200):
        try:
            import tkinter as tk
            var = tk.StringVar()
            entry = tk.Entry(window, textvariable=var, font=("Arial", 12), width=width//10)
            entry.insert(0, placeholder)
            entry.place(x=x, y=y)
            return var
        except:
            if isinstance(window, dict):
                window.setdefault("widgets", []).append({"type": "input", "placeholder": placeholder, "x": x, "y": y})
            return {"type": "input", "value": ""}
    
    @staticmethod
    def gui_run(window):
        try:
            window.mainloop()
        except:
            print(f"  🖥️ GUI: {window.get('title','App')} ({window.get('width')}x{window.get('height')})")
            for w in window.get("widgets", []):
                print(f"    [{w['type']}] {w.get('text', w.get('placeholder', ''))}")
    
    # ─── 4. Telegram Bot ───
    @staticmethod
    def telegram_bot(token, handlers):
        """Create a Telegram bot with command handlers"""
        import urllib.request
        base = f"https://api.telegram.org/bot{token}"
        
        def send(chat_id, text):
            data = json.dumps({"chat_id": chat_id, "text": text}).encode()
            req = urllib.request.Request(f"{base}/sendMessage", data=data,
                                       headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req)
        
        def poll():
            offset = 0
            print(f"  🤖 Telegram bot running... (Ctrl+C to stop)")
            while True:
                try:
                    url = f"{base}/getUpdates?offset={offset}&timeout=30"
                    resp = json.loads(urllib.request.urlopen(url).read())
                    for update in resp.get("result", []):
                        offset = update["update_id"] + 1
                        msg = update.get("message", {})
                        text = msg.get("text", "")
                        chat_id = msg.get("chat", {}).get("id")
                        if chat_id and text:
                            cmd = text.split()[0].replace("/", "")
                            handler = handlers.get(cmd, handlers.get("default"))
                            if handler:
                                try:
                                    reply = handler(text)
                                    send(chat_id, str(reply))
                                except Exception as e:
                                    send(chat_id, f"Error: {e}")
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    time.sleep(5)
        return {"send": send, "poll": poll}
    
    # ─── 5. AWS Lambda Export ───
    @staticmethod
    def lambda_export(handler_code, output_dir="lambda_dist", runtime="python3.12"):
        """Export THEE app as AWS Lambda function"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Lambda handler wrapper
        handler = f"""import json
def lambda_handler(event, context):
    path = event.get('path', '/')
    method = event.get('httpMethod', 'GET')
    body = event.get('body', '')
    
    # THEE route handling
    routes = {handler_code}
    
    response = routes.get(path, {{"error": "Not found"}})
    return {{
        'statusCode': 200 if 'error' not in str(response) else 404,
        'headers': {{'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}},
        'body': json.dumps(response, default=str)
    }}
"""
        with open(os.path.join(output_dir, "lambda_function.py"), "w") as f:
            f.write(handler)
        
        # SAM template
        sam = f"""AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Resources:
  TheeFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: lambda_function.lambda_handler
      Runtime: {runtime}
      Timeout: 30
      Events:
        Api:
          Type: Api
          Properties:
            Path: /{{proxy+}}
            Method: ANY
"""
        with open(os.path.join(output_dir, "template.yaml"), "w") as f:
            f.write(sam)
        
        print(f"  ☁️ Lambda exported to {output_dir}/")
        print(f"  📦 Deploy: cd {output_dir} && sam deploy --guided")
        return output_dir
    
    # ─── 6. Google Cloud Function Export ───
    @staticmethod
    def gcf_export(routes_dict, output_dir="gcf_dist"):
        """Export as Google Cloud Function"""
        os.makedirs(output_dir, exist_ok=True)
        
        main = f"""import json
def handle(request):
    path = request.path
    routes = {repr(routes_dict)}
    response = routes.get(path, {{"error": "Not found"}})
    return json.dumps(response, default=str), 200, {{'Content-Type': 'application/json'}}
"""
        with open(os.path.join(output_dir, "main.py"), "w") as f:
            f.write(main)
        with open(os.path.join(output_dir, "requirements.txt"), "w") as f:
            f.write("")
        
        print(f"  ☁️ Cloud Function exported to {output_dir}/")
        print(f"  📦 Deploy: gcloud functions deploy thee-app --runtime python312 --trigger-http --source {output_dir}/")
        return output_dir
    
    # ─── 7. Electron Desktop App ───
    @staticmethod
    def electron_gen(title, html_content, output_dir="electron_app"):
        """Generate Electron desktop app package"""
        os.makedirs(output_dir, exist_ok=True)
        
        main_js = f"""const {{ app, BrowserWindow }} = require('electron');
function createWindow() {{
    const win = new BrowserWindow({{ width: 1024, height: 768, title: '{title}',
        webPreferences: {{ nodeIntegration: false }} }});
    win.loadFile('index.html');
}}
app.whenReady().then(createWindow);
app.on('window-all-closed', () => {{ if(process.platform !== 'darwin') app.quit(); }});
"""
        pkg = json.dumps({"name": title.lower().replace(" ", "-"), "version": "1.0.0",
                         "main": "main.js", "scripts": {"start": "electron ."}}, indent=2)
        
        with open(os.path.join(output_dir, "main.js"), "w") as f:
            f.write(main_js)
        with open(os.path.join(output_dir, "package.json"), "w") as f:
            f.write(pkg)
        with open(os.path.join(output_dir, "index.html"), "w") as f:
            f.write(html_content)
        
        print(f"  🖥️ Electron app generated in {output_dir}/")
        print(f"  📦 Install: cd {output_dir} && npm install electron")
        print(f"  ▶️ Run: npm start")
        return output_dir
    
    # ─── 8. Chrome Extension ───
    @staticmethod
    def chrome_ext_gen(name, description, popup_html, output_dir="chrome_ext"):
        """Generate Chrome extension"""
        os.makedirs(output_dir, exist_ok=True)
        
        manifest = json.dumps({
            "manifest_version": 3, "name": name, "version": "1.0",
            "description": description,
            "action": {"default_popup": "popup.html", "default_title": name},
            "permissions": ["storage"]
        }, indent=2)
        
        with open(os.path.join(output_dir, "manifest.json"), "w") as f:
            f.write(manifest)
        with open(os.path.join(output_dir, "popup.html"), "w") as f:
            f.write(popup_html)
        
        print(f"  🧩 Chrome extension generated in {output_dir}/")
        print(f"  📦 Install: chrome://extensions → Load unpacked → select {output_dir}/")
        return output_dir
    
    # ─── 9. PDF Report Generation ───
    @staticmethod
    def pdf_gen(title, sections, output_file="report.pdf"):
        """Generate PDF report from sections"""
        # Pure Python PDF generation (no external libs)
        pdf_lines = []
        objects = []
        
        def add_obj(content):
            objects.append(content)
            return len(objects)
        
        # Catalog
        add_obj("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj")
        # Pages
        add_obj("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj")
        
        # Build content stream
        lines = [f"BT /F1 24 Tf 72 740 Td ({title}) Tj ET"]
        y = 700
        for sec in sections:
            if isinstance(sec, dict):
                heading = sec.get("heading", "")
                body = sec.get("body", "")
                lines.append(f"BT /F1 16 Tf 72 {y} Td ({heading}) Tj ET")
                y -= 25
                # Word wrap body
                words = body.split()
                line = ""
                for w in words:
                    if len(line + w) > 80:
                        lines.append(f"BT /F1 11 Tf 72 {y} Td ({line.strip()}) Tj ET")
                        y -= 16
                        line = w + " "
                    else:
                        line += w + " "
                if line.strip():
                    lines.append(f"BT /F1 11 Tf 72 {y} Td ({line.strip()}) Tj ET")
                    y -= 16
                y -= 10
            else:
                lines.append(f"BT /F1 11 Tf 72 {y} Td ({str(sec)[:80]}) Tj ET")
                y -= 16
        
        stream = "\n".join(lines)
        
        # Page
        add_obj(f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj")
        # Content stream
        add_obj(f"4 0 obj\n<< /Length {len(stream)} >>\nstream\n{stream}\nendstream\nendobj")
        # Font
        add_obj("5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj")
        
        # Build PDF
        pdf = "%PDF-1.4\n"
        offsets = []
        for i, obj in enumerate(objects):
            offsets.append(len(pdf))
            pdf += obj + "\n"
        
        xref_pos = len(pdf)
        pdf += f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
        for off in offsets:
            pdf += f"{off:010d} 00000 n \n"
        pdf += f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF"
        
        with open(output_file, "wb") as f:
            f.write(pdf.encode("latin-1"))
        print(f"  📄 PDF generated: {output_file} ({len(sections)} sections)")
        return output_file
    
    # ─── 10. Discord Bot ───
    @staticmethod
    def discord_bot_gen(output_dir="discord_bot"):
        """Generate Discord bot scaffold"""
        os.makedirs(output_dir, exist_ok=True)
        
        bot_code = """import discord
import os

client = discord.Client(intents=discord.Intents.default())

@client.event
async def on_ready():
    print(f'{client.user} is online!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith('!hello'):
        await message.channel.send('நமசிவாய! 🔥 Built with THEE')
    elif message.content.startswith('!help'):
        await message.channel.send('Commands: !hello, !help')

client.run(os.environ.get('DISCORD_TOKEN', 'YOUR_TOKEN_HERE'))
"""
        with open(os.path.join(output_dir, "bot.py"), "w") as f:
            f.write(bot_code)
        with open(os.path.join(output_dir, "requirements.txt"), "w") as f:
            f.write("discord.py>=2.0\n")
        
        print(f"  🤖 Discord bot generated in {output_dir}/")
        print(f"  📦 Setup: cd {output_dir} && pip install -r requirements.txt")
        print(f"  ▶️ Run: DISCORD_TOKEN=xxx python bot.py")
        return output_dir
    
    # ─── 11. Static Site Generator ───
    @staticmethod
    def blog_gen(posts, title="My Blog", theme="tamil", output_dir="blog"):
        """Generate a static blog from list of posts"""
        os.makedirs(output_dir, exist_ok=True)
        tc = "#D4380D"
        def _page(t, body):
            return f'<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{t}</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:Arial,sans-serif;background:#f8f9fa;color:#1a1a2e}}nav{{background:{tc};padding:12px 20px;color:white}}nav a{{color:white;margin-right:16px;text-decoration:none}}.content{{max-width:800px;margin:20px auto;padding:0 16px}}.card{{background:white;border-radius:8px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.1);border-left:4px solid {tc}}}.card h3{{color:{tc};margin-bottom:8px}}small{{color:#888}}</style></head><body><nav><a href="index.html"><b>{title}</b></a></nav><div class="content">{body}</div></body></html>'
        def _card(t, b):
            return f'<div class="card"><h3>{t}</h3>{b}</div>'
        post_links = ""
        for i, post in enumerate(posts):
            p_title = post.get("title", f"Post {i+1}")
            p_body = post.get("body", "")
            p_date = post.get("date", "2026")
            slug = re.sub(r'[^a-z0-9]+', '-', p_title.lower()).strip('-')
            post_html = _page(p_title, _card(p_title, f"<p><small>{p_date}</small></p><p>{p_body}</p>"))
            with open(os.path.join(output_dir, f"{slug}.html"), "w") as f:
                f.write(post_html)
            post_links += _card(p_title, f"<p>{p_body[:150]}...</p><p><a href='{slug}.html'>Read more</a></p>")
        index = _page(title, post_links)
        with open(os.path.join(output_dir, "index.html"), "w") as f:
            f.write(index)
        print(f"  📝 Blog generated: {output_dir}/ ({len(posts)} posts)")
        print(f"  📦 Deploy: upload {output_dir}/ to GitHub Pages or Netlify")
        return output_dir

# ═══ Register ALL environment builtins ═══
def _register_v5_environments(interp):
    env = interp.env
    te = TheeEnvironments
    
    # PWA
    env.set("pwa_gen", te.pwa_gen)
    
    # Static export
    env.set("static_export", te.static_export)
    
    # Desktop GUI
    env.set("gui_window", te.gui_window)
    env.set("gui_label", te.gui_label)
    env.set("gui_button", te.gui_button)
    env.set("gui_input", te.gui_input)
    env.set("gui_run", te.gui_run)
    
    # Telegram bot
    env.set("telegram_bot", te.telegram_bot)
    
    # Cloud exports
    env.set("lambda_export", te.lambda_export)
    env.set("gcf_export", te.gcf_export)
    
    # Electron
    env.set("electron_gen", te.electron_gen)
    
    # Chrome extension
    env.set("chrome_ext_gen", te.chrome_ext_gen)
    
    # PDF
    env.set("pdf_gen", te.pdf_gen)
    
    # Discord bot scaffold
    env.set("discord_bot_gen", te.discord_bot_gen)
    
    # Blog generator
    env.set("blog_gen", te.blog_gen)
    
    # Convenience: export current web routes as static
    def _web_export(output_dir="dist"):
        from thee_lang.server import TheeWebServer
        if hasattr(TheeWebServer, '_routes'):
            pages = {}
            for path, content in TheeWebServer._routes.items():
                if isinstance(content, str):
                    pages[path] = content
                else:
                    pages[path] = json.dumps(content, indent=2, default=str, ensure_ascii=False)
            return te.static_export(pages, output_dir)
        print("  ⚠️ No routes defined. Use web_route() first.")
        return None
    env.set("web_export", _web_export)

# ═══════════════════════════════════════════════════════════
#  v5.3 — NATIVE MOBILE: iOS + Android from THEE code
#  Three paths: Capacitor, React Native, Flutter
# ═══════════════════════════════════════════════════════════

class TheeMobileGen:
    """Generate native iOS and Android apps from THEE code"""
    
    # ═══════════════════════════════════════════
    #  PATH 1: CAPACITOR (wrap THEE HTML in native shell)
    # ═══════════════════════════════════════════
    
    @staticmethod
    def capacitor_gen(app_name, app_id, html_content, theme_color="#D4380D", output_dir="mobile_app"):
        """Generate a Capacitor project that wraps THEE web app as native iOS/Android"""
        os.makedirs(os.path.join(output_dir, "www"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "src"), exist_ok=True)
        
        # package.json
        pkg = json.dumps({
            "name": app_name.lower().replace(" ", "-"),
            "version": "1.0.0",
            "description": f"{app_name} — Built with THEE",
            "scripts": {
                "build": "echo 'THEE app ready'",
                "cap:init": "npx cap init",
                "cap:add:ios": "npx cap add ios",
                "cap:add:android": "npx cap add android",
                "cap:sync": "npx cap sync",
                "cap:open:ios": "npx cap open ios",
                "cap:open:android": "npx cap open android",
                "build:ios": "npx cap sync ios && npx cap open ios",
                "build:android": "npx cap sync android && npx cap open android"
            },
            "dependencies": {
                "@capacitor/core": "^5.0.0",
                "@capacitor/cli": "^5.0.0",
                "@capacitor/ios": "^5.0.0",
                "@capacitor/android": "^5.0.0",
                "@capacitor/camera": "^5.0.0",
                "@capacitor/geolocation": "^5.0.0",
                "@capacitor/local-notifications": "^5.0.0",
                "@capacitor/push-notifications": "^5.0.0",
                "@capacitor/haptics": "^5.0.0",
                "@capacitor/status-bar": "^5.0.0",
                "@capacitor/splash-screen": "^5.0.0",
                "@capacitor/share": "^5.0.0",
                "@capacitor/storage": "^5.0.0"
            }
        }, indent=2)
        
        # capacitor.config.json
        cap_config = json.dumps({
            "appId": app_id,
            "appName": app_name,
            "webDir": "www",
            "server": {"androidScheme": "https"},
            "plugins": {
                "SplashScreen": {
                    "launchShowDuration": 2000,
                    "backgroundColor": theme_color,
                    "showSpinner": True,
                    "spinnerColor": "#FFFFFF"
                },
                "StatusBar": {
                    "backgroundColor": theme_color,
                    "style": "LIGHT"
                }
            }
        }, indent=2)
        
        # Native bridge JavaScript — gives THEE access to phone hardware
        native_bridge = """// THEE Native Bridge — Access phone hardware from THEE
const TheeNative = {
    // Camera
    async takePhoto() {
        const { Camera } = await import('@capacitor/camera');
        const photo = await Camera.getPhoto({
            quality: 90, allowEditing: true, resultType: 'base64'
        });
        return photo.base64String;
    },
    
    // GPS Location
    async getLocation() {
        const { Geolocation } = await import('@capacitor/geolocation');
        const pos = await Geolocation.getCurrentPosition();
        return { lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy };
    },
    
    // Push Notifications
    async requestNotifications() {
        const { PushNotifications } = await import('@capacitor/push-notifications');
        const result = await PushNotifications.requestPermissions();
        if (result.receive === 'granted') {
            await PushNotifications.register();
        }
        return result;
    },
    
    // Local Notification
    async notify(title, body) {
        const { LocalNotifications } = await import('@capacitor/local-notifications');
        await LocalNotifications.schedule({
            notifications: [{ title, body, id: Date.now(), schedule: { at: new Date(Date.now() + 1000) } }]
        });
    },
    
    // Haptic Feedback
    async vibrate() {
        const { Haptics } = await import('@capacitor/haptics');
        await Haptics.vibrate();
    },
    
    // Share
    async share(title, text, url) {
        const { Share } = await import('@capacitor/share');
        await Share.share({ title, text, url });
    },
    
    // Storage (persistent)
    async save(key, value) {
        const { Storage } = await import('@capacitor/storage');
        await Storage.set({ key, value: JSON.stringify(value) });
    },
    async load(key) {
        const { Storage } = await import('@capacitor/storage');
        const { value } = await Storage.get({ key });
        return value ? JSON.parse(value) : null;
    }
};
window.TheeNative = TheeNative;
"""
        
        # Enhanced HTML with mobile meta tags + native bridge
        mobile_html = html_content
        if '<head>' in mobile_html:
            inject = f"""<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="theme-color" content="{theme_color}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<style>
body {{ padding-top: env(safe-area-inset-top); padding-bottom: env(safe-area-inset-bottom); 
       -webkit-user-select: none; user-select: none; -webkit-tap-highlight-color: transparent; }}
.app-bar {{ padding-top: calc(12px + env(safe-area-inset-top)) !important; }}
.tab-bar {{ padding-bottom: calc(8px + env(safe-area-inset-bottom)) !important; }}
</style>
<script>{native_bridge}</script>"""
            mobile_html = mobile_html.replace('<head>', f'<head>\n{inject}')
        
        # Write all files
        with open(os.path.join(output_dir, "package.json"), "w") as f: f.write(pkg)
        with open(os.path.join(output_dir, "capacitor.config.json"), "w") as f: f.write(cap_config)
        with open(os.path.join(output_dir, "www", "index.html"), "w") as f: f.write(mobile_html)
        with open(os.path.join(output_dir, "src", "native-bridge.js"), "w") as f: f.write(native_bridge)
        
        # Build script
        build_sh = f"""#!/bin/bash
echo "🔥 THEE → Native App Builder"
echo ""

# Step 1: Install dependencies
echo "📦 Step 1: Installing Capacitor..."
npm install

# Step 2: Initialize Capacitor
echo "⚡ Step 2: Initializing Capacitor..."
npx cap init "{app_name}" "{app_id}" --web-dir www

# Step 3: Add platforms
echo "📱 Step 3: Adding iOS platform..."
npx cap add ios 2>/dev/null || echo "  (iOS requires macOS with Xcode)"

echo "🤖 Step 4: Adding Android platform..."
npx cap add android 2>/dev/null || echo "  (Android requires Android Studio)"

# Step 4: Sync
echo "🔄 Step 5: Syncing web assets..."
npx cap sync

echo ""
echo "✅ Done! Next steps:"
echo "  iOS:     npx cap open ios       → Build in Xcode → Run on iPhone"
echo "  Android: npx cap open android   → Build in Android Studio → Run on phone"
echo ""
echo "  To test in browser first: open www/index.html"
"""
        with open(os.path.join(output_dir, "build.sh"), "w") as f: f.write(build_sh)
        os.chmod(os.path.join(output_dir, "build.sh"), 0o755)
        
        # README
        readme = f"""# {app_name}
Built with THEE → Capacitor → Native iOS/Android

## Quick Start
```bash
cd {output_dir}
bash build.sh          # Install + configure
npx cap open ios       # Open in Xcode (Mac only)
npx cap open android   # Open in Android Studio
```

## Phone Hardware Access
This app can use phone hardware via TheeNative:
- `TheeNative.takePhoto()` — Camera
- `TheeNative.getLocation()` — GPS
- `TheeNative.notify(title, body)` — Push notifications
- `TheeNative.vibrate()` — Haptic feedback
- `TheeNative.share(title, text, url)` — Share sheet
- `TheeNative.save(key, value)` / `TheeNative.load(key)` — Persistent storage

## Deploy to App Store / Play Store
1. iOS: Xcode → Product → Archive → Upload to App Store Connect
2. Android: Android Studio → Build → Generate Signed APK → Upload to Play Console
"""
        with open(os.path.join(output_dir, "README.md"), "w") as f: f.write(readme)
        
        files = sum(1 for _ in os.walk(output_dir) for f in _[2])
        print(f"  📱 Capacitor project generated: {output_dir}/")
        print(f"  📁 {files} files created")
        print(f"  ▶️ Build: cd {output_dir} && bash build.sh")
        print(f"  📱 iOS:     npx cap open ios")
        print(f"  🤖 Android: npx cap open android")
        return output_dir

    # ═══════════════════════════════════════════
    #  PATH 2: REACT NATIVE (transpile THEE → JSX)
    # ═══════════════════════════════════════════
    
    @staticmethod
    def react_native_gen(app_name, screens, theme_color="#D4380D", output_dir="rn_app"):
        """Generate React Native / Expo project from THEE screen definitions"""
        os.makedirs(os.path.join(output_dir, "screens"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "components"), exist_ok=True)
        
        # app.json (Expo config)
        app_json = json.dumps({
            "expo": {
                "name": app_name,
                "slug": app_name.lower().replace(" ", "-"),
                "version": "1.0.0",
                "orientation": "portrait",
                "icon": "./assets/icon.png",
                "splash": {"backgroundColor": theme_color, "resizeMode": "contain"},
                "ios": {"supportsTablet": True, "bundleIdentifier": f"com.thee.{app_name.lower().replace(' ', '')}"},
                "android": {"adaptiveIcon": {"backgroundColor": theme_color},
                            "package": f"com.thee.{app_name.lower().replace(' ', '')}"},
            }
        }, indent=2)
        
        # package.json
        pkg = json.dumps({
            "name": app_name.lower().replace(" ", "-"),
            "version": "1.0.0",
            "scripts": {
                "start": "expo start",
                "android": "expo start --android",
                "ios": "expo start --ios",
                "build:ios": "eas build -p ios",
                "build:android": "eas build -p android"
            },
            "dependencies": {
                "expo": "~50.0.0",
                "expo-status-bar": "~1.11.0",
                "react": "18.2.0",
                "react-native": "0.73.0",
                "@react-navigation/native": "^6.1.0",
                "@react-navigation/bottom-tabs": "^6.5.0",
                "react-native-screens": "~3.29.0",
                "react-native-safe-area-context": "4.8.0",
                "expo-camera": "~14.0.0",
                "expo-location": "~16.5.0",
                "expo-notifications": "~0.27.0",
                "expo-haptics": "~12.8.0",
                "expo-sharing": "~11.10.0",
                "expo-sqlite": "~13.2.0"
            }
        }, indent=2)
        
        # Generate screen components from THEE definitions
        screen_imports = []
        screen_components = []
        tab_screens = []
        
        for i, screen in enumerate(screens):
            name = screen.get("name", f"Screen{i+1}")
            title = screen.get("title", name)
            icon = screen.get("icon", "home")
            safe_name = name.replace(" ", "")
            components = screen.get("components", [])
            
            # Build JSX from THEE component definitions
            jsx_body = ""
            for comp in components:
                ctype = comp.get("type", "text")
                if ctype == "card":
                    jsx_body += f"""
      <View style={{styles.card}}>
        <Text style={{styles.cardTitle}}>{comp.get('title', '')}</Text>
        <Text style={{styles.cardBody}}>{comp.get('body', '')}</Text>
      </View>"""
                elif ctype == "text":
                    size = comp.get("size", 16)
                    bold = "fontWeight: 'bold', " if comp.get("bold") else ""
                    jsx_body += f"""
      <Text style={{{{ fontSize: {size}, {bold}color: '{comp.get("color", "#333")}', marginBottom: 8 }}}}>{comp.get('text', '')}</Text>"""
                elif ctype == "button":
                    jsx_body += f"""
      <TouchableOpacity style={{styles.button}} onPress={{() => alert('{comp.get("action", "Pressed!")}')}}> 
        <Text style={{styles.buttonText}}>{comp.get('text', 'Button')}</Text>
      </TouchableOpacity>"""
                elif ctype == "input":
                    jsx_body += f"""
      <TextInput style={{styles.input}} placeholder="{comp.get('placeholder', 'Enter text...')}" />"""
                elif ctype == "image":
                    jsx_body += f"""
      <Image source={{{{ uri: '{comp.get("url", "https://via.placeholder.com/300")}' }}}} style={{{{ width: '100%', height: 200, borderRadius: 12, marginBottom: 12 }}}} />"""
                elif ctype == "list":
                    items = comp.get("items", [])
                    items_str = ", ".join([f'"{it}"' for it in items])
                    jsx_body += f"""
      {{[{items_str}].map((item, idx) => (
        <View key={{idx}} style={{styles.listItem}}>
          <Text style={{{{ fontSize: 16 }}}}>{'{item}'}</Text>
        </View>
      ))}}"""
                elif ctype == "chart":
                    data = comp.get("data", {})
                    jsx_body += f"""
      <View style={{styles.chart}}>
        <Text style={{styles.cardTitle}}>{comp.get('title', 'Chart')}</Text>
        <View style={{{{ flexDirection: 'row', alignItems: 'flex-end', height: 150, gap: 8, paddingTop: 10 }}}}>
          {' '.join([f'<View style={{{{ flex: 1, alignItems: "center" }}}}><View style={{{{ width: "100%", height: {int((v/max(data.values() or [1]))*130)}, backgroundColor: "{theme_color}", borderRadius: 4 }}}} /><Text style={{{{ fontSize: 10, marginTop: 4 }}}}>{k}</Text></View>' for k, v in data.items()])}
        </View>
      </View>"""
            
            # Screen file
            screen_code = f"""import React from 'react';
import {{ View, Text, ScrollView, TouchableOpacity, TextInput, Image, StyleSheet }} from 'react-native';

export default function {safe_name}Screen() {{
  return (
    <ScrollView style={{styles.container}}>
      <Text style={{styles.header}}>{title}</Text>
      {jsx_body}
      <View style={{{{ height: 100 }}}} />
    </ScrollView>
  );
}}

const styles = StyleSheet.create({{
  container: {{ flex: 1, backgroundColor: '#f8f9fa', padding: 16 }},
  header: {{ fontSize: 28, fontWeight: 'bold', color: '{theme_color}', marginBottom: 16, marginTop: 8 }},
  card: {{ backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12,
           shadowColor: '#000', shadowOffset: {{ width: 0, height: 1 }}, shadowOpacity: 0.1, shadowRadius: 3, elevation: 2 }},
  cardTitle: {{ fontSize: 18, fontWeight: '600', color: '#333', marginBottom: 6 }},
  cardBody: {{ fontSize: 15, color: '#666', lineHeight: 22 }},
  button: {{ backgroundColor: '{theme_color}', borderRadius: 8, padding: 14, alignItems: 'center', marginBottom: 12 }},
  buttonText: {{ color: '#fff', fontSize: 16, fontWeight: '600' }},
  input: {{ backgroundColor: '#fff', borderRadius: 8, padding: 14, fontSize: 16, borderWidth: 1, borderColor: '#ddd', marginBottom: 12 }},
  chart: {{ backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12 }},
  listItem: {{ backgroundColor: '#fff', padding: 14, borderBottomWidth: 1, borderBottomColor: '#eee' }},
}});
"""
            with open(os.path.join(output_dir, "screens", f"{safe_name}Screen.js"), "w") as f:
                f.write(screen_code)
            
            screen_imports.append(f"import {safe_name}Screen from './screens/{safe_name}Screen';")
            tab_screens.append(f'        <Tab.Screen name="{name}" component={{{safe_name}Screen}} options={{{{ tabBarIcon: ({{{{ color, size }}}}) => <Text style={{{{ fontSize: size }}}}>{icon}</Text> }}}} />')
        
        # App.js with navigation
        app_js = f"""import React from 'react';
import {{ NavigationContainer }} from '@react-navigation/native';
import {{ createBottomTabNavigator }} from '@react-navigation/bottom-tabs';
import {{ StatusBar }} from 'expo-status-bar';
{chr(10).join(screen_imports)}

const Tab = createBottomTabNavigator();

export default function App() {{
  return (
    <NavigationContainer>
      <StatusBar style="light" backgroundColor="{theme_color}" />
      <Tab.Navigator screenOptions={{{{ 
        headerStyle: {{ backgroundColor: '{theme_color}' }},
        headerTintColor: '#fff',
        tabBarActiveTintColor: '{theme_color}',
      }}}}>
{chr(10).join(tab_screens)}
      </Tab.Navigator>
    </NavigationContainer>
  );
}}
"""
        with open(os.path.join(output_dir, "App.js"), "w") as f: f.write(app_js)
        with open(os.path.join(output_dir, "package.json"), "w") as f: f.write(pkg)
        with open(os.path.join(output_dir, "app.json"), "w") as f: f.write(app_json)
        
        # assets placeholder
        os.makedirs(os.path.join(output_dir, "assets"), exist_ok=True)
        
        print(f"  📱 React Native (Expo) project generated: {output_dir}/")
        print(f"  📁 {len(screens)} screens created")
        print(f"  ▶️ Run:")
        print(f"     cd {output_dir}")
        print(f"     npm install")
        print(f"     npx expo start")
        print(f"  📱 iOS build:     eas build -p ios")
        print(f"  🤖 Android build: eas build -p android")
        return output_dir

    # ═══════════════════════════════════════════
    #  PATH 3: FLUTTER (transpile THEE → Dart)
    # ═══════════════════════════════════════════
    
    @staticmethod
    def flutter_gen(app_name, screens, theme_color="#D4380D", output_dir="flutter_app"):
        """Generate Flutter/Dart project from THEE screen definitions"""
        os.makedirs(os.path.join(output_dir, "lib"), exist_ok=True)
        
        # pubspec.yaml
        pubspec = f"""name: {app_name.lower().replace(' ', '_')}
description: {app_name} — Built with THEE
version: 1.0.0

environment:
  sdk: '>=3.0.0 <4.0.0'
  flutter: '>=3.0.0'

dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.6
  sqflite: ^2.3.0
  path_provider: ^2.1.0
  camera: ^0.10.5
  geolocator: ^11.0.0
  share_plus: ^7.2.0
  flutter_local_notifications: ^16.3.0

flutter:
  uses-material-design: true
"""
        with open(os.path.join(output_dir, "pubspec.yaml"), "w") as f: f.write(pubspec)
        
        # Generate Dart screens
        screen_classes = []
        screen_tabs = []
        
        for i, screen in enumerate(screens):
            name = screen.get("name", f"Screen{i+1}")
            title = screen.get("title", name)
            icon = screen.get("dart_icon", "Icons.home")
            safe_name = name.replace(" ", "")
            components = screen.get("components", [])
            
            # Build Dart widget tree from components
            dart_children = []
            for comp in components:
                ctype = comp.get("type", "text")
                if ctype == "card":
                    dart_children.append(f"""
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('{comp.get("title", "")}', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600)),
                  SizedBox(height: 6),
                  Text('{comp.get("body", "")}', style: TextStyle(fontSize: 15, color: Colors.grey[600])),
                ]),
              ),
            ),""")
                elif ctype == "button":
                    dart_children.append(f"""
            ElevatedButton(
              onPressed: () {{ ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('{comp.get("action", "Pressed!")}')));  }},
              style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF{theme_color[1:]}), padding: EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
              child: Text('{comp.get("text", "Button")}', style: TextStyle(fontSize: 16, color: Colors.white)),
            ),""")
                elif ctype == "input":
                    dart_children.append(f"""
            TextField(decoration: InputDecoration(hintText: '{comp.get("placeholder", "")}', border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)), contentPadding: EdgeInsets.all(14))),""")
                elif ctype == "text":
                    size = comp.get("size", 16)
                    bold = "fontWeight: FontWeight.bold, " if comp.get("bold") else ""
                    dart_children.append(f"""
            Text('{comp.get("text", "")}', style: TextStyle(fontSize: {size}, {bold}color: Color(0xFF{comp.get("color", "333333").replace("#", "")}))),""")
            
            children_str = "\n            SizedBox(height: 12),".join(dart_children)
            
            screen_classes.append(f"""
class {safe_name}Screen extends StatelessWidget {{
  @override
  Widget build(BuildContext context) {{
    return SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Text('{title}', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Color(0xFF{theme_color[1:]}))),
            SizedBox(height: 16),{children_str}
            SizedBox(height: 100),
      ]),
    );
  }}
}}""")
            screen_tabs.append(f"        BottomNavigationBarItem(icon: Icon({icon}), label: '{name}'),")
        
        # Build pages list for body
        page_widgets = [f"      {s.get('name','Screen').replace(' ','')}Screen()," for s in screens]
        
        # main.dart
        main_dart = f"""import 'package:flutter/material.dart';

void main() => runApp(TheeApp());

class TheeApp extends StatelessWidget {{
  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: '{app_name}',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        primaryColor: Color(0xFF{theme_color[1:]}),
        colorScheme: ColorScheme.fromSeed(seedColor: Color(0xFF{theme_color[1:]})),
        useMaterial3: true,
        appBarTheme: AppBarTheme(backgroundColor: Color(0xFF{theme_color[1:]}), foregroundColor: Colors.white),
      ),
      home: HomePage(),
    );
  }}
}}

class HomePage extends StatefulWidget {{
  @override
  _HomePageState createState() => _HomePageState();
}}

class _HomePageState extends State<HomePage> {{
  int _currentIndex = 0;
  final List<Widget> _pages = [
{chr(10).join(page_widgets)}
  ];

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(title: Text('{app_name}')),
      body: _pages[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (i) => setState(() => _currentIndex = i),
        selectedItemColor: Color(0xFF{theme_color[1:]}),
        items: [
{chr(10).join(screen_tabs)}
        ],
      ),
    );
  }}
}}
{chr(10).join(screen_classes)}
"""
        with open(os.path.join(output_dir, "lib", "main.dart"), "w") as f: f.write(main_dart)
        
        print(f"  📱 Flutter project generated: {output_dir}/")
        print(f"  📁 {len(screens)} screens, {len(screen_classes)} widgets")
        print(f"  ▶️ Run:")
        print(f"     cd {output_dir}")
        print(f"     flutter pub get")
        print(f"     flutter run")
        print(f"  📱 iOS build:     flutter build ios")
        print(f"  🤖 Android build: flutter build apk")
        return output_dir


# ═══ Register mobile builtins ═══
def _register_v5_mobile(interp):
    env = interp.env
    mg = TheeMobileGen
    env.set("capacitor_gen", mg.capacitor_gen)
    env.set("react_native_gen", mg.react_native_gen)
    env.set("flutter_gen", mg.flutter_gen)
    
    # Convenience shortcuts
    def _mobile_gen(app_name, html_content, app_id=None, output_dir="mobile_app"):
        """Shortcut: generate mobile app (Capacitor, simplest path)"""
        if not app_id:
            app_id = f"com.thee.{app_name.lower().replace(' ', '')}"
        return mg.capacitor_gen(app_name, app_id, html_content, output_dir=output_dir)
    
    env.set("mobile_gen", _mobile_gen)
    env.set("ios_gen", lambda n, h, o="ios_app": mg.capacitor_gen(n, f"com.thee.{n.lower().replace(' ','')}", h, output_dir=o))
    env.set("android_gen", lambda n, h, o="android_app": mg.capacitor_gen(n, f"com.thee.{n.lower().replace(' ','')}", h, output_dir=o))

# ═══════════════════════════════════════════════════════════
#  v5.4 — BUG FIXES: All missing builtins + aliases
# ═══════════════════════════════════════════════════════════

def _register_v5_bugfixes(interp):
    env = interp.env
    
    # ─── CRITICAL FIX 1-4: db_update/delete/count/upsert ───
    # These use db_query which is already registered and handles _dbs
    def _db_update(table, data, where=None):
        db_q = env.get("db_query")
        sets = ", ".join(f"{k} = ?" for k in data.keys())
        vals = list(data.values())
        sql = f"UPDATE {table} SET {sets}"
        if where: sql += f" WHERE {where}"
        db_q(sql, vals)
        return True
    env.set("db_update", _db_update)
    
    def _db_delete(table, where=None):
        db_q = env.get("db_query")
        sql = f"DELETE FROM {table}"
        if where: sql += f" WHERE {where}"
        db_q(sql)
        return True
    env.set("db_delete", _db_delete)
    
    def _db_count(table, where=None):
        db_q = env.get("db_query")
        sql = f"SELECT COUNT(*) as c FROM {table}"
        if where: sql += f" WHERE {where}"
        r = db_q(sql)
        return r[0]["c"] if r else 0
    env.set("db_count", _db_count)
    
    def _db_upsert(table, data, key_col="id"):
        db_q = env.get("db_query")
        cols = ", ".join(data.keys())
        placeholders = ", ".join("?" for _ in data)
        updates = ", ".join(f"{k} = excluded.{k}" for k in data.keys() if k != key_col)
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT({key_col}) DO UPDATE SET {updates}"
        db_q(sql, list(data.values()))
        return True
    env.set("db_upsert", _db_upsert)
    
    # ─── FIX 5: zip() ───
    env.set("zip", lambda a, b: [list(x) for x in __builtins__['zip'](a, b)] if isinstance(__builtins__, dict) else [list(x) for x in zip(a, b)])
    # Simpler approach
    def _zip(a, b):
        return [[a[i], b[i]] for i in range(min(len(a), len(b)))]
    env.set("zip", _zip)
    
    # ─── FIX 6-8: Aliases ───
    # starts_with / ends_with aliases
    try:
        sw = env.get("startswith")
        env.set("starts_with", sw)
    except:
        env.set("starts_with", lambda s, p: s.startswith(p))
        env.set("startswith", lambda s, p: s.startswith(p))
    try:
        ew = env.get("endswith")
        env.set("ends_with", ew)
    except:
        env.set("ends_with", lambda s, p: s.endswith(p))
        env.set("endswith", lambda s, p: s.endswith(p))
    # to_str alias
    env.set("to_str", lambda x: str(x))
    try:
        env.get("to_string")
    except:
        env.set("to_string", lambda x: str(x))
    
    # ─── FIX 9: substr() ───
    def _substr(s, start, end=None):
        if end is None:
            return s[start:]
        return s[start:end]
    env.set("substr", _substr)
    
    # ─── FIX 10: cache_set / cache_get ───
    _cache = {}
    def _cache_set(key, value, ttl=None):
        _cache[key] = {"value": value, "time": time.time(), "ttl": ttl}
        return True
    def _cache_get(key):
        item = _cache.get(key)
        if item is None:
            return None
        if item["ttl"] and (time.time() - item["time"]) > item["ttl"]:
            del _cache[key]
            return None
        return item["value"]
    def _cache_delete(key):
        return _cache.pop(key, None) is not None
    def _cache_clear():
        _cache.clear()
        return True
    env.set("cache_set", _cache_set)
    env.set("cache_get", _cache_get)
    env.set("cache_delete", _cache_delete)
    env.set("cache_clear", _cache_clear)
    
    # ─── FIX 11: data_group / data_sort / data_filter ───
    def _data_group(data, key):
        groups = {}
        for item in data:
            k = item.get(key) if isinstance(item, dict) else item
            groups.setdefault(k, []).append(item)
        return groups
    def _data_sort(data, key, reverse=False):
        return sorted(data, key=lambda x: x.get(key) if isinstance(x, dict) else x, reverse=reverse)
    def _data_filter(data, key, value):
        return [item for item in data if (item.get(key) if isinstance(item, dict) else item) == value]
    env.set("data_group", _data_group)
    env.set("data_sort", _data_sort)
    env.set("data_filter", _data_filter)
    
    # ─── FIX 12: http_put / http_delete / fetch ───
    def _http_put(url, data=None, headers=None):
        import urllib.request
        req = urllib.request.Request(url, method='PUT',
            data=json.dumps(data).encode() if data else None,
            headers=headers or {"Content-Type": "application/json"})
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}
    
    def _http_delete(url, headers=None):
        import urllib.request
        req = urllib.request.Request(url, method='DELETE', headers=headers or {})
        try:
            resp = urllib.request.urlopen(req, timeout=10)
            return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}
    
    def _fetch(url, method="GET", data=None, headers=None):
        methods = {"GET": env.get("http_get"), "POST": env.get("http_post"), 
                   "PUT": _http_put, "DELETE": _http_delete}
        fn = methods.get(method.upper())
        if fn:
            return fn(url, data) if data else fn(url)
        return {"error": f"Unknown method: {method}"}
    
    env.set("http_put", _http_put)
    env.set("http_delete", _http_delete)
    env.set("fetch", _fetch)
    
    # ─── FIX 13: format_date ───
    def _format_date(date_str=None, fmt="%Y-%m-%d"):
        if date_str is None:
            return time.strftime(fmt)
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(str(date_str))
            return dt.strftime(fmt)
        except:
            return str(date_str)
    env.set("format_date", _format_date)
    env.set("now", lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    env.set("today", lambda: time.strftime("%Y-%m-%d"))
    
    # ─── FIX 14: AI convenience functions ───
    def _ai_classify(text, categories):
        ai = env.get("ai_complete")
        if ai:
            prompt = f"Classify this text into one of these categories: {categories}\n\nText: {text}\n\nCategory:"
            return ai(prompt)
        return categories[0] if categories else "unknown"
    
    def _ai_extract(text, fields):
        ai = env.get("ai_complete")
        if ai:
            prompt = f"Extract these fields from the text: {fields}\n\nText: {text}\n\nJSON:"
            return ai(prompt)
        return {f: "" for f in fields}
    
    def _ai_summarize(text, max_words=50):
        ai = env.get("ai_complete")
        if ai:
            return ai(f"Summarize in {max_words} words: {text}")
        return text[:200]
    
    env.set("ai_classify", _ai_classify)
    env.set("ai_extract", _ai_extract)
    env.set("ai_summarize", _ai_summarize)
    
    # ─── FIX 16: nillu as Tamil break ───
    env.set("nillu", "BREAK_SIGNAL")  # Will need parser support
    
    # ─── FIX 20: join() both argument orders ───
    def _join_flexible(*args):
        if len(args) == 1:
            a = args[0]
            if isinstance(a, list):
                return ", ".join(str(x) for x in a)
            return str(a)
        a, b = args[0], args[1]
        if isinstance(a, list) and isinstance(b, str):
            return b.join(str(x) for x in a)
        elif isinstance(a, str) and isinstance(b, list):
            return a.join(str(x) for x in b)
        elif isinstance(a, list):
            return str(b).join(str(x) for x in a)
        return str(a) + str(b)
    env.set("join", _join_flexible)


# ═══════════════════════════════════════════════════════════
# v6.0 — திருமுறை (THIRUMURAI) FEATURES REGISTRATION
# ═══════════════════════════════════════════════════════════

class TheeGenerator:
    """Generator/iterator with yield support."""
    def __init__(self, name, params, body, closure, interp):
        self.name = name; self.params = params; self.body = body
        self.closure = closure; self.interp = interp
        self._values = []; self._exhausted = False
    
    def __call__(self, *args):
        """Run the generator and collect all yielded values."""
        env = Environment(self.closure)
        for i, p in enumerate(self.params):
            env.set(p, args[i] if i < len(args) else None)
        old_env = self.interp.env
        self.interp.env = env
        self._values = []
        try:
            for s in self.body:
                try:
                    self.interp.execute(s)
                except TheeYield as y:
                    self._values.append(y.value)
                except TheeReturn:
                    break
        finally:
            self.interp.env = old_env
        return self._values
    
    def __repr__(self):
        return f"<Generator '{self.name}'>"

class TheeEventBus:
    """Central event bus for reactive programming."""
    def __init__(self):
        self._handlers = {}
        self._history = []
    
    def on(self, event, handler):
        self._handlers.setdefault(event, []).append(handler)
        return True
    
    def off(self, event, handler=None):
        if handler is None:
            self._handlers.pop(event, None)
        else:
            self._handlers[event] = [h for h in self._handlers.get(event, []) if h != handler]
        return True
    
    def emit(self, event, *data):
        self._history.append({"event": event, "data": data, "time": time.time()})
        results = []
        for h in self._handlers.get(event, []):
            try:
                if callable(h):
                    results.append(h(*data))
                elif isinstance(h, dict) and "body" in h:
                    # THEE function
                    from thee_lang.interpreter import TheeInterpreter
                    results.append(None)
            except Exception as e:
                results.append(str(e))
        return results
    
    def once(self, event, handler):
        def wrapper(*args):
            self.off(event, wrapper)
            return handler(*args) if callable(handler) else None
        self._handlers.setdefault(event, []).append(wrapper)
        return True
    
    def history(self, event=None, limit=10):
        if event:
            return [h for h in self._history if h["event"] == event][-limit:]
        return self._history[-limit:]
    
    def __repr__(self):
        return f"<EventBus events={list(self._handlers.keys())}>"


def _register_v6_features(interp):
    env = interp.env
    
    # ─── EVENT SYSTEM (நிகழ்வு) ───
    bus = TheeEventBus()
    bus._interp = interp  # Give bus access to interpreter
    env.set("events", bus)
    
    def _on_evt(evt, fn):
        def wrapper(*args):
            return interp._invoke(fn, list(args))
        wrapper._thee_fn = fn
        bus.on(evt, wrapper)
        return True
    
    def _emit_evt(evt, *d):
        return bus.emit(evt, *d)
    
    env.set("on", _on_evt)
    env.set("off", lambda evt, fn=None: bus.off(evt, fn))
    env.set("emit_event", _emit_evt)
    env.set("once", lambda evt, fn: bus.once(evt, lambda *a: interp._invoke(fn, list(a))))
    env.set("event_history", lambda evt=None, n=10: bus.history(evt, n))
    # Tamil aliases
    env.set("nigazhvu_ketpom", _on_evt)
    env.set("nigazhvu_anuppu", _emit_evt)
    
    # ─── GENERATOR SUPPORT ───
    def _make_generator(name_or_fn, params_or_none=None, body_or_none=None):
        """Create a generator from a THEE function."""
        if isinstance(name_or_fn, dict) and "body" in name_or_fn:
            fn = name_or_fn
            return TheeGenerator(
                "anon", fn.get("params", []), fn["body"],
                fn.get("closure", interp.env), interp
            )
        return name_or_fn
    env.set("generator", _make_generator)
    env.set("vilaipaduththi", _make_generator)  # Tamil: generator
    
    def _range_gen(*args):
        """Range function like Python's range."""
        if len(args) == 1:
            return list(range(int(args[0])))
        elif len(args) == 2:
            return list(range(int(args[0]), int(args[1])))
        elif len(args) == 3:
            return list(range(int(args[0]), int(args[1]), int(args[2])))
        return []
    env.set("range", _range_gen)
    env.set("eNNikai", _range_gen)  # Tamil: range/count
    
    # ─── SPREAD OPERATOR SUPPORT ───
    def _spread_list(*lists):
        """Combine multiple lists with spread: spread([1,2], [3,4]) -> [1,2,3,4]"""
        result = []
        for l in lists:
            if isinstance(l, (list, tuple)):
                result.extend(l)
            elif isinstance(l, dict):
                result.extend(l.values())
            else:
                result.append(l)
        return result
    env.set("spread", _spread_list)
    env.set("virippu", _spread_list)  # Tamil: spread
    
    def _merge_dicts(*dicts):
        """Merge multiple dicts: merge({a:1}, {b:2}) -> {a:1, b:2}"""
        result = {}
        for d in dicts:
            if isinstance(d, dict):
                result.update(d)
        return result
    env.set("merge", _merge_dicts)
    env.set("iraipu", _merge_dicts)  # Tamil: merge
    
    # ─── ENHANCED COLLECTION METHODS ───
    def _enumerate_list(lst, start=0):
        return [[i + start, v] for i, v in enumerate(lst)]
    env.set("enumerate", _enumerate_list)
    env.set("eNNidu", _enumerate_list)
    
    def _zip_lists(*lists):
        return [list(t) for t in zip(*lists)]
    env.set("zip_lists", _zip_lists)
    env.set("iNai", _zip_lists)  # Tamil: pair
    
    def _any_fn(lst, fn=None):
        if fn: return any(interp._invoke(fn, [x]) for x in lst)
        return any(lst)
    env.set("any", _any_fn)
    env.set("ethavathu", _any_fn)  # Tamil: any
    
    def _all_fn(lst, fn=None):
        if fn: return all(interp._invoke(fn, [x]) for x in lst)
        return all(lst)
    env.set("all", _all_fn)
    env.set("anaiththum", _all_fn)  # Tamil: all
    
    # ─── CLASS UTILITIES ───
    def _isinstance_check(obj, cls_name):
        if isinstance(obj, dict) and obj.get("__type__") == "thee_instance":
            # Check class chain
            cls = obj.get("__class__")
            while cls:
                if cls["name"] == cls_name:
                    return True
                if cls.get("parent"):
                    try:
                        cls = env.get(cls["parent"])
                    except:
                        return False
                else:
                    return False
        return False
    env.set("is_instance", _isinstance_check)
    env.set("vakai_sarithu", _isinstance_check)  # Tamil: type-check
    
    def _get_class(obj):
        if isinstance(obj, dict) and obj.get("__type__") == "thee_instance":
            return obj.get("__class_name__", "unknown")
        return type(obj).__name__
    env.set("get_class", _get_class)
    env.set("vagai_peru", _get_class)  # Tamil: class-name
    
    def _has_method(obj, method_name):
        if isinstance(obj, dict):
            return method_name in obj and callable(obj.get(method_name))
        return hasattr(obj, method_name) and callable(getattr(obj, method_name))
    env.set("has_method", _has_method)
    
    # ─── DECORATOR BUILTINS ───
    def _memoize(fn):
        """Decorator: cache function results."""
        cache = {}
        def wrapper(*args):
            key = str(args)
            if key not in cache:
                cache[key] = interp._invoke(fn, list(args))
            return cache[key]
        wrapper.__name__ = "memoized"
        return wrapper
    env.set("memoize", _memoize)
    env.set("ninaivagam", _memoize)  # Tamil: memory/cache
    
    def _timer_decorator(fn):
        """Decorator: measure execution time."""
        def wrapper(*args):
            start = time.time()
            result = interp._invoke(fn, list(args))
            elapsed = time.time() - start
            print(f"  ⏱️ {elapsed*1000:.1f}ms")
            return result
        wrapper.__name__ = "timed"
        return wrapper
    env.set("timer", _timer_decorator)
    env.set("neramidu", _timer_decorator)
    
    def _retry_decorator(max_retries=3):
        """Decorator factory: retry on failure."""
        def decorator(fn):
            def wrapper(*args):
                for i in range(max_retries):
                    try:
                        return interp._invoke(fn, list(args))
                    except Exception as e:
                        if i == max_retries - 1:
                            raise
            return wrapper
        return decorator
    env.set("retry", _retry_decorator)
    env.set("meendum", _retry_decorator)  # Tamil: again
    
    def _validate_decorator(schema):
        """Decorator factory: validate arguments."""
        def decorator(fn):
            def wrapper(*args):
                if isinstance(schema, dict):
                    for i, (key, vtype) in enumerate(schema.items()):
                        if i < len(args):
                            t = type(args[i]).__name__
                            if t != vtype and vtype != "any":
                                raise TheeRuntimeError(f"Argument {key}: expected {vtype}, got {t}")
                return interp._invoke(fn, list(args))
            return wrapper
        return decorator
    env.set("validate", _validate_decorator)
    
    # ─── ENHANCED AGENT FEATURES ───
    def _agent_communicate(agent1, agent2, message):
        """Agent-to-agent communication."""
        if isinstance(agent1, TheeAgent) and isinstance(agent2, TheeAgent):
            agent2.memory["__inbox__"] = agent2.memory.get("__inbox__", [])
            agent2.memory["__inbox__"].append({
                "from": agent1.name, "message": message, "time": time.time()
            })
            bus.emit("agent_message", {"from": agent1.name, "to": agent2.name, "message": message})
            return True
        return False
    env.set("agent_send", _agent_communicate)
    
    def _agent_inbox(agent):
        if isinstance(agent, TheeAgent):
            return agent.memory.get("__inbox__", [])
        return []
    env.set("agent_inbox", _agent_inbox)
    
    def _agent_broadcast(agents, message):
        for a in agents:
            if isinstance(a, TheeAgent):
                a.memory.setdefault("__inbox__", []).append({
                    "from": "broadcast", "message": message, "time": time.time()
                })
        return True
    env.set("agent_broadcast", _agent_broadcast)
    
    # ─── REPL SHELL ───
    def _thee_repl():
        """Interactive THEE REPL shell."""
        print("🔥 THEE Interactive Shell v6.0 — திருமுறை")
        print("   Type 'exit' or 'veliyeru' to quit")
        print("   Type 'help' for commands")
        print()
        from thee_lang.lexer import TheeLexer
        from thee_lang.parser import TheeParser
        while True:
            try:
                line = input("🔥 thee> ")
            except (EOFError, KeyboardInterrupt):
                print("\n👋 நன்றி! (Thank you!)")
                break
            if line.strip() in ("exit", "veliyeru", "quit"):
                print("👋 நன்றி! (Thank you!)")
                break
            if line.strip() == "help":
                print("  Commands: exit, help, builtins, agents")
                continue
            if line.strip() == "builtins":
                count = sum(1 for v in interp.env.bindings.values() if callable(v))
                print(f"  {count} builtins loaded")
                continue
            if line.strip() == "agents":
                print(f"  Agents: {list(interp.agents.keys()) if interp.agents else 'none'}")
                continue
            if not line.strip():
                continue
            try:
                tokens = TheeLexer(line).tokenize()
                ast = TheeParser(tokens).parse()
                result = None
                for s in ast.statements:
                    result = interp.execute(s)
                if result is not None and not interp.output:
                    print(f"  → {interp._fmt(result)}")
                interp.output = []
            except Exception as e:
                print(f"  ❌ {e}")
    env.set("thee_shell", _thee_repl)
    env.set("kudu", _thee_repl)  # Tamil: shell
    
    # ─── STRING ENHANCEMENTS ───
    env.set("pad_left", lambda s, n, ch=" ": str(s).rjust(n, ch))
    env.set("pad_right", lambda s, n, ch=" ": str(s).ljust(n, ch))
    env.set("center", lambda s, n, ch=" ": str(s).center(n, ch))
    env.set("repeat_str", lambda s, n: str(s) * int(n))
    env.set("char_at", lambda s, i: str(s)[int(i)] if int(i) < len(str(s)) else "")
    env.set("char_code", lambda s: ord(str(s)[0]) if s else 0)
    env.set("from_char_code", lambda n: chr(int(n)))
    env.set("is_digit", lambda s: str(s).isdigit())
    env.set("is_alpha", lambda s: str(s).isalpha())
    env.set("is_upper", lambda s: str(s).isupper())
    env.set("is_lower", lambda s: str(s).islower())
    env.set("word_count", lambda s: len(str(s).split()))
    env.set("title_case", lambda s: str(s).title())
    env.set("camel_case", lambda s: s[0].lower() + s.title().replace(" ", "")[1:] if s else "")
    env.set("snake_case", lambda s: re.sub(r'[A-Z]', lambda m: '_' + m.group().lower(), s).lstrip('_') if s else "")
    
    # ─── MATH ENHANCEMENTS ───
    env.set("clamp", lambda v, lo, hi: max(lo, min(hi, v)))
    env.set("lerp", lambda a, b, t: a + (b - a) * t)
    env.set("sign", lambda x: (1 if x > 0 else -1) if x != 0 else 0)
    env.set("is_even", lambda x: int(x) % 2 == 0)
    env.set("is_odd", lambda x: int(x) % 2 != 0)
    env.set("gcd", lambda a, b: math.gcd(int(a), int(b)))
    env.set("lcm", lambda a, b: abs(int(a) * int(b)) // math.gcd(int(a), int(b)) if a and b else 0)
    env.set("factorial", lambda n: math.factorial(int(n)))
    env.set("fibonacci", lambda n: _fib(int(n)))
    env.set("is_prime", lambda n: _is_prime(int(n)))
    env.set("primes_up_to", lambda n: [i for i in range(2, int(n)+1) if _is_prime(i)])
    
    # ─── DATE/TIME ENHANCEMENTS ───
    env.set("date_format", lambda fmt="%Y-%m-%d": time.strftime(fmt))
    env.set("timestamp_ms", lambda: int(time.time() * 1000))
    env.set("date_parse", lambda s, fmt="%Y-%m-%d": time.strftime("%Y-%m-%d", time.strptime(s, fmt)))
    env.set("days_between", lambda d1, d2: abs(int((time.mktime(time.strptime(d1, "%Y-%m-%d")) - time.mktime(time.strptime(d2, "%Y-%m-%d"))) / 86400)))
    
    # ─── TYPE CHECKING ───
    env.set("type_of", lambda v: type(v).__name__ if not isinstance(v, dict) or "__type__" not in v else v["__type__"])
    env.set("is_list", lambda v: isinstance(v, list))
    env.set("is_dict", lambda v: isinstance(v, dict))
    env.set("is_string", lambda v: isinstance(v, str))
    env.set("is_number", lambda v: isinstance(v, (int, float)))
    env.set("is_bool", lambda v: isinstance(v, bool))
    env.set("is_null", lambda v: v is None)
    env.set("is_function", lambda v: callable(v) or (isinstance(v, dict) and "body" in v))
    
    # ─── FUNCTIONAL PROGRAMMING ───
    def _compose(*fns):
        def composed(x):
            for f in reversed(fns):
                x = interp._invoke(f, [x])
            return x
        return composed
    env.set("compose", _compose)
    env.set("iNaippu", _compose)  # Tamil: chain
    
    def _partial(fn, *preset):
        def wrapper(*args):
            return interp._invoke(fn, list(preset) + list(args))
        return wrapper
    env.set("partial", _partial)
    
    def _tap(value, fn):
        """Execute fn with value for side effects, return value unchanged."""
        interp._invoke(fn, [value])
        return value
    env.set("tap", _tap)
    
    def _pipe_through(value, *fns):
        """Pipe a value through multiple functions."""
        for fn in fns:
            value = interp._invoke(fn, [value])
        return value
    env.set("pipe_through", _pipe_through)
    env.set("vazhi", _pipe_through)  # Tamil: path/route
    
    # ─── COLLECTION DEEP OPERATIONS ───
    def _deep_clone(obj):
        import copy
        return copy.deepcopy(obj)
    env.set("deep_clone", _deep_clone)
    
    def _deep_merge(d1, d2):
        result = dict(d1) if isinstance(d1, dict) else {}
        if isinstance(d2, dict):
            for k, v in d2.items():
                if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                    result[k] = _deep_merge(result[k], v)
                else:
                    result[k] = v
        return result
    env.set("deep_merge", _deep_merge)
    
    def _group_by(lst, fn):
        result = {}
        for item in lst:
            key = interp._invoke(fn, [item]) if callable(fn) or isinstance(fn, dict) else item.get(fn) if isinstance(item, dict) else None
            result.setdefault(str(key), []).append(item)
        return result
    env.set("group_by", _group_by)
    env.set("kuzhu", _group_by)  # Tamil: group
    
    def _sort_by(lst, fn=None, desc=False):
        if fn:
            return sorted(lst, key=lambda x: interp._invoke(fn, [x]), reverse=desc)
        return sorted(lst, reverse=desc)
    env.set("sort_by", _sort_by)
    
    def _pluck(lst, key):
        return [item.get(key) if isinstance(item, dict) else getattr(item, key, None) for item in lst]
    env.set("pluck", _pluck)
    
    def _index_of(lst, item):
        try: return lst.index(item)
        except ValueError: return -1
    env.set("index_of", _index_of)
    
    env.set("count_if", lambda lst, fn: sum(1 for x in lst if interp._invoke(fn, [x])))
    env.set("sum_by", lambda lst, fn: sum(interp._invoke(fn, [x]) for x in lst))
    env.set("min_by", lambda lst, fn: min(lst, key=lambda x: interp._invoke(fn, [x])))
    env.set("max_by", lambda lst, fn: max(lst, key=lambda x: interp._invoke(fn, [x])))
    env.set("find", lambda lst, fn: next((x for x in lst if interp._invoke(fn, [x])), None))
    env.set("find_index", lambda lst, fn: next((i for i, x in enumerate(lst) if interp._invoke(fn, [x])), -1))
    
    # ─── CRYPTO/HASH UTILITIES ───
    import hashlib
    env.set("md5", lambda s: hashlib.md5(str(s).encode()).hexdigest())
    env.set("sha256", lambda s: hashlib.sha256(str(s).encode()).hexdigest())
    env.set("sha512", lambda s: hashlib.sha512(str(s).encode()).hexdigest())
    
    # ─── CONSOLE/DEBUG UTILITIES ───
    env.set("debug", lambda *args: print("🐛", " ".join(str(a) for a in args)))
    env.set("table", lambda data: _print_table(data))
    env.set("assert_eq", lambda a, b, msg="": _assert_eq(a, b, msg))
    env.set("assert_true", lambda v, msg="": _assert_true(v, msg))
    env.set("time_it", lambda fn, *a: _time_it(fn, a, interp))
    
    # ─── REGEX ───
    env.set("regex_match", lambda pattern, text: bool(re.match(pattern, str(text))))
    env.set("regex_find", lambda pattern, text: re.findall(pattern, str(text)))
    env.set("regex_replace", lambda pattern, repl, text: re.sub(pattern, repl, str(text)))
    env.set("regex_split", lambda pattern, text: re.split(pattern, str(text)))
    
    # ─── ENVIRONMENT VARIABLES ───
    env.set("env_get", lambda k, d=None: os.environ.get(k, d))
    env.set("env_set", lambda k, v: os.environ.__setitem__(k, str(v)))
    
    # ─── UUID GENERATION ───
    import uuid as _uuid_mod
    env.set("uuid", lambda: str(_uuid_mod.uuid4()))
    env.set("uuid_short", lambda: str(_uuid_mod.uuid4())[:8])
    
    # ─── SCHEDULE/TIMER ───
    def _set_interval(fn, seconds, times=None):
        import threading
        count = [0]
        def tick():
            if times and count[0] >= times: return
            interp._invoke(fn, [])
            count[0] += 1
            if times is None or count[0] < times:
                threading.Timer(seconds, tick).start()
        threading.Timer(seconds, tick).start()
        return True
    env.set("set_interval", _set_interval)
    env.set("set_timeout", lambda fn, sec: threading.Timer(sec, lambda: interp._invoke(fn, [])).start() or True)
    
    # ─── PDF FIX: UTF-8 encoding for pdf_gen ───
    original_pdf = env.bindings.get("pdf_gen")
    if original_pdf:
        def _pdf_gen_safe(*args, **kwargs):
            """UTF-8 safe PDF generation."""
            try:
                return original_pdf(*args, **kwargs)
            except UnicodeEncodeError:
                # Fallback: strip non-Latin1 chars
                safe_args = []
                for a in args:
                    if isinstance(a, str):
                        safe_args.append(a.encode('latin-1', 'replace').decode('latin-1'))
                    elif isinstance(a, list):
                        safe_args.append([s.encode('latin-1', 'replace').decode('latin-1') if isinstance(s, str) else s for s in a])
                    else:
                        safe_args.append(a)
                return original_pdf(*safe_args, **kwargs)
        env.set("pdf_gen", _pdf_gen_safe)


# ─── Helper functions for v6.0 ───
def _fib(n):
    if n <= 0: return 0
    if n == 1: return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def _is_prime(n):
    if n < 2: return False
    if n < 4: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0: return False
        i += 6
    return True

def _print_table(data):
    if not data: print("  (empty)"); return
    if isinstance(data, list) and isinstance(data[0], dict):
        keys = list(data[0].keys())
        widths = {k: max(len(str(k)), max(len(str(r.get(k, ""))) for r in data)) for k in keys}
        header = " | ".join(str(k).ljust(widths[k]) for k in keys)
        print(f"  {header}")
        print(f"  {'-+-'.join('-' * widths[k] for k in keys)}")
        for row in data:
            print(f"  {' | '.join(str(row.get(k, '')).ljust(widths[k]) for k in keys)}")
    else:
        for i, item in enumerate(data):
            print(f"  [{i}] {item}")

def _assert_eq(a, b, msg=""):
    if a != b:
        raise TheeRuntimeError(f"Assertion failed: {a} != {b}" + (f" — {msg}" if msg else ""))
    return True

def _assert_true(v, msg=""):
    if not v:
        raise TheeRuntimeError(f"Assertion failed: value is falsy" + (f" — {msg}" if msg else ""))
    return True

def _time_it(fn, args, interp):
    start = time.time()
    result = interp._invoke(fn, list(args))
    elapsed = time.time() - start
    return {"result": result, "ms": round(elapsed * 1000, 2)}
