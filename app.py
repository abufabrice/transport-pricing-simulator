import streamlit as st
import pandas as pd
import altair as alt

# Load configuration data from CSV files
modules_df = pd.read_csv('modules_config.csv')
tiers_df   = pd.read_csv('module_tiers.csv')

# Drop any internal cost or profit columns from the data (not used in calculations)
for col in list(modules_df.columns):
    if 'internal' in col.lower() or 'profit' in col.lower():
        modules_df.drop(columns=[col], inplace=True)
for col in list(tiers_df.columns):
    if 'internal' in col.lower() or 'profit' in col.lower():
        tiers_df.drop(columns=[col], inplace=True)

# Identify important column names in the data
# (Adjust these if your CSV headers use different names)
module_col = None       # column name for module name
type_col = None         # column name for pricing type (flat or tiered)
price_col = None        # column name for flat price per unit
for col in modules_df.columns:
    clower = col.lower()
    if 'module' in clower or 'name' in clower:
        module_col = col
    elif 'type' in clower:
        type_col = col
    elif 'price' in clower and ('unit' in clower or clower.strip() == 'price'):
        price_col = col
# Ensure required columns are found
if module_col is None or type_col is None:
    st.error("`modules_config.csv` must have columns for module name and pricing type.")
    st.stop()
if price_col is None:
    # If no explicit unit price column is found, assume it's named 'Price' or 'UnitPrice'
    if 'UnitPrice' in modules_df.columns:
        price_col = 'UnitPrice'
    elif 'Price' in modules_df.columns:
        price_col = 'Price'
    else:
        # If flat prices are not provided (e.g., all modules are tiered), we can continue
        price_col = None

# Identify tier CSV columns for module, threshold, and price
tier_module_col = None
tier_threshold_col = None
tier_price_col = None
for col in tiers_df.columns:
    clower = col.lower()
    if 'module' in clower or 'name' in clower:
        tier_module_col = col
    elif 'threshold' in clower or 'limit' in clower:
        tier_threshold_col = col
    elif 'price' in clower and 'internal' not in clower and 'profit' not in clower:
        tier_price_col = col
if tier_module_col is None or tier_threshold_col is None or tier_price_col is None:
    st.error("`module_tiers.csv` must have columns for module name, threshold, and price.")
    st.stop()

# Title and description
st.title("Transport Pricing Simulator")
st.write("Adjust the usage of each module to simulate monthly costs. Toggle **Admin mode** to modify pricing parameters (unit prices or tier structures).")

# Admin mode toggle
admin_mode = st.checkbox("Admin mode")

# Dictionaries to store inputs and (possibly adjusted) pricing
usage_inputs = {}   # usage per module as set by the user
flat_prices = {}    # per-unit prices for flat modules (updated in admin mode)
tier_configs = {}   # tier DataFrames for tiered modules (updated in admin mode)

# Display sliders for each module's usage and admin inputs if applicable
for _, mod in modules_df.iterrows():
    module_name = str(mod[module_col])
    pricing_type = str(mod[type_col]).strip().lower()
    # Usage slider for this module
    usage = st.slider(f"{module_name} usage", min_value=0, max_value=1000, value=0, step=1)
    usage_inputs[module_name] = usage

    if admin_mode:
        # Show editable pricing parameters
        if pricing_type == 'flat':
            # Flat pricing: editable unit price
            if price_col is not None and pd.notna(mod.get(price_col, None)):
                default_price = float(mod[price_col])
            else:
                default_price = 0.0
            new_price = st.number_input(f"{module_name} unit price", min_value=0.0, value=default_price, step=0.01, format="%.2f")
            flat_prices[module_name] = new_price
        elif pricing_type == 'tiered':
            # Tiered pricing: show an editable table for tier thresholds and prices
            st.markdown(f"**{module_name} – Pricing Tiers:**")
            module_tiers = tiers_df[tiers_df[tier_module_col] == module_name].copy()
            # Remove the module name column from the display (for cleaner editing)
            if tier_module_col in module_tiers.columns:
                module_tiers_display = module_tiers.drop(columns=[tier_module_col])
            else:
                module_tiers_display = module_tiers
            # Editable data editor for tier thresholds and prices
            edited_tiers = st.data_editor(module_tiers_display, num_rows="fixed", hide_index=True, key=f"tiers_{module_name}")
            # Add the module name column back to the edited data for calculations
            edited_tiers[tier_module_col] = module_name
            tier_configs[module_name] = edited_tiers
        else:
            # If an unexpected pricing type is encountered
            st.warning(f"Module **{module_name}** has an unknown pricing type ('{mod[type_col]}').")
    else:
        # Not in admin mode: use original pricing values
        if pricing_type == 'flat':
            # Store the default flat price from the CSV (if available)
            if price_col is not None and pd.notna(mod.get(price_col, None)):
                flat_prices[module_name] = float(mod[price_col])
            else:
                flat_prices[module_name] = 0.0
        elif pricing_type == 'tiered':
            # Store the original tier DataFrame for this module
            module_tiers = tiers_df[tiers_df[tier_module_col] == module_name].copy()
            tier_configs[module_name] = module_tiers

