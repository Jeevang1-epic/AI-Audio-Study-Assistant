import io
import random
import re
from collections import Counter
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from gtts import gTTS
from pydantic import BaseModel

app = FastAPI(title="AI Audio Study Assistant")
db = {"text": ""}

stop = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
    "you",
    "your",
    "this",
    "these",
    "those",
    "or",
    "if",
    "but",
    "not",
    "can",
    "we",
    "they",
    "their",
    "our",
    "about",
    "into",
    "than",
    "then",
    "there",
    "here",
    "when",
    "where",
    "how",
    "what",
    "why",
}


class InText(BaseModel):
    text: str


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split(text: str) -> List[str]:
    a = clean(text)
    if not a:
        return []
    b = re.split(r"(?<=[.!?])\s+", a)
    return [i.strip() for i in b if i.strip()]


def words(text: str) -> List[str]:
    a = re.findall(r"[a-zA-Z']+", text.lower())
    return [i for i in a if i not in stop and len(i) > 2]


def make_sum(text: str, n: int = 3) -> List[str]:
    a = split(text)
    if not a:
        return []

    b = words(text)
    out: List[str] = []

    if b:
        c = Counter(b)
        d = []
        for i, s in enumerate(a):
            w = words(s)
            v = sum(c.get(x, 0) for x in w) / (len(w) or 1)
            d.append((v, i, s))
        d.sort(key=lambda x: x[0], reverse=True)
        out = [i[2] for i in sorted(d[:n], key=lambda x: x[1])]
    else:
        out = a[:n]

    for s in a:
        if len(out) >= n:
            break
        if s not in out:
            out.append(s)

    e = []
    for i in out:
        j = i.strip()
        if not j:
            continue
        if j[-1] not in ".!?":
            j += "."
        e.append(j)

    if len(e) < n:
        p = [i.strip() for i in re.split(r"[;,]\s*", clean(text)) if len(i.strip()) > 15]
        for i in p:
            if len(e) >= n:
                break
            j = i if i.endswith((".", "!", "?")) else i + "."
            if j not in e:
                e.append(j)

    while len(e) < n and e:
        e.append(e[-1])

    return e[:n]


def make_quiz(text: str, n: int = 3) -> List[Dict]:
    a = split(text)
    if not a:
        return []

    r = random.Random(11)
    pool = list(dict.fromkeys(words(text)))
    if len(pool) < 6:
        pool += ["concept", "detail", "example", "result", "topic", "idea"]

    out: List[Dict] = []
    seen = set()

    for s in a:
        w = [i for i in words(s) if i not in seen]
        if not w:
            continue

        ans = max(w, key=len)
        seen.add(ans)

        q = re.sub(rf"\b{re.escape(ans)}\b", "____", s, flags=re.IGNORECASE, count=1)
        if "____" not in q:
            q = "____ " + s

        d = [i for i in pool if i != ans]
        r.shuffle(d)
        opt = [ans] + d[:2]
        while len(opt) < 3:
            opt.append("term")

        r.shuffle(opt)
        out.append(
            {
                "q": f"Which word best completes this note: {q}",
                "opt": opt[:3],
                "ans": opt[:3].index(ans),
            }
        )

        if len(out) >= n:
            break

    b = make_sum(text, n)
    i = 0
    while len(out) < n and i < len(b):
        s = b[i]
        ans = pool[(i + 1) % len(pool)]
        d = [x for x in pool if x != ans]
        r.shuffle(d)
        opt = [ans] + d[:2]
        r.shuffle(opt)
        out.append(
            {
                "q": f"Which term is most related to this point: {s}",
                "opt": opt,
                "ans": opt.index(ans),
            }
        )
        i += 1

    while len(out) < n:
        opt = ["concept", "detail", "example"]
        r.shuffle(opt)
        out.append(
            {
                "q": "Which option is most likely a key study term from the notes?",
                "opt": opt,
                "ans": opt.index("concept"),
            }
        )

    return out[:n]


@app.post("/upload")
def upload(a: InText):
    text = clean(a.text)
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")
    db["text"] = text
    return {"ok": True, "chars": len(text)}


@app.post("/summarize")
def summarize(a: InText):
    text = clean(a.text)
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")
    sum = make_sum(text, 3)
    return {"summary": sum}


@app.post("/quiz")
def quiz(a: InText):
    text = clean(a.text)
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")
    q = make_quiz(text, 3)
    return {"quiz": q}


@app.post("/tts")
def tts(a: InText):
    text = clean(a.text)
    if not text:
        raise HTTPException(status_code=400, detail="Text is empty")
    try:
        mp = io.BytesIO()
        t = gTTS(text=text, lang="en")
        t.write_to_fp(mp)
        mp.seek(0)
        h = {"Content-Disposition": "attachment; filename=summary.mp3"}
        return StreamingResponse(mp, media_type="audio/mpeg", headers=h)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS failed: {e}")
