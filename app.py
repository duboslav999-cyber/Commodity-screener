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

st.title("📊 Commodity Swing Screener")

# Přesný seznam komodit podle TradingView screenshotu
# Mapování pro yfinance: front kontrakt a odhadovaný následující kontrakt pro Prompt Spread
COMMODITIES = {
    "Ropa WTI (USOIL)": {"front": "CL=F", "next": "CLM26.NYM"},
    "Zemní Plyn (NATGAS)": {"front": "NG=F", "next": "NGM26.NYM"},
    "Kukuřice (CORN)": {"front": "ZC=F", "next": "ZCN26.CBT"},
    "Pšenice (WHEAT)": {"front": "ZW=F", "next": "ZWN26.CBT"},
    "Sója (SOYBEAN)": {"front": "ZS=F", "next": "ZSN26.CBT"},
    "Káva (COFFEE)": {"front": "KC=F", "next": "KCN26.NYB"},
    "Kakao (COCOA)": {"front": "CC=F", "next": "CCN26.NYB"},
    "Cukr (SUGAR)": {"front": "SB=F", "next": "SBN26.NYB"},
    "Zlato (GOLD)": {"front": "GC=F", "next": "GCM26.CMX"},
    "Stříbro (XAGUSD)": {"front": "SI=F", "next": "SIN26.CMX"},
    "Platina (PLATINUM)": {"front": "PL=F", "next": "PLN26.NYM"},
    "Měď (COPPER)": {"front": "HG=F", "next": "HGM26.CMX"}
}

MACRO_TICKERS = {
    "DXY": "DX-Y.NYB"
}

@st.cache_data(ttl=1800)  # Refresh dat každých 30 minut
def fetch_screener_data():
    results = []
    
    # Stáhnutí DXY pro výpočet korelací
    try:
        dxy_data = yf.Ticker(MACRO_TICKERS["DXY"]).history(period="60d")['Close']
    except:
        dxy_data = pd.Series()
    
    for name, config in COMMODITIES.items():
        try:
            front_ticker = yf.Ticker(config["front"])
            next_ticker = yf.Ticker(config["next"])
            
            df_front = front_ticker.history(period="60d")
            df_next = next_ticker.history(period="60d")
            
            if df_front.empty:
                continue
                
            close_front = df_front['Close']
            price_current = close_front.iloc[-1]
            
            # --- 1. Termínová struktura (Prompt Spread) ---
            if not df_next.empty:
                price_next = df_next['Close'].iloc[-1]
                prompt_spread = round(price_current - price_next, 3)
                structure = "BACKWARDATION 🟢" if prompt_spread > 0 else "CONTANGO 🔴"
            else:
                prompt_spread = 0.0
                structure = "N/A"

            # --- 2. Statisická odchylka (20D Z-Score) ---
            mean_20 = close_front.rolling(20).mean().iloc[-1]
            std_20 = close_front.rolling(20).std().iloc[-1]
            z_score = round((price_current - mean_20) / std_20, 2) if std_20 > 0 else 0
            
            # --- 3. Změna ceny ---
            change_1d = round(((price_current / close_front.iloc[-2]) - 1) * 100, 2)
            change_5d = round(((price_current / close_front.iloc[-6]) - 1) * 100, 2)
            
            # --- 4. Korelace s DXY ---
            if not dxy_data.empty:
                combined = pd.concat([close_front, dxy_data], axis=1, join='inner').dropna()
                corr_dxy = round(combined.iloc[:, 0].corr(combined.iloc[:, 1]), 2) if len(combined) > 10 else 0
            else:
                corr_dxy = 0.0

            results.append({
                "Komodita": name,
                "Cena": round(price_current, 2),
                "1D %": change_1d,
                "5D %": change_5d,
                "Struktura": structure,
                "Prompt Spread": prompt_spread,
                "20D Z-Score": z_score,
                "30D DXY Corr": corr_dxy
            })
        except Exception as e:
            continue
            
    return pd.DataFrame(results)

# --- VYTVOŘENÍ ROZHRANÍ (UI) ---

with st.spinner("Aktualizuji seznam komodit..."):
    df_screener = fetch_screener_data()

if not df_screener.empty:
    st.subheader("📋 Přehled sledovaných komodit")
    
    # Čistá tabulka bez kategorie sektorů
    st.dataframe(
        df_screener.style.background_gradient(subset=["20D Z-Score"], cmap="PiYG")
                         .background_gradient(subset=["30D DXY Corr"], cmap="coolwarm"),
        use_container_width=True,
        height=480
    )
else:
    st.warning("Data se nepodařilo načíst. Zkontrolujte připojení k trhu.")