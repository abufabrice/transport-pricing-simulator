import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Set page config for better layout
st.set_page_config(page_title="Transport Pricing Simulator", layout="wide")

# Load configuration files
try:
    modules_df = pd.read_csv("modules_config.csv")
    tiers_df   = pd.read_csv("module_tiers.csv")
except Exception as e:
    st.error(f"Configuration files not found or unreadable: {e}")
    st.stop()

# Clean and prepare the data
# Remove any placeholder header rows (e.g. category labels) where measurement unit is NaN
if 'Measurement Unit' in modules_df.columns:
    modules_df = modules_df[modules_df['Measurement Unit'].notna()]

# Convert numeric fields to proper types
if 'Default' in modules_df.columns:
    modules_df['Default'] = pd.to_numeric(modules_df['Default'], errors='coerce').fillna(0).astype(int)
if 'InternalCost' in modules_df.columns:
    modules_df['InternalCost'] = pd.to_numeric(modules_df['InternalCost'], errors='coerce').fillna(0.0)
# Convert tier columns to numeric, NaNs for blanks
for col in ['tier1_max', 'tier1_price', 'tier2_max', 'tier2_price', 'tier3_price']:
    if col in tiers_df.columns:
        tiers_df[col] = pd.to_numeric(tiers_df[col], errors='coerce')

# Merge module info with tier pricing info on Module name
merged_df = pd.merge(modules_df, tiers_df, on='Module', how='left')
# Fill NaN in tier fields with 0 for easier calculations (0 indicates no tier or no price)
for col in ['tier1_max', 'tier2_max', 'tier1_price', 'tier2_price', 'tier3_price']:
    if col in merged_df.columns:
        merged_df[col] = merged_df[col].fillna(0)

# Title and description
st.title("Transport Pricing Simulator")
st.markdown("Adjust the usage sliders for each module to estimate monthly costs. "
            "Turn on **Admin Mode** to edit pricing tiers and view revenue/cost/profit breakdowns.")

# Admin mode toggle
admin_mode = st.checkbox("Enable Admin Mode")

# Prepare containers for layout
# We'll use two columns for sliders to make use of wide layout
col1, col2 = st.columns(2)

# Lists to collect results for each module
module_names = []
usage_values = []
amount_values = []
cost_values = []
profit_values = []

# Iterate through each module in the merged data
for idx, row in merged_df.iterrows():
    module = str(row["Module"])
    unit = str(row["Measurement Unit"]) if "Measurement Unit" in row else ""  # unit may not exist for all rows
    default_usage = int(row["Default"]) if "Default" in row else 0

    # Determine which column to place this module's controls in for two-col layout
    target_col = col1 if idx % 2 == 0 else col2

    # Compute slider range
    slider_min = 0
    # Start with 3x default or 50, whichever is larger (to provide a reasonable max)
    slider_max = max(default_usage * 3, 50)
    # If tier thresholds exist, extend the slider max to cover them and a bit beyond
    if row.get("tier2_max", 0) and row["tier2_max"] > 0:
        slider_max = max(slider_max, int(row["tier2_max"]))
        if row.get("tier3_price", 0) and row["tier3_price"] > 0:
            # If a third tier price exists, allow usage beyond tier2_max (e.g. up to 2x tier2_max)
            slider_max = max(slider_max, int(row["tier2_max"] * 2))
    # Ensure slider_max is at least as large as default_usage
    slider_max = max(slider_max, default_usage)

    # Create usage slider
    slider_label = module if unit == "" else f"{module} ({unit})"
    usage = target_col.slider(slider_label, min_value=slider_min, max_value=slider_max, value=default_usage)

    # If Admin Mode, provide inputs to edit pricing tiers
    if admin_mode:
        with target_col.expander(f"Edit pricing for {module}"):
            if row.get("tier2_max", 0) and row["tier2_max"] > 0:
                # Module has tiered pricing (tier2_max > 0 indicates a second tier exists)
                tier1_max = st.number_input("Tier 1 max", min_value=0, value=int(row["tier1_max"]), key=f"{idx}_{module}_t1max")
                tier1_price = st.number_input("Tier 1 price (FCFA)", min_value=0.0, value=float(row["tier1_price"]), key=f"{idx}_{module}_t1price")
                tier2_max = st.number_input("Tier 2 max", min_value=0, value=int(row["tier2_max"]), key=f"{idx}_{module}_t2max")
                tier2_price = st.number_input("Tier 2 price (FCFA)", min_value=0.0, value=float(row["tier2_price"]), key=f"{idx}_{module}_t2price")
                tier3_price = st.number_input("Tier 3 price (FCFA)", min_value=0.0, value=float(row["tier3_price"]), key=f"{idx}_{module}_t3price")
            else:
                # Module has no second tier -> single price
                tier1_max = 0
                tier2_max = 0
                tier2_price = 0.0
                tier3_price = 0.0
                tier1_price = st.number_input("Price per unit (FCFA)", min_value=0.0, value=float(row["tier1_price"]), key=f"{idx}_{module}_price")
    else:
        # Not admin: use pricing from config as-is
        tier1_max = int(row.get("tier1_max", 0))
        tier1_price = float(row.get("tier1_price", 0.0))
        tier2_max = int(row.get("tier2_max", 0))
        tier2_price = float(row.get("tier2_price", 0.0))
        tier3_price = float(row.get("tier3_price", 0.0))

    # Calculate revenue (amount charged) for this module based on usage and tiered pricing
    if tier2_max <= 0:
        # No second tier defined, flat pricing
        amount = usage * tier1_price
    else:
        # Tiered pricing calculation
        if usage <= tier1_max:
            amount = usage * tier1_price
        elif usage <= tier2_max:
            amount = tier1_max * tier1_price + (usage - tier1_max) * tier2_price
        else:
            amount = tier1_max * tier1_price
            amount += (tier2_max - tier1_max) * tier2_price
            amount += (usage - tier2_max) * tier3_price

    # Calculate internal cost and profit if available
    if "InternalCost" in modules_df.columns:
        internal_cost = usage * float(row.get("InternalCost", 0.0))
        profit = amount - internal_cost
    else:
        internal_cost = None
        profit = None

    # Store results
    module_names.append(module)
    usage_values.append(usage)
    amount_values.append(round(amount))
    cost_values.append(round(internal_cost) if internal_cost is not None else None)
    profit_values.append(round(profit) if profit is not None else None)