# Calculate the cost for each module based on usage and pricing
results = []  # list to collect cost breakdown per module
for module_name, usage in usage_inputs.items():
    # Determine pricing type for this module
    mod_row = modules_df[modules_df[module_col] == module_name].iloc[0]
    pricing_type = str(mod_row[type_col]).strip().lower()
    cost = 0.0

    if pricing_type == 'flat':
        # Flat pricing calculation
        price_per_unit = flat_prices.get(module_name, 0.0)
        cost = usage * price_per_unit

    elif pricing_type == 'tiered':
        # Tiered pricing calculation
        # Use the tier configuration (edited if in admin mode, otherwise original)
        module_tiers = tier_configs.get(module_name, pd.DataFrame())
        if module_tiers.empty:
            # No tier data found; cost remains 0 (or could handle as error)
            cost = 0.0
        else:
            # Sort tiers by threshold value (numeric order); treat non-numeric or NaN as infinite tier
            finite_tiers = []
            infinite_price = None
            prev_threshold = 0.0

            for _, tier in module_tiers.iterrows():
                # Get threshold and price from the row
                threshold_val = tier[tier_threshold_col]
                price_val = tier[tier_price_col]
                # Determine if threshold is infinite (blank or non-numeric entry)
                thresh = None
                if pd.notna(threshold_val):
                    try:
                        thresh = float(threshold_val)
                    except:
                        thresh = None
                # Determine price as float (NaN -> 0)
                price = float(price_val) if pd.notna(price_val) else 0.0

                if thresh is None:
                    # Mark this tier as the "infinite" (no upper limit) tier
                    infinite_price = price
                else:
                    finite_tiers.append((thresh, price))

            # Sort finite tiers by threshold
            finite_tiers.sort(key=lambda x: x[0])
            remaining = float(usage)
            prev_threshold = 0.0

            # Apply costs for each finite tier in order
            for threshold, price in finite_tiers:
                if remaining <= 0:
                    break
                # Units applicable in this tier = difference between this tier's threshold and the previous tier's threshold
                tier_max_units = threshold - prev_threshold
                units_in_tier = min(tier_max_units, remaining)
                cost += units_in_tier * price
                remaining -= units_in_tier
                prev_threshold = threshold

            # If there's remaining usage beyond the last finite tier, apply the infinite tier price or last tier price
            if remaining > 0:
                if infinite_price is not None:
                    cost += remaining * infinite_price
                elif finite_tiers:
                    # If no infinite tier defined, use the last tier's price for the rest
                    last_price = finite_tiers[-1][1]
                    cost += remaining * last_price
                # If no tiers at all (edge case), remaining usage cost stays 0

    # Append this module's results
    results.append({"Module": module_name, "Usage": usage, "Cost": cost})

# Create a DataFrame with the results for display and charting
results_df = pd.DataFrame(results)

# Display the total monthly cost
total_cost = results_df["Cost"].sum()
st.subheader(f"**Total Monthly Cost: $ {total_cost:,.2f}**")

# Display bar chart and pie chart for cost breakdown by module
st.markdown("**Cost Breakdown by Module:**")
# Bar chart (cost per module)
st.bar_chart(results_df.set_index('Module')["Cost"])
# Pie chart (cost distribution) using Altair for better presentation
pie_chart = alt.Chart(results_df).mark_arc(innerRadius=50).encode(
    theta=alt.Theta(field="Cost", type="quantitative"),
    color=alt.Color(field="Module", type="nominal"),
    tooltip=[
        alt.Tooltip(field="Module", type="nominal"),
        alt.Tooltip(field="Cost", type="quantitative", format="$,.2f")
    ]
)
st.altair_chart(pie_chart, use_container_width=True)

# Provide a download button for the cost breakdown CSV
csv_data = results_df.to_csv(index=False)
st.download_button(
    label="Download cost breakdown CSV",
    data=csv_data,
    file_name="cost_breakdown.csv",
    mime="text/csv"
)
