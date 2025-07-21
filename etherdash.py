import streamlit as st
import requests
import pandas as pd

# --- CONFIG ---
ETHERSCAN_API_KEY = "S8SFCF8MJMW53P7YTW9UC4KEE1UMZPGQ5G"
ETHERSCAN_BASE = "https://api.etherscan.io/api"

# --- UI ---
st.title("🧪 Etherscan Debugger")
address = st.text_input("Enter Ethereum Wallet Address")

if address:
    st.write(f"🔍 Fetching last 10 transactions for `{address}`")

    # --- API Call ---
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 10,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }

    try:
        response = requests.get(ETHERSCAN_BASE, params=params)
        data = response.json()

        if data.get("status") != "1" or not isinstance(data.get("result"), list):
            st.error(f"❌ API Error: {data.get('message', 'Unknown error')}")
            st.json(data)  # Show raw response for debugging
        else:
            txs = data["result"]
            df = pd.DataFrame(txs)

            if df.empty:
                st.warning("⚠️ No transactions found.")
            else:
                df["value_ETH"] = df["value"].astype(float) / 1e18
                st.dataframe(df[["timeStamp", "hash", "to", "value_ETH", "gasUsed", "isError"]])
    except Exception as e:
        st.error(f"❌ Request failed: {e}")
