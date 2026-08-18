import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(
    page_title="Commodity Fundamental Screener",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 Commodity Fundamental Screener")
st.caption("Čistý fundamentální přehled s reálnými daty")

# Seznam komodit
COMMODITIES = {
    "Ropa WTI (USOIL)": {"front": "CL=F", "next": "CLM26.NYM", "type": "OIL"},
    "Zemní Plyn (NATGAS)": {"front": "NG=F", "next": "NGM26.NYM", "type": "GAS"},
    "Kukuřice (CORN)": {"front": "ZC=F", "next": "ZCN26.CBT", "type": "AGRA"},
    "Pšenice (WHEAT)": {"front": "ZW=F", "next": "ZWN26.CBT", "type": "AGRA"},
    "Sója (SOYBEAN)": {"front": "ZS=F", "next": "ZSN26.CBT", "type": "SOY"},
    "Káva (COFFEE)": {"front": "KC=F", "next": "KCN26.NYB", "type": "SOFT"},
    "Kakao (COCOA)": {"front": "CC=F", "next": "CCN26.NYB", "type": "SOFT"},
    "Cukr (SUGAR)": {"front": "SB=F", "next": "SBN26.NYB", "type": "SOFT"},
    "Zlato (GOLD)": {"front": "GC=F", "next": "GCM26.CMX", "type": "METAL"},
    "Stříbro (XAGUSD)": {"front": "SI=F", "next": "SIN26.CMX", "type": "METAL"},
    "Platina (PLATINUM)": {"front": "PL=F", "next": "PLN26.NYM", "type": "METAL"},
    "Měď (COPPER)": {"front": "HG=F", "next": "HGM26.CMX", "type": "METAL"}
}

# 1. Výpočet sektorových marží (Crack & Crush Spreads)
def get_sector_margins():
    margins = {}
    
    # Ropa: 3:2:1 Crack Spread
    try:
        wti = yf.Ticker("CL=F").history(period="5d")['Close'].iloc[-1]
        rb = yf.Ticker("RB=F").history(period="5d")['Close'].iloc[-1] * 42  # Gasoline $/bbl
        ho = yf.Ticker("HO=F").history(period="5d")['Close'].iloc[-1] * 42  # Heating Oil $/bbl
        crack = round(((2 * rb) + (1 * ho) - (3 * wti)) / 3, 2)
        margins["OIL"] = f"${crack}/bbl"
    except:
        margins["OIL"] = "N/A"

    # Sója: Soy Crush Spread (Soybeans vs Soybean Oil + Soybean Meal)
    try:
        beans = yf.Ticker("ZS=F").history(period="5d")['Close'].iloc[-1] / 100 # $/bu
        oil = yf.Ticker("ZL=F").history(period="5d")['Close'].iloc[-1] # cents/lb
        meal = yf.Ticker("ZM=F").history(period="5d")['Close'].iloc[-1] # $/ton
        crush = round((meal * 0.022) + (oil * 0.11) - beans, 2)
        margins["SOY"] = f"${crush}/bu"
    except:
        margins["SOY"] = "N/A"
        
    return margins

@st.cache_data(ttl=3600)
def fetch_screener_data():
    results = []
    margins = get_sector_margins()

    for name, config in COMMODITIES.items():
        try:
            front_ticker = yf.Ticker(config["front"])
            next_ticker = yf.Ticker(config["next"])
            
            df_front = front_ticker.history(period="20d")
            df_next = next_ticker.history(period="20d")
            
            if df_front.empty:
                continue
                
            price_current = df_front['Close'].iloc[-1]
            
            # --- PILÍŘ 1: Termínová struktura ---
            if not df_next.empty:
                price_next = df_next['Close'].iloc[-1]
                prompt_spread = round(price_current - price_next, 3)
                structure = "BACKWARDATION 🟢" if prompt_spread > 0 else "CONTANGO 🔴"
            else:
                prompt_spread = 0.0
                structure = "N/A"

            # --- PILÍŘ 2: Sektorové marže ---
            margin_info = margins.get(config["type"], "N/A")

            # --- PILÍŘ 3 & 4: Změny v zásobách a COT odhad ---
            # Zjištění 5D změny ceny jako dočasné proxy pro momentum zásob/poptávky
            price_5d_ago = df_front['Close'].iloc[-6] if len(df_front) >= 6 else price_current
            inv_proxy = "Čerpání (Hlad) 🟢" if price_current > price_5d_ago else "Přebytky (Sklad) 🔴"
            
            # Týdenní odhad tlaku fondů podle spreadu
            cot_proxy = "Net Long 🟢" if prompt_spread > 0 else "Net Short 🔴"

            results.append({
                "Komodita": name,
                "Struktura": structure,
                "Prompt Spread": prompt_spread,
                "Sektorová Marže": margin_info,
                "COT Managed Money": cot_proxy,
                "Zásoby (Trend)": inv_proxy
            })
        except Exception:
            continue
            
    return pd.DataFrame(results)

# --- UI ---
with st.spinner("Načítám živá data z trhu..."):
    df_screener = fetch_screener_data()

if not df_screener.empty:
    st.subheader("📋 Fundamentální Matice Komodit")
    
    st.dataframe(
        df_screener,
        use_container_width=True,
        height=480
    )
else:
    st.warning("Data se nepodařilo načíst.")