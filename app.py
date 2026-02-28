import requests
import streamlit as st

url = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Audio Study Assistant", layout="centered")
st.title("AI Audio Study Assistant")
st.caption("Global Innovation Build Challenge V1")

if "sum" not in st.session_state:
    st.session_state["sum"] = []
if "quiz" not in st.session_state:
    st.session_state["quiz"] = []
if "aud" not in st.session_state:
    st.session_state["aud"] = b""
if "err" not in st.session_state:
    st.session_state["err"] = ""
if "rid" not in st.session_state:
    st.session_state["rid"] = 0

text = st.text_area("Paste lecture notes", height=260)

if st.button("Process"):
    if not text.strip():
        st.session_state["err"] = "Please paste lecture notes first."
    else:
        st.session_state["err"] = ""
        with st.spinner("Processing..."):
            try:
                requests.post(f"{url}/upload", json={"text": text}, timeout=20).raise_for_status()

                a = requests.post(f"{url}/summarize", json={"text": text}, timeout=30)
                a.raise_for_status()
                st.session_state["sum"] = a.json().get("summary", [])

                b = requests.post(f"{url}/quiz", json={"text": text}, timeout=30)
                b.raise_for_status()
                st.session_state["quiz"] = b.json().get("quiz", [])

                c = "\n".join(st.session_state["sum"])
                d = requests.post(f"{url}/tts", json={"text": c}, timeout=90)
                d.raise_for_status()
                st.session_state["aud"] = d.content

                st.session_state["rid"] += 1
            except requests.RequestException as e:
                st.session_state["err"] = f"Backend error: {e}"

if st.session_state["err"]:
    st.error(st.session_state["err"])

if st.session_state["sum"]:
    st.subheader("Summary")
    for i in st.session_state["sum"]:
        st.markdown(f"- {i}")

if st.session_state["aud"]:
    st.subheader("Audio Summary")
    st.audio(st.session_state["aud"], format="audio/mp3")

if st.session_state["quiz"]:
    st.subheader("Quiz")
    rid = st.session_state["rid"]

    for i, q in enumerate(st.session_state["quiz"], 1):
        st.write(f"{i}. {q['q']}")
        st.radio(
            f"Answer {i}",
            q["opt"],
            key=f"ans_{rid}_{i}",
            index=None,
            label_visibility="collapsed",
        )

    if st.button("Check Answers"):
        a = 0
        b = len(st.session_state["quiz"])
        c = 0

        for i, q in enumerate(st.session_state["quiz"], 1):
            v = st.session_state.get(f"ans_{rid}_{i}")
            if v is None:
                continue
            c += 1
            if v == q["opt"][q["ans"]]:
                a += 1

        st.info(f"Score: {a}/{b}")
        if c < b:
            st.warning("Some questions are unanswered.")
