import streamlit as st
import requests
import pandas as pd

# === CONFIG ===
ETHERSCAN_API_KEY = "S8SFCF8MJMW53P7YTW9UC4KEE1UMZPGQ5G"
ETHERSCAN_API_URL = "https://api.etherscan.io/api"

st.title("🔍 Ethereum Wallet Viewer")

# === User input ===
wallet = st.text_input("Enter Ethereum wallet address")

if wallet:
    # === Fetch balance ===
    balance_params = {
        "module": "account",
        "action": "balance",
        "address": wallet,
        "tag": "latest",
        "apikey": ETHERSCAN_API_KEY
    }

    balance_response = requests.get(ETHERSCAN_API_URL, params=balance_params).json()
    if balance_response.get("status") == "1":
        balance_eth = int(balance_response["result"]) / 1e18
        st.subheader(f"💰 Wallet Balance: {balance_eth:.4f} ETH")
    else:
        st.error(f"❌ Error fetching balance: {balance_response.get('message', 'Unknown error')}")
        st.stop()

    # === Fetch transactions ===
    tx_params = {
        "module": "account",
        "action": "txlist",
        "address": wallet,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": 10000,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }

    tx_response = requests.get(ETHERSCAN_API_URL, params=tx_params).json()

    if tx_response.get("status") == "1" and isinstance(tx_response.get("result"), list):
        txs = tx_response["result"]
        if not txs:
            st.info("ℹ️ No transactions found.")
        else:
            df = pd.DataFrame(txs)
            df["value_eth"] = df["value"].astype(float) / 1e18
            df["timestamp"] = pd.to_datetime(df["timeStamp"].astype(int), unit="s")
            df_display = df[["timestamp", "hash", "from", "to", "value_eth", "isError"]]
            st.subheader("📄 Last 10 Transactions")
            st.dataframe(df_display)
    else:
        st.error(f"❌ Error fetching transactions: {tx_response.get('result', 'Unknown error')}")
