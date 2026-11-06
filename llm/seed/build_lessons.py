# -*- coding: utf-8 -*-
"""Hand-written tutor lessons in spoken Tamil: a beginner's question and the tutor's answer.

These teach the tutor *style* (code first, then a short Tamil explanation). Every code
block is run in sandbox mode and its output must match `expect`. Writes lessons.jsonl.

  python3 llm/seed/build_lessons.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from common import run_thee, write_jsonl  # noqa: E402

# (question, code, explanation, expected stdout lines)
L = [
    ("THEE-ல முதல் program எப்படி எழுதுறது?",
     'மூச்சு "வணக்கம் உலகம்!"',
     "`மூச்சு` (romanized-ல `moochhu`) screen-ல print பண்ணும். Quotes-க்குள்ள இருக்கிறது ஒரு string. இத `hello.th` file-ல save பண்ணி `thee hello.th`-னு run பண்ணுங்க.",
     ["வணக்கம் உலகம்!"]),
    ("Variable-னா என்ன? ஒரு example காட்டுங்க",
     'நா பெயர் = "கவிதா"\nநா வயது = 21\nமூச்சு பெயர் + "-க்கு " + வயது + " வயசு"',
     "`நா` (na) வச்சு ஒரு variable உருவாக்குறோம், அதாவது ஒரு value-ஐ ஒரு பேர்ல வச்சுக்கிற பெட்டி மாதிரி. `+` string-ஐயும் number-ஐயும் சேர்த்து ஒரே வரியா மாத்திடும்.",
     ["கவிதா-க்கு 21 வயசு"]),
    ("Function எப்படி எழுதுறது?",
     "தீ கூட்டு(அ, ஆ) {\n    கனல் அ + ஆ\n}\nமூச்சு கூட்டு(10, 5)",
     "`தீ` (thee) ஒரு function-ஐ define பண்ணுது. Brackets-க்குள்ள inputs, `கனல்` (kanal) result-ஐ திருப்பி அனுப்பும். `கூட்டு(10, 5)` call பண்ணா 15 வரும்.",
     ["15"]),
    ("if else எப்படி use பண்றது?",
     'நா மார்க் = 72\nஎன்றால் மார்க் >= 50 {\n    மூச்சு "Pass ஆயிட்ட!"\n} இல்லை {\n    மூச்சு "அடுத்த தடவை try பண்ணு"\n}',
     "`என்றால்` (endral) condition உண்மையா இருந்தா முதல் block ஓடும், இல்லன்னா `இல்லை` (illai) block ஓடும். இங்க 72 >= 50 உண்மை, அதனால Pass.",
     ["Pass ஆயிட்ட!"]),
    ("மூணு condition இருந்தா? A, B, C grade மாதிரி",
     'தீ grade(m) {\n    என்றால் m >= 90 { கனல் "A" }\n    அல்லது m >= 75 { கனல் "B" }\n    இல்லை { கனல் "C" }\n}\nமூச்சு grade(80)',
     "நடுவுல இருக்கிற condition-க்கு `அல்லது` (allathu) போடணும், இது Python-ஓட elif மாதிரி. மேல இருந்து கீழ ஒவ்வொண்ணா check பண்ணி, முதல்ல உண்மையாகுற block மட்டும் ஓடும்.",
     ["B"]),
    ("Loop போட்டு 1 முதல் 5 வரை print பண்ணணும்",
     "ஓழுகு i உள் range(1, 6) {\n    மூச்சு i\n}",
     "`ஓழுகு` (ozhugu) loop, `உள்` (ul) அப்படின்னா \"இதுக்குள்ள\". `range(1, 6)` 1-ல ஆரம்பிச்சு 6-க்கு முன்னாடி நிக்கும், அதனால 1 முதல் 5 வரை வரும்.",
     ["1", "2", "3", "4", "5"]),
    ("ஒரு வேலையை 3 தடவை மட்டும் பண்ணணும், count வேணாம்",
     'ஓழுகு 3 முறை {\n    மூச்சு "வணக்கம்"\n}',
     "`ஓழுகு 3 முறை` (ozhugu 3 murai) அப்படியே 3 தடவை ஓடும். Counter variable தேவையில்லாத இடத்துல இது simple-ஆ இருக்கும்.",
     ["வணக்கம்", "வணக்கம்", "வணக்கம்"]),
    ("while loop THEE-ல எப்படி?",
     "நா n = 3\nவரை n > 0 {\n    மூச்சு n\n    n = n - 1\n}\nமூச்சு \"Go!\"",
     "`வரை` (varai) condition உண்மையா இருக்கிற வரைக்கும் ஓடிக்கிட்டே இருக்கும். உள்ள `n = n - 1` போடலன்னா loop நிக்கவே நிக்காது, அத மறக்காதீங்க.",
     ["3", "2", "1", "Go!"]),
    ("List-னா என்ன? அதுல item எப்படி சேர்க்கிறது?",
     'நா பழங்கள் = ["மாம்பழம்", "வாழைப்பழம்"]\nபழங்கள்.push("பலாப்பழம்")\nமூச்சு len(பழங்கள்)\nமூச்சு பழங்கள்[0]',
     "List-ல பல values-ஐ ஒரே variable-ல வச்சுக்கலாம். `.push()` கடைசியில ஒண்ணு சேர்க்கும், `len()` எத்தனை இருக்குன்னு சொல்லும், `[0]` முதல் item (counting 0-ல ஆரம்பிக்கும்).",
     ["3", "மாம்பழம்"]),
    ("List-ல எல்லா numbers-ஐயும் double பண்ண short-ஆ எழுத முடியுமா?",
     "நா எண்கள் = [1, 2, 3]\nமூச்சு எண்கள்.map((x) => x * 2)\nமூச்சு எண்கள்.filter((x) => x > 1)",
     "`(x) => x * 2` ஒரு சின்ன function (lambda). `.map` ஒவ்வொரு item-க்கும் அத apply பண்ணும், `.filter` condition உண்மையான items-ஐ மட்டும் வச்சுக்கும்.",
     ["[2, 4, 6]", "[2, 3]"]),
    ("Dictionary எப்படி use பண்றது?",
     'நா மாணவன் = {"பெயர்": "அருண்", "ஊர்": "மதுரை"}\nமூச்சு மாணவன்["ஊர்"]\nமாணவன்["மார்க்"] = 88\nமூச்சு keys(மாணவன்)',
     "Dictionary-ல key-value pairs இருக்கும், பேர் வச்சு value-ஐ எடுக்கலாம். புது key-க்கு value assign பண்ணா அது சேர்ந்துடும். `keys()` எல்லா keys-ஐயும் list-ஆ குடுக்கும்.",
     ["மதுரை", "[பெயர், ஊர், மார்க்]"]),
    ("Class எப்படி எழுதுறது?",
     'வகு நாய் {\n    தீ init(பெயர்) {\n        self.பெயர் = பெயர்\n    }\n    தீ குரை() {\n        கனல் self.பெயர் + ": லொள் லொள்!"\n    }\n}\nநா d = புது நாய்("டாமி")\nமூச்சு d.குரை()',
     "`வகு` (vagu) ஒரு class, அதாவது ஒரு blueprint. `init` object உருவாகும்போது ஓடும், `self` அந்த object-ஐ குறிக்கும். `புது` (pudhu) வச்சு object உருவாக்குறோம்.",
     ["டாமி: லொள் லொள்!"]),
    ("ஒரு class இன்னொரு class-ல இருந்து inherit பண்ண முடியுமா?",
     'வகு விலங்கு {\n    தீ init() { self.வகை = "விலங்கு" }\n    தீ சத்தம்() { கனல் "..." }\n}\nவகு பூனை மிரசு விலங்கு {\n    தீ சத்தம்() { கனல் "மியாவ்" }\n}\nமூச்சு புது பூனை().சத்தம்()',
     "`மிரசு` (mirasu) அப்படின்னா extends. பூனை, விலங்கு-ஓட எல்லாத்தையும் எடுத்துக்கும், `சத்தம்()` மட்டும் தன்னோட version-ஆ மாத்திக்குது.",
     ["மியாவ்"]),
    ("Error வந்தா program crash ஆகாம எப்படி handle பண்றது?",
     'முயற்சி {\n    நா வயது = int("abc")\n} பிழை_பிடி(e) {\n    மூச்சு "Number-ஆ மாத்த முடியல"\n}',
     "`முயற்சி` (muyarchi) block-ல error வந்தா, program நிக்காம `பிழை_பிடி` (pizhai) block-க்கு போயிடும். \"abc\"-ஐ number-ஆ மாத்த முடியாது, அதனால அந்த message வருது.",
     ["Number-ஆ மாத்த முடியல"]),
    ("நானே ஒரு error throw பண்ணலாமா?",
     'தீ வகு_(a, b) {\n    என்றால் b == 0 { எறி "zero-ஆல வகுக்க முடியாது" }\n    கனல் a / b\n}\nமுயற்சி {\n    மூச்சு வகு_(10, 0)\n} பிழை_பிடி(e) {\n    மூச்சு e.message\n}',
     "`எறி` (eri) நம்மளே ஒரு error-ஐ கிளப்ப use ஆகுது. Catch பண்ணும்போது `e` ஒரு dict, அதனால message-க்கு `e.message`.",
     ["zero-ஆல வகுக்க முடியாது"]),
    ("Recursion-னா என்ன? factorial வச்சு சொல்லுங்க",
     "தீ factorial(n) {\n    என்றால் n <= 1 { கனல் 1 }\n    கனல் n * factorial(n - 1)\n}\nமூச்சு factorial(5)",
     "Function தன்னையே call பண்றது recursion. ஒவ்வொரு தடவையும் n ஒண்ணு குறையுது, n 1 ஆனதும் நிக்குது. 5 × 4 × 3 × 2 × 1 = 120.",
     ["120"]),
    ("String-ல இருக்கிற ஒவ்வொரு எழுத்தையும் எப்படி எடுக்கிறது?",
     'ஓழுகு ch உள் list("THEE") {\n    மூச்சு ch\n}',
     "`list(text)` ஒரு string-ஐ எழுத்து எழுத்தா list-ஆ பிரிச்சு குடுக்கும். Tamil text-ல ஒரு உயிர்மெய் எழுத்து ரெண்டு Unicode characters-ஆ வரலாம், அது ஞாபகம் வச்சுக்கோங்க.",
     ["T", "H", "E", "E"]),
    ("String functions என்னென்ன இருக்கு?",
     'நா s = "  Chennai  "\nமூச்சு trim(s)\nமூச்சு upper(trim(s))\nமூச்சு replace("a-b-c", "-", " ")\nமூச்சு split("a,b,c", ",")',
     "`trim` ரெண்டு பக்க space-ஐயும் எடுக்கும், `upper` capital ஆக்கும், `replace` ஒண்ண இன்னொண்ணா மாத்தும், `split` ஒரு string-ஐ list-ஆ உடைக்கும்.",
     ["Chennai", "CHENNAI", "a b c", "[a, b, c]"]),
    ("Python-ல slice [1:3] பண்ணுவேன், THEE-ல?",
     'நா xs = [10, 20, 30, 40]\nமூச்சு slice(xs, 1, 3)\nமூச்சு substr("தமிழ்நாடு", 0, 5)',
     "THEE-ல `[1:3]` syntax இல்ல, அதுக்கு பதிலா `slice(list, start, end)` and string-க்கு `substr(text, start, end)`. End index சேராது, Python மாதிரியே.",
     ["[20, 30]", "தமிழ்"]),
    ("Division-ல decimal வேணாம், integer மட்டும் வேணும்",
     "மூச்சு 7 / 2\nமூச்சு floor(7 / 2)\nமூச்சு 7 % 2",
     "THEE-ல `/` எப்பவும் decimal division, 3.5 வரும். Integer-க்கு `floor()` போடுங்க. மீதி (remainder) வேணும்னா `%`.",
     ["3.5", "3", "1"]),
    ("என் code-ல 'Undefined' error வருது: மூச்சு மொத்தம்",
     "நா மொத்தம் = 0\nஓழுகு x உள் [5, 10] {\n    மொத்தம் = மொத்தம் + x\n}\nமூச்சு மொத்தம்",
     "'Undefined' வந்தா அந்த variable-ஐ முதல்ல `நா` வச்சு create பண்ணல-ன்னு அர்த்தம். Loop-க்கு முன்னாடி `நா மொத்தம் = 0` போட்டா சரியாயிடும்.",
     ["15"]),
    ("Romanized-லயும் எழுதலாமா? Tamil type பண்ண கஷ்டமா இருக்கு",
     'na peyar = "Bala"\nthee vanakkam(p) { kanal "Vanakkam " + p }\nmoochhu vanakkam(peyar)',
     "கண்டிப்பா! ஒவ்வொரு keyword-க்கும் romanized alias இருக்கு: `na`, `thee`, `kanal`, `moochhu`. ரெண்டையும் ஒரே file-ல கூட கலந்து எழுதலாம், ரெண்டும் ஒரே மாதிரி ஓடும்.",
     ["Vanakkam Bala"]),
    ("ஒரு list-ல பெரிய number-ஐ loop போட்டு எப்படி கண்டுபிடிக்கிறது?",
     "தீ பெரியது(xs) {\n    நா m = xs[0]\n    ஓழுகு x உள் xs {\n        என்றால் x > m { m = x }\n    }\n    கனல் m\n}\nமூச்சு பெரியது([4, 19, 7])",
     "முதல் item-ஐ இப்போதைக்கு பெரியதுன்னு வச்சுக்கிறோம். ஒவ்வொரு item-ஐயும் அதோட compare பண்ணி, பெருசா இருந்தா மாத்திக்கிறோம். கடைசியில m-ல பெரிய number இருக்கும்.",
     ["19"]),
    ("Test எப்படி எழுதுறது? என் function சரியான்னு check பண்ணணும்",
     'தீ square(n) { கனல் n * n }\nassert_eq(square(4), 16)\nassert_eq(square(-3), 9)\nமூச்சு "எல்லா test-உம் pass!"',
     "`assert_eq(actual, expected)` ரெண்டும் equal-ஆ இல்லன்னா error குடுக்கும். எல்லாம் pass ஆனா கடைசி line print ஆகும். புது function எழுதும்போதெல்லாம் 2-3 test போடுங்க.",
     ["எல்லா test-உம் pass!"]),
    ("Python package-ஐ THEE-ல use பண்ண முடியுமா?",
     "கொணர் python.statistics as st\nமூச்சு st.mean([2, 4, 6])",
     "`கொணர் python.<package>` (konar) எந்த Python package-ஐயும் import பண்ணும். Sandbox mode-ல இது block ஆகும், உங்க சொந்த computer-ல normal-ஆ ஓட்டுங்க.",
     None),  # Python imports are blocked in the sandbox, so this one is checked without it
]


def main():
    rows, bad = [], []
    for i, (q, code, expl, expect) in enumerate(L, 1):
        answer = f"```thee\n{code}\n```\n\n{expl}"
        rows.append({"id": f"lesson{i:02d}", "question_ta": q, "answer_ta": answer, "code": code})
        if expect is None:
            continue
        r = run_thee(code)
        got = [ln for ln in r["stdout"].splitlines()]
        if not r["ok"] or got != expect:
            bad.append((i, q, got, r["stderr"][:200]))
    write_jsonl(os.path.join(HERE, "lessons.jsonl"), rows)
    print(f"{len(rows)} lessons written, {len(rows) - len(bad)} verified")
    for b in bad:
        print("  FAIL", *b)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
