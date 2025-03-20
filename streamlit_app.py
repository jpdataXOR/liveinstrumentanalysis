import streamlit as st
import time
import pandas as pd
import plotly.graph_objects as go
import streamlit.components.v1 as components
from data_utils import get_forex_data, convert_to_aest, generate_future_projections_from_point
from datetime import datetime
import numpy as np

# Streamlit UI
st.set_page_config(page_title="Live Forex Prices", layout="wide")
st.title("📈 Live Forex Prices & Future Projections")

# UI Controls - Top Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("**💱 Forex Pair:**")
    forex_pair = st.selectbox(
        "Select currency pair:",
        ["AUDUSD=X", "USDJPY=X", "AUDNZD=X", "USDCHF=X", "EURUSD=X"],
        format_func=lambda x: x.replace("=X", ""),
        index=0
    )

with col2:
    st.markdown("**⏳ Refresh Interval:**")
    refresh_rate = st.radio(
        "Choose refresh rate:",
        [15, 30, 60, 300],
        format_func=lambda x: f"{x} sec" if x < 60 else f"{x//60} min",
        horizontal=True,
        index=1
    )

with col3:
    st.markdown("**🕒 Chart Interval:**")
    ohlc_interval = st.radio(
        "Choose interval:",
        ["15m", "1h", "4h"],
        horizontal=True,
        index=1
    )

with col4:
    st.markdown("**⏳ Next Refresh In:**")
    countdown_placeholder = st.empty()

# Display latest price
latest_price_container = st.container()
col1, col2 = latest_price_container.columns([1, 1])

with col1:
    latest_price_placeholder = st.empty()

with col2:
    latest_time_placeholder = st.empty()

# Add controls for Y-axis scaling and projections
col1, col2, col3 = st.columns(3)
with col1:
    y_axis_padding = st.slider(
        "Y-Axis Padding (%)",
        min_value=1,
        max_value=10,
        value=5,
        help="Percentage padding above and below the main price range"
    )

with col2:
    clip_projections = st.checkbox(
        "Clip Extreme Projections",
        value=True,
        help="Limit projection values to a reasonable range"
    )

with col3:
    projections_per_point = st.slider(
        "Projections per Point",
        min_value=1,
        max_value=10,
        value=3,
        help="Number of prediction lines to generate from each point"
    )

# Additional options for forex data - just lookback period (removed display points)
lookback_period = st.selectbox(
    "Historical Data Period:",
    ["1d", "5d", "7d", "1mo"],
    index=3,
    help="How far back to fetch historical data"
)

# Initialize session state for first run tracking
if "is_first_run" not in st.session_state:
    st.session_state.is_first_run = True

# Initialize session state
if "price_history" not in st.session_state:
    st.session_state.price_history = pd.DataFrame(columns=["date", "close"])

# Chart & Debug placeholders
placeholder_chart = st.empty()
placeholder_debug = st.empty()
placeholder_data_info = st.empty()

