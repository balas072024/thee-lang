# 🇮🇳 THEE - Tamil Programming Language

> Write code in Tamil. Build the future.

THEE (Tamil Human-Equivalent Expression) is a full-featured programming language that lets you write code in Tamil script.

## ✨ Features

- 🗣️ **Tamil Syntax** - Write variables, functions, classes in Tamil
- ⚡ **Fast** - Built in Python, runs instantly
- 🤖 **AI Built-in** - `ai_complete()` for AI-powered coding
- 🌐 **HTTP Requests** - `http_get()` and `http_post()` 
- 🔄 **Async/Await** - Concurrent programming support
- 📦 **Modules** - Import/export functionality
- 🎯 **Structs** - Custom data types
- 🔧 **GPIO/Arduino** - Hardware programming support
- 📚 **192 Built-ins** - Extensive standard library

## 🏃 Quick Start

```bash
# Run a THEE program
thee hello.thee
```

## 📝 Example

```tamil
// Hello World in Tamil
மூச்சு "வணக்கம் உலகம்!"

// Variables
நா பெயர் = "முருகன்"
மூச்சு "பெயர்: " + பெயர்

// Function
தீ வணக்கம்(நபர்) {
    கனல் "வணக்கம் " + நபர்
}

// Class
வகு மாணவன் {
    தீ init(பெயர், மதிப்பெண்) {
        self.பெயர் = பெயர்
        self.மதிப்பெண் = மதிப்பெண்
    }
}
```

## 📋 Keywords

| English | Tamil |
|---------|-------|
| print | மூச்சு, moochhu |
| var | na,நா |
| function | thee,தீ |
| class | vagu,வகு |
| for | ozhugu |
| if | enral,என்றால் |
| else | illai,இல்லை |
| try | muyarchi,முயற்சி |
| catch | pilai,பிழை |
| return | virambu,விற்பு |
| import | kondu,கொண்டு |

## 🤖 AI Integration

```tamil
na code = ai_complete("Write a function to add two numbers in THEE")
```
Requires `thee_llm` module.

## 🐍 Python Bridge

Import any installed Python package directly:

```
konar python.statistics as st
moochhu st.mean([1, 2, 3, 4])      // 2.5

konar python.os.path               // alias defaults to the last part: path
moochhu path.join("a", "b")
```

## 🛡️ Sandbox Mode (பாதுகாப்பு முறை)

Run code you didn't write yourself — for example code from the THEE AI tutor — safely:

```bash
thee --sandbox program.thee                 # 10s timeout, 512 MB memory cap
thee --sandbox --timeout 5 --max-mem 256 program.thee
THEE_SANDBOX=1 thee program.thee            # same, via environment variable
```

Sandbox mode blocks files, network, shell commands, GPIO, environment variables,
AI API calls, code generators, `py_*` helpers, `konar python.*`, `konar os/http/ai`,
file imports, and private (`_`) attributes on Python objects. Databases are
limited to `:memory:`. Pure THEE code — loops, functions, classes, strings,
math, charts, in-memory data — runs normally. From Python:
`TheeInterpreter(sandbox=True)`.

Tests: `python3 -m unittest discover -s tests -v`

## 📦 Installation

```bash
# Clone
git clone https://github.com/balas072024/thee-lang.git
cd thee-lang

# Install
python install.bat

# Run
thee examples/hello.thee
```

## 📂 Examples

- `examples/hello.thee` - Basic Hello World
- `examples/calculator.thee` - Calculator demo
- `examples/tamil.thee` - Full Tamil demo
- `examples/agents.thee` - AI agents demo

## 📊 Stats

- **Language**: Python-based interpreter
- **Version**: v6.0
- **Lines of Code**: ~5000+
- **Built-in Functions**: 192
- **Platform**: Windows, Linux, Mac

## 🌍 Why THEE?

1. **First Tamil Programming Language** - No competitors
2. **Educational** - Teach programming in native language
3. **AI-Powered** - Built-in LLM integration
4. **Hardware Ready** - Arduino/GPIO support
5. **Open Source** - Free to use and modify

## 📄 License

MIT License - Free to use, modify, and distribute.

## 👨‍💻 Author

**Bala (Balamurugan Suriyaprakash)**
- Built with 🇮🇳 pride
- Powered by Tamil engineering

---

*🇮🇳 தமிழ் நிரலாக்கத்தின் எதிர்காலம் - THEE!*
