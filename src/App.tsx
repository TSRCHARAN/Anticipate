import { useState, useEffect } from "react";
import { 
  Flame, 
  CloudRain, 
  Calendar, 
  AlertTriangle, 
  CheckCircle, 
  Trash2, 
  RotateCcw, 
  TrendingUp, 
  Database, 
  ShoppingBag, 
  Clock, 
  HelpCircle, 
  ChevronRight, 
  Sliders, 
  AlertCircle 
} from "lucide-react";

// Types corresponding to Python SQLite models
interface OrderHistoryItem {
  id: number;
  order_type: "food" | "instamart";
  restaurant_id?: string;
  restaurant_name?: string;
  item_id: string;
  item_name: string;
  price: number;
  quantity: number;
  order_time: string;
  day_of_week: number;
  hour: number;
  weather_condition: "rainy" | "pleasant" | "hot" | "cold";
}

interface StapleConfig {
  product_id: string;
  product_name: string;
  price: number;
  is_confirmed: boolean;
  dismissed_count: number;
  cycle_length: number;
  last_suggested_date?: string;
  dates: string[];
}

interface ActiveOrder {
  order_id: string;
  type: "food" | "instamart";
  origin_name: string;
  items: { name: string; price: number; quantity: number }[];
  total_amount: number;
  eta_minutes: number;
  status: "ORDERED" | "PREPARING" | "PACKING" | "DISPATCHED" | "RIDER_NEARBY" | "DELIVERED";
}

