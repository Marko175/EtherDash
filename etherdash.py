import streamlit as st
import pandas as pd
import requests
import time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np



st.set_page_config(page_title="Ethereum Wallet Explorer", page_icon="🧠", layout="wide")
st.title("🧠 Ethereum Wallet Explorer & Gas Fee Visualizer")

ETHERSCAN_API_KEY = "S8SFCF8MJMW53P7YTW9UC4KEE1UMZPGQ5G"
address = st.text_input("🔑 Enter Ethereum Wallet Address", placeholder="Press enter to search")

# Dynamic start block (approx. 2 years ago = 5.2 million blocks)
latest_block_res = requests.get("https://api.etherscan.io/api", params={
    "module": "proxy", "action": "eth_blockNumber", "apikey": ETHERSCAN_API_KEY
}).json()

latest_block = int(latest_block_res["result"], 16)
startblock = 0
TXS_PER_PAGE = 100
MAX_PAGES = 2

if address:
    try:
        with st.spinner("🔄 Fetching wallet balance..."):
            balance_res = requests.get("https://api.etherscan.io/api", params={
                "module": "account",
                "action": "balance",
                "address": address,
                "tag": "latest",
                "apikey": ETHERSCAN_API_KEY
            }).json()
            eth_balance = int(balance_res["result"]) / 1e18
            st.success(f"💰 Wallet Balance: {eth_balance:.4f} ETH")

        # Pagination: Fetch all transactions in past 2 years
        all_txs = []
        page = 1
        st.info("⏳ Fetching past transactions...")

        while page <= MAX_PAGES:
            tx_params = {
                "module": "account",
                "action": "txlist",
                "address": address,
                "startblock": 0,
                "endblock": 99999999,
                "sort": "desc",
                "apikey": ETHERSCAN_API_KEY
            }

            res = requests.get("https://api.etherscan.io/api", params=tx_params).json()
            txs = res.get("result", [])
            if not txs:
                break
            all_txs.extend(txs)
            if len(txs) < TXS_PER_PAGE:
                break
            page += 1
            time.sleep(0.2)

        if not all_txs:
            st.warning("⚠️ No transactions found in the past 2 years.")
        else:
            df = pd.DataFrame(all_txs)
            st.dataframe(df)

            df["timeStamp"] = pd.to_datetime(df["timeStamp"].astype(int), unit='s')
            df["value_ETH"] = df["value"].astype(float) / 1e18
            df["gasPrice_Gwei"] = df["gasPrice"].astype(float) / 1e9
            df["gasFee_ETH"] = (df["gasUsed"].astype(float) * df["gasPrice"].astype(float)) / 1e18
            df["status"] = df["isError"].apply(lambda x: "❌ Failed" if x == "1" else "✅ Success")
            df["direction"] = df.apply(lambda row: "📤 Out" if row["from"].lower() == address.lower() else "📥 In", axis=1)
            df["tx_link"] = df["hash"].apply(lambda h: f"[View ↗](https://etherscan.io/tx/{h})")
            df["month"] = df["timeStamp"].dt.to_period("M").astype(str)

            # Metrics
            total_tx = len(df)
            success_tx = df[df["status"] == "✅ Success"].shape[0]
            success_rate = (success_tx / total_tx) * 100
            badge = f"<span style='color:green;font-weight:bold;'>{success_rate:.0f}% ✅</span>" if success_rate >= 90 else \
                    f"<span style='color:orange;font-weight:bold;'>{success_rate:.0f}% ⚠️</span>" if success_rate >= 60 else \
                    f"<span style='color:red;font-weight:bold;'>{success_rate:.0f}% ❌</span>"

            # ETH Price
            price_res = requests.get("https://api.coingecko.com/api/v3/simple/price", params={
                "ids": "ethereum", "vs_currencies": "usd"
            }).json()
            eth_price = price_res["ethereum"]["usd"]

            total_fees_eth = df["gasFee_ETH"].sum()
            total_fees_usd = total_fees_eth * eth_price
            avg_fee_per_tx = total_fees_eth / total_tx if total_tx > 0 else 0

            # Display
            st.success(f"📦 Total Transactions Analyzed: {total_tx}")
            st.subheader("📊 Gas Fee Summary")
            st.metric("Avg Fee (ETH)", f"{df['gasFee_ETH'].mean():.6f}")
            st.metric("Max Fee (ETH)", f"{df['gasFee_ETH'].max():.6f}")
            st.metric("Min Fee (ETH)", f"{df['gasFee_ETH'].min():.6f}")
            st.markdown(f"📉 **Current ETH Price:** ${eth_price:,.2f}")
            st.metric("🔻 Total Gas Fees (ETH)", f"{total_fees_eth:.4f}")
            st.metric("💸 Total Gas Fees (USD)", f"${total_fees_usd:,.2f}")
            st.metric("📊 Avg Fee Per Tx (ETH)", f"{avg_fee_per_tx:.6f}")
            st.markdown(f"**Tx Success Rate:** {badge}", unsafe_allow_html=True)

            st.subheader("📄 Recent Transactions")
            # Show most recent transactions first
            sorted_df = df.sort_values("timeStamp", ascending=False)

            st.dataframe(sorted_df[[
                "timeStamp", "direction", "to", "value_ETH", "gasFee_ETH", "gasPrice_Gwei", "status", "tx_link"
            ]])


            st.subheader("📈 Gas Fee Over Time")
            st.line_chart(df.set_index("timeStamp")["gasFee_ETH"])

            st.subheader("📆 Gas Fees Per Month")
            monthly_fees = df.groupby("month")["gasFee_ETH"].sum()
            st.bar_chart(monthly_fees)

            # Step 1: Define percentiles for filtering
            eth_cutoff = df["value_ETH"].quantile(0.995)
            gas_cutoff = df["gasFee_ETH"].quantile(0.995)

            # Step 2: Split into inliers and outliers
            inliers = df[(df["value_ETH"] > 0) & (df["value_ETH"] < eth_cutoff) & (df["gasFee_ETH"] < gas_cutoff)].copy()
            outliers = df[(df["value_ETH"] >= eth_cutoff) | (df["gasFee_ETH"] >= gas_cutoff)].copy()

            # Step 3: Prepare data
            x_in = inliers["value_ETH"].values
            y_in = inliers["gasFee_ETH"].values
            x_out = outliers["value_ETH"].values
            y_out = outliers["gasFee_ETH"].values

            # Step 4: Plot
            st.subheader("⚖️ Gas Fees vs ETH Transferred (Per Transaction)")

            # Define outliers (top 1% by ETH transferred or gas fee)
            eth_cutoff = df["value_ETH"].quantile(0.99)
            gas_cutoff = df["gasFee_ETH"].quantile(0.99)

            # Split data
            inliers = df[(df["value_ETH"] > 0) & (df["value_ETH"] < eth_cutoff) & (df["gasFee_ETH"] < gas_cutoff)].copy()
            outliers = df[(df["value_ETH"] >= eth_cutoff) | (df["gasFee_ETH"] >= gas_cutoff)].copy()

            # Extract data
            x_in = inliers["value_ETH"].values
            y_in = inliers["gasFee_ETH"].values
            x_out = outliers["value_ETH"].values
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
                display_cols = ["timeStamp", "value_ETH", "gasFee_ETH", "to", "tx_link"]
                st.dataframe(outliers[display_cols].rename(columns={
                    "value_ETH": "ETH Transferred",
                    "gasFee_ETH": "Gas Fee (ETH)",
                    "to": "To Address",
                    "tx_link": "Tx"
                }))
            else:
                st.info("No outliers detected.")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
