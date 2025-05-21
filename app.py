import streamlit as st
import pandas as pd
import altair as alt

# Load data
modules_df = pd.read_csv('modules_config.csv')
tiers_df = pd.read_csv('module_tiers.csv')

# Set up app
st.set_page_config(page_title="Transport Pricing Simulator", layout="wide")
st.title("Transport Pricing Simulator")
st.markdown("Adjust usage per module to simulate your monthly costs. Toggle **Admin Mode** to configure pricing.")

# Identify required columns
module_col = 'Module'
type_col = 'Type'
price_col = 'UnitPrice'
tier_module_col = 'Module'
tier_threshold_col = 'Threshold'
tier_price_col = 'Price'

# Admin mode toggle
admin_mode = st.sidebar.checkbox("Enable Admin Mode")

# Inputs
usage_inputs = {}
flat_prices = {}
tier_configs = {}

for _, mod in modules_df.iterrows():
    module_name = str(mod[module_col])
    pricing_type = str(mod[type_col]).lower()

    usage = st.slider(f"{module_name} usage", 0, 1000, 0)
    usage_inputs[module_name] = usage

    if admin_mode:
        if pricing_type == 'flat':
            default_price = float(mod[price_col]) if price_col in mod else 0.0
            flat_prices[module_name] = st.number_input(
                f"{module_name} unit price", value=default_price, min_value=0.0, step=0.01)
        elif pricing_type == 'tiered':
            st.markdown(f"**{module_name} – Pricing Tiers:**")
            tiers = tiers_df[tiers_df[tier_module_col] == module_name].copy()
            editable = st.data_editor(tiers.drop(columns=[tier_module_col]), num_rows="fixed", key=f"tiers_{module_name}")
            editable[tier_module_col] = module_name
            tier_configs[module_name] = editable
    else:
        if pricing_type == 'flat':
            flat_prices[module_name] = float(mod[price_col]) if price_col in mod else 0.0
        elif pricing_type == 'tiered':
            tier_configs[module_name] = tiers_df[tiers_df[tier_module_col] == module_name].copy()

# Calculate costs
results = []
for module_name, usage in usage_inputs.items():
    pricing_type = str(modules_df[modules_df[module_col] == module_name][type_col].values[0]).lower()
    cost = 0.0

    if pricing_type == 'flat':
        cost = usage * flat_prices.get(module_name, 0.0)
    elif pricing_type == 'tiered':
        tiers = tier_configs.get(module_name, pd.DataFrame())
        if not tiers.empty:
            finite = []
            infinite_price = None
            for _, t in tiers.iterrows():
                try:
                    thresh = float(t[tier_threshold_col])
                    price = float(t[tier_price_col])
                    finite.append((thresh, price))
                except:
                    infinite_price = float(t[tier_price_col])
            finite.sort()
            remaining = usage
            prev = 0
            for thresh, price in finite:
                if remaining <= 0: break
                span = thresh - prev
                portion = min(span, remaining)
                cost += portion * price
                remaining -= portion
                prev = thresh
            if remaining > 0:
                cost += remaining * (infinite_price if infinite_price is not None else finite[-1][1] if finite else 0.0)

    results.append({"Module": module_name, "Usage": usage, "Cost": cost})

# Display results
results_df = pd.DataFrame(results)
total = results_df["Cost"].sum()
st.subheader(f"**Total Monthly Cost: {total:,.2f} FCFA**")

st.bar_chart(results_df.set_index("Module")["Cost"])
pie = alt.Chart(results_df).mark_arc(innerRadius=40).encode(
    theta=alt.Theta("Cost", type="quantitative"),
    color=alt.Color("Module", type="nominal"),
    tooltip=["Module", "Cost"]
)
st.altair_chart(pie, use_container_width=True)

# Export
csv = results_df.to_csv(index=False)
st.download_button("Download CSV", csv, "pricing_breakdown.csv", "text/csv")
