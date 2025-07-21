import streamlit as st
import requests
import pandas as pd

# === CONFIG ===
ETHERSCAN_API_KEY = "S8SFCF8MJMW53P7YTW9UC4KEE1UMZPGQ5G"
ETHERSCAN_API_URL = "https://api.etherscan.io/api"

st.title("🔍 Ethereum Wallet Analyzer")

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

    # === Get ETH price in USD ===
    def get_eth_price():
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "ethereum", "vs_currencies": "usd"}
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("ethereum", {}).get("usd", None)
        return None
    
    eth_price = get_eth_price()
    st.write(f"🪙 Current ETH Price: ${eth_price:,.2f}")

    # === Fetch wallet balance ===
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
        balance_usd = balance_eth * eth_price if eth_price else None
    
        st.subheader("💰 Wallet Balance")
        col1, col2 = st.columns(2)
        col1.metric("ETH", f"{balance_eth:.4f} ETH")
        if balance_usd:
            col2.metric("USD", f"${balance_usd:,.2f}")
        else:
            col2.write("USD conversion unavailable")
    else:
        st.error("❌ Failed to retrieve wallet balance.")
        st.stop()


    # === Fetch last 10,000 transactions ===
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
            df["isError"] = df["isError"].astype(int)

            # === Failed transaction stats ===
            total_tx = len(df)
            failed_tx = df["isError"].sum()
            success_rate = 100 * (1 - failed_tx / total_tx)

            st.subheader("📊 Transaction Statistics")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Transactions", total_tx)
            col2.metric("Failed Transactions", failed_tx, delta_color="inverse")
            col3.metric("Success Rate", f"{success_rate:.2f}%", delta_color="normal")

            # === Show transaction table ===
            df_display = df[["timestamp", "hash", "from", "to", "value_eth", "isError"]]
            st.subheader("📄 Recent Transactions (up to 10,000)")
            st.dataframe(df_display)
    else:
        st.error(f"❌ Error fetching transactions: {tx_response.get('result', 'Unknown error')}")

    # === Gas Fee Summary ===
    st.subheader("⛽ Gas Fee Summary")
    
    # Convert gas used and gas price to numeric
    df["gasUsed"] = df["gasUsed"].astype(float)
    df["gasPrice"] = df["gasPrice"].astype(float)
    
    # Compute gas fee in ETH
    df["gas_fee_eth"] = (df["gasUsed"] * df["gasPrice"]) / 1e18
    
    # Show summary stats
    total_fees = df["gas_fee_eth"].sum()
    average_fee = df["gas_fee_eth"].mean()
    max_fee = df["gas_fee_eth"].max()
    min_fee = df["gas_fee_eth"].min()
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Gas Used (ETH)", f"{total_fees:.5f}")
    col2.metric("Avg Fee (ETH)", f"{average_fee:.5f}")
    col3.metric("Max Fee (ETH)", f"{max_fee:.5f}")
    col4.metric("Min Fee (ETH)", f"{min_fee:.5f}")

