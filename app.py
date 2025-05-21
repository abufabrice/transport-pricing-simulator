
import streamlit as st
import pandas as pd
import plotly.express as px

# Load module usage and tier pricing data
df = pd.read_csv("modules_config.csv")
tiers = pd.read_csv("module_tiers.csv")

st.set_page_config(page_title="Transport Pricing Simulator", layout="wide")
st.title("🚌 Transport Pricing Simulator")

st.markdown("Use the sliders below to simulate module usage and view projected monthly costs. Pricing is applied per module using custom tiers.")

scenario = st.sidebar.radio("Select Scenario", ["Low (80%)", "Medium (100%)", "High (120%)"])
scenario_factor = {"Low (80%)": 0.8, "Medium (100%)": 1.0, "High (120%)": 1.2}[scenario]

# Admin mode
edit_prices = st.sidebar.checkbox("🛠️ Admin: Edit Default Prices")

if edit_prices:
    st.sidebar.markdown("### Adjust Base Prices")
    new_prices = []
    for i, row in df.iterrows():
        new_price = st.sidebar.number_input(f"{row['name']}", min_value=0.0, value=float(row['price']), step=10.0)
        new_prices.append(new_price)
    df["price"] = new_prices

# Adjust usage sliders
usage = []
st.sidebar.header("Adjust Usage")

for i, row in df.iterrows():
    default = int(row["default_usage"] * scenario_factor)
    val = st.sidebar.slider(f"{row['name']} ({row['unit']})", 0, int(row["default_usage"] * 2.5), default)
    usage.append(val)

df["usage"] = usage

# Merge tiers with df
df = df.merge(tiers, on="name", how="left")

# Apply module-specific tiered pricing
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

# Simulate client revenue (platform earnings) and your internal cost
# Assume cost is 40% of revenue
df["internal_cost"] = df["amount"] * 0.4
df["profit"] = df["amount"] - df["internal_cost"]

# Total summary
total_revenue = df["amount"].sum()
total_cost = df["internal_cost"].sum()
total_profit = df["profit"].sum()

st.metric("💰 Monthly Revenue", f"{total_revenue:,.0f} FCFA")
st.metric("🧾 Estimated Ops Cost", f"{total_cost:,.0f} FCFA")
st.metric("📈 Projected Profit", f"{total_profit:,.0f} FCFA")

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Revenue by Category")
    fig1 = px.pie(df.groupby("category")["amount"].sum().reset_index(), names="category", values="amount")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("📈 Cost by Module")
    fig2 = px.bar(df, x="name", y="amount", text="amount", title="Module Revenue", labels={"amount": "FCFA"})
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

# Revenue vs Cost Chart
st.subheader("📊 Revenue vs. Cost by Module")
fig3 = px.bar(df, x="name", y=["amount", "internal_cost"], barmode="group",
              labels={"value": "FCFA", "name": "Module", "variable": "Type"})
fig3.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig3, use_container_width=True)

# Export and table
st.subheader("📥 Export")
st.download_button("Download Breakdown", df.to_csv(index=False), "full_pricing_breakdown.csv")
st.dataframe(df[["name", "category", "unit", "usage", "unit_price", "amount", "internal_cost", "profit"]])
