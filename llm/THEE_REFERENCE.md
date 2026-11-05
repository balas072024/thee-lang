# THEE quick reference (for model prompts)

THEE is a Python-like language with Tamil keywords. Every keyword has a Tamil-script form and a romanized alias; both work. Blocks use `{ }`, no semicolons, `//` comments.

| Meaning | Tamil | Romanized |
|---|---|---|
| print | மூச்சு | moochhu |
| variable | நா | na |
| constant | நிரை | nirai |
| function | தீ | thee |
| return | கனல் | kanal |
| if / elif / else | என்றால் / அல்லது / இல்லை | endral / allathu / illai |
| loop | ஓழுகு | ozhugu |
| in | உள் | ul |
| times | முறை | murai |
| while | வரை | varai |
| break / continue | நிறுத்து / தொடரு | niruthu / thodaru |
| try / catch / finally / throw | முயற்சி / பிழை_பிடி / இறுதி / எறி | muyarchi / pizhai / iruthi / eri |
| class / new / extends / super | வகு / புது / மிரசு / மூலம் | vagu / pudhu / mirasu / moolam |
| true / false / null | உண்மை / பொய் / சாம்பல் | unmai / poi / sambal |
| and / or / not | மற்றும் / அல் / அன்று | and / or / not |
| match / case / default | பொருத்து / வழக்கு / இயல்பு | poruthu / vazhakku / iyalbu |
| import | கொணர் | konar |

## Examples

```thee
// variables, print, strings
na name = "Murugan"
na age = 25
moochhu "Name: " + name + ", age: " + age
```

```thee
// function with if / elif / else
thee grade(mark) {
    endral mark >= 90 { kanal "A" }
    allathu mark >= 50 { kanal "Pass" }
    illai { kanal "Fail" }
}
moochhu grade(95)
moochhu grade(40)
```

```thee
// loops
ozhugu i ul range(1, 4) { moochhu i * i }
ozhugu 2 murai { moochhu "hi" }
na n = 3
varai n > 0 {
    moochhu n
    n = n - 1
}
```

```thee
// lists, dicts, lambdas
na nums = [3, 1, 2]
nums.push(5)
moochhu len(nums)
moochhu sort(nums)
moochhu nums.map((x) => x * 2)
moochhu nums.filter((x) => x > 2)
moochhu sum(nums)
na person = {"name": "Kavitha", "city": "Chennai"}
moochhu person["city"]
moochhu keys(person)
```

```thee
// recursion and assert_eq tests
thee fact(n) {
    endral n <= 1 { kanal 1 }
    kanal n * fact(n - 1)
}
assert_eq(fact(5), 120)
```

```thee
// classes
vagu Student {
    thee init(name, mark) {
        self.name = name
        self.mark = mark
    }
    thee passed() { kanal self.mark >= 50 }
}
na s = pudhu Student("Arun", 85)
moochhu s.name
moochhu s.passed()
```

```thee
// errors
muyarchi {
    eri "something went wrong"
} pizhai(e) {
    moochhu "caught: " + e.message
}
```

```thee
// the same program in Tamil script
தீ கூட்டு(அ, ஆ) {
    கனல் அ + ஆ
}
நா மொத்தம் = கூட்டு(2, 3)
மூச்சு மொத்தம்
ஓழுகு எண் உள் [1, 2, 3] {
    என்றால் எண் % 2 == 0 { மூச்சு "இரட்டை" } இல்லை { மூச்சு "ஒற்றை" }
}
```

Useful builtins: `len range sum min max abs round sort reverse unique join split upper lower trim replace contains starts_with ends_with substr slice char_at index_of count_str str int float keys values items is_prime factorial gcd sqrt pow floor ceil`.

Rules that differ from Python:
- No-argument string members are read without parentheses: `s.upper`, `s.lower`, `s.trim`, `s.length`. Prefer the builtins `upper(s)`, `lower(s)`, `trim(s)`, `len(s)`.
- Members with arguments use parentheses: `s.split(",")`, `s.contains("x")`, `nums.push(4)`, `nums.map((x) => x * 2)`.
- No slice syntax: use `slice(list, start, end)` and `substr(text, start, end)` (end is exclusive).
- `/` is true division (7 / 2 = 3.5); use `floor(a / b)` for integer division. `**` is power, `%` is remainder.
- A caught error `e` is a dict: use `e.message`.
- Printed booleans look like `உண்மை (true)`; compare values in tests with `assert_eq`, not printed text.