export default function App() {
  // --- STATE 1: Simulation Context ---
  const [selectedDay, setSelectedDay] = useState<string>("Friday");
  const [selectedWeather, setSelectedWeather] = useState<"rainy" | "pleasant" | "hot" | "cold">("rainy");
  const [restaurantDistance, setRestaurantDistance] = useState<number>(2.1); // in km (Meghana = 2.1, Empire = 5.2)

  // --- STATE 2: Database Storage (In-Memory / LocalStorage) ---
  const [orderHistory, setOrderHistory] = useState<OrderHistoryItem[]>([
    // Rainy Friday Evening Food Biryani Pattern (4 items, 75% rainy weather)
    { id: 1, order_type: "food", restaurant_id: "rest_001", restaurant_name: "Meghana Foods", item_id: "m1", item_name: "Special Chicken Biryani", price: 320, quantity: 1, order_time: "2206-06-26T19:30:00", day_of_week: 5, hour: 19, weather_condition: "rainy" },
    { id: 2, order_type: "food", restaurant_id: "rest_001", restaurant_name: "Meghana Foods", item_id: "m1", item_name: "Special Chicken Biryani", price: 320, quantity: 1, order_time: "2206-06-19T20:15:00", day_of_week: 5, hour: 20, weather_condition: "rainy" },
    { id: 3, order_type: "food", restaurant_id: "rest_001", restaurant_name: "Meghana Foods", item_id: "m1", item_name: "Special Chicken Biryani", price: 320, quantity: 1, order_time: "2206-06-12T19:45:00", day_of_week: 5, hour: 19, weather_condition: "rainy" },
    { id: 4, order_type: "food", restaurant_id: "rest_001", restaurant_name: "Meghana Foods", item_id: "m1", item_name: "Special Chicken Biryani", price: 320, quantity: 1, order_time: "2206-06-05T19:15:00", day_of_week: 5, hour: 19, weather_condition: "pleasant" },

    // Milk Replenishment (Instamart, ordered every 4 days)
    { id: 5, order_type: "instamart", item_id: "p1", item_name: "Nandini Fresh Milk (500ml)", price: 27, quantity: 2, order_time: "2206-06-16T08:00:00", day_of_week: 2, hour: 8, weather_condition: "pleasant" },
    { id: 6, order_type: "instamart", item_id: "p1", item_name: "Nandini Fresh Milk (500ml)", price: 27, quantity: 2, order_time: "2206-06-20T08:30:00", day_of_week: 6, hour: 8, weather_condition: "pleasant" },
    { id: 7, order_type: "instamart", item_id: "p1", item_name: "Nandini Fresh Milk (500ml)", price: 27, quantity: 2, order_time: "2206-06-24T08:15:00", day_of_week: 3, hour: 8, weather_condition: "pleasant" },
    { id: 8, order_type: "instamart", item_id: "p1", item_name: "Nandini Fresh Milk (500ml)", price: 27, quantity: 2, order_time: "2206-06-28T09:00:00", day_of_week: 0, hour: 9, weather_condition: "pleasant" },
    { id: 9, order_type: "instamart", item_id: "p1", item_name: "Nandini Fresh Milk (500ml)", price: 27, quantity: 2, order_time: "2206-07-02T08:10:00", day_of_week: 4, hour: 8, weather_condition: "pleasant" },

    // Fresh Eggs (Ordered 2 times => candidate, not yet confirmed)
    { id: 10, order_type: "instamart", item_id: "p2", item_name: "Fresh Eggs (Pack of 6)", price: 48, quantity: 1, order_time: "2206-06-25T08:30:00", day_of_week: 4, hour: 8, weather_condition: "pleasant" },
    { id: 11, order_type: "instamart", item_id: "p2", item_name: "Fresh Eggs (Pack of 6)", price: 48, quantity: 1, order_time: "2206-06-30T08:45:00", day_of_week: 2, hour: 8, weather_condition: "pleasant" },
  ]);

  const [stapleConfigs, setStapleConfigs] = useState<StapleConfig[]>([
    {
      product_id: "p1",
      product_name: "Nandini Fresh Milk (500ml)",
      price: 27,
      is_confirmed: true,
      dismissed_count: 0,
      cycle_length: 4.0,
      dates: ["2206-06-16", "2206-06-20", "2206-06-24", "2206-06-28", "2206-07-02"]
    },
    {
      product_id: "p2",
      product_name: "Fresh Eggs (Pack of 6)",
      price: 48,
      is_confirmed: false, // Pending User Confirmation
      dismissed_count: 0,
      cycle_length: 5.0,
      dates: ["2206-06-25", "2206-06-30"]
    }
  ]);

  const [dismissedPatterns, setDismissedPatterns] = useState<Record<string, number>>({});

  // --- STATE 3: Engine Computation Outputs ---
  const [activeTab, setActiveTab] = useState<"suggestions" | "staples" | "tracker" | "database">("suggestions");
  const [isRunningTriggers, setIsRunningTriggers] = useState<boolean>(false);
  const [triggeredSuggestions, setTriggeredSuggestions] = useState<any[]>([]);
  const [langGraphLogs, setLangGraphLogs] = useState<string[]>([]);
  const [activeOrders, setActiveOrders] = useState<ActiveOrder[]>([]);

  // Keep track of edited item quantities in draft suggestion carts
  const [draftCartQuantities, setDraftCartQuantities] = useState<Record<string, number>>({});

  // --- TRIGGER ENGINE SIMULATION LOGIC ---
  const executeTriggers = () => {
    setIsRunningTriggers(true);
    setLangGraphLogs([]);
    setTriggeredSuggestions([]);

    const logs: string[] = [];
    const addLog = (msg: string) => logs.push(`[${new Date().toLocaleTimeString()}] ${msg}`);

    // Simulate LangGraph thread orchestration
    setTimeout(() => {
      addLog("Initializing LangGraph thread for thread_id: sandbox_user_01");
      addLog("Loading state variables: current_time, location, weather");
      
      // Node 1: Event-based trigger check
      addLog("Running node: analyze_patterns_node");
      
      let eventSuggestion: any = null;
      const isFriday = selectedDay === "Friday";
      const isRainy = selectedWeather === "rainy";
      const patternKey = "food_event_Friday_18-21";
      const eventDismissedCount = dismissedPatterns[patternKey] || 0;

      if (isFriday && isRainy) {
        if (eventDismissedCount >= 3) {
          addLog(`⚠️ Event trigger suppressed: '${patternKey}' has been dismissed ${eventDismissedCount} times (Trust Guardrail enabled)`);
        } else {
          addLog("✅ Event Pattern Match! Friday evening ordering pattern detected with 75% historical rainy weather matching (>= 60% requirement).");
          eventSuggestion = {
            id: "sug_event_01",
            trigger_type: "event_based",
            order_type: "food",
            restaurant_id: "rest_001",
            restaurant_name: restaurantDistance > 5 ? "Empire Restaurant" : "Meghana Foods",
            explanation: `Based on your past orders on Fridays around 19:30 and today's rainy weather, we drafted your favorite meal.`,
            items: [
              { id: "m1", name: "Special Chicken Biryani", price: 320, defaultQty: 1 }
            ],
            pattern_key: patternKey,
            distance: restaurantDistance
          };
        }
      } else {
        addLog(`❌ No Event-Based trigger matches today (Context: Day: ${selectedDay}, Weather: ${selectedWeather})`);
      }

      // Node 2: Consumption-based staple check
      addLog("Running node: process_consumption_node");
      const consumptionSuggestions: any[] = [];

      stapleConfigs.forEach((staple) => {
        if (staple.is_confirmed) {
          const stapleDismissedCount = staple.dismissed_count;
          if (stapleDismissedCount >= 3) {
            addLog(`⚠️ Staple '${staple.product_name}' replenishment alerts blocked (3 Dismissals reached).`);
            return;
          }

          // Prediction logic: Last order was July 2. Cycle length is 4 days. Next is July 6.
          // Since today is Saturday July 4, we are 2 days before predicted Run Out!
          // Trigger if day corresponds to predictedRunOut - 2 days (i.e. Saturday July 4 or onwards)
          const todayIndexOffset = ["Friday", "Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"].indexOf(selectedDay);
          // Milk last order: July 2 (Thursday).
          // Friday July 3: 1 day since last order.
          // Saturday July 4: 2 days since last order (Triggered since next predicted is July 6, buffer is 2 days!)
          const daysSinceLastOrder = todayIndexOffset + 1; // Thursday to Friday is 1, Saturday is 2
          const nextPredictedDays = staple.cycle_length; // 4.0

          if (daysSinceLastOrder >= (nextPredictedDays - 2)) {
            addLog(`✅ Staple Alert: '${staple.product_name}' is due soon (Replenished every ${staple.cycle_length} days. Last ordered 2 days ago). Drafting replenishment.`);
            consumptionSuggestions.push({
              id: `sug_staple_${staple.product_id}`,
              trigger_type: "consumption_based",
              order_type: "instamart",
              explanation: `Looks like you are running low on ${staple.product_name}. Based on your last 5 order gaps, you consume this every ${staple.cycle_length} days.`,
              items: [
                { id: staple.product_id, name: staple.product_name, price: staple.price, defaultQty: 2 }
              ],
              pattern_key: staple.product_id
            });
          } else {
            addLog(`ℹ️ Staple '${staple.product_name}' not yet due (Replenishment in ${Math.ceil(nextPredictedDays - daysSinceLastOrder)} days).`);
          }
        }
      });

      // Node 3: Merge node
      addLog("Running node: merge_proactive_signals_node");
      const finalSuggestions: any[] = [];
      if (eventSuggestion && consumptionSuggestions.length > 0) {
        addLog("🔀 MERGE TRIGGER: Both Event & Staple replenishment fired on the same day. Merging into a Unified Daily Digest card to prevent notification fatigue.");
        
        // Form a merged card structure
        finalSuggestions.push({
          id: "merged_digest",
          trigger_type: "merged",
          order_type: "mixed",
          restaurant_name: eventSuggestion.restaurant_name,
          explanation: "Here is your unified Daily Proactive Digest! We bundled your Friday evening biryani draft and Instamart milk replenishment into a single layout to keep you focused.",
          sub_suggestions: [eventSuggestion, ...consumptionSuggestions],
          pattern_key: "merged_daily_digest"
        });
      } else {
        if (eventSuggestion) finalSuggestions.push(eventSuggestion);
        consumptionSuggestions.forEach(s => finalSuggestions.push(s));
      }

      addLog("Graph execution completed successfully.");
      setLangGraphLogs(logs);
      setTriggeredSuggestions(finalSuggestions);
      setIsRunningTriggers(false);
    }, 1000);
  };

  // Run initial trigger check
  useEffect(() => {
    executeTriggers();
  }, [selectedDay, selectedWeather, restaurantDistance]);

  // --- LIVE ORDER TRACKING TICKER ---
  // Swiggy dispatches orders automatically. We poll the tracker every 10 seconds.
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveOrders((prevOrders) => {
        return prevOrders.map((order) => {
          if (order.status === "DELIVERED") return order;

          let nextStatus = order.status;
          let nextEta = Math.max(0, order.eta_minutes - 5);

          if (order.status === "ORDERED") {
            nextStatus = order.type === "food" ? "PREPARING" : "PACKING";
          } else if (order.status === "PREPARING" || order.status === "PACKING") {
            nextStatus = "DISPATCHED";
          } else if (order.status === "DISPATCHED") {
            nextStatus = "RIDER_NEARBY";
          } else if (order.status === "RIDER_NEARBY" && nextEta === 0) {
            nextStatus = "DELIVERED";
          }

          return {
            ...order,
            status: nextStatus,
            eta_minutes: nextEta
          };
        });
      });
    }, 10000); // Polled every 10 seconds

    return () => clearInterval(timer);
  }, []);

  // --- ACTIONS ---
  const handleConfirmOrder = (suggestion: any, ordType: "food" | "instamart", restId?: string, restName?: string) => {
    const itemsToPlace = suggestion.items.map((it: any) => {
      const currentQty = draftCartQuantities[`${suggestion.id}_${it.id}`] ?? it.defaultQty;
      return {
        name: it.name,
        price: it.price,
        quantity: currentQty
      };
    });

    const totalAmount = itemsToPlace.reduce((sum: number, it: any) => sum + (it.price * it.quantity), 0);

    // Builders Club Cap Check (Strict Limit ₹1000)
    if (totalAmount > 1000) {
      alert(`❌ Order Blocked: Under Swiggy Builders Club Sandbox mandates, test carts are strictly capped at ₹1000. Your cart total is ₹${totalAmount}. Please reduce quantities.`);
      return;
    }

    const orderId = ordType === "food" ? `SWG-FOOD-${Math.floor(100000 + Math.random() * 900000)}` : `SWG-IM-${Math.floor(100000 + Math.random() * 900000)}`;
    const newOrder: ActiveOrder = {
      order_id: orderId,
      type: ordType,
      origin_name: ordType === "food" ? (restName ?? "Meghana Foods") : "Instamart Staples",
      items: itemsToPlace,
      total_amount: totalAmount,
      eta_minutes: ordType === "food" ? 35 : 20,
      status: "ORDERED"
    };

    setActiveOrders((prev) => [newOrder, ...prev]);
    setActiveTab("tracker");
    alert(`🎉 Order Placed Successfully via COD (Cash on Delivery)!\nOrder ID: ${orderId}\nSwiggy live dispatch tracking is now active inside the Order Tracker tab.`);
  };

  const handleDismissPattern = (patternKey: string, isStaple: boolean) => {
    if (isStaple) {
      setStapleConfigs((prev) => 
        prev.map((sc) => {
          if (sc.product_id === patternKey) {
            const nextCount = sc.dismissed_count + 1;
            return { ...sc, dismissed_count: nextCount };
          }
          return sc;
        })
      );
      alert(`Pattern dismissed. If an item is dismissed 3 times, the agent stops drafting it. This helps build safety & trust.`);
    } else {
      setDismissedPatterns((prev) => {
        const nextCount = (prev[patternKey] || 0) + 1;
        return { ...prev, [patternKey]: nextCount };
      });
      alert(`Friday Biryani pattern dismissed. Dismiss count: ${(dismissedPatterns[patternKey] || 0) + 1}/3.`);
    }
    executeTriggers();
  };

  const toggleStapleOptIn = (prodId: string) => {
    setStapleConfigs((prev) =>
      prev.map((sc) => {
        if (sc.product_id === prodId) {
          const nextState = !sc.is_confirmed;
          if (nextState) {
            alert(`🥛 Opt-In Confirmed: Replenishment monitoring activated for ${sc.product_name}. The agent will calculate order gaps and proactively draft orders.`);
          } else {
            alert(`Disabled replenishment tracking for ${sc.product_name}.`);
          }
          return { ...sc, is_confirmed: nextState };
        }
        return sc;
      })
    );
  };

  const updateDraftItemQty = (sugId: string, itemId: string, diff: number, defaultVal: number) => {
    const key = `${sugId}_${itemId}`;
    const currentVal = draftCartQuantities[key] ?? defaultVal;
    const nextVal = Math.max(1, Math.min(10, currentVal + diff));
    setDraftCartQuantities((prev) => ({ ...prev, [key]: nextVal }));
  };

  return (
    <div className="min-h-screen bg-[#FFFDFB] text-[#3E3E3E] font-sans antialiased flex flex-col">
      {/* HEADER BAR */}
      <header className="bg-white border-b border-orange-100 py-4 px-6 sticky top-0 z-50 shadow-xs">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-[#fc8019] text-white p-2.5 rounded-2xl shadow-sm shadow-orange-200">
              <Flame className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <h1 className="font-display font-bold text-xl text-[#1E1E1E] tracking-tight">
                Swiggy Builders Club Proactive Ordering Agent
              </h1>
              <p className="text-xs text-[#fc8019] font-medium tracking-wide uppercase">
                Mocked MCP Developer Program Sandbox Demo
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
              MCP SANDBOX LIVE
            </span>
            <span className="text-xs font-mono bg-orange-50 text-orange-700 px-3 py-1 rounded-md border border-orange-100">
              COD Mode (₹1000 Cap)
            </span>
          </div>
        </div>
      </header>

      {/* DASHBOARD CONTENT CONTAINER */}
      <main className="flex-1 max-w-7xl w-full mx-auto py-6 px-4 sm:px-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: SIMULATION CONTROL PANEL (4 Cols) */}
        <section className="lg:col-span-4 flex flex-col gap-6">
          
          {/* SIMULATOR CARD */}
          <div className="bg-white rounded-3xl border border-orange-50 p-6 shadow-sm shadow-orange-50/50">
            <div className="flex items-center gap-2 mb-4">
              <Sliders className="w-5 h-5 text-[#fc8019]" />
              <h2 className="font-display font-semibold text-lg text-[#1E1E1E]">
                Simulation Control Panel
              </h2>
            </div>
            <p className="text-xs text-[#7E7E7E] mb-5">
              Tweak temporal and weather presets to trigger our agentic models.
            </p>

            <div className="flex flex-col gap-4">
              {/* Day selector */}
              <div>
                <label className="block text-xs font-semibold text-[#1E1E1E] uppercase tracking-wider mb-2">
                  Simulated Day &amp; Window
                </label>
                <select 
                  className="w-full bg-[#FFFDFB] border border-orange-100 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none focus:border-[#fc8019] text-[#1E1E1E]"
                  value={selectedDay}
                  onChange={(e) => setSelectedDay(e.target.value)}
                >
                  <option value="Friday">Friday Evening (Biryani pattern matches)</option>
                  <option value="Saturday">Saturday Afternoon</option>
                  <option value="Sunday">Sunday Lunch</option>
                  <option value="Monday">Monday Morning (Milk cycle due)</option>
                  <option value="Tuesday">Tuesday Lunch</option>
                  <option value="Wednesday">Wednesday Morning</option>
                  <option value="Thursday">Thursday Dinner</option>
                </select>
              </div>

              {/* Weather selector */}
              <div>
                <label className="block text-xs font-semibold text-[#1E1E1E] uppercase tracking-wider mb-2">
                  Simulated Weather
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {(["rainy", "pleasant", "hot", "cold"] as const).map((w) => (
                    <button
                      key={w}
                      type="button"
                      onClick={() => setSelectedWeather(w)}
                      className={`py-2 px-3 text-xs font-semibold rounded-xl border transition-all flex items-center justify-center gap-1.5 ${
                        selectedWeather === w
                          ? "bg-[#fc8019]/10 text-[#fc8019] border-[#fc8019]"
                          : "bg-[#FFFDFB] text-[#5E5E5E] border-orange-50 hover:bg-orange-50/30"
                      }`}
                    >
                      {w === "rainy" && <CloudRain className="w-3.5 h-3.5" />}
                      {w.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              {/* Distance Slider (Swiggy Guardrail Warning) */}
              <div>
                <label className="block text-xs font-semibold text-[#1E1E1E] uppercase tracking-wider mb-2 flex justify-between">
                  <span>Restaurant Distance</span>
                  <span className="font-mono text-[#fc8019]">{restaurantDistance} km</span>
                </label>
                <input 
                  type="range" 
                  min="1.0" 
                  max="8.0" 
                  step="0.1" 
                  value={restaurantDistance}
                  onChange={(e) => setRestaurantDistance(parseFloat(e.target.value))}
                  className="w-full accent-[#fc8019]"
                />
                <span className="text-[10px] text-gray-400 mt-1 block">
                  🍔 Swiggy safety guidelines mandate warning the user for food orders &gt;5km.
                </span>
              </div>
            </div>

            <div className="mt-6 pt-5 border-t border-orange-50 flex items-center justify-between">
              <span className="text-xs text-gray-500 font-medium">Currently simulating:</span>
              <span className="text-xs font-bold text-[#1E1E1E] bg-orange-50 px-2 py-1 rounded-md">
                {selectedDay}s @ 19:30
              </span>
            </div>
          </div>

          {/* SANDBOX CONSTRAINTS CHEATSHEET */}
          <div className="bg-[#1E1E1E] text-white rounded-3xl p-6 shadow-md">
            <h3 className="font-display font-semibold text-sm tracking-wide uppercase text-orange-400 mb-3 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4" />
              Builders Club API Mandates
            </h3>
            <ul className="text-xs space-y-3.5 text-gray-300">
              <li className="flex gap-2">
                <span className="text-orange-400 font-bold">1.</span>
                <span><strong>No Auto-placement:</strong> The agent never forces orders. Suggestions are staged strictly as inactive drafts.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-orange-400 font-bold">2.</span>
                <span><strong>Single Restaurant:</strong> Cart update flushes automatically if you cross-order from multi-restaurants.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-orange-400 font-bold">3.</span>
                <span><strong>COD Limit:</strong> Program checkout capped at ₹1000 with Cash on Delivery enforced.</span>
              </li>
              <li className="flex gap-2">
                <span className="text-orange-400 font-bold">4.</span>
                <span><strong>Live Poll Ticker:</strong> Custom dispatch post-order trackers poll every 10s to dynamically compute active ETAs.</span>
              </li>
            </ul>
          </div>
        </section>

        {/* RIGHT COLUMN: TABS AND INTERACTIVE WORKSPACE (8 Cols) */}
        <section className="lg:col-span-8 flex flex-col gap-6">
          
          {/* TABS SELECTOR */}
          <div className="bg-white p-1.5 rounded-2xl border border-orange-50 flex flex-wrap gap-1 shadow-xs">
            {[
              { id: "suggestions", label: "🎯 Proactive Suggestions", icon: ShoppingBag },
              { id: "staples", label: "🥛 Instamart Staples", icon: TrendingUp },
              { id: "tracker", label: "🛵 Order Tracker", icon: Clock },
              { id: "database", label: "📜 SQLite DB", icon: Database }
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex-1 py-2.5 px-4 rounded-xl text-xs font-semibold transition-all flex items-center justify-center gap-2 ${
                    activeTab === tab.id
                      ? "bg-[#fc8019] text-white shadow-xs"
                      : "text-gray-500 hover:bg-orange-50/20"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* TAB CONTENTS */}
          <div className="bg-white rounded-3xl border border-orange-50 p-6 min-h-[460px] shadow-sm flex flex-col justify-between">
            
            <div>
              {/* --- TABS: SUGGESTIONS --- */}
              {activeTab === "suggestions" && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between border-b border-orange-50 pb-4">
                    <div>
                      <h3 className="font-display font-semibold text-lg text-[#1E1E1E]">
                        Proactive Draft Recommendations
                      </h3>
                      <p className="text-xs text-gray-500">
                        Evaluated dynamically using internal LangGraph models.
                      </p>
                    </div>
                    {isRunningTriggers ? (
                      <span className="text-xs font-semibold text-[#fc8019] flex items-center gap-1.5 animate-pulse bg-orange-50 px-3 py-1.5 rounded-full">
                        <span className="w-2 h-2 rounded-full bg-[#fc8019] animate-ping"></span>
                        LangGraph checking...
                      </span>
                    ) : (
                      <button 
                        onClick={executeTriggers}
                        className="text-xs font-semibold text-white bg-[#fc8019] px-3.5 py-1.5 rounded-xl hover:bg-[#e06f15] transition-all"
                      >
                        Force Run Triggers
                      </button>
                    )}
                  </div>

                  {triggeredSuggestions.length === 0 ? (
                    <div className="text-center py-16 space-y-3">
                      <div className="w-12 h-12 rounded-full bg-orange-50 text-[#fc8019] flex items-center justify-center mx-auto">
                        <CheckCircle className="w-6 h-6" />
                      </div>
                      <h4 className="font-semibold text-gray-700">No Triggers Activated</h4>
                      <p className="text-xs text-gray-500 max-w-sm mx-auto">
                        Current simulated window (<strong>{selectedDay}</strong> with <strong>{selectedWeather}</strong> weather) does not establish sufficient past patterns or a staple replenishment run-out. Tweak controls on the left to fire predictions!
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {triggeredSuggestions.map((sug) => {
                        const isMerged = sug.trigger_type === "merged";
                        const subSuggestions = isMerged ? sug.sub_suggestions : [sug];

                        return (
                          <div key={sug.id} className="border border-orange-100/70 rounded-2xl bg-[#FFFDFB] overflow-hidden shadow-xs animate-fade-in">
                            {/* Card Main Header */}
                            <div className="bg-orange-50/40 px-5 py-4 border-b border-orange-100 flex items-center justify-between">
                              <span className="text-xs font-bold uppercase tracking-wider text-[#fc8019] bg-[#fc8019]/10 px-2.5 py-1 rounded-full flex items-center gap-1">
                                <Flame className="w-3.5 h-3.5" />
                                {isMerged ? "Daily Proactive Digest (Merged)" : `${sug.trigger_type.replace("_", " ")} trigger`}
                              </span>
                              <span className="text-xs font-semibold text-gray-500">
                                Simulated COD
                              </span>
                            </div>

                            <div className="p-5 space-y-5">
                              <p className="text-sm font-medium text-gray-800 leading-relaxed bg-white border border-orange-50/50 p-3 rounded-xl">
                                {sug.explanation}
                              </p>

                              {/* Map sub suggestions */}
                              {subSuggestions.map((subSug: any, sIdx: number) => {
                                const isFood = subSug.order_type === "food";
                                const isEmpire = subSug.restaurant_name === "Empire Restaurant";
                                
                                return (
                                  <div key={sIdx} className="space-y-3.5 pt-3 border-t border-orange-100/50 first:border-0 first:pt-0">
                                    <div className="flex items-center justify-between">
                                      <span className="text-xs font-bold text-gray-900">
                                        {isFood ? `🍽️ Food Draft: ${subSug.restaurant_name}` : "🥛 Instamart Grocery Staple Draft"}
                                      </span>
                                      <span className="text-xs font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded-sm">
                                        {isFood ? "Food Cart Rules" : "Grocery Cart Rules"}
                                      </span>
                                    </div>

                                    {/* Distance safety guardrail */}
                                    {isFood && isEmpire && (
                                      <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-xl p-3 flex gap-2 text-xs">
                                        <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                                        <div>
                                          <strong>Swiggy Distance Guardrail:</strong> This restaurant is {subSug.distance}km away (&gt;5km). Extended delivery times (40-50 min) and distance fees apply.
                                        </div>
                                      </div>
                                    )}

                                    {/* Item table with quantity modifiers */}
                                    <div className="space-y-2">
                                      {subSug.items.map((it: any) => {
                                        const curQty = draftCartQuantities[`${sug.id}_${it.id}`] ?? it.defaultQty;
                                        return (
                                          <div key={it.id} className="flex items-center justify-between bg-white px-3.5 py-2.5 rounded-xl border border-gray-100">
                                            <div>
                                              <p className="text-xs font-semibold text-gray-800">{it.name}</p>
                                              <p className="text-[10px] font-medium text-gray-400">Unit Price: ₹{it.price}</p>
                                            </div>
                                            <div className="flex items-center gap-3">
                                              <div className="flex items-center border border-orange-100 rounded-lg overflow-hidden bg-white">
                                                <button 
                                                  onClick={() => updateDraftItemQty(sug.id, it.id, -1, it.defaultQty)}
                                                  className="px-2 py-1 text-xs hover:bg-orange-50 text-gray-500 font-bold"
                                                >
                                                  -
                                                </button>
                                                <span className="px-3 py-1 text-xs font-bold font-mono text-gray-800">
                                                  {curQty}
                                                </span>
                                                <button 
                                                  onClick={() => updateDraftItemQty(sug.id, it.id, 1, it.defaultQty)}
                                                  className="px-2 py-1 text-xs hover:bg-orange-50 text-gray-500 font-bold"
                                                >
                                                  +
                                                </button>
                                              </div>
                                              <span className="text-xs font-bold text-gray-800 font-mono min-w-[50px] text-right">
                                                ₹{it.price * curQty}
                                              </span>
                                            </div>
                                          </div>
                                        );
                                      })}
                                    </div>

                                    {/* Suggestions Actions */}
                                    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 bg-white p-3 rounded-xl border border-orange-100/20">
                                      <div className="text-xs">
                                        <span className="text-gray-500 font-medium">Cart Total: </span>
                                        <span className="font-bold text-[#fc8019] font-mono text-sm">
                                          ₹{subSug.items.reduce((sum: number, it: any) => sum + (it.price * (draftCartQuantities[`${sug.id}_${it.id}`] ?? it.defaultQty)), 0)}
                                        </span>
                                      </div>
                                      <div className="flex items-center gap-2 w-full sm:w-auto">
                                        <button
                                          onClick={() => handleDismissPattern(subSug.pattern_key, subSug.trigger_type === "consumption_based")}
                                          className="flex-1 sm:flex-initial py-1.5 px-3.5 rounded-xl border border-orange-100 text-[#fc8019] text-xs font-semibold hover:bg-orange-50/20 transition-all text-center"
                                        >
                                          Dismiss Pattern
                                        </button>
                                        <button
                                          onClick={() => handleConfirmOrder(subSug, subSug.order_type, subSug.restaurant_id, subSug.restaurant_name)}
                                          className="flex-1 sm:flex-initial py-1.5 px-4 rounded-xl bg-[#fc8019] text-white text-xs font-semibold hover:bg-[#e06f15] transition-all text-center shadow-sm"
                                        >
                                          Confirm &amp; Checkout (COD)
                                        </button>
                                      </div>
                                    </div>

                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Dynamic Reasoning Node Logger for user visibility */}
                  <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 mt-6">
                    <h4 className="text-xs font-bold text-slate-700 font-mono tracking-wider uppercase mb-2 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-ping"></span>
                      LangGraph Engine Execution Logs
                    </h4>
                    <div className="font-mono text-[10px] text-slate-600 space-y-1 bg-white p-3 rounded-xl border border-slate-100 max-h-[140px] overflow-y-auto">
                      {langGraphLogs.map((log, lIdx) => (
                        <div key={lIdx} className="border-l border-slate-200 pl-2 leading-relaxed">
                          {log}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* --- TABS: STAPLES --- */}
              {activeTab === "staples" && (
                <div className="space-y-6">
                  <div>
                    <h3 className="font-display font-semibold text-lg text-[#1E1E1E] mb-1">
                      Instamart Grocery Staples Optimizer
                    </h3>
                    <p className="text-xs text-gray-500 mb-5">
                      Under Swiggy Builders Club constraints, we strictly prevent unsolicited tracking. Confirmed staples are evaluated on rolling 5-order intervals.
                    </p>
                  </div>

                  <div className="space-y-4">
                    {stapleConfigs.map((staple) => (
                      <div key={staple.product_id} className="border border-orange-50 bg-[#FFFDFB] rounded-2xl p-5 space-y-4 shadow-2xs">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-bold text-[#1E1E1E]">{staple.product_name}</span>
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                staple.is_confirmed 
                                  ? "bg-emerald-50 text-emerald-700" 
                                  : "bg-amber-50 text-amber-700"
                              }`}>
                                {staple.is_confirmed ? "ACTIVE ALERT MONITORING" : "CANDIDATE STAPLE (PENDING OPT-IN)"}
                              </span>
                            </div>
                            <p className="text-xs text-gray-500 mt-1">
                              History details: Purchased {staple.dates.length} times in SQLite.
                            </p>
                          </div>
                          
                          {/* Opt In Slider Toggle */}
                          <div className="flex items-center gap-3 self-end sm:self-auto">
                            <span className="text-xs font-semibold text-gray-600">Alerts:</span>
                            <button
                              type="button"
                              onClick={() => toggleStapleOptIn(staple.product_id)}
                              className={`w-12 h-6 rounded-full p-1 transition-all ${
                                staple.is_confirmed ? "bg-[#fc8019]" : "bg-gray-200"
                              }`}
                            >
                              <div className={`w-4 h-4 rounded-full bg-white shadow-xs transition-all transform ${
                                staple.is_confirmed ? "translate-x-6" : "translate-x-0"
                              }`}></div>
                            </button>
                          </div>
                        </div>

                        {/* Gap analysis visualization */}
                        <div className="bg-white p-4 rounded-xl border border-orange-50 grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                          <div>
                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Purchase History</p>
                            <p className="text-xs font-bold text-gray-700 mt-1 font-mono">{staple.dates.length} orders</p>
                          </div>
                          <div>
                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Rolling Gap (Avg)</p>
                            <p className="text-xs font-bold text-emerald-600 mt-1 font-mono">{staple.cycle_length} Days</p>
                          </div>
                          <div>
                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Last Order Date</p>
                            <p className="text-xs font-bold text-gray-700 mt-1 font-mono">July 02, 2206</p>
                          </div>
                          <div>
                            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Replenishment predicted</p>
                            <p className="text-xs font-bold text-[#fc8019] mt-1 font-mono">July 06, 2206</p>
                          </div>
                        </div>

                        {/* Hybrid Ask Display */}
                        {!staple.is_confirmed && (
                          <div className="bg-[#FFF9F3] border border-orange-100 rounded-xl p-3.5 text-xs text-orange-900 flex flex-col sm:flex-row items-center justify-between gap-3">
                            <div className="flex gap-2 items-start">
                              <HelpCircle className="w-4 h-4 text-[#fc8019] shrink-0 mt-0.5" />
                              <p>
                                <strong>Staple Replenishment Offer:</strong> "Looks like you purchase {staple.product_name} every {staple.cycle_length} days. Want the Proactive Agent to auto-draft a draft cart 2 days before you run out?"
                              </p>
                            </div>
                            <button 
                              onClick={() => toggleStapleOptIn(staple.product_id)}
                              className="text-xs font-bold bg-[#fc8019] text-white px-3 py-1.5 rounded-lg hover:bg-[#e06f15] transition-all shrink-0 w-full sm:w-auto text-center"
                            >
                              Yes, track this
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* --- TABS: TRACKER --- */}
              {activeTab === "tracker" && (
                <div className="space-y-6">
                  <div>
                    <h3 className="font-display font-semibold text-lg text-[#1E1E1E] mb-1">
                      🛵 Post-Order Dispatch &amp; Live Tracking
                    </h3>
                    <p className="text-xs text-gray-500 mb-5">
                      Swiggy automatically assigns drivers. Live ETAs are polled every 10 seconds.
                    </p>
                  </div>

                  {activeOrders.length === 0 ? (
                    <div className="text-center py-16 space-y-3">
                      <div className="w-12 h-12 rounded-full bg-orange-50 text-[#fc8019] flex items-center justify-center mx-auto">
                        <Clock className="w-6 h-6 animate-pulse" />
                      </div>
                      <h4 className="font-semibold text-gray-700">No Active Orders Being Tracked</h4>
                      <p className="text-xs text-gray-500 max-w-sm mx-auto">
                        To activate live tracking, confirm and checkout any proactive recommendation card from the Suggestions tab first!
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {activeOrders.map((order) => (
                        <div key={order.order_id} className="border border-orange-50 bg-[#FFFDFB] rounded-2xl p-5 space-y-5 shadow-2xs">
                          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-orange-50">
                            <div>
                              <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">ORDER ID: {order.order_id}</p>
                              <p className="text-sm font-bold text-gray-900 mt-0.5">Origin: {order.origin_name}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-xs font-bold text-[#fc8019] bg-orange-50 px-3 py-1 rounded-full inline-block">
                                {order.status}
                              </p>
                            </div>
                          </div>

                          {/* Live ETA tracker bar */}
                          <div className="space-y-2">
                            <div className="flex justify-between text-xs font-bold text-gray-700">
                              <span>Simulated Polled ETA</span>
                              <span className="font-mono text-lg text-[#fc8019]">{order.eta_minutes} MINUTES</span>
                            </div>

                            {/* Simulated tracker bars */}
                            <div className="grid grid-cols-4 gap-1.5 h-2">
                              <div className={`rounded-full ${order.status !== "DELIVERED" ? "bg-[#fc8019]" : "bg-emerald-500"}`}></div>
                              <div className={`rounded-full ${
                                ["PREPARING", "PACKING", "DISPATCHED", "RIDER_NEARBY", "DELIVERED"].includes(order.status) 
                                  ? (order.status === "DELIVERED" ? "bg-emerald-500" : "bg-[#fc8019]") 
                                  : "bg-gray-200"
                              }`}></div>
                              <div className={`rounded-full ${
                                ["DISPATCHED", "RIDER_NEARBY", "DELIVERED"].includes(order.status) 
                                  ? (order.status === "DELIVERED" ? "bg-emerald-500" : "bg-[#fc8019]") 
                                  : "bg-gray-200"
                              }`}></div>
                              <div className={`rounded-full ${
                                ["RIDER_NEARBY", "DELIVERED"].includes(order.status) 
                                  ? (order.status === "DELIVERED" ? "bg-emerald-500" : "bg-[#fc8019]") 
                                  : "bg-gray-200"
                              }`}></div>
                            </div>
                          </div>

                          <div className="bg-white p-3 rounded-xl border border-gray-100 flex items-center justify-between text-xs">
                            <div className="text-gray-500 font-medium">
                              {order.items.length} items • <span className="font-mono">COD</span>
                            </div>
                            <div className="font-bold text-gray-800 font-mono">
                              Total: ₹{order.total_amount}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* --- TABS: DATABASE VIEWER --- */}
              {activeTab === "database" && (
                <div className="space-y-6">
                  <div>
                    <h3 className="font-display font-semibold text-lg text-[#1E1E1E] mb-1">
                      📜 SQLite Seeding Database (In-Memory Viewer)
                    </h3>
                    <p className="text-xs text-gray-500 mb-5">
                      This log represents the `order_history` table used by our dual LangGraph predictive models to trace temporal clusters.
                    </p>
                  </div>

                  <div className="overflow-x-auto rounded-2xl border border-orange-50 bg-[#FFFDFB]">
                    <table className="w-full border-collapse text-left text-xs">
                      <thead>
                        <tr className="bg-orange-50/50 text-gray-500 font-semibold border-b border-orange-50">
                          <th className="p-3">ID</th>
                          <th className="p-3">Type</th>
                          <th className="p-3">Restaurant/Store</th>
                          <th className="p-3">Item Name</th>
                          <th className="p-3">Price</th>
                          <th className="p-3 font-mono">Qty</th>
                          <th className="p-3">Simulated Order Date</th>
                          <th className="p-3">Weather</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-orange-50/30 text-gray-700">
                        {orderHistory.map((row) => (
                          <tr key={row.id} className="hover:bg-orange-50/10">
                            <td className="p-3 font-semibold text-gray-400">{row.id}</td>
                            <td className="p-3 uppercase tracking-wider text-[10px] font-bold">
                              {row.order_type}
                            </td>
                            <td className="p-3 font-medium text-gray-900">
                              {row.restaurant_name ?? "Swiggy Instamart"}
                            </td>
                            <td className="p-3">{row.item_name}</td>
                            <td className="p-3 font-mono">₹{row.price}</td>
                            <td className="p-3 font-mono">{row.quantity}</td>
                            <td className="p-3 text-gray-500">
                              {new Date(row.order_time).toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                            </td>
                            <td className="p-3">
                              <span className={`inline-block px-2 py-0.5 rounded-md text-[10px] font-bold ${
                                row.weather_condition === "rainy" 
                                  ? "bg-blue-50 text-blue-700 border border-blue-100" 
                                  : "bg-gray-100 text-gray-600"
                              }`}>
                                {row.weather_condition.toUpperCase()}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

            </div>

            {/* TAB FOOTER STATS */}
            <div className="mt-8 pt-4 border-t border-orange-50/60 flex flex-col sm:flex-row justify-between items-center gap-3 text-xs text-gray-400">
              <span className="font-mono">
                Thread: sandbox_user_01_session
              </span>
              <span className="font-mono flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 shrink-0" />
                Live Dispatch Polling Interval: 10 seconds
              </span>
            </div>

          </div>
        </section>

      </main>

      {/* FOOTER */}
      <footer className="bg-white border-t border-orange-100 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-6 text-center text-xs text-gray-400 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© 2026 Swiggy Builders Club Program. All rights reserved.</p>
          <div className="flex gap-4">
            <a href="#suggestions" onClick={() => setActiveTab("suggestions")} className="hover:text-[#fc8019] font-medium transition-colors">Triggers Dashboard</a>
            <span>•</span>
            <a href="#staples" onClick={() => setActiveTab("staples")} className="hover:text-[#fc8019] font-medium transition-colors">Staples Tracker</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
