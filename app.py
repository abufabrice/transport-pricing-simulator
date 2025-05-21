import streamlit as st
import pandas as pd
import plotly.express as px

# Load data
df = pd.read_csv("modules_config.csv")
tiers = pd.read_csv("module_tiers.csv")

st.set_page_config(page_title="Transport Pricing Simulator", layout="wide")
st.title("🚌 Transport Pricing Simulator")

scenario = st.sidebar.radio("Select Scenario", ["Low (80%)", "Medium (100%)", "High (120%)"])
scenario_factor = {"Low (80%)": 0.8, "Medium (100%)": 1.0, "High (120%)": 1.2}[scenario]

# Admin options
edit_prices = st.sidebar.checkbox("🛠️ Admin: Edit Default Prices")
edit_tiers = st.sidebar.checkbox("🪜 Admin: Edit Tiered Pricing")
is_admin = edit_prices or edit_tiers

# Edit base prices
if edit_prices:
    st.sidebar.markdown("### Adjust Unit Prices")
    new_prices = []
    for i, row in df.iterrows():
        new_price = st.sidebar.number_input(f"{row['name']}", min_value=0.0, value=float(row['price']), step=10.0)
        new_prices.append(new_price)
    df["price"] = new_prices

# Edit tiered pricing
if edit_tiers:
    st.subheader("🪜 Configure Tiered Pricing Per Module")
    editable_tiers = tiers.copy()
    for i, row in editable_tiers.iterrows():
        cols = st.columns(6)
        cols[0].markdown(f"**{row['name']}**")
        editable_tiers.at[i, 'tier1_max'] = cols[1].number_input("Tier 1 Max", value=int(row['tier1_max']), key=f"t1max_{i}")
        editable_tiers.at[i, 'tier1_price'] = cols[2].number_input("T1 Price", value=float(row['tier1_price']), step=10.0, key=f"t1p_{i}")
        editable_tiers.at[i, 'tier2_max'] = cols[3].number_input("Tier 2 Max", value=int(row['tier2_max']), key=f"t2max_{i}")
        editable_tiers.at[i, 'tier2_price'] = cols[4].number_input("T2 Price", value=float(row['tier2_price']), step=10.0, key=f"t2p_{i}")
        editable_tiers.at[i, 'tier3_price'] = cols[5].number_input("T3 Price", value=float(row['tier3_price']), step=10.0, key=f"t3p_{i}")
    tiers = editable_tiers
    st.download_button("💾 Download Updated Tier Settings", tiers.to_csv(index=False), "updated_module_tiers.csv")

# Usage sliders
usage = []
st.sidebar.header("Adjust Usage")
for i, row in df.iterrows():
    default = int(row["default_usage"] * scenario_factor)
    val = st.sidebar.sli
