import streamlit as tf
import requests
import time
from datetime import datetime

# Configure Streamlit Page
tf.set_page_config(
    page_title="Swiggy Proactive Ordering Agent",
    page_icon="🍊",
    layout="wide"
)

API_URL = "http://localhost:8000/api"

tf.title("🍊 Swiggy Proactive Ordering Agent")
tf.subheader("Builders Club MCP Developer Program Sandbox Demo")

# Custom Styling
tf.markdown("""
<style>
    .reportview-container {
        background: #FFF5EC;
    }
    .stButton>button {
        border-radius: 8px;
    }
    .card-style {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #fc8019;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Session States
if "active_orders" not in tf.session_state:
    tf.session_state.active_orders = []
if "edit_quantities" not in tf.session_state:
    tf.session_state.edit_quantities = {}

# Sidebar for Sandbox Simulation Settings
tf.sidebar.header("🛠️ Simulation Control Panel")
tf.sidebar.info("Simulate user context to trigger the proactive agents:")

sim_day = tf.sidebar.selectbox(
    "Day of the Week",
    options=["Friday (History Fired!)", "Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
    index=0
)

# Map selected day to an actual date in the seed calendar
day_map = {
    "Friday (History Fired!)": "2026-07-03T19:30:00",
    "Saturday": "2026-07-04T12:00:00",
    "Sunday": "2026-07-05T13:00:00",
    "Monday": "2026-07-06T08:30:00",
    "Tuesday": "2026-07-07T08:30:00",
    "Wednesday": "2026-07-08T08:30:00",
    "Thursday": "2026-07-09T08:30:00"
}

sim_date_iso = day_map[sim_day]

sim_weather = tf.sidebar.selectbox(
    "Current Weather Condition",
    options=["rainy (History Fired!)", "pleasant", "hot", "cold"],
    index=0
)
weather_val = sim_weather.split(" ")[0]

tf.sidebar.markdown("---")
tf.sidebar.subheader("🔒 Builders Club Constraints")
tf.sidebar.markdown("""
- **Cart Cap**: Max ₹1000 per cart.
- **Payment**: Cash on Delivery (COD) only.
- **Food Cart**: Strict single-restaurant binding.
- **Scheduled Orders**: Not supported (immediate only).
""")

# Tabs
tab_triggers, tab_optin, tab_track, tab_history = tf.tabs([
    "🎯 Proactive Suggestions", 
    "🥛 Instamart Staples Opt-In", 
    "🛵 Live Order Tracking", 
    "📜 SQLite Past Orders"
])

# --- TAB 1: PROACTIVE SUGGESTIONS ---
with tab_triggers:
    tf.write("### Today's Context")
    col1, col2, col3 = tf.columns(3)
    col1.metric("Simulated Time/Date", datetime.fromisoformat(sim_date_iso).strftime('%A, %b %d, %Y - %H:%M'))
    col2.metric("Simulated Weather", weather_val.upper())
    col3.metric("Builders Club Account Cap", "₹1000.00 (COD)")

    if tf.button("⚡ Run Proactive Agent Triggers", type="primary"):
        with tf.spinner("LangGraph engines analyzing historical frequency and weather signals..."):
            try:
                # Call triggers API
                res = requests.post(f"{API_URL}/check-triggers", params={"simulated_date": sim_date_iso, "weather": weather_val})
                if res.status_code == 200:
                    data = res.json()
                    suggestions = data.get("suggestions", [])
                    
                    if not suggestions:
                        tf.info("No proactive order suggestions triggered today. Weather frequency threshold (>=60%) or historical ordering time windows not matched, or pattern was dismissed.")
                    else:
                        for idx, sug in enumerate(suggestions):
                            # Handle Merged Suggestion
                            if sug["trigger_type"] == "merged":
                                tf.markdown(f"### 🍊 {sug['explanation']}")
                                sub_sugs = sug["sub_suggestions"]
                            else:
                                sub_sugs = [sug]
                                
                            for s_idx, sub_sug in enumerate(sub_sugs):
                                trig_type = sub_sug["trigger_type"].replace("_", " ").title()
                                ord_type = sub_sug["order_type"].upper()
                                
                                tf.markdown(f"""
                                <div class="card-style">
                                    <h4>💡 {trig_type} Recommendation ({ord_type})</h4>
                                    <p><strong>Reasoning:</strong> {sub_sug['explanation']}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Distance warning guardrail (Swiggy MCP constraint: warn user if food >5km)
                                if ord_type == "FOOD":
                                    # Since Meghana is 2.1km and Empire is 5.2km, display a clean warning for Empire:
                                    # For simplicity in mock data, check if distance > 5km
                                    if sub_sug.get("restaurant_id") == "rest_004":
                                        tf.warning("⚠️ Swiggy Distance Guardrail: This restaurant is > 5.0 km away (5.2 km). Extended delivery fees and longer timings might apply.")

                                # Display draft items
                                items_to_order = []
                                tf.write("**Draft Cart Items:**")
                                for item in sub_sug["items"]:
                                    item_id = item.get("item_id") or item.get("product_id")
                                    # Edit Quantity Section
                                    qty_key = f"qty_{idx}_{s_idx}_{item_id}"
                                    qty = tf.number_input(f"Quantity for {item['name']} (₹{item['price']})", min_value=1, max_value=10, value=item["quantity"], key=qty_key)
                                    
                                    items_to_order.append({
                                        "item_id" if ord_type == "FOOD" else "product_id": item_id,
                                        "quantity": qty,
                                        "price": item["price"],
                                        "name": item["name"]
                                    })
                                
                                total_amt = sum(it["price"] * it["quantity"] for it in items_to_order)
                                tf.write(f"**Total Amount: ₹{total_amt:.2f}**")
                                
                                # Buttons
                                btn_col1, btn_col2, btn_col3 = tf.columns(3)
                                
                                # Confirm Order Button
                                confirm_id = f"confirm_{idx}_{s_idx}"
                                if btn_col1.button("✅ Confirm & Place Order", key=confirm_id):
                                    # Call place order
                                    payload = {
                                        "order_type": sub_sug["order_type"],
                                        "restaurant_id": sub_sug.get("restaurant_id"),
                                        "items": items_to_order,
                                        "payment_method": "COD"
                                    }
                                    order_res = requests.post(f"{API_URL}/order/place", json=payload)
                                    if order_res.status_code == 200:
                                        order_data = order_res.json()
                                        if order_data.get("success"):
                                            tf.success(f"🎉 {order_data['message']} Order ID: {order_data['order_id']}")
                                            tf.session_state.active_orders.append({
                                                "order_id": order_data["order_id"],
                                                "type": sub_sug["order_type"]
                                            })
                                        else:
                                            tf.error(f"❌ Order placement failed: {order_data.get('message')}")
                                    else:
                                        tf.error("❌ API server error.")
                                
                                # Dismiss Button
                                dismiss_id = f"dismiss_{idx}_{s_idx}"
                                if btn_col2.button("🚫 Dismiss (Stop Suggesting)", key=dismiss_id):
                                    payload = {
                                        "pattern_key": sub_sug["pattern_key"],
                                        "is_staple": sub_sug["trigger_type"] == "consumption_based"
                                    }
                                    dismiss_res = requests.post(f"{API_URL}/dismiss-pattern", json=payload)
                                    if dismiss_res.status_code == 200:
                                        dis_data = dismiss_res.json()
                                        tf.warning(f"Pattern dismissed. {dis_data['message']}")
                                    else:
                                        tf.error("❌ API server error.")
                else:
                    tf.error("Failed to fetch suggestions from FastAPI.")
            except Exception as e:
                tf.error(f"Could not connect to FastAPI backend at {API_URL}. Is the server running? Details: {e}")

# --- TAB 2: INSTAMART STAPLES OPT-IN ---
with tab_optin:
    tf.write("### Instamart Staples Optimization (Hybrid Confirmation)")
    tf.markdown("""
    Under Swiggy Builders Club constraints, we **strictly reject unsolicited surveillance** of user items.
    Items must be purchased **at least 2+ times** to be highlighted as candidates, and will only be monitored
    for replenishment alerts if you **explicitly opt-in** once here.
    """)
    
    # Refresh triggers first to search candidates
    try:
        res = requests.post(f"{API_URL}/check-triggers", params={"simulated_date": sim_date_iso, "weather": weather_val})
        if res.status_code == 200:
            candidates = res.json().get("candidate_staples", [])
            if not candidates:
                tf.write("No candidate staples (ordered 2+ times) found yet. Try ordering staples in the Sandbox history.")
            else:
                for cand in candidates:
                    col_name, col_cycle, col_action = tf.columns([3, 2, 2])
                    col_name.write(f"🥛 **{cand['product_name']}**")
                    col_cycle.write(f"Estimated consumption cycle: Every **{cand['estimated_cycle']} days**")
                    
                    opt_key = f"opt_{cand['product_id']}"
                    # Ask once hybrid confirmation
                    if col_action.button("Opt-In Replenishment Alerts", key=opt_key):
                        payload = {
                            "product_id": cand["product_id"],
                            "product_name": cand["product_name"],
                            "confirm": True
                        }
                        opt_res = requests.post(f"{API_URL}/opt-in-staple", json=payload)
                        if opt_res.status_code == 200:
                            tf.success(f"Opt-in confirmed for {cand['product_name']}! We will proactively draft order suggests {cand['estimated_cycle']} days after purchase.")
                            time.sleep(1)
                            tf.rerun()
    except Exception as e:
        tf.error(f"Could not connect to API: {e}")

# --- TAB 3: LIVE ORDER TRACKING ---
with tab_track:
    tf.write("### Live Order Tracking (Post-Order Polling)")
    tf.markdown("Under Swiggy platform constraints, live order ETAs are polled every **10 seconds** post-placement.")
    
    if not tf.session_state.active_orders:
        tf.write("No active orders being tracked. Confirm a draft suggestion first!")
    else:
        for idx, act in enumerate(tf.session_state.active_orders):
            order_id = act["order_id"]
            ord_type = act["type"]
            
            tf.markdown(f"#### Order: `{order_id}` ({ord_type.upper()})")
            
            # Button to simulate polling
            if tf.button(f"🔄 Poll Track Status for {order_id}", key=f"poll_{order_id}"):
                with tf.spinner("Requesting live Swiggy delivery dispatcher ETA..."):
                    track_res = requests.get(f"{API_URL}/order/track/{order_id}", params={"type": ord_type})
                    if track_res.status_code == 200:
                        track_data = track_res.json()
                        if track_data.get("success"):
                            col_stat, col_eta = tf.columns(2)
                            col_stat.success(f"Status: **{track_data['status']}**")
                            col_eta.metric("Simulated Live ETA", f"{track_data['eta_minutes']} MINS")
                        else:
                            tf.error(f"Tracking error: {track_data.get('message')}")
                    else:
                        tf.error("Tracking request failed.")

# --- TAB 4: SQLITE PAST ORDERS ---
with tab_history:
    tf.write("### SQLite Order History Database")
    tf.write("This table shows the historic database used by the LangGraph agents to extract order frequency patterns:")
    try:
        history_res = requests.get(f"{API_URL}/history")
        if history_res.status_code == 200:
            hist_list = history_res.json()
            if not hist_list:
                tf.warning("Order history is currently empty. Run python seed_data.py to populate.")
            else:
                tf.dataframe(hist_list)
        else:
            tf.error("Could not fetch database rows.")
    except Exception as e:
        tf.error(f"Could not connect: {e}")
