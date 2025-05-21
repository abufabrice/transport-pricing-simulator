import streamlit as st
import pandas as pd
import plotly.express as px

# Load module and tier data
df = pd.read_csv("modules_config.csv")
tiers = pd.read_csv("module_tiers.csv")

st.set_page_config(page_title="Transport Pricing Simulator", layout="wide")
st.title("🚌 Transport Pricing Simulator")

st.markdown("Use the sliders below to simulate module usage and view projected monthly costs. Pricing is applied per module using custom tiers.")

# Scenario Selector
scenario = st.sidebar.radio("Select Scenario", ["Low (80%)", "Medium (100%)", "High (120%)"])
scenario_factor = {"Low (80%)": 0.8, "Medium (100%)": 1.0, "High (120%)": 1.2}[scenario]

# Admin Price Editing Toggle
edit_prices = st.sidebar.checkbox("🛠️ Admin: Edit Default Prices")

# Editable Unit Prices
if edit_prices:
    st.sidebar.markdown("### Adjust Unit Prices")
    new_prices = []
    for i, row in df.iterrows():
        new_price = st.sidebar.number_input(f"{row['name']}", min_value=0.0, value=float(row['price']), step=10.0)
        new_prices.append(new_price)
    df["price"] = new_prices

# Usage Input Sliders
usage = []
st.sidebar.header("Adjust Usage")
for i, row in df.iterrows():
    default = int(row["default_usage"] * scenario_factor)
    val = st.sidebar.slider(f"{row['name']} ({row['unit']})", 0, int(row["default_usage"] * 2.5), default)
    usage.append(val)

df["usage"] = usage

# Merge Tiers with Main Table
df = df.merge(tiers, on="name", how="left")

# Apply Custom Tiered Pricing
def module_price(row):
    u = row["usage"]
    if u <= row["tier1_max"]:
        return row["tier1_price"]
    elif u <= row["tier2_max"]:
        return row["tier2_price"]
    else:
        return row["tier3_price"]

df["unit_price"] = df.apply(module_price, axis=1)
df["amount"] = df["usage"] * df["unit_price"]

# Estimate Costs and Profits
df["internal_cost"] = df["amount"] * 0.4  # Assume 40% of revenue as cost
df["profit"] = df["amount"] - df["internal_cost"]

# Total Metrics
total_revenue = df["amount"].sum()
total_cost = df["internal_cost"].sum()
total_profit = df["profit"].sum()

st.metric("💰 Monthly Revenue", f"{total_revenue:,.0f} FCFA")
st.metric("🧾 Estimated Ops Cost", f"{total_cost:,.0f} FCFA")
st.metric("📈 Projected Profit", f"{total_profit:,.0f} FCFA")

# Pie Chart: Revenue by Category
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Revenue by Category")
    pie_data = df.groupby("category")["amount"].sum().reset_index()
    fig1 = px.pie(pie_data, names="category", values="amount")
    st.plotly_chart(fig1, use_container_width=True)

# Bar Chart: Module Revenue
with col2:
    st.subheader("📈 Cost by Module")
    fig2 = px.bar(df, x="name", y="amount", text="amount", title="Module Revenue", labels={"amount": "FCFA"})