# Main loop
while True:
    # Fetch latest forex data
    stock_data = get_forex_data(forex_pair, ohlc_interval, lookback_period)

    if not stock_data:
        debug_message = "**⚠ No new data received!**"
        data_info_message = ""
        latest_price = "N/A"
        latest_time = "N/A"
    else:
        st.session_state.price_history = stock_data.copy()

        # Calculate how much historical data we have
        total_data_points = len(stock_data)
        earliest_date = datetime.strptime(stock_data[0]["date"], "%d-%b-%Y %H:%M")
        latest_date = datetime.strptime(stock_data[-1]["date"], "%d-%b-%Y %H:%M")
        date_range = latest_date - earliest_date

        # Format date range based on its span
        if date_range.days > 0:
            date_range_str = f"{date_range.days} days, {date_range.seconds // 3600} hours"
        else:
            date_range_str = f"{date_range.seconds // 3600} hours, {(date_range.seconds % 3600) // 60} minutes"

        latest_row = stock_data[-1]
        latest_price = latest_row["close"]
        latest_time = convert_to_aest(latest_row["date"])
        debug_message = f"📌 **Debug:** Latest Data → {latest_row}"

        # Create data info message
        data_info_message = f"""
        📊 **Historical Data Summary:**
        - Total data points: **{total_data_points}**
        - Date range: **{date_range_str}**
        - First record: **{convert_to_aest(stock_data[0]['date'])}**
        - Last record: **{latest_time}**
        - Interval: **{ohlc_interval}**
        """

    # Display latest price with appropriate formatting based on forex pair
    with latest_price_placeholder:
        # Format price based on currency pair (most forex have 4-5 decimal places)
        if "JPY" in forex_pair:
            price_format = f"{latest_price:.3f}"  # JPY pairs typically have 3 decimal places
        else:
            price_format = f"{latest_price:.5f}"  # Other pairs typically have 5 decimal places
            
        pair_display = forex_pair.replace("=X", "")
        st.markdown(f"<h2 style='text-align: center; color: green;'>{pair_display}: {price_format}</h2>", unsafe_allow_html=True)

    with latest_time_placeholder:
        st.markdown(f"<h3 style='text-align: center;'>🕒 {latest_time} AEST</h3>", unsafe_allow_html=True)

    # Create chart
    with placeholder_chart.container():
        fig = go.Figure()

        if stock_data:
            # Get the last 20 data points for display
            last_20_data = stock_data[-20:]

            # Determine y-axis range based on actual price data
            prices = [item["close"] for item in last_20_data]
            min_price = min(prices)
            max_price = max(prices)
            price_range = max_price - min_price

            # Calculate y-axis limits with padding
            padding = price_range * (y_axis_padding / 100)
            y_min = max(0, min_price - padding)  # Ensure we don't go below zero
            y_max = max_price + padding

            # Add the main price line
            fig.add_trace(go.Scatter(
                x=[convert_to_aest(item["date"]) for item in last_20_data],
                y=[item["close"] for item in last_20_data],
                mode="lines",
                line=dict(shape="hv", color="black", width=2),
                name="Price",
            ))

            # Add dot and price label at the latest point
            latest_point = last_20_data[-1]
            latest_point_date = convert_to_aest(latest_point["date"])
            latest_point_price = latest_point["close"]

            # Format price label based on currency pair
            if "JPY" in forex_pair:
                price_text = f"{latest_point_price:.3f}"
            else:
                price_text = f"{latest_point_price:.5f}"

            fig.add_trace(go.Scatter(
                x=[latest_point_date],
                y=[latest_point_price],
                mode="markers+text",
                marker=dict(size=10, color="black"),
                text=[price_text],
                textposition="top right",
                textfont=dict(size=12, color="black"),
                name="Latest Point",
                showlegend=False,
            ))

            # Starting point for projections (point 10 to point 20) - 0-indexed
            # This is the simplified approach from paste-2.txt
            projection_start_points = range(9, 20)  # 9 is the 10th point from the end (0-indexed)

            # Store all projection points to analyze extreme values
            all_projection_values = []

            # Dictionary to store projection values for each future time point
            future_projection_values = {}
            latest_point_projection_values = {}  # Store projections from the latest point

            # Track pattern matches to report on pattern quality
            pattern_matches = {}

            # Generate and display projections for each starting point
            for idx in projection_start_points:
                # Skip if outside the range of our displayed data
                if idx >= len(last_20_data):
                    continue
                    
                # Get the point from last_20_data
                start_point = last_20_data[idx]
                
                # Find the corresponding index in the full stock_data
                start_idx_full = stock_data.index(start_point)
                
                # Generate multiple projections starting from this point
                projections = generate_future_projections_from_point(
                    stock_data, 
                    start_idx_full, 
                    future_points=10, 
                    num_lines=projections_per_point
                )

                # Store pattern match information for reporting
                if projections:
                    pattern_matches[idx] = {
                        "count": len(projections),
                        "pattern_lengths": []
                    }

                # Is this the latest point? (p20)
                is_latest_point = (idx == 19) or (idx == len(last_20_data) - 1)

                # Process each projection for this point
                for proj_idx, proj in enumerate(projections):
                    # Capture pattern length if available
                    if "pattern_length" in proj:
                        pattern_matches[idx]["pattern_lengths"].append(proj["pattern_length"])

                    # Use red for latest point projections, gray for others
                    # Vary opacity for multiple lines from the same point
                    base_opacity = 0.8 if is_latest_point else 0.6
                    opacity = base_opacity - (0.1 * proj_idx)  # Decrease opacity for additional lines
                    opacity = max(0.3, opacity)  # Don't go too transparent

                    if is_latest_point:
                        color = f"rgba(255,0,0,{opacity})"
                        line_width = 2 if proj_idx == 0 else 1.5
                    else:
                        color = f"rgba(150,150,150,{opacity})"
                        line_width = 1

                    # Format the projection label
                    point_number = idx + 1
                    if proj_idx == 0:
                        label = f"Latest Projection" if is_latest_point else f"From P{point_number}"
                    else:
                        label = f"Latest Alt {proj_idx+1}" if is_latest_point else f"From P{point_number} Alt {proj_idx+1}"

                    # Process projection data
                    projection_data = proj["data"].copy()
                    if clip_projections:
                        # Collect all values for checking extremes
                        for point in projection_data:
                            all_projection_values.append(point["close"])

                    # Store projection values by time point
                    for point_idx, point in enumerate(projection_data):
                        time_point = point["date"]
                        if time_point not in future_projection_values:
                            future_projection_values[time_point] = {}
                        if idx not in future_projection_values[time_point]:
                            future_projection_values[time_point][idx] = []
                        future_projection_values[time_point][idx].append(point["close"])

                        # Store latest point's projections separately
                        if is_latest_point:
                            if time_point not in latest_point_projection_values:
                                latest_point_projection_values[time_point] = []
                            latest_point_projection_values[time_point].append(point["close"])

                    fig.add_trace(go.Scatter(
                        x=[convert_to_aest(item["date"]) for item in projection_data],
                        y=[item["close"] for item in projection_data],
                        mode="lines",
                        line=dict(shape="hv", dash="dot", color=color, width=line_width),
                        name=label,
                    ))

            # Calculate and display average projections for each time point (overall average)
            avg_projection_data = {}
            for time_point, start_point_projections in future_projection_values.items():
                avg_projection_data[time_point] = {}
                all_values = []
                for start_idx_local, values in start_point_projections.items():
                    all_values.extend(values)
                if all_values:
                    avg_projection_data[time_point]["avg"] = np.mean(all_values)

            sorted_time_points_overall = sorted(avg_projection_data.keys())
            avg_projection_x_overall = [convert_to_aest(t) for t in sorted_time_points_overall]
            avg_projection_y_overall = [avg_projection_data[t]["avg"] for t in sorted_time_points_overall]

            if avg_projection_x_overall and avg_projection_y_overall:
                fig.add_trace(go.Scatter(
                    x=avg_projection_x_overall,
                    y=avg_projection_y_overall,
                    mode="lines",
                    line=dict(shape="hv", dash="dot", color="rgba(100,180,255,0.8)", width=2.5), # Light blue
                    name="Average Projection (All)",
                ))

            # Calculate and display average projection for the latest point
            avg_latest_projection_data = {}
            for time_point, values in latest_point_projection_values.items():
                if values:
                    avg_latest_projection_data[time_point] = np.mean(values)

            sorted_time_points_latest = sorted(avg_latest_projection_data.keys())
            avg_latest_projection_x = [convert_to_aest(t) for t in sorted_time_points_latest]
            avg_latest_projection_y = [avg_latest_projection_data[t] for t in sorted_time_points_latest]

            if avg_latest_projection_x and avg_latest_projection_y:
                fig.add_trace(go.Scatter(
                    x=avg_latest_projection_x,
                    y=avg_latest_projection_y,
                    mode="lines",
                    line=dict(shape="hv", dash="dot", color="rgba(0,0,180,0.8)", width=2.5), # Darker blue
                    name="Average Projection (Latest Point)",
                ))

            # Adjust y-axis range if extreme projections need to be accommodated
            if clip_projections and all_projection_values:
                # Calculate reasonable limits for projections
                # Allow projections to extend the range by 50% at most
                projection_min = min(all_projection_values)
                projection_max = max(all_projection_values)

                # Only expand the range if projections are within a reasonable distance
                max_expansion = price_range * 0.5

                if projection_min < y_min and projection_min > y_min - max_expansion:
                    y_min = projection_min

                if projection_max > y_max and projection_max < y_max + max_expansion:
                    y_max = projection_max

            # Set the y-axis range
            fig.update_layout(
                yaxis=dict(
                    range=[y_min, y_max],
                )
            )

        pair_display = forex_pair.replace("=X", "")
        fig.update_layout(
            title=f"Live {pair_display} Price with Future Predictions ({ohlc_interval})",
            xaxis_title="Time (AEST)",
            yaxis_title="Price",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    # Show data info message
    with placeholder_data_info:
        st.markdown(data_info_message)

    # Show debug message
    with placeholder_debug.container():
        st.markdown(debug_message)
        if clip_projections and 'all_projection_values' in locals() and all_projection_values and stock_data:
            total_projections = len(projection_start_points) * projections_per_point
            
            if "JPY" in forex_pair:
                y_min_format = f"{y_min:.3f}"
                y_max_format = f"{y_max:.3f}"
            else:
                y_min_format = f"{y_min:.5f}"
                y_max_format = f"{y_max:.5f}"
                
            st.markdown(f"Y-axis range: {y_min_format} - {y_max_format} | Generating {projections_per_point} projections per point × {len(projection_start_points)} points = {total_projections} total projections")

            # Display pattern match information if available
            if pattern_matches:
                total_patterns = sum(match["count"] for match in pattern_matches.values())
                all_pattern_lengths = [length for match in pattern_matches.values() for length in match["pattern_lengths"]]
                avg_pattern_length = np.mean(all_pattern_lengths) if all_pattern_lengths else "N/A"

                pattern_info = f"""
                🔍 **Pattern Matching Stats:**
                - Total pattern matches found: **{total_patterns}**
                - Average pattern length: **{avg_pattern_length if avg_pattern_length != 'N/A' else 'N/A'}**
                - Using **{len(stock_data)}** historical data points for pattern matching
                """
                st.markdown(pattern_info)

    # Update countdown timer
    for remaining in range(refresh_rate, 0, -1):
        countdown_placeholder.markdown(f"**{remaining} sec**", unsafe_allow_html=True)
        time.sleep(1)

    # Update browser tab with latest price
    if isinstance(latest_price, (int, float)):
        if "JPY" in forex_pair:
            price_format = f"{latest_price:.3f}"
        else:
            price_format = f"{latest_price:.5f}"
        pair_display = forex_pair.replace("=X", "")
        components.html(f"<script>document.title = '{pair_display}: {price_format}';</script>", height=0)