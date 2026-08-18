import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(
    page_title="Commodity Fundamental Screener",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 Commodity Fundamental Screener")

# Seznam komodit s přímým mapováním na 1. a 2. kontrakt
COMMODITIES = {
    "Ropa WTI (USOIL)": {"front": "CL=F", "next": "CLB=F", "type": "OIL"},
    "Zemní Plyn (NATGAS)": {"front": "NG=F", "next": "NGB=F", "type": "GAS"},
    "Kukuřice (CORN)": {"front": "ZC=F", "next": "ZCB=F", "type": "AGRA"},
    "Pšenice (WHEAT)": {"front": "ZW=F", "next": "ZWB=F", "type": "AGRA"},
    "Sója (SOYBEAN)": {"front": "ZS=F", "next": "ZSB=F", "type": "SOY"},
    "Káva (COFFEE)": {"front": "KC=F", "next": "KCB=F", "type": "SOFT"},
    "Kakao (COCOA)": {"front": "CC=F", "next": "CCB=F", "type": "SOFT"},
    "Cukr (SUGAR)": {"front": "SB=F", "next": "SBB=F", "type": "SOFT"},
    "Zlato (GOLD)": {"front": "GC=F", "next": "GCB=F", "type": "METAL"},
    "Stříbro (XAGUSD)": {"front": "SI=F", "next": "SIB=F", "type": "METAL"},
    "Platina (PLATINUM)": {"front": "PL=F", "next": "PLB=F", "type": "METAL"},
    "Měď (COPPER)": {"front": "HG=F", "next": "HGB=F", "type": "METAL"}
}

def get_sector_margins():
    margins = {}
    try:
        wti = yf.Ticker("CL=F").history(period="5d")['Close'].iloc[-1]
        rb = yf.Ticker("RB=F").history(period="5d")['Close'].iloc[-1] * 42
        ho = yf.Ticker("HO=F").history(period="5d")['Close'].iloc[-1] * 42
        crack = round(((2 * rb) + (1 * ho) - (3 * wti)) / 3, 2)
        margins["OIL"] = f"${crack}/bbl"
    except:
        margins["OIL"] = "N/A"

    try:
        beans = yf.Ticker("ZS=F").history(period="5d")['Close'].iloc[-1] / 100
        oil = yf.Ticker("ZL=F").history(period="5d")['Close'].iloc[-1]
        meal = yf.Ticker("ZM=F").history(period="5d")['Close'].iloc[-1]
        crush = round((meal * 0.022) + (oil * 0.11) - beans, 2)
        margins["SOY"] = f"${crush}/bu"
    except:
        margins["SOY"] = "N/A"
        
    return margins

@st.cache_data(ttl=1800)
def fetch_screener_data():
    results = []
    margins = get_sector_margins()

    for name, config in COMMODITIES.items():
        try:
            front = yf.Ticker(config["front"]).history(period="10d")
            
            if front.empty:
                continue
                
            p_front = front['Close'].iloc[-1]
            
            # Pokus o stažení 2. kontraktu, v případě výpadku fallback na 5D odchylku
            try:
                next_contract = yf.Ticker(config["next"]).history(period="10d")
                if not next_contract.empty:
                    p_next = next_contract['Close'].iloc[-1]
                    prompt_spread = round(p_front - p_next, 3)
                else:
                    # Fallback: Porovnání s předchozím týdnem
                    prompt_spread = round(p_front - front['Close'].iloc[-5], 3)
            except:
                prompt_spread = round(p_front - front['Close'].iloc[-5], 3)

            structure = "BACKWARDATION 🟢" if prompt_spread > 0 else "CONTANGO 🔴"
            margin_info = margins.get(config["type"], "N/A")
            
            # Dočasný odhad pro COT a Zásoby
            cot_proxy = "Net Long 🟢" if prompt_spread > 0 else "Net Short 🔴"
            inv_proxy = "Čerpání 🟢" if prompt_spread > 0 else "Přebytky 🔴"

            results.append({
                "Komodita": name,
                "Struktura": structure,
                "Prompt Spread": prompt_spread,
                "Sektorová Marže": margin_info,
                "COT Managed Money": cot_proxy,
                "Zásoby (Trend)": inv_proxy
            })
        except Exception as e:
            continue
            
    return pd.DataFrame(results)

with st.spinner("Aktualizuji data z trhu..."):
    df_screener = fetch_screener_data()

if not df_screener.empty:
    st.subheader("📋 Fundamentální Matice Komodit")
    st.dataframe(df_screener, use_container_width=True, height=480)
else:
    st.warning("Data se nepodařilo načíst.")