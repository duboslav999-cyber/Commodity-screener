import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Konfigurace stránky
st.set_page_config(
    page_title="Commodity Fundamental Screener",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("📊 Commodity Fundamental Screener")
st.caption("Čistý fundamentální přehled bez cenového šumu")

# Seznam 12 komodit a jejich mapování
COMMODITIES = {
    "Ropa WTI (USOIL)": {"front": "CL=F", "next": "CLM26.NYM", "has_crack": True},
    "Zemní Plyn (NATGAS)": {"front": "NG=F", "next": "NGM26.NYM", "has_crack": False},
    "Kukuřice (CORN)": {"front": "ZC=F", "next": "ZCN26.CBT", "has_crack": False},
    "Pšenice (WHEAT)": {"front": "ZW=F", "next": "ZWN26.CBT", "has_crack": False},
    "Sója (SOYBEAN)": {"front": "ZS=F", "next": "ZSN26.CBT", "has_crack": False},
    "Káva (COFFEE)": {"front": "KC=F", "next": "KCN26.NYB", "has_crack": False},
    "Kakao (COCOA)": {"front": "CC=F", "next": "CCN26.NYB", "has_crack": False},
    "Cukr (SUGAR)": {"front": "SB=F", "next": "SBN26.NYB", "has_crack": False},
    "Zlato (GOLD)": {"front": "GC=F", "next": "GCM26.CMX", "has_crack": False},
    "Stříbro (XAGUSD)": {"front": "SI=F", "next": "SIN26.CMX", "has_crack": False},
    "Platina (PLATINUM)": {"front": "PL=F", "next": "PLN26.NYM", "has_crack": False},
    "Měď (COPPER)": {"front": "HG=F", "next": "HGM26.CMX", "has_crack": False}
}

@st.cache_data(ttl=1800)
def fetch_screener_data():
    results = []
    
    # Pomocný výpočet pro 3:2:1 Crack Spread (Ropa)
    try:
        wti = yf.Ticker("CL=F").history(period="5d")['Close'].iloc[-1]
        rb = yf.Ticker("RB=F").history(period="5d")['Close'].iloc[-1] * 42  # Benzín ($/gal -> $/bbl)
        ho = yf.Ticker("HO=F").history(period="5d")['Close'].iloc[-1] * 42  # Topný olej ($/gal -> $/bbl)
        crack_321 = round(((2 * rb) + (1 * ho) - (3 * wti)) / 3, 2)
    except:
        crack_321 = None

    for name, config in COMMODITIES.items():
        try:
            front_ticker = yf.Ticker(config["front"])
            next_ticker = yf.Ticker(config["next"])
            
            df_front = front_ticker.history(period="20d")
            df_next = next_ticker.history(period="20d")
            
            if df_front.empty:
                continue
                
            price_current = df_front['Close'].iloc[-1]
            
            # --- PILÍŘ 1: Termínová struktura (Prompt Spread) ---
            if not df_next.empty:
                price_next = df_next['Close'].iloc[-1]
                prompt_spread = round(price_current - price_next, 3)
                structure = "BACKWARDATION 🟢" if prompt_spread > 0 else "CONTANGO 🔴"
            else:
                prompt_spread = 0.0
                structure = "N/A"

            # --- PILÍŘ 2: Sektorové marže (Crack Spread u Ropy) ---
            margin_info = f"${crack_321}/bbl" if config["has_crack"] and crack_321 is not None else "N/A"

            # --- PILÍŘ 3 & 4: COT Report a Zásoby (Příprava struktury) ---
            # Tyto metriky doplníme v dalším kroku z CFTC a EIA/USDA API
            cot_net_change = "Načítám..."
            inventory_vs_5y = "Načítám..."

            results.append({
                "Komodita": name,
                "Struktura": structure,
                "Prompt Spread": prompt_spread,
                "Sektorová Marže": margin_info,
                "COT Managed Money (Net)": cot_net_change,
                "Zásoby vs. 5Y Průměr": inventory_vs_5y
            })
        except Exception:
            continue
            
    return pd.DataFrame(results)

# --- UI ---
with st.spinner("Aktualizuji fundamentální matici..."):
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