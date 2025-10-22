import os
import streamlit as st
import requests
import pandas as pd
import json
import time
from typing import Any, Dict, Tuple, List

# ---------- Config ----------
API_URL = "https://decryptkarnrwalebkl.wasmer.app/"
API_KEY = os.getenv("API_KEY", None)
TERM_PARAM = "term"
KEY_PARAM = "key"

# ---------- Streamlit setup ----------
st.set_page_config(page_title="NumInfo", layout="wide", initial_sidebar_state="collapsed")

st.title("📱 NumInfo")
st.caption("Secure DecryptKarn API Lookup")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("⚙️ Settings")
    use_mock = st.checkbox("Mock Data", value=False)
    timeout = st.number_input("Timeout (s)", 5, 30, 10)
    auto_map = st.checkbox("Auto-map Fields", value=True)
    dark_mode = st.checkbox("Dark Mode", value=False)

    if not API_KEY and not use_mock:
        st.error("❌ Set API_KEY in Render Environment")
        st.stop()

# ---------- Styles ----------
st.markdown("""
<style>
body { background: var(--bg, #fff); color: var(--text, #0f172a); }
.card { background: linear-gradient(180deg, var(--card-bg, #fff), var(--card-bg-end, #f3f4f6));
        padding: 10px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 8px; }
.key { font-weight: 600; color: var(--key, #0b1220); }
.val { font-weight: 500; color: var(--val, #064e3b); }
.stButton>button { background: #3b82f6; color: white; border-radius: 6px; }
@media (max-width: 640px) { .card { padding: 8px; } .stButton>button { width: 100%; } }
</style>
""", unsafe_allow_html=True)

if dark_mode:
    st.markdown("""
    <style>
    :root { --bg: #1f2937; --text: #f3f4f6; --card-bg: #374151; --card-bg-end: #1f2937; --key: #e5e7eb; --val: #34d399; }
    section[data-testid="stSidebar"] { background: #111827; }
    .stTextInput>div>div>input { background: #374151; color: #f3f4f6; }
    </style>
    """, unsafe_allow_html=True)

# ---------- Input ----------
col1, col2 = st.columns([4, 1])
with col1:
    term = st.text_input("", placeholder="Phone / ID / Keyword")
with col2:
    lookup = st.button("🔍", use_container_width=True)

# ---------- Helpers ----------
def mock_lookup(term_value: str) -> Dict[str, Any]:
    samples = [
        {"name": "Rahul Kumar", "mobile": term_value, "email": "rahul.k@example.com"},
        {"name": "Priya Sharma", "mobile": term_value, "email": "priya.sh@example.com"},
        {"name": "Unknown", "mobile": term_value, "note": "No data"},
    ]
    return samples[hash(term_value) % len(samples)]

def call_api(term_value: str, timeout: int) -> Tuple[Any, int]:
    params = {KEY_PARAM: API_KEY, TERM_PARAM: term_value}
    response = requests.get(API_URL, params=params, timeout=timeout)
    status = response.status_code
    try:
        data = response.json()
    except ValueError:
        data = {"text": response.text}
    return data, status

def auto_map_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return {"raw": data}
    mapping = {
        "name": ["name", "fullname", "user"],
        "mobile": ["mobile", "phone", "number"],
        "email": ["email", "mail"],
        "address": ["address", "location"],
    }
    mapped = {}
    for out_key, keys in mapping.items():
        for k in keys:
            if k in data and data[k]:
                mapped[out_key] = data[k]
                break
    others = {k: v for k, v in data.items() if k not in [key for keys in mapping.values() for key in keys]}
    if others:
        mapped["others"] = others
    return mapped

def handle_multiple_results(result: Any) -> List[Dict[str, Any]]:
    if isinstance(result, list):
        return [auto_map_fields(item) if auto_map else item for item in result]
    elif isinstance(result, dict) and "results" in result and isinstance(result["results"], list):
        return [auto_map_fields(item) if auto_map else item for item in result["results"]]
    else:
        return [auto_map_fields(result) if auto_map else result]

# ---------- Lookup ----------
if lookup:
    if not term:
        st.error("❌ Enter a search term")
    else:
        with st.spinner("Fetching..."):
            try:
                if use_mock:
                    raw_result = mock_lookup(term)
                    status = 200
                else:
                    raw_result, status = call_api(term, timeout)
                time.sleep(0.2)
            except requests.RequestException as e:
                raw_result = {"error": str(e)}
                status = getattr(e.response, "status_code", None)
            except Exception as e:
                raw_result = {"error": str(e)}
                status = None

        st.info(f"Status: {status or 'N/A'}")

        results = handle_multiple_results(raw_result)

        tab1, tab2 = st.tabs(["📋 Results", "🧾 JSON"])
        with tab1:
            if len(results) > 1:
                for idx, display in enumerate(results, 1):
                    with st.expander(f"Result {idx}", expanded=idx == 1):
                        for key in ("name", "mobile", "email", "address"):
                            if key in display:
                                st.markdown(f"<div class='card'><div class='key'>{key.capitalize()}</div><div class='val'>{display.get(key, 'N/A')}</div></div>", unsafe_allow_html=True)
                        if "others" in display:
                            with st.expander("More"):
                                st.json(display["others"])
            else:
                display = results[0]
                cols = st.columns(2)
                for i, key in enumerate(["name", "mobile", "email", "address"]):
                    if key in display:
                        with cols[i % 2]:
                            st.markdown(f"<div class='card'><div class='key'>{key.capitalize()}</div><div class='val'>{display.get(key, 'N/A')}</div></div>", unsafe_allow_html=True)
                if "others" in display:
                    with st.expander("More"):
                        st.json(display["others"])

        with tab2:
            st.json(raw_result)
            try:
                df = pd.DataFrame(results)
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ CSV", csv_bytes, f"numinfo_{term}.csv", mime="text/csv", use_container_width=True)
            except Exception as e:
                st.warning(f"CSV Error: {e}")

st.caption("🔐 API key loaded from Render Environment")
