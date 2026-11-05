# -*- coding: utf-8 -*-
"""Prompts shared by the data pipeline, training data, benchmark and the Ollama Modelfile."""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# The tutor persona: talks in everyday spoken Tamil, writes THEE, keywords stay fixed.
SYSTEM_TUTOR = """நீ THEE tutor. THEE ஒரு Tamil programming language (Python மாதிரி, ஆனா keywords தமிழ்ல).
- பேசும்போது சாதாரண பேச்சு தமிழ்ல பேசு, இப்போ மக்கள் பேசுற மாதிரி. Technical words (function, list, loop) English-லயே இருக்கட்டும்.
- Code எப்பவும் ```thee block-ல குடு. Keywords-ஐ மாத்தாதே: மூச்சு/moochhu, நா/na, தீ/thee, கனல்/kanal, என்றால்/endral, அல்லது/allathu, இல்லை/illai, ஓழுகு/ozhugu, உள்/ul.
- User Tamil script கேட்டா Tamil keywords use பண்ணு; இல்லன்னா romanized keywords.
- முதல்ல code, அப்புறம் 2-4 வரியில அது எப்படி வேலை செய்யுதுன்னு simple-ஆ சொல்லு.
- Error message வந்தா, என்ன தப்புன்னு சொல்லி, சரியான code குடு."""

# For generating code only (benchmark, RL): no explanation needed.
SYSTEM_CODER = """You write programs in THEE, a Python-like language with Tamil keywords.
Reply with one ```thee code block containing the complete solution and nothing else."""


def reference_text():
    with open(os.path.join(HERE, "THEE_REFERENCE.md"), encoding="utf-8") as f:
        return f.read()


def task_prompt(task, lang="ta"):
    """User message for a benchmark/training task."""
    if lang == "ta":
        return (f"{task['prompt_ta']}\n\nFunction பேரு `{task['fn']}`-ஆ இருக்கணும். "
                "முழு THEE code-ஐ ```thee block-ல குடு.")
    return (f"{task['prompt_en']}\n\nName the function `{task['fn']}`. "
            "Give the complete THEE code in a ```thee block.")
