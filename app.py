import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Konfigurace stránky
st.set_page_config(
    page_title="Commodity Fundamental Screener",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Commodity Fundamental Swing Screener")
st.caption("Ranní fundamentální filtr pro komoditní swingové obchodování")

# 1. DEFINICE MAPOVÁNÍ KONTRAKTŮ (1. a 2. blízký měsíc pro Prompt Spread)
COMMODITIES = {
    "Ropa WTI": {"front": "CL=F", "next": "CLM26.NYM", "cat": "Energies"}, # YFinance kódování měsíců
    "Zemní Plyn": {"front": "NG=F", "next": "NGM26.NYM", "cat": "Energies"},
    "Zlato": {"front": "GC=F", "next": "GCM26.CMX", "cat": "Metals"},
    "Měď": {"front": "HG=F", "next": "HGM26.CMX", "cat": "Metals"},
    "Kukuřice": {"front": "ZC=F", "next": "ZCN26.CBT", "cat": "Agra"},
    "Káva": {"front": "KC=F", "next": "KCN26.NYB", "cat": "Agra"}
}

MACRO_TICKERS = {
    "DXY (Dolar)": "DX-Y.NYB",
    "US 10Y Yield": "^TNX"
}

@st.cache_data(ttl=3600)  # Data kešujeme na 1 hodinu, aby byl skript bleskový
def fetch_screener_data():
    results = []
    
    # Stáhnutí DXY pro výpočet korelací
    dxy_data = yf.Ticker(MACRO_TICKERS["DXY (Dolar)"]).history(period="60d")['Close']
    
    for name, config in COMMODITIES.items():
        try:
            # Stáhnutí dat pro 1. kontrakt (Front) a 2. kontrakt (Next)
            front_ticker = yf.Ticker(config["front"])
            next_ticker = yf.Ticker(config["next"])
            
            df_front = front_ticker.history(period="60d")
            df_next = next_ticker.history(period="60d")
            
            if df_front.empty:
                continue
                
            close_front = df_front['Close']
            price_current = close_front.iloc[-1]
            
            # --- PILÍŘ 1: Termínová struktura (Prompt Spread) ---
            if not df_next.empty:
                price_next = df_next['Close'].iloc[-1]
                prompt_spread = round(price_current - price_next, 3)
                structure = "BACKWARDATION 🟢" if prompt_spread > 0 else "CONTANGO 🔴"
            else:
                prompt_spread = 0.0
                structure = "N/A"

            # --- PILÍŘ 2: Statisická odchylka (20D Z-Score) ---
            mean_20 = close_front.rolling(20).mean().iloc[-1]
            std_20 = close_front.rolling(20).std().iloc[-1]
            z_score = round((price_current - mean_20) / std_20, 2) if std_20 > 0 else 0
            
            # --- PILÍŘ 3: Změna ceny ---
            change_1d = round(((price_current / close_front.iloc[-2]) - 1) * 100, 2)
            change_5d = round(((price_current / close_front.iloc[-6]) - 1) * 100, 2)
            
            # --- PILÍŘ 4: Korelace s USD (DXY) ---
            # Sladění datových řad
            combined = pd.concat([close_front, dxy_data], axis=1, join='inner').dropna()
            corr_dxy = round(combined.iloc[:, 0].corr(combined.iloc[:, 1]), 2) if len(combined) > 10 else 0

            results.append({
                "Sektor": config["cat"],
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
            st.error(f"Chyba při stahování {name}: {e}")
            
    return pd.DataFrame(results)

# --- VYTVOŘENÍ ROZHRANÍ (UI) ---

with st.spinner("Stahuji aktuální tržní a fundamentální data..."):
    df_screener = fetch_screener_data()

if not df_screener.empty:
    # Horní souhrnné metrické karty
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sledované Komodity", len(df_screener))
    with col2:
        bw_count = len(df_screener[df_screener['Struktura'].str.contains("BACKWARDATION")])
        st.metric("V Backwardation (Fyzický hlad)", f"{bw_count} z {len(df_screener)}")
    with col3:
        top_mover = df_screener.sort_values(by="5D %", ascending=False).iloc[0]
        st.metric("Nejsilnější 5D Trik", f"{top_mover['Komodita']} ({top_mover['5D %']}%)")

    st.markdown("---")
    st.subheader("📋 Hlavní Fundamentální Matice")
    
    # Podbarvení dat v tabulce pro okamžitou vizuální orientaci
    st.dataframe(
        df_screener.style.background_gradient(subset=["20D Z-Score"], cmap="PiYG")
                         .background_gradient(subset=["30D DXY Corr"], cmap="coolwarm"),
        use_container_width=True,
        height=300
    )

    st.info("💡 **Jak číst tabulku:** **Backwardation** značí okamžitý požadavek na fyzickém trhu. **Z-Score nad +2 / pod -2** ukazuje na statistický extrém zralý na reakci. **DXY Corr blízko -1.0** znamená, že komodita striktně reaguje na pohyb amerického dolaru.")
else:
    st.warning("Žádná data nebyla stažena.")