# Create dataframe for results
results_df = pd.DataFrame({
    "Module": module_names,
    "Usage": usage_values,
    "Amount (FCFA)": amount_values
})
if "InternalCost" in modules_df.columns:
    results_df["Internal Cost (FCFA)"] = cost_values
    results_df["Profit (FCFA)"] = profit_values

# Compute totals
total_amount = results_df["Amount (FCFA)"].sum()
total_cost = results_df["Internal Cost (FCFA)"].sum() if "Internal Cost (FCFA)" in results_df.columns else 0
total_profit = results_df["Profit (FCFA)"].sum() if "Profit (FCFA)" in results_df.columns else 0

# Display results
st.markdown("---")
if admin_mode:
    # Show detailed table and metrics for admin
    st.subheader("Revenue and Profit Breakdown by Module")
    st.table(results_df)  # display table with all columns
    # Show total revenue, cost, profit
    colA, colB, colC = st.columns(3)
    colA.metric("Total Revenue (FCFA)", f"{total_amount:,.0f}")
    colB.metric("Total Internal Cost (FCFA)", f"{total_cost:,.0f}")
    colC.metric("Total Profit (FCFA)", f"{total_profit:,.0f}")
else:
    # Show only total cost metric for normal user
    st.subheader("Total Estimated Cost")
    st.metric("Estimated Monthly Cost (FCFA)", f"{total_amount:,.0f}")

# If there's no usage at all (total_amount 0), avoid showing empty charts
if total_amount <= 0:
    st.warning("No usage entered. Adjust the sliders above to see the cost breakdown.")
else:
    # Prepare data for charts (use only Module and Amount columns for clarity)
    chart_df = results_df[["Module", "Amount (FCFA)"]]
    # Bar chart of cost by module
    fig_bar = px.bar(chart_df, x="Module", y="Amount (FCFA)", title="Cost by Module (FCFA)")
    # Pie chart of cost distribution
    fig_pie = px.pie(chart_df, names="Module", values="Amount (FCFA)", title="Cost Distribution by Module")
    st.plotly_chart(fig_bar, use_container_width=True)
    st.plotly_chart(fig_pie, use_container_width=True)

# Download CSV breakdown
if admin_mode:
    # Admin gets full breakdown including cost and profit
    export_df = results_df.copy()
else:
    # Regular user gets only Module, Usage, Amount
    export_df = results_df[["Module", "Usage", "Amount (FCFA)"]].copy()
    export_df = export_df.rename(columns={"Amount (FCFA)": "Cost (FCFA)"})
csv_data = export_df.to_csv(index=False)
st.download_button("Download breakdown CSV", data=csv_data, file_name="pricing_breakdown.csv", mime="text/csv")
