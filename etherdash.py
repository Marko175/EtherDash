import streamlit as st
import pandas as pd
import requests
import time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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
        headers = {"User-Agent": "Mozilla/5.0"}
    
        try:
            response = requests.get(url, params=params, headers=headers, timeout=5)
    
            response.raise_for_status()
            data = response.json()
            price = data.get("ethereum", {}).get("usd", None)
    
            if price is None:
                st.warning("⚠️ ETH price not found in API response.")
            return price
    
        except Exception as e:
            st.error(f"❌ Failed to fetch ETH price: {e}")
            return None

    
    eth_price = get_eth_price()
    st.write(f"💱 1 ETH = ${eth_price:,.2f} USD")




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
            #df["value_eth"] = df["value"].astype(float) / 1e18
            #df["timestamp"] = pd.to_datetime(df["timeStamp"].astype(int), unit="s")
            df["isError"] = df["isError"].astype(int)

            df["timestamp"] = pd.to_datetime(df["timeStamp"].astype(int), unit='s')
            df["value_eth"] = df["value"].astype(float) / 1e18
            df["gasPrice_Gwei"] = df["gasPrice"].astype(float) / 1e9
            df["gasFee_ETH"] = (df["gasUsed"].astype(float) * df["gasPrice"].astype(float)) / 1e18
            df["status"] = df["isError"].apply(lambda x: "❌ Failed" if x == "1" else "✅ Success")
            df["tx_link"] = df["hash"].apply(lambda h: f"[View ↗](https://etherscan.io/tx/{h})")

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

    # Display


    # Step 1: Define percentiles for filtering
    eth_cutoff = df["value_eth"].quantile(0.995)
    gas_cutoff = df["gasFee_ETH"].quantile(0.995)

    # Step 2: Split into inliers and outliers
    inliers = df[(df["value_eth"] > 0) & (df["value_eth"] < eth_cutoff) & (df["gasFee_ETH"] < gas_cutoff)].copy()
    outliers = df[(df["value_eth"] >= eth_cutoff) | (df["gasFee_ETH"] >= gas_cutoff)].copy()

    # Step 3: Prepare data
    x_in = inliers["value_eth"].values
    y_in = inliers["gasFee_ETH"].values
    x_out = outliers["value_eth"].values
    y_out = outliers["gasFee_ETH"].values

    # Step 4: Plot
    st.subheader("⚖️ Gas Fees vs ETH Transferred (Per Transaction)")

    # Define outliers (top 1% by ETH transferred or gas fee)
    eth_cutoff = df["value_eth"].quantile(0.99)
    gas_cutoff = df["gasFee_ETH"].quantile(0.99)

    # Split data
    inliers = df[(df["value_eth"] > 0) & (df["value_eth"] < eth_cutoff) & (df["gasFee_ETH"] < gas_cutoff)].copy()
    outliers = df[(df["value_eth"] >= eth_cutoff) | (df["gasFee_ETH"] >= gas_cutoff)].copy()

    # Extract data
    x_in = inliers["value_eth"].values
    y_in = inliers["gasFee_ETH"].values
    x_out = outliers["value_eth"].values
    y_out = outliers["gasFee_ETH"].values

    # Plot
    fig, ax = plt.subplots(figsize=(8, 6))

    # Scatter points
    ax.scatter(x_in, y_in, alpha=0.6, color="#1f77b4", edgecolors="k", s=40, label="Normal Tx")
    ax.scatter(x_out, y_out, alpha=0.9, color="red", edgecolors="k", s=60, label="Outlier Tx")

    # Regression line (fit to inliers only)
    if len(x_in) > 1:
        slope, intercept = np.polyfit(x_in, y_in, 1)
        x_vals = np.linspace(min(x_in), max(x_in), 100)
        y_vals = slope * x_vals + intercept
        ax.plot(x_vals, y_vals, color="green", linewidth=2, label="Regression (Inliers)")

    # Style
    ax.set_xlabel("ETH Transferred")
    ax.set_ylabel("Gas Fee (ETH)")
    ax.set_title("Gas Cost vs Value Transferred")
    ax.set_ylim(0,.0015)
    ax.set_xlim(0,1)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    st.pyplot(fig)



    st.subheader("📦 Gas Fee as % of ETH Transferred")

    # Filter only valid transactions
    pct_df = df[df["value_ETH"] > 0].copy()
    pct_df["fee_pct"] = (pct_df["gasFee_ETH"] / pct_df["value_ETH"]) * 100

    # Remove extreme outliers (e.g. > 100%)
    pct_df = pct_df[pct_df["fee_pct"] < 1000]  # you can adjust this cap

    # Plot boxplot
    fig2, ax2 = plt.subplots(figsize=(6, 5))
    ax2.boxplot(pct_df["fee_pct"], vert=True, patch_artist=True,
                boxprops=dict(facecolor='skyblue', color='black'),
                medianprops=dict(color='red'))
    ax2.set_ylim(0, 10)  # Show only 0–10% range

    ax2.set_ylabel("Gas Fee (% of ETH transferred)")
    ax2.set_title("Gas Fee as a Percentage of Transfer Value")
    st.pyplot(fig2)


    # Step 5: Show outlier table
    st.subheader("🚨 Notable Outlier Transactions")
    if not outliers.empty:
        outliers = outliers.sort_values("gasFee_ETH", ascending=False).drop_duplicates("hash")
        display_cols = ["timeStamp", "value_eth", "gasFee_ETH", "to", "tx_link"]
        st.dataframe(outliers[display_cols].rename(columns={
            "value_ETH": "ETH Transferred",
            "gasFee_ETH": "Gas Fee (ETH)",
            "to": "To Address",
            "tx_link": "Tx"
        }))
    else:
        st.info("No outliers detected.")

