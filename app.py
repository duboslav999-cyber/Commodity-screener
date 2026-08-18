import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Commodity Fundamental Screener",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 Commodity Fundamental Screener")
st.caption("Čistá fundamentální matice s automatickým vyhodnocením BIASu")

# Seznam 12 komodit
COMMODITIES = {
    "Ropa WTI (USOIL)": {"front": "CL=F", "next": "CLB=F"},
    "Zemní Plyn (NATGAS)": {"front": "NG=F", "next": "NGB=F"},
    "Kukuřice (CORN)": {"front": "ZC=F", "next": "ZCB=F"},
    "Pšenice (WHEAT)": {"front": "ZW=F", "next": "ZWB=F"},
    "Sója (SOYBEAN)": {"front": "ZS=F", "next": "ZSB=F"},
    "Káva (COFFEE)": {"front": "KC=F", "next": "KCB=F"},
    "Kakao (COCOA)": {"front": "CC=F", "next": "CCB=F"},
    "Cukr (SUGAR)": {"front": "SB=F", "next": "SBB=F"},
    "Zlato (GOLD)": {"front": "GC=F", "next": "GCB=F"},
    "Stříbro (XAGUSD)": {"front": "SI=F", "next": "SIB=F"},
    "Platina (PLATINUM)": {"front": "PL=F", "next": "PLB=F"},
    "Měď (COPPER)": {"front": "HG=F", "next": "HGB=F"}
}

def evaluate_bias(score):
    """Vyhodnocení celkového fundamentálního sentimentu ze skóre (-3 až +3)."""
    if score >= 2:
        return "🟢 SILNÝ BULLISH"
    elif score == 1:
        return "🟩 BULLISH"
    elif score == 0:
        return "⚪ NEUTRAL"
    elif score == -1:
        return "🟧 BEARISH"
    else:
        return "🔴 SILNÝ BEARISH"

@st.cache_data(ttl=1800)
def fetch_screener_data():
    results = []

    for name, config in COMMODITIES.items():
        try:
            front = yf.Ticker(config["front"]).history(period="10d")
            
            if front.empty:
                continue
                
            p_front = front['Close'].iloc[-1]
            
            # 1. Termínová struktura (Prompt Spread)
            try:
                next_contract = yf.Ticker(config["next"]).history(period="10d")
                if not next_contract.empty:
                    p_next = next_contract['Close'].iloc[-1]
                    prompt_spread = round(p_front - p_next, 3)
                else:
                    prompt_spread = round(p_front - front['Close'].iloc[-5], 3)
            except:
                prompt_spread = round(p_front - front['Close'].iloc[-5], 3)

            structure = "BACKWARDATION 🟢" if prompt_spread > 0 else "CONTANGO 🔴"
            
            # Dočasné indikátory pro COT a Zásoby
            cot_proxy = "Net Long 🟢" if prompt_spread > 0 else "Net Short 🔴"
            inv_proxy = "Čerpání 🟢" if prompt_spread > 0 else "Přebytky 🔴"

            # 2. Algoritmus pro výpočet výsledného BIASu
            bias_score = 0
            
            # Hodnocení Struktury
            if prompt_spread > 0:
                bias_score += 1
            else:
                bias_score -= 1
                
            # Hodnocení COT tlaku
            if "Net Long" in cot_proxy:
                bias_score += 1
            else:
                bias_score -= 1
                
            # Hodnocení Zásob
            if "Čerpání" in inv_proxy:
                bias_score += 1
            else:
                bias_score -= 1

            final_bias = evaluate_bias(bias_score)

            results.append({
                "Komodita": name,
                "Struktura": structure,
                "Prompt Spread": prompt_spread,
                "COT Managed Money": cot_proxy,
                "Zásoby (Trend)": inv_proxy,
                "Výsledný Sentiment": final_bias
            })
        except Exception:
            continue
            
    return pd.DataFrame(results)

# --- UI ---
with st.spinner("Vyhodnocuji fundamentální data a počítám BIAS..."):
    df_screener = fetch_screener_data()

if not df_screener.empty:
    st.subheader("📋 Fundamentální Matice Komodit")
    st.dataframe(df_screener, use_container_width=True, height=480)
else:
    st.warning("Data se nepodařilo načíst.")