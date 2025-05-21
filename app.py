
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Load module data
df = pd.read_csv("modules_config.csv")

st.set_page_config(page_title="Transport Pricing Simulator", layout="wide")

st.title("🚌 Transport Pricing Simulator")
st.markdown("Use the sliders below to simulate module usage and view projected monthly costs. Pricing is tiered based on usage volume.")

# Sidebar for scenario switching
scenario = st.sidebar.radio("Select Scenario", ["Low (80%)", "Medium (100%)", "High (120%)"])
scenario_factor = {"Low (80%)": 0.8, "Medium (100%)": 1.0, "High (120%)": 1.2}[scenario]

# User input for module usage
usage = []
st.sidebar.header("Adjust Usage")

for i, row in df.iterrows():
    default = int(row["default_usage"] * scenario_factor)
    val = st.sidebar.slider(f"{row['name']} ({row['unit']})", 0, int(row["default_usage"] * 2), default)
    usage.append(val)

df["usage"] = usage

# Apply tiered pricing
def tiered_price(unit_price, quantity):
    if quantity <= 100:
        return unit_price
    elif quantity <= 500:
        return unit_price * 0.9
    else:
        return unit_price * 0.8

df["unit_price"] = df.apply(lambda row: tiered_price(row["price"], row["usage"]), axis=1)
df["amount"] = df["usage"] * df["unit_price"]

# Display summary
total = df["amount"].sum()
st.metric("💰 Total Monthly Cost", f"{total:,.0f} FCFA")

# Group by category
category_summary = df.groupby("category")["amount"].sum().reset_index()

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Cost by Category")
    fig1 = px.pie(category_summary, names="category", values="amount", title="Cost Breakdown")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("📈 Cost by Module")
    fig2 = px.bar(df, x="name", y="amount", text="amount", labels={"amount": "FCFA"}, title="Module Cost")
    fig2.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig2, use_container_width=True)

# Data export
st.subheader("📥 Export")
st.download_button("Download Breakdown as CSV", df.to_csv(index=False), "pricing_breakdown.csv")

st.dataframe(df[["name", "category", "unit", "usage", "unit_price", "amount"]], use_container_width=True)
