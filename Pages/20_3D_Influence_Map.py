
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

st.set_page_config(page_title="3D Influence Map", page_icon="🧬", layout="wide")

# Password protection
auth_ok = any(bool(st.session_state.get(k, False)) for k in ("authenticated","logged_in","is_authenticated"))
if not auth_ok:
    st.warning("Please log in first (Simulation -> Login).")
    st.stop()

# =============================================================================
# PAGE HEADER
# =============================================================================

st.title("🧬 3D AlphaFold-Style Influence Map")

with st.expander("ℹ️ About this visualization — click to expand", expanded=False):
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 16px 20px; border-radius: 10px; margin-bottom: 14px;'>
        <h4 style='color: white; margin: 0 0 4px 0;'>External Policy Pressures & Internal Cultural Forces</h4>
        <p style='color: rgba(255,255,255,0.85); margin: 0; font-size: 13px;'>
            Interactive 3D Visualization of AI Governance Influences
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("""
Unlike traditional network visualizations that show static relationships, this **AlphaFold-style influence map**
reveals how **external policy pressures** (like GDPR, export controls) and **internal cultural forces**
(like democratic values, tech nationalism) shape countries' AI governance positions in 3D space.

**The 3D Space:**
- **X-axis**: Economic strength (GDP)
- **Y-axis**: Influence score (0-1)
- **Z-axis**: Policy position alignment

**Each node represents:**
- Countries (US, EU, China, UK, Japan, Dubai, etc.)
- Organizations (NATO)

**Visualization Elements:**
- 🔵 **Blue Arrows** = External policy pressures (GDPR, sanctions, export controls)
- 🟣 **Purple Spheres** = Internal cultural forces (democratic norms, tech nationalism)
- 📊 **Node Size** = Relative influence
- 🎨 **Node Color** = Alignment clusters

**Interactive Features:**
- Rotate: Click and drag
- Zoom: Scroll
- Animate: Watch policy convergence over time
    """)

# =============================================================================
# DATA DEFINITIONS (same as original)
# =============================================================================

default_data = {
    "European Union": {"gdp": 15.0, "influence": 0.90, "position": "Strict data protection (GDPR)", "mil_exp": 1.5, "internet": 89.0, "cultural_alignment": "Western"},
    "Dubai": {"gdp": 0.5, "influence": 0.7, "position": "Moderate regulatory stance", "mil_exp": 5.6, "internet": 99.0, "cultural_alignment": "Western-Middle East hybrid"},
    "United Kingdom": {"gdp": 3.2, "influence": 0.85, "position": "Supports EU-style data protection", "mil_exp": 2.2, "internet": 96.0, "cultural_alignment": "Western"},
    "United States": {"gdp": 21.0, "influence": 0.95, "position": "Favors innovation over regulation", "mil_exp": 3.4, "internet": 92.0, "cultural_alignment": "Western"},
    "Japan": {"gdp": 5.1, "influence": 0.88, "position": "Pro-regulation for trust", "mil_exp": 1.0, "internet": 95.0, "cultural_alignment": "Eastern-Western hybrid"},
    "China": {"gdp": 17.7, "influence": 0.93, "position": "Strict state-driven AI governance", "mil_exp": 1.7, "internet": 73.0, "cultural_alignment": "Eastern"},
    "Brazil": {"gdp": 2.0, "influence": 0.75, "position": "Leaning toward EU-style regulation", "mil_exp": 1.4, "internet": 81.0, "cultural_alignment": "Latin American"},
    "India": {"gdp": 3.7, "influence": 0.82, "position": "Strategic tech balancing", "mil_exp": 2.4, "internet": 43.0, "cultural_alignment": "South Asian"},
    "Russia": {"gdp": 1.8, "influence": 0.78, "position": "Sovereign tech control", "mil_exp": 4.3, "internet": 85.0, "cultural_alignment": "Eastern"},
    "Iraq": {"gdp": 0.2, "influence": 0.42, "position": "Developing governance framework", "mil_exp": 3.5, "internet": 49.0, "cultural_alignment": "Middle East"},
    "Qatar": {"gdp": 0.18, "influence": 0.68, "position": "Tech-forward with state oversight", "mil_exp": 3.7, "internet": 99.0, "cultural_alignment": "Middle East"},
    "NATO": {"gdp": 25.0, "influence": 0.97, "position": "Collective security & data interoperability", "mil_exp": 2.5, "internet": 90.0, "cultural_alignment": "Western Alliance"},
    "Greenland": {"gdp": 0.003, "influence": 0.45, "position": "Emerging Arctic tech governance", "mil_exp": 0.0, "internet": 68.0, "cultural_alignment": "Nordic"},
    "Venezuela": {"gdp": 0.048, "influence": 0.58, "position": "State-controlled digital infrastructure", "mil_exp": 0.9, "internet": 72.0, "cultural_alignment": "Latin American"},

    "Israel": {"gdp": 0.5, "influence": 0.75, "position": "Cyber & security-forward; high-tech economy", "mil_exp": 5.0, "internet": 88.0, "cultural_alignment": "Middle East / Western-linked"},
    "Paraguay": {"gdp": 0.04, "influence": 0.35, "position": "Developing market; regulatory capacity building", "mil_exp": 1.2, "internet": 65.0, "cultural_alignment": "Latin American"},
    "Belgium": {"gdp": 0.6, "influence": 0.60, "position": "EU/NATO hub; compliance-aligned", "mil_exp": 1.1, "internet": 92.0, "cultural_alignment": "Western (EU)"},
    "Denmark": {"gdp": 0.4, "influence": 0.55, "position": "High-trust governance; strong digital state", "mil_exp": 1.7, "internet": 98.0, "cultural_alignment": "Nordic/Western"},
    "Ukraine": {"gdp": 0.2, "influence": 0.65, "position": "Conflict resilience; reconstruction & security alignment", "mil_exp": 15.0, "internet": 76.0, "cultural_alignment": "Eastern Europe / Western-aligned"},
    "Serbia": {"gdp": 0.07, "influence": 0.40, "position": "Non-aligned balancing; regional interoperability", "mil_exp": 2.0, "internet": 80.0, "cultural_alignment": "Balkan / mixed"},
    "Argentina": {"gdp": 0.6, "influence": 0.50, "position": "Emerging market; institutional volatility risk", "mil_exp": 0.7, "internet": 88.0, "cultural_alignment": "Latin American"},
    "Norway": {"gdp": 0.5, "influence": 0.55, "position": "Energy wealth; NATO-aligned; high trust", "mil_exp": 1.6, "internet": 99.0, "cultural_alignment": "Nordic/Western"},
    "Switzerland": {"gdp": 0.8, "influence": 0.60, "position": "Neutral hub; high compliance; finance-centric", "mil_exp": 0.7, "internet": 97.0, "cultural_alignment": "Western (neutral)"},
    "Poland": {"gdp": 0.9, "influence": 0.60, "position": "NATO frontline; rapid defense modernization", "mil_exp": 3.5, "internet": 90.0, "cultural_alignment": "Eastern Europe / Western-aligned"},
    "Global South": {"gdp": 30.0, "influence": 0.80, "position": "Plural bloc; sovereignty & development-focused governance", "mil_exp": 2.0, "internet": 60.0, "cultural_alignment": "Multi-regional"}
}

EXTERNAL_INFLUENCES = {
    "GDPR": {"type": "regulation", "strength": 0.9, "targets": ["European Union", "United Kingdom", "Brazil"]},
    "US Export Controls": {"type": "policy", "strength": 0.85, "targets": ["China", "Russia", "Iraq"]},
    "Belt & Road Initiative": {"type": "economic", "strength": 0.75, "targets": ["Brazil", "Qatar", "Dubai"]},
    "AUKUS Agreement": {"type": "alliance", "strength": 0.8, "targets": ["United States", "United Kingdom", "Japan"]},
    "UN AI Ethics": {"type": "norm", "strength": 0.6, "targets": ["India", "Brazil", "NATO"]}
}

INTERNAL_INFLUENCES = {
    "Democratic Norms": {"strength": 0.85, "countries": ["United States", "European Union", "United Kingdom", "Japan", "India", "Brazil"]},
    "Tech Nationalism": {"strength": 0.9, "countries": ["China", "Russia", "United States"]},
    "Post-Colonial Sovereignty": {"strength": 0.7, "countries": ["India", "Brazil", "Iraq", "Qatar"]},
    "Energy Wealth": {"strength": 0.75, "countries": ["Russia", "Qatar", "Dubai", "Venezuela"]},
    "Military-Tech Integration": {"strength": 0.8, "countries": ["United States", "China", "Russia", "NATO"]}
}

# =============================================================================
# EMBED THE 3D ANIMATED VISUALIZATION
# =============================================================================

html_code = """

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0e27;
            color: #e0e7ff;
            overflow: hidden;
        }
        /* ── MAXIMIZE / RESTORE BUTTON ── */
        #maxBtn {
            position: fixed;
            top: 10px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 9999;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 20px;
            padding: 6px 18px;
            font-size: 0.8rem;
            font-weight: 700;
            cursor: pointer;
            letter-spacing: 0.04em;
            box-shadow: 0 2px 10px rgba(102,126,234,0.5);
            transition: all 0.2s;
        }
        #maxBtn:hover { box-shadow: 0 4px 16px rgba(102,126,234,0.7); transform: translateX(-50%) translateY(-1px); }
        /* MAXIMIZED state – full viewport */
        body.maximized { overflow: hidden; }
        body.maximized #wrapper {
            position: fixed !important;
            inset: 0 !important;
            z-index: 9998;
            width: 100vw !important;
            height: 100vh !important;
        }
        /* ── LAYOUT ── */
        #wrapper {
            display: flex;
            width: 100%;
            height: 800px;
            background: #0a0e27;
            transition: all 0.35s cubic-bezier(0.4,0,0.2,1);
        }
        /* LEFT SIDEBAR */
        #sidebar {
            width: 280px;
            min-width: 280px;
            background: rgba(26,31,58,0.95);
            border-right: 1px solid rgba(102,126,234,0.2);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            transition: width 0.3s, min-width 0.3s;
        }
        #sidebar.collapsed { width: 0; min-width: 0; overflow: hidden; }
        #sidebarToggle {
            position: absolute;
            left: 270px;
            top: 50%;
            transform: translateY(-50%);
            z-index: 100;
            background: rgba(102,126,234,0.7);
            border: none;
            color: white;
            width: 18px;
            height: 40px;
            border-radius: 0 6px 6px 0;
            cursor: pointer;
            font-size: 0.65rem;
            transition: left 0.3s;
        }
        #sidebar.collapsed ~ #sidebarToggle { left: 0; }
        .sidebar-section {
            padding: 1rem;
            border-bottom: 1px solid rgba(102,126,234,0.1);
        }
        .sidebar-section h3 {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #818cf8;
            margin-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .ctrl-group { margin-bottom: 0.8rem; }
        .ctrl-group label {
            display: flex;
            justify-content: space-between;
            font-size: 0.78rem;
            margin-bottom: 0.4rem;
            color: #c7d2fe;
        }
        .val { color: #818cf8; font-weight: 600; }
        input[type=range] {
            width: 100%;
            height: 5px;
            border-radius: 3px;
            background: linear-gradient(90deg, #4c1d95 0%, #818cf8 100%);
            outline: none;
            -webkit-appearance: none;
        }
        input[type=range]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 14px; height: 14px;
            border-radius: 50%;
            background: #818cf8;
            cursor: pointer;
            box-shadow: 0 0 8px rgba(129,140,248,0.5);
        }
        .btn {
            width: 100%;
            padding: 0.6rem;
            margin-bottom: 0.4rem;
            border: none;
            border-radius: 7px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            font-size: 0.82rem;
            cursor: pointer;
            transition: transform 0.15s, box-shadow 0.15s;
        }
        .btn:hover { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(102,126,234,0.4); }
        .btn.sec {
            background: rgba(129,140,248,0.15);
            border: 1px solid #818cf8;
        }
        .toggle-btn {
            width: 100%;
            padding: 0.5rem;
            margin-bottom: 0.3rem;
            border: 1px solid rgba(129,140,248,0.3);
            border-radius: 5px;
            background: rgba(129,140,248,0.08);
            color: #c7d2fe;
            font-size: 0.78rem;
            cursor: pointer;
            transition: all 0.15s;
        }
        .toggle-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: transparent;
        }
        /* ── COUNTRY FOCUS SELECT ── */
        #focusSelect {
            width: 100%;
            background: rgba(26,31,58,0.9);
            border: 1px solid rgba(129,140,248,0.3);
            color: #c7d2fe;
            padding: 0.5rem;
            border-radius: 6px;
            font-size: 0.8rem;
            margin-bottom: 0.5rem;
        }
        #focusSelect option { background: #1a1f3a; }
        /* ── FOCUS DETAIL CARD ── */
        #focusCard {
            background: rgba(102,126,234,0.08);
            border: 1px solid rgba(102,126,234,0.2);
            border-radius: 8px;
            padding: 0.75rem;
            font-size: 0.75rem;
            line-height: 1.6;
            display: none;
        }
        #focusCard.visible { display: block; }
        #focusCard .fc-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: #818cf8;
            margin-bottom: 0.5rem;
        }
        #focusCard .fc-row { display: flex; justify-content: space-between; padding: 2px 0; }
        #focusCard .fc-key { color: #94a3b8; }
        #focusCard .fc-val { color: #e0e7ff; font-weight: 600; }
        #focusCard .fc-pills { margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 4px; }
        #focusCard .pill {
            padding: 2px 8px;
            border-radius: 20px;
            font-size: 0.68rem;
            font-weight: 600;
        }
        .pill-ext { background: rgba(102,126,234,0.25); color: #818cf8; border: 1px solid #667eea; }
        .pill-int { background: rgba(168,85,247,0.2); color: #c084fc; border: 1px solid #a855f7; }
        .pill-hot { background: rgba(249,115,22,0.25); color: #fb923c; border: 1px solid #f97316; animation: pulse 1.2s infinite; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
        /* ── LIVE OVERLAY PANEL ── */
        #livePanel {
            background: rgba(26,31,58,0.9);
            border: 1px solid rgba(249,115,22,0.4);
            border-radius: 8px;
            padding: 0.75rem;
            font-size: 0.75rem;
        }
        .live-badge {
            display: inline-block;
            background: #f97316;
            color: white;
            font-size: 0.6rem;
            font-weight: 700;
            padding: 1px 6px;
            border-radius: 20px;
            letter-spacing: 0.05em;
            animation: pulse 1.5s infinite;
        }
        .live-metric { display: flex; justify-content: space-between; padding: 3px 0; }
        .live-key { color: #94a3b8; font-size: 0.72rem; }
        .live-val { font-weight: 700; font-size: 0.78rem; }
        .tension-high { color: #ef4444; }
        .tension-mid  { color: #f59e0b; }
        .tension-low  { color: #10b981; }
        .align-high   { color: #10b981; }
        .align-low    { color: #f59e0b; }
        .round-chip {
            background: rgba(102,126,234,0.2);
            border: 1px solid #667eea;
            border-radius: 4px;
            padding: 2px 6px;
            color: #818cf8;
            font-size: 0.7rem;
        }
        /* ── MAIN CANVAS AREA ── */
        #vizArea {
            flex: 1;
            position: relative;
            background: #0a0e27;
            overflow: hidden;
        }
        canvas#mainCanvas { width: 100%; height: 100%; display: block; }
        /* ── STATS OVERLAY (top-right) ── */
        #statsOverlay {
            position: absolute;
            top: 0.75rem;
            right: 0.75rem;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            pointer-events: none;
        }
        .stat-chip {
            background: rgba(26,31,58,0.92);
            padding: 0.5rem 0.75rem;
            border-radius: 7px;
            border: 1px solid rgba(102,126,234,0.25);
            backdrop-filter: blur(8px);
        }
        .stat-label { display: block; font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; }
        .stat-value { display: block; font-size: 1.1rem; font-weight: 700; color: #818cf8; }
        /* ── LEGEND (bottom-left) ── */
        #legend {
            position: absolute;
            bottom: 0.75rem;
            left: 0.75rem;
            background: rgba(26,31,58,0.92);
            padding: 0.75rem;
            border-radius: 8px;
            border: 1px solid rgba(102,126,234,0.2);
            backdrop-filter: blur(8px);
            font-size: 0.72rem;
        }
        #legend h4 { font-size: 0.75rem; margin-bottom: 0.4rem; color: #818cf8; }
        .leg-row { display: flex; align-items: center; margin-bottom: 0.3rem; }
        .leg-dot { width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
        /* ── FOCUSED NODE RING ── */
        #focusRing {
            position: absolute;
            border: 2px solid #f97316;
            border-radius: 50%;
            pointer-events: none;
            display: none;
            box-shadow: 0 0 12px rgba(249,115,22,0.6);
            transition: all 0.2s;
        }
        /* ── STRESS TICKER ── */
        #stressTicker {
            position: absolute;
            bottom: 0.75rem;
            right: 0.75rem;
            background: rgba(26,31,58,0.92);
            border: 1px solid rgba(249,115,22,0.3);
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            font-size: 0.72rem;
            display: none;
        }
        #stressTicker.visible { display: block; }
        .ticker-title { color: #f97316; font-weight: 700; font-size: 0.7rem; text-transform: uppercase; margin-bottom: 3px; }
        /* ── TOOLTIP ── */
        #tooltip {
            position: absolute;
            background: rgba(10,14,39,0.97);
            border: 1px solid rgba(102,126,234,0.4);
            border-radius: 8px;
            padding: 0.6rem 0.9rem;
            font-size: 0.75rem;
            pointer-events: none;
            display: none;
            max-width: 220px;
            backdrop-filter: blur(10px);
            z-index: 50;
        }
        #tooltip .tt-name { font-weight: 700; color: #818cf8; margin-bottom: 4px; }
        #tooltip .tt-row  { display: flex; justify-content: space-between; gap: 12px; color: #94a3b8; }
        #tooltip .tt-row span:last-child { color: #e0e7ff; font-weight: 600; }
    </style>
</head>
<body>
<button id="maxBtn" onclick="toggleMaximize()">⛶ MAXIMIZE</button>
<div id="wrapper">
  <!-- LEFT SIDEBAR -->
  <div id="sidebar">
    <!-- INFLUENCE PARAMETERS -->
    <div class="sidebar-section">
      <h3>Influence Parameters</h3>
      <div class="ctrl-group">
        <label>External Pressure <span class="val" id="ext_val">70%</span></label>
        <input type="range" id="external_pressure" min="0" max="100" value="70" oninput="updateParams()">
      </div>
      <div class="ctrl-group">
        <label>Internal Forces <span class="val" id="int_val">60%</span></label>
        <input type="range" id="internal_forces" min="0" max="100" value="60" oninput="updateParams()">
      </div>
      <div class="ctrl-group">
        <label>Policy Convergence <span class="val" id="conv_val">45%</span></label>
        <input type="range" id="convergence" min="0" max="100" value="45" oninput="updateParams()">
      </div>
      <div class="ctrl-group">
        <label>Time Evolution <span class="val" id="time_val">0 mo</span></label>
        <input type="range" id="time" min="0" max="36" value="0" oninput="updateParams()">
      </div>
    </div>
    <!-- VIZ TOGGLES -->
    <div class="sidebar-section">
      <h3>Visualization Options</h3>
      <button class="toggle-btn active" id="show_arrows" onclick="toggleArrows()">🔵 Policy Pressures</button>
      <button class="toggle-btn active" id="show_spheres" onclick="toggleSpheres()">🟣 Cultural Forces</button>
      <button class="toggle-btn active" id="show_connections" onclick="toggleConnections()">🔗 Alignments</button>
      <button class="toggle-btn active" id="show_labels" onclick="toggleLabels()">🏷️ Labels</button>
    </div>
    <!-- ANIMATION -->
    <div class="sidebar-section">
      <h3>Animation</h3>
      <button class="btn" onclick="toggleAnimation()"><span id="anim_text">▶ Start Animation</span></button>
      <button class="btn sec" onclick="resetView()">↺ Reset View</button>
    </div>
    <!-- COUNTRY FOCUS DRILL-DOWN -->
    <div class="sidebar-section">
      <h3>🔍 Country Focus</h3>
      <select id="focusSelect" onchange="focusCountry(this.value)">
        <option value="">— Select country —</option>
        <option value="US">United States</option>
        <option value="EU">European Union</option>
        <option value="CN">China</option>
        <option value="UK">United Kingdom</option>
        <option value="JP">Japan</option>
        <option value="IN">India</option>
        <option value="BR">Brazil</option>
        <option value="RU">Russia</option>
        <option value="NATO">NATO</option>
        <option value="Dubai">Dubai</option>
        <option value="Qatar">Qatar</option>
        <option value="Iraq">Iraq</option>
        <option value="Greenland">Greenland</option>
        <option value="Venezuela">Venezuela</option>
        <option value="Israel">Israel</option>
        <option value="Paraguay">Paraguay</option>
        <option value="Belgium">Belgium</option>
        <option value="Denmark">Denmark</option>
        <option value="Ukraine">Ukraine</option>
        <option value="Serbia">Serbia</option>
        <option value="Argentina">Argentina</option>
        <option value="Norway">Norway</option>
        <option value="Switzerland">Switzerland</option>
        <option value="Poland">Poland</option>
        <option value="Global South">Global South</option>
      </select>
      <div id="focusCard"></div>
      <button class="btn sec" id="clearFocusBtn" style="display:none;margin-top:0.4rem" onclick="clearFocus()">✕ Clear Focus</button>
    </div>
    <!-- LIVE STRESS OVERLAY -->
    <div class="sidebar-section">
      <h3>⚡ Live Stress Test <span class="live-badge" id="liveBadge">LIVE</span></h3>
      <div id="livePanel">
        <div class="live-metric"><span class="live-key">Active Actors</span><span class="live-val" id="lv_actors">—</span></div>
        <div class="live-metric"><span class="live-key">Round</span><span class="live-val" id="lv_round">—</span></div>
        <div class="live-metric"><span class="live-key">Reward</span><span class="live-val" id="lv_reward">—</span></div>
        <div class="live-metric"><span class="live-key">Risk</span><span class="live-val" id="lv_risk">—</span></div>
        <div class="live-metric"><span class="live-key">Tension</span><span class="live-val" id="lv_tension">—</span></div>
        <div class="live-metric"><span class="live-key">Alignment</span><span class="live-val" id="lv_align">—</span></div>
        <div class="live-metric"><span class="live-key">Confidence</span><span class="live-val" id="lv_conf">—</span></div>
      </div>
      <button class="btn sec" style="margin-top:0.5rem;font-size:0.75rem" onclick="injectTestData()">🧪 Inject Test Data</button>
    </div>
    <!-- INFO -->
    <div class="sidebar-section">
      <h3>Information</h3>
      <div style="font-size:0.72rem;color:#94a3b8;line-height:1.6">
        <p><strong>Drag:</strong> Rotate scene</p>
        <p><strong>Scroll:</strong> Zoom</p>
        <p><strong>Click node:</strong> Focus country</p>
        <p><strong>Hover node:</strong> Tooltip details</p>
        <p><strong>⛶ Maximize:</strong> Full-screen 3D view</p>
      </div>
    </div>
  </div>
  <!-- SIDEBAR COLLAPSE TOGGLE -->
  <button id="sidebarToggle" onclick="toggleSidebar()">◀</button>

  <!-- MAIN VIZ AREA -->
  <div id="vizArea">
    <canvas id="mainCanvas"></canvas>
    <!-- Stats overlay -->
    <div id="statsOverlay">
      <div class="stat-chip"><span class="stat-label">Countries</span><span class="stat-value" id="country_count">25</span></div>
      <div class="stat-chip"><span class="stat-label">Influences</span><span class="stat-value" id="influence_count">12</span></div>
      <div class="stat-chip"><span class="stat-label">Alignment</span><span class="stat-value" id="alignment_score">45%</span></div>
      <div class="stat-chip"><span class="stat-label">Clusters</span><span class="stat-value" id="cluster_count">4</span></div>
    </div>
    <!-- Legend -->
    <div id="legend">
      <h4>Legend</h4>
      <div class="leg-row"><div class="leg-dot" style="background:#667eea"></div><span>Western-aligned</span></div>
      <div class="leg-row"><div class="leg-dot" style="background:#ef4444"></div><span>State-controlled</span></div>
      <div class="leg-row"><div class="leg-dot" style="background:#f59e0b"></div><span>Hybrid approach</span></div>
      <div class="leg-row"><div class="leg-dot" style="background:#10b981"></div><span>Regional/Developing</span></div>
      <div class="leg-row"><div class="leg-dot" style="background:#f97316;animation:pulse 1.2s infinite"></div><span>🔥 Stress-test active</span></div>
    </div>
    <!-- Stress ticker -->
    <div id="stressTicker">
      <div class="ticker-title">⚡ Stress Pulse</div>
      <div id="tickerBody">—</div>
    </div>
    <!-- Tooltip -->
    <div id="tooltip"></div>
    <!-- Focus ring (DOM overlay, hidden by default) -->
    <div id="focusRing"></div>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
// ════════════════════════════════════════════════════════════
// DATA
// ════════════════════════════════════════════════════════════
const countries = [
    {id:'US',       gdp:21.0,  inf:0.95, pos:[0.80,0.90,0.70], c:0x667eea, align:'Western',
     fullName:'United States',  position:'Favors innovation over regulation',          milExp:3.4,  internet:92,  cultural:'Western'},
    {id:'EU',       gdp:15.0,  inf:0.90, pos:[0.90,0.85,0.90], c:0x667eea, align:'Western',
     fullName:'European Union',  position:'Strict data protection (GDPR)',              milExp:1.5,  internet:89,  cultural:'Western'},
    {id:'CN',       gdp:17.7,  inf:0.93, pos:[0.20,0.90,0.30], c:0xef4444, align:'State',
     fullName:'China',           position:'Strict state-driven AI governance',          milExp:1.7,  internet:73,  cultural:'Eastern'},
    {id:'UK',       gdp:3.2,   inf:0.85, pos:[0.85,0.80,0.85], c:0x667eea, align:'Western',
     fullName:'United Kingdom',  position:'Supports EU-style data protection',          milExp:2.2,  internet:96,  cultural:'Western'},
    {id:'JP',       gdp:5.1,   inf:0.88, pos:[0.70,0.85,0.80], c:0xf59e0b, align:'Hybrid',
     fullName:'Japan',           position:'Pro-regulation for trust',                   milExp:1.0,  internet:95,  cultural:'E-W hybrid'},
    {id:'IN',       gdp:3.7,   inf:0.82, pos:[0.60,0.80,0.60], c:0xf59e0b, align:'Hybrid',
     fullName:'India',           position:'Strategic tech balancing',                   milExp:2.4,  internet:43,  cultural:'South Asian'},
    {id:'BR',       gdp:2.0,   inf:0.75, pos:[0.70,0.70,0.65], c:0x10b981, align:'Regional',
     fullName:'Brazil',          position:'Leaning toward EU-style regulation',         milExp:1.4,  internet:81,  cultural:'Latin American'},
    {id:'RU',       gdp:1.8,   inf:0.78, pos:[0.30,0.75,0.40], c:0xef4444, align:'State',
     fullName:'Russia',          position:'Sovereign tech control',                     milExp:4.3,  internet:85,  cultural:'Eastern'},
    {id:'NATO',     gdp:25.0,  inf:0.97, pos:[0.85,0.95,0.85], c:0x667eea, align:'Western',
     fullName:'NATO',            position:'Collective security & data interoperability',milExp:2.5,  internet:90,  cultural:'W. Alliance'},
    {id:'Dubai',    gdp:0.5,   inf:0.70, pos:[0.65,0.65,0.60], c:0xf59e0b, align:'Hybrid',
     fullName:'Dubai (UAE)',     position:'Moderate regulatory stance',                 milExp:5.6,  internet:99,  cultural:'W-ME hybrid'},
    {id:'Qatar',    gdp:0.18,  inf:0.68, pos:[0.60,0.65,0.55], c:0x10b981, align:'Regional',
     fullName:'Qatar',           position:'Tech-forward with state oversight',          milExp:3.7,  internet:99,  cultural:'Middle East'},
    {id:'Iraq',     gdp:0.20,  inf:0.42, pos:[0.40,0.40,0.45], c:0x10b981, align:'Regional',
     fullName:'Iraq',            position:'Developing governance framework',            milExp:3.5,  internet:49,  cultural:'Middle East'},
    {id:'Greenland',gdp:0.003, inf:0.45, pos:[0.50,0.40,0.50], c:0x10b981, align:'Regional',
     fullName:'Greenland',       position:'Emerging Arctic tech governance',            milExp:0.0,  internet:68,  cultural:'Nordic'},
    {id:'Venezuela',gdp:0.048, inf:0.58, pos:[0.35,0.55,0.40], c:0xef4444, align:'State',
     fullName:'Venezuela',       position:'State-controlled digital infrastructure',    milExp:0.9,  internet:72,  cultural:'Latin American'},
    {id:'Israel',   gdp:0.52,  inf:0.82, pos:[0.78,0.80,0.76], c:0x667eea, align:'Western',
     fullName:'Israel',          position:'Cyber & security-forward; high-tech economy',milExp:5.0, internet:88,  cultural:'ME/W-linked'},
    {id:'Paraguay', gdp:0.04,  inf:0.62, pos:[0.62,0.60,0.58], c:0x10b981, align:'Regional',
     fullName:'Paraguay',        position:'Developing market; regulatory capacity building',milExp:1.2,internet:65,cultural:'Latin American'},
    {id:'Belgium',  gdp:0.58,  inf:0.86, pos:[0.88,0.84,0.88], c:0x667eea, align:'Western',
     fullName:'Belgium',         position:'EU/NATO hub; compliance-aligned',            milExp:1.1,  internet:92,  cultural:'Western (EU)'},
    {id:'Denmark',  gdp:0.41,  inf:0.87, pos:[0.87,0.86,0.89], c:0x667eea, align:'Western',
     fullName:'Denmark',         position:'High-trust governance; strong digital state', milExp:1.7, internet:98,  cultural:'Nordic/Western'},
    {id:'Ukraine',  gdp:0.18,  inf:0.70, pos:[0.80,0.72,0.72], c:0x667eea, align:'Western',
     fullName:'Ukraine',         position:'Conflict resilience; reconstruction & security',milExp:15.0,internet:76,cultural:'E-EU/W-aligned'},
    {id:'Serbia',   gdp:0.07,  inf:0.68, pos:[0.75,0.70,0.70], c:0xf59e0b, align:'Hybrid',
     fullName:'Serbia',          position:'Non-aligned balancing; regional interop',    milExp:2.0,  internet:80,  cultural:'Balkan/mixed'},
    {id:'Argentina',gdp:0.64,  inf:0.66, pos:[0.64,0.62,0.60], c:0x10b981, align:'Regional',
     fullName:'Argentina',       position:'Emerging market; institutional volatility',  milExp:0.7,  internet:88,  cultural:'Latin American'},
    {id:'Norway',   gdp:0.48,  inf:0.88, pos:[0.86,0.88,0.90], c:0x667eea, align:'Western',
     fullName:'Norway',          position:'Energy wealth; NATO-aligned; high trust',    milExp:1.6,  internet:99,  cultural:'Nordic/Western'},
    {id:'Switzerland',gdp:0.88,inf:0.89, pos:[0.89,0.87,0.92], c:0x667eea, align:'Western',
     fullName:'Switzerland',     position:'Neutral hub; high compliance; finance-centric',milExp:0.7,internet:97, cultural:'Western (neutral)'},
    {id:'Poland',   gdp:0.80,  inf:0.84, pos:[0.83,0.78,0.80], c:0x667eea, align:'Western',
     fullName:'Poland',          position:'NATO frontline; rapid defense modernization', milExp:3.5, internet:90,  cultural:'E-EU/W-aligned'},
    {id:'Global South',gdp:35.0,inf:0.65,pos:[0.55,0.60,0.55],c:0x10b981, align:'Regional',
     fullName:'Global South',    position:'Plural bloc; sovereignty & development-focused',milExp:2.0,internet:60,cultural:'Multi-regional'}
];

const policyArrows = [
    {name:'GDPR',         targets:['EU','UK','BR','Belgium','Denmark','Norway','Switzerland','Poland'],  strength:0.9,  color:0x667eea},
    {name:'US Export',    targets:['CN','RU','Iraq','Serbia'],                                          strength:0.85, color:0xef4444},
    {name:'Belt&Road',    targets:['BR','Qatar','Dubai','Argentina','Serbia'],                          strength:0.75, color:0xfbbf24},
    {name:'AUKUS',        targets:['US','UK','JP'],                                                     strength:0.80, color:0x667eea},
    {name:'UN Ethics',    targets:['IN','BR','NATO','Global South','Paraguay'],                         strength:0.60, color:0x10b981},
    {name:'NATO Expand',  targets:['Ukraine','Poland','Norway','Denmark','Belgium'],                    strength:0.88, color:0x818cf8},
    {name:'Conflict Zone',targets:['Ukraine','Israel','Iraq'],                                          strength:0.82, color:0xf97316}
];

const culturalSpheres = [
    {name:'Democratic',    countries:['US','EU','UK','JP','IN','BR','Belgium','Denmark','Norway','Switzerland','Poland','Ukraine'], strength:0.85, color:0x667eea},
    {name:'TechNat',       countries:['CN','RU','US','Israel'],                                                                    strength:0.90, color:0xef4444},
    {name:'PostColonial',  countries:['IN','BR','Iraq','Qatar','Paraguay','Argentina','Global South'],                             strength:0.70, color:0x10b981},
    {name:'Energy',        countries:['RU','Qatar','Dubai','Venezuela','Norway'],                                                  strength:0.75, color:0xfbbf24},
    {name:'MilTech',       countries:['US','CN','RU','NATO','Israel','Ukraine','Poland'],                                          strength:0.80, color:0xa855f7},
    {name:'NeutralHub',    countries:['Switzerland','Serbia'],                                                                     strength:0.65, color:0x94a3b8}
];

// ════════════════════════════════════════════════════════════
// SCENE STATE
// ════════════════════════════════════════════════════════════
let scene, camera, renderer;
let nodes=[], arrows=[], spheres=[], connections=[], labels=[];
let isAnimating=false;
let showArrows=true, showSpheres=true, showConnections=true, showLabels=true;
let focusedId=null, sidebarOpen=true;
let liveData={};  // injected from Streamlit via postMessage or injected directly

// ════════════════════════════════════════════════════════════
// MAXIMIZE / MINIMIZE
// ════════════════════════════════════════════════════════════
function toggleMaximize() {
    const body = document.body;
    const btn = document.getElementById('maxBtn');
    const maximized = body.classList.toggle('maximized');
    btn.textContent = maximized ? '⛶ RESTORE' : '⛶ MAXIMIZE';
    setTimeout(() => {
        const canvas = document.getElementById('mainCanvas');
        if (camera && renderer) {
            camera.aspect = canvas.clientWidth / canvas.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(canvas.clientWidth, canvas.clientHeight);
        }
    }, 370);
}

// ════════════════════════════════════════════════════════════
// SIDEBAR TOGGLE
// ════════════════════════════════════════════════════════════
function toggleSidebar() {
    const sb = document.getElementById('sidebar');
    const btn = document.getElementById('sidebarToggle');
    sidebarOpen = !sidebarOpen;
    sb.classList.toggle('collapsed', !sidebarOpen);
    btn.textContent = sidebarOpen ? '◀' : '▶';
    btn.style.left = sidebarOpen ? '270px' : '0px';
    setTimeout(() => {
        const canvas = document.getElementById('mainCanvas');
        if (camera && renderer) {
            camera.aspect = canvas.clientWidth / canvas.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(canvas.clientWidth, canvas.clientHeight);
        }
    }, 330);
}

// ════════════════════════════════════════════════════════════
// INIT THREE.JS
// ════════════════════════════════════════════════════════════
function init() {
    const canvas = document.getElementById('mainCanvas');
    const w = canvas.clientWidth, h = canvas.clientHeight;

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0e27);

    camera = new THREE.PerspectiveCamera(60, w/h, 0.1, 1000);
    camera.position.set(25, 20, 25);
    camera.lookAt(0,0,0);

    renderer = new THREE.WebGLRenderer({canvas, antialias:true});
    renderer.setSize(w, h);
    renderer.setPixelRatio(window.devicePixelRatio);

    scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const p1 = new THREE.PointLight(0x667eea, 1, 100);
    p1.position.set(20,20,20); scene.add(p1);
    const p2 = new THREE.PointLight(0x764ba2, 0.8, 100);
    p2.position.set(-20,-20,-20); scene.add(p2);

    createNodes();
    createPolicyArrows();
    createCulturalSpheres();
    createConnections();
    setupMouseControls(canvas);
    animate();
}

// ════════════════════════════════════════════════════════════
// NODE CREATION
// ════════════════════════════════════════════════════════════
function createNodes() {
    countries.forEach((c,i) => {
        const sz = 0.3 + c.inf * 0.5;
        const geo = new THREE.SphereGeometry(sz, 32, 32);
        const mat = new THREE.MeshPhongMaterial({color:c.c, emissive:c.c, emissiveIntensity:0.3, shininess:30});
        const mesh = new THREE.Mesh(geo, mat);
        const x=(c.pos[0]-0.5)*30, y=(c.pos[1]-0.5)*25, z=(c.pos[2]-0.5)*30;
        mesh.position.set(x,y,z);
        mesh.userData = {countryId: c.id};
        scene.add(mesh);

        const label = makeLabel(c.id);
        label.position.set(x, y+sz+0.8, z);
        scene.add(label);

        nodes.push({mesh, label, country:c, initialPos:mesh.position.clone(), baseColor:c.c});
        labels.push(label);
    });
}

function makeLabel(text) {
    const cv = document.createElement('canvas');
    cv.width=256; cv.height=128;
    const ctx = cv.getContext('2d');
    ctx.fillStyle='rgba(0,0,0,0.4)';
    ctx.roundRect(10,20,236,80,12);
    ctx.fill();
    ctx.fillStyle='#ffffff';
    ctx.font='Bold 42px Arial';
    ctx.textAlign='center';
    ctx.fillText(text, 128, 78);
    const tex = new THREE.Texture(cv);
    tex.needsUpdate=true;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({map:tex, transparent:true}));
    sp.scale.set(3.2, 1.6, 1);
    return sp;
}

// ════════════════════════════════════════════════════════════
// ARROWS & SPHERES & CONNECTIONS
// ════════════════════════════════════════════════════════════
function createPolicyArrows() {
    policyArrows.forEach(policy => {
        policy.targets.forEach(tid => {
            const tn = nodes.find(n=>n.country.id===tid);
            if (!tn) return;
            const origin = new THREE.Vector3(0,10,0);
            const dir = new THREE.Vector3().subVectors(tn.mesh.position, origin);
            const len = dir.length();
            const ah = new THREE.ArrowHelper(dir.normalize(), origin, len, policy.color, len*0.2, len*0.1);
            ah.userData = {type:'arrow', policy};
            scene.add(ah);
            arrows.push(ah);
        });
    });
}

function createCulturalSpheres() {
    culturalSpheres.forEach(sph => {
        sph.countries.forEach(cid => {
            const nd = nodes.find(n=>n.country.id===cid);
            if (!nd) return;
            const geo = new THREE.SphereGeometry(2.5, 32, 32);
            const mat = new THREE.MeshBasicMaterial({color:sph.color, transparent:true, opacity:0.1, wireframe:true});
            const mesh = new THREE.Mesh(geo, mat);
            mesh.position.copy(nd.mesh.position);
            mesh.userData = {type:'cultural', sphere:sph};
            scene.add(mesh);
            spheres.push(mesh);
        });
    });
}

function createConnections() {
    for (let i=0; i<nodes.length; i++) {
        for (let j=i+1; j<nodes.length; j++) {
            const d = nodes[i].mesh.position.distanceTo(nodes[j].mesh.position);
            if (d < 12) {
                const mat = new THREE.LineBasicMaterial({color:0x667eea, transparent:true, opacity:Math.max(0.08, 1-d/15)});
                const geo = new THREE.BufferGeometry().setFromPoints([nodes[i].mesh.position, nodes[j].mesh.position]);
                const line = new THREE.Line(geo, mat);
                scene.add(line);
                connections.push(line);
            }
        }
    }
}

// ════════════════════════════════════════════════════════════
// MOUSE CONTROLS
// ════════════════════════════════════════════════════════════
function setupMouseControls(canvas) {
    let dragging=false, prev={x:0,y:0};
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    canvas.addEventListener('mousedown', e=>{dragging=true; prev={x:e.clientX,y:e.clientY};});
    canvas.addEventListener('mouseup', ()=>{dragging=false;});
    canvas.addEventListener('mouseleave', ()=>{dragging=false; hideTooltip();});

    canvas.addEventListener('mousemove', e=>{
        if (dragging) {
            const dx=e.clientX-prev.x, dy=e.clientY-prev.y;
            camera.position.applyAxisAngle(new THREE.Vector3(0,1,0), dx*0.005);
            camera.position.applyAxisAngle(new THREE.Vector3(1,0,0), dy*0.005);
            camera.lookAt(0,0,0);
            prev={x:e.clientX,y:e.clientY};
        } else {
            // Hover tooltip
            const rect = canvas.getBoundingClientRect();
            mouse.x = ((e.clientX-rect.left)/rect.width)*2-1;
            mouse.y = -((e.clientY-rect.top)/rect.height)*2+1;
            raycaster.setFromCamera(mouse, camera);
            const hits = raycaster.intersectObjects(nodes.map(n=>n.mesh));
            if (hits.length>0) {
                const nd = nodes.find(n=>n.mesh===hits[0].object);
                if (nd) showTooltip(e, nd.country, e.clientX-rect.left, e.clientY-rect.top);
            } else {
                hideTooltip();
            }
        }
    });

    canvas.addEventListener('click', e=>{
        const rect = canvas.getBoundingClientRect();
        mouse.x = ((e.clientX-rect.left)/rect.width)*2-1;
        mouse.y = -((e.clientY-rect.top)/rect.height)*2+1;
        raycaster.setFromCamera(mouse, camera);
        const hits = raycaster.intersectObjects(nodes.map(n=>n.mesh));
        if (hits.length>0) {
            const nd = nodes.find(n=>n.mesh===hits[0].object);
            if (nd) {
                document.getElementById('focusSelect').value = nd.country.id;
                focusCountry(nd.country.id);
            }
        }
    });

    canvas.addEventListener('wheel', e=>{
        e.preventDefault();
        camera.position.multiplyScalar(1 + (e.deltaY>0?1:-1)*0.001*Math.abs(e.deltaY));
    }, {passive:false});
}

// ════════════════════════════════════════════════════════════
// TOOLTIP
// ════════════════════════════════════════════════════════════
function showTooltip(e, c, cx, cy) {
    const tip = document.getElementById('tooltip');
    const extPressures = policyArrows.filter(p=>p.targets.includes(c.id)).map(p=>p.name);
    const cultures = culturalSpheres.filter(s=>s.countries.includes(c.id)).map(s=>s.name);
    tip.innerHTML = `
        <div class="tt-name">${c.fullName}</div>
        <div class="tt-row"><span>Influence</span><span>${(c.inf*100).toFixed(0)}%</span></div>
        <div class="tt-row"><span>GDP</span><span>$${c.gdp}T</span></div>
        <div class="tt-row"><span>Mil Exp</span><span>${c.milExp}% GDP</span></div>
        <div class="tt-row"><span>Internet</span><span>${c.internet}%</span></div>
        <div class="tt-row"><span>Alignment</span><span>${c.align}</span></div>
        ${extPressures.length ? `<div class="tt-row"><span>Policy Pressures</span><span>${extPressures.join(', ')}</span></div>` : ''}
        ${cultures.length ? `<div class="tt-row"><span>Cultural Spheres</span><span>${cultures.join(', ')}</span></div>` : ''}
        <div class="tt-row" style="margin-top:4px;font-size:0.68rem;color:#64748b"><span colspan="2">${c.position}</span></div>
    `;
    tip.style.display = 'block';
    tip.style.left = Math.min(cx+12, 600) + 'px';
    tip.style.top  = Math.max(cy-20, 5) + 'px';
}

function hideTooltip() {
    document.getElementById('tooltip').style.display = 'none';
}

// ════════════════════════════════════════════════════════════
// COUNTRY FOCUS / DRILL-DOWN
// ════════════════════════════════════════════════════════════
const countryFullNames = {};
countries.forEach(c=>{ countryFullNames[c.id] = c.fullName; });

function focusCountry(id) {
    focusedId = id || null;
    // Reset all node emissive
    nodes.forEach(n=>{
        n.mesh.material.emissiveIntensity = 0.3;
        n.mesh.material.color.setHex(n.baseColor);
        n.mesh.material.emissive.setHex(n.baseColor);
    });

    const card = document.getElementById('focusCard');
    const clearBtn = document.getElementById('clearFocusBtn');

    if (!id) { card.classList.remove('visible'); clearBtn.style.display='none'; return; }

    // Highlight focused node
    const nd = nodes.find(n=>n.country.id===id);
    if (nd) {
        nd.mesh.material.emissiveIntensity = 0.9;
        nd.mesh.material.color.setHex(0xffffff);
        // Fly camera toward node
        const tp = nd.mesh.position;
        const offset = new THREE.Vector3(tp.x, tp.y+3, tp.z+12);
        camera.position.lerp(offset, 0.4);
        camera.lookAt(tp);
    }

    // Build detail card
    const c = countries.find(x=>x.id===id);
    if (!c) return;

    const extPressures = policyArrows.filter(p=>p.targets.includes(id));
    const cultures = culturalSpheres.filter(s=>s.countries.includes(id));

    // Check if this country is an active stress-test actor
    const isStressActor = (liveData.actorA === id || liveData.actorB === id ||
                           liveData.actorA === c.fullName || liveData.actorB === c.fullName);

    const extPills = extPressures.map(p=>
        `<span class="pill ${isStressActor&&p.strength>0.8?'pill-hot':'pill-ext'}">${p.name} (${(p.strength*100).toFixed(0)}%)</span>`
    ).join('');
    const intPills = cultures.map(s=>
        `<span class="pill pill-int">${s.name}</span>`
    ).join('');

    let stressBlock = '';
    if (isStressActor && liveData.round) {
        const isA = (liveData.actorA === id || liveData.actorA === c.fullName);
        stressBlock = `
        <div style="margin-top:0.6rem;padding-top:0.5rem;border-top:1px solid rgba(249,115,22,0.3)">
            <div style="color:#f97316;font-size:0.68rem;font-weight:700;margin-bottom:4px">⚡ STRESS TEST ACTIVE — Round ${liveData.round}</div>
            <div class="fc-row"><span class="fc-key">Role</span><span class="fc-val">${isA?'Actor A':'Actor B'}</span></div>
            <div class="fc-row"><span class="fc-key">Reward</span><span class="fc-val">${liveData.reward!==undefined?(liveData.reward*100).toFixed(1)+'%':'—'}</span></div>
            <div class="fc-row"><span class="fc-key">Risk</span><span class="fc-val ${liveData.risk>0.7?'tension-high':liveData.risk>0.4?'tension-mid':'tension-low'}">${liveData.risk!==undefined?(liveData.risk*100).toFixed(1)+'%':'—'}</span></div>
            <div class="fc-row"><span class="fc-key">Tension</span><span class="fc-val ${liveData.tension>0.7?'tension-high':liveData.tension>0.4?'tension-mid':'tension-low'}">${liveData.tension!==undefined?(liveData.tension*100).toFixed(1)+'%':'—'}</span></div>
        </div>`;
    }

    card.innerHTML = `
        <div class="fc-title">${c.fullName}</div>
        <div class="fc-row"><span class="fc-key">Influence Score</span><span class="fc-val">${(c.inf*100).toFixed(0)}%</span></div>
        <div class="fc-row"><span class="fc-key">GDP</span><span class="fc-val">$${c.gdp}T</span></div>
        <div class="fc-row"><span class="fc-key">Military Exp</span><span class="fc-val">${c.milExp}% GDP</span></div>
        <div class="fc-row"><span class="fc-key">Internet</span><span class="fc-val">${c.internet}%</span></div>
        <div class="fc-row"><span class="fc-key">Cultural Align</span><span class="fc-val">${c.cultural}</span></div>
        <div class="fc-row"><span class="fc-key">Cluster</span><span class="fc-val">${c.align}</span></div>
        <div style="margin-top:0.5rem;font-size:0.68rem;color:#94a3b8;font-style:italic">"${c.position}"</div>
        <div class="fc-pills" style="margin-top:0.6rem">
            <div style="font-size:0.67rem;color:#818cf8;width:100%;margin-bottom:2px">📋 Policy Pressures:</div>
            ${extPills || '<span style="color:#64748b;font-size:0.68rem">None identified</span>'}
        </div>
        <div class="fc-pills">
            <div style="font-size:0.67rem;color:#a855f7;width:100%;margin-bottom:2px">🌐 Cultural Spheres:</div>
            ${intPills || '<span style="color:#64748b;font-size:0.68rem">None identified</span>'}
        </div>
        ${stressBlock}
    `;
    card.classList.add('visible');
    clearBtn.style.display='block';
}

function clearFocus() {
    document.getElementById('focusSelect').value = '';
    focusCountry(null);
}

// ════════════════════════════════════════════════════════════
// LIVE STRESS TEST OVERLAY
// ════════════════════════════════════════════════════════════
function updateLivePanel(data) {
    liveData = data;

    // Update sidebar metrics
    if (data.actorA||data.actorB) {
        const aName = countryFullNames[data.actorA]||data.actorA||'—';
        const bName = countryFullNames[data.actorB]||data.actorB||'—';
        document.getElementById('lv_actors').textContent = (aName||'—') + ' vs ' + (bName||'—');
    }
    document.getElementById('lv_round').innerHTML   = data.round!==undefined ? `<span class="round-chip">R${data.round}</span>` : '—';
    document.getElementById('lv_reward').textContent  = data.reward!==undefined  ? (data.reward*100).toFixed(1)+'%' : '—';

    const tVal = data.tension!==undefined ? (data.tension*100).toFixed(1)+'%' : '—';
    const tClass = data.tension>0.7?'tension-high':data.tension>0.4?'tension-mid':'tension-low';
    document.getElementById('lv_tension').innerHTML  = `<span class="${tClass}">${tVal}</span>`;

    const rVal = data.risk!==undefined ? (data.risk*100).toFixed(1)+'%' : '—';
    const rClass = data.risk>0.7?'tension-high':data.risk>0.4?'tension-mid':'tension-low';
    document.getElementById('lv_risk').innerHTML     = `<span class="${rClass}">${rVal}</span>`;

    const aVal = data.alignment!==undefined ? (data.alignment*100).toFixed(0)+'%' : '—';
    const aClass = data.alignment>0.5?'align-high':'align-low';
    document.getElementById('lv_align').innerHTML    = `<span class="${aClass}">${aVal}</span>`;
    document.getElementById('lv_conf').textContent   = data.confidence!==undefined ? (data.confidence*100).toFixed(1)+'%' : '—';

    // Pulse stressed actors in scene
    const stressIds = [data.actorA, data.actorB].filter(Boolean);
    const tensionVal = data.tension || 0;
    nodes.forEach(n=>{
        if (stressIds.includes(n.country.id) || stressIds.includes(n.country.fullName)) {
            // Orange pulse on high tension
            if (tensionVal > 0.6) {
                n.mesh.material.emissive.setHex(0xf97316);
                n.mesh.material.emissiveIntensity = 0.7 + 0.3*Math.sin(Date.now()*0.005);
            } else {
                n.mesh.material.emissiveIntensity = 0.55;
            }
        }
    });

    // Show stress ticker
    if (data.round) {
        const ticker = document.getElementById('stressTicker');
        ticker.classList.add('visible');
        const shock = data.shockEvent ? `<div style="color:#f97316;margin-top:3px">💥 ${data.shockEvent}</div>` : '';
        document.getElementById('tickerBody').innerHTML =
            `R${data.round}: T=${tVal} | Reward=${(data.reward*100||0).toFixed(1)}%${shock}`;
    }

    // Refresh focus card if open
    if (focusedId) focusCountry(focusedId);
}

// Listen for Streamlit postMessage data bridge
window.addEventListener('message', function(event) {
    if (event.data && event.data.type === 'auracelle_stress') {
        updateLivePanel(event.data.payload);
    }
});

// ════════════════════════════════════════════════════════════
// TEST DATA INJECTOR
// ════════════════════════════════════════════════════════════
function injectTestData() {
    updateLivePanel({
        actorA: 'US', actorB: 'CN',
        round: Math.floor(Math.random()*10)+1,
        reward: Math.random(),
        risk: 0.5 + Math.random()*0.4,
        tension: 0.5 + Math.random()*0.45,
        alignment: Math.random()*0.6,
        confidence: 0.5 + Math.random()*0.4,
        shockEvent: Math.random()>0.7 ? 'cyber_attack' : null
    });
}

// ════════════════════════════════════════════════════════════
// PARAM UPDATE
// ════════════════════════════════════════════════════════════
function updateParams() {
    const ext  = parseInt(document.getElementById('external_pressure').value)/100;
    const intF = parseInt(document.getElementById('internal_forces').value)/100;
    const conv = parseInt(document.getElementById('convergence').value)/100;
    const time = parseInt(document.getElementById('time').value);

    document.getElementById('ext_val').textContent  = Math.round(ext*100)+'%';
    document.getElementById('int_val').textContent  = Math.round(intF*100)+'%';
    document.getElementById('conv_val').textContent = Math.round(conv*100)+'%';
    document.getElementById('time_val').textContent = time+' mo';

    const center = new THREE.Vector3(0,0,0);
    nodes.forEach(n=>{
        const tp = n.initialPos.clone().lerp(center, conv*0.7);
        n.mesh.position.lerp(tp, 0.1);
        n.label.position.copy(n.mesh.position);
        n.label.position.y += 1.2;
    });

    document.getElementById('alignment_score').textContent = Math.round(conv*100)+'%';
    document.getElementById('cluster_count').textContent   = Math.max(1, Math.round(5*(1-conv)));

    arrows.forEach(a=>{a.visible=showArrows; if(a.line) a.line.material.opacity=ext*0.8;});
    spheres.forEach(s=>{s.visible=showSpheres; s.material.opacity=intF*0.15;});
    updateConnections();
}

function updateConnections() {
    connections.forEach(c=>scene.remove(c));
    connections=[];
    createConnections();
    connections.forEach(c=>c.visible=showConnections);
}

// ════════════════════════════════════════════════════════════
// TOGGLE HELPERS
// ════════════════════════════════════════════════════════════
function toggleArrows()      { showArrows=!showArrows;      arrows.forEach(a=>a.visible=showArrows);      document.getElementById('show_arrows').classList.toggle('active'); }
function toggleSpheres()     { showSpheres=!showSpheres;    spheres.forEach(s=>s.visible=showSpheres);    document.getElementById('show_spheres').classList.toggle('active'); }
function toggleConnections() { showConnections=!showConnections; connections.forEach(c=>c.visible=showConnections); document.getElementById('show_connections').classList.toggle('active'); }
function toggleLabels()      { showLabels=!showLabels;      labels.forEach(l=>l.visible=showLabels);      document.getElementById('show_labels').classList.toggle('active'); }

// ════════════════════════════════════════════════════════════
// ANIMATION
// ════════════════════════════════════════════════════════════
function toggleAnimation() {
    isAnimating=!isAnimating;
    document.getElementById('anim_text').textContent = isAnimating ? '⏸ Pause' : '▶ Start Animation';
    if (isAnimating) runAnim();
}

function runAnim() {
    if (!isAnimating) return;
    const tsl = document.getElementById('time');
    const csl = document.getElementById('convergence');
    let tv=parseFloat(tsl.value), cv=parseFloat(csl.value);
    if (tv<36) {
        tv+=0.5; tsl.value=tv;
        cv=Math.min(90,cv+1); csl.value=cv;
        updateParams();
        setTimeout(runAnim,100);
    } else {
        isAnimating=false;
        document.getElementById('anim_text').textContent='▶ Start Animation';
    }
}

function resetView() {
    camera.position.set(25,20,25);
    camera.lookAt(0,0,0);
    ['external_pressure','internal_forces','convergence','time'].forEach((id,i)=>{
        document.getElementById(id).value=[70,60,45,0][i];
    });
    updateParams();
    clearFocus();
    document.getElementById('focusSelect').value='';
}

// ════════════════════════════════════════════════════════════
// RENDER LOOP
// ════════════════════════════════════════════════════════════
function animate() {
    requestAnimationFrame(animate);
    if (!isAnimating && !focusedId) {
        const t = Date.now()*0.0001;
        camera.position.x = Math.sin(t)*30;
        camera.position.z = Math.cos(t)*30;
        camera.lookAt(0,0,0);
    }
    // Pulse stressed nodes continuously
    if (liveData.tension > 0.6) {
        const stressIds = [liveData.actorA, liveData.actorB].filter(Boolean);
        nodes.forEach(n=>{
            if (stressIds.includes(n.country.id) || stressIds.includes(n.country.fullName)) {
                if (!focusedId || focusedId!==n.country.id)
                    n.mesh.material.emissiveIntensity = 0.45 + 0.35*Math.abs(Math.sin(Date.now()*0.003));
            }
        });
    }
    renderer.render(scene,camera);
}

window.addEventListener('load', init);
window.addEventListener('resize', ()=>{
    const cv = document.getElementById('mainCanvas');
    if (camera&&renderer) {
        camera.aspect = cv.clientWidth/cv.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(cv.clientWidth, cv.clientHeight);
    }
});
</script>
</body>
</html>
"""

# Display the visualization
components.html(html_code, height=900, scrolling=False)

# =============================================================================
# INFLUENCE ANALYSIS SECTION  (Live Stress Bridge + Per-Country Drill-Down)
# =============================================================================

st.markdown("---")
st.header("📊 Influence Analysis & Stress-Test Interpretation")

# ─── LIVE STRESS-TEST DATA BRIDGE ───────────────────────────────────────────
st.subheader("⚡ Live Stress-Test State")
st.caption("This panel mirrors the current simulation round so you can interpret what the 3D map is showing in real time.")

col_a, col_b, col_c, col_d, col_e = st.columns(5)
trace = st.session_state.get("round_metrics_trace", [])
adj   = st.session_state.get("adjudication", {}) or {}
rnd   = st.session_state.get("round", "—")
actA  = st.session_state.get("selected_country_a", "—")
actB  = st.session_state.get("selected_country_b", "—")
align = st.session_state.get("alignment_score")
reward_val = trace[-1]["reward"]  if trace else None
risk_val   = trace[-1]["risk"]    if trace else None
tension    = adj.get("tension_index")
confidence = adj.get("confidence_score")

with col_a: st.metric("Round", rnd)
with col_b: st.metric("Actors", f"{actA} vs {actB}")
with col_c: st.metric("Reward", f"{reward_val*100:.1f}%" if reward_val is not None else "—")
with col_d:
    if tension is not None:
        color = "🔴" if tension>0.7 else ("🟡" if tension>0.4 else "🟢")
        st.metric("Tension", f"{color} {tension*100:.1f}%")
    else:
        st.metric("Tension", "—")
with col_e: st.metric("Alignment", f"{align*100:.0f}%" if align is not None else "—")

if trace:
    import plotly.graph_objects as go
    rounds = [t["round"] for t in trace]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=rounds, y=[t["reward"]*100  for t in trace], name="Reward",    line=dict(color="#10b981", width=2)))
    fig.add_trace(go.Scatter(x=rounds, y=[t["risk"]*100    for t in trace], name="Risk",      line=dict(color="#ef4444", width=2)))
    fig.add_trace(go.Scatter(x=rounds, y=[t["tension"]*100 for t in trace], name="Tension",   line=dict(color="#f97316", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=rounds, y=[t["alignment"]*100 for t in trace], name="Alignment", line=dict(color="#818cf8", width=2, dash="dash")))
    fig.update_layout(
        title="Stress-Test Metrics Trace",
        xaxis_title="Round", yaxis_title="%",
        template="plotly_dark", height=280,
        margin=dict(l=30,r=20,t=40,b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ─── WHAT THE MAP ELEMENTS MEAN ─────────────────────────────────────────────
with st.expander("📖 Interpreting the Influence Map — Policy Pressures, Alignments & Cultural Forces", expanded=False):
    st.markdown("""
    ### 🔵 Policy Pressures (Blue/Coloured Arrows)
    Each arrow enters a country node from the **global policy origin point** (centre of the scene).
    The arrow colour, thickness and opacity reflect the **pressure strength** and current **external pressure slider**.

    | Arrow | Type | Meaning in the Map |
    |---|---|---|
    | **GDPR** | Regulation | Forces EU-standard data governance on targeted states |
    | **US Export Controls** | Policy | Restricts dual-use tech; creates governance isolation for targets |
    | **Belt & Road** | Economic | Creates economic dependency → soft governance alignment toward China |
    | **AUKUS** | Alliance | Deep defence-tech integration; pulls Japan/UK/US into joint posture |
    | **UN AI Ethics** | Norm | Legitimacy pressure toward inclusive, rights-based frameworks |
    | **NATO Expansion** | Alliance | Security alignment pulls EE states toward Western governance cluster |
    | **Conflict Zone** | Crisis | Distorts normal policy trajectories; elevates military spend weighting |

    **When you stress-test a policy move**, the tension and reward outputs tell you how much that move is amplifying or dampening these pressures for your two chosen actors.

    ### 🟣 Cultural Forces (Wireframe Spheres)
    Each translucent sphere around a node represents a **cultural/structural force** shaping that country's governance baseline.
    The sphere opacity tracks the **internal forces slider**.

    | Sphere | Meaning |
    |---|---|
    | **Democratic Norms** | Baseline bias toward transparency, rights, multilateral frameworks |
    | **Tech Nationalism** | Drives domestic AI stacks, data localisation, export-control logic |
    | **Post-Colonial Sovereignty** | Resistance to external norm-setting; preference for pluralism |
    | **Energy Wealth** | Resource leverage shapes negotiating posture and AI investment capacity |
    | **Military-Tech Integration** | Fuses national security and AI R&D; elevates dual-use risk |
    | **NeutralHub** | Mediator/compliance posture; avoids bloc alignment |

    ### 🔗 Alignment Connections (Lines)
    Lines connect nodes within **spatial proximity** in 3D space (distance < 12 units). Closer = more similar governance posture.
    Line opacity reflects similarity strength. During animation, convergence pulls all nodes toward centre — watch which
    countries *resist* convergence (they have strong cultural forces) vs which ones *conform quickly*.

    ### 📊 Node Properties
    - **Size** = Influence score (0–1 scale)
    - **Colour** = Alignment cluster: 🔵 Western · 🔴 State-controlled · 🟡 Hybrid · 🟢 Regional/Developing
    - **Orange pulse** = Country is currently an active stress-test actor
    - **Click any node** = Opens full drill-down in the Country Focus panel
    """)

st.markdown("---")

# ─── PER-COUNTRY DRILL-DOWN TABLE ───────────────────────────────────────────
st.subheader("🔬 Per-Country Influence Breakdown")

EXTERNAL_INFLUENCES_PY = {
    "GDPR":                {"type":"regulation", "strength":0.90, "targets":["European Union","United Kingdom","Brazil","Belgium","Denmark","Norway","Switzerland","Poland"]},
    "US Export Controls":  {"type":"policy",     "strength":0.85, "targets":["China","Russia","Iraq","Serbia"]},
    "Belt & Road":         {"type":"economic",   "strength":0.75, "targets":["Brazil","Qatar","Dubai","Argentina","Serbia"]},
    "AUKUS":               {"type":"alliance",   "strength":0.80, "targets":["United States","United Kingdom","Japan"]},
    "UN AI Ethics":        {"type":"norm",       "strength":0.60, "targets":["India","Brazil","NATO","Global South","Paraguay"]},
    "NATO Expansion":      {"type":"alliance",   "strength":0.88, "targets":["Ukraine","Poland","Norway","Denmark","Belgium"]},
    "Conflict Zone":       {"type":"crisis",     "strength":0.82, "targets":["Ukraine","Israel","Iraq"]},
}
INTERNAL_INFLUENCES_PY = {
    "Democratic Norms":        {"strength":0.85, "countries":["United States","European Union","United Kingdom","Japan","India","Brazil","Belgium","Denmark","Norway","Switzerland","Poland","Ukraine"]},
    "Tech Nationalism":        {"strength":0.90, "countries":["China","Russia","United States","Israel"]},
    "Post-Colonial Sovereignty":{"strength":0.70,"countries":["India","Brazil","Iraq","Qatar","Paraguay","Argentina","Global South"]},
    "Energy Wealth":           {"strength":0.75, "countries":["Russia","Qatar","Dubai","Venezuela","Norway"]},
    "Military-Tech Integration":{"strength":0.80,"countries":["United States","China","Russia","NATO","Israel","Ukraine","Poland"]},
    "NeutralHub":              {"strength":0.65, "countries":["Switzerland","Serbia"]},
}

country_selector = st.selectbox(
    "🔍 Select a country for detailed pressure/alignment breakdown:",
    ["— All countries —"] + list(default_data.keys())
)

influence_rows = []
for cname, cdata in default_data.items():
    ext_pressures = [(pname, pdata["strength"]) for pname, pdata in EXTERNAL_INFLUENCES_PY.items() if cname in pdata["targets"]]
    int_forces    = [(fname, fdata["strength"]) for fname, fdata in INTERNAL_INFLUENCES_PY.items() if cname in fdata["countries"]]
    total_ext_strength = sum(s for _,s in ext_pressures)
    total_int_strength = sum(s for _,s in int_forces)
    influence_rows.append({
        "Country":              cname,
        "GDP ($T)":             f"${cdata['gdp']:.3f}",
        "Influence Score":      f"{cdata['influence']*100:.0f}%",
        "Military Exp":         f"{cdata['mil_exp']:.1f}%",
        "Internet":             f"{cdata['internet']:.0f}%",
        "Ext Pressures":        ", ".join(f"{n} ({s:.0%})" for n,s in ext_pressures) or "None",
        "Ext Pressure Total":   f"{total_ext_strength:.2f}",
        "Cultural Forces":      ", ".join(f"{n}" for n,_ in int_forces) or "None",
        "Int Force Total":      f"{total_int_strength:.2f}",
        "Governance Cluster":   cdata["cultural_alignment"],
        "Policy Position":      cdata["position"],
    })

df_all = pd.DataFrame(influence_rows).sort_values("Ext Pressure Total", ascending=False)

if country_selector != "— All countries —":
    df_show = df_all[df_all["Country"] == country_selector]
    # Full detail card for selected country
    row = df_show.iloc[0] if not df_show.empty else None
    if row is not None:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Policy Position**")
            st.info(row["Policy Position"])
        with c2:
            st.markdown(f"**External Policy Pressures**")
            for pname, pstr in [(p, d["strength"]) for p,d in EXTERNAL_INFLUENCES_PY.items() if country_selector in d["targets"]]:
                bar = "█" * int(pstr*10) + "░" * (10-int(pstr*10))
                clr = "🔴" if pstr>0.8 else ("🟡" if pstr>0.6 else "🟢")
                st.markdown(f"{clr} **{pname}** `{bar}` {pstr:.0%}")
        with c3:
            st.markdown(f"**Cultural Forces**")
            for fname, fstr in [(f, d["strength"]) for f,d in INTERNAL_INFLUENCES_PY.items() if country_selector in d["countries"]]:
                bar = "█" * int(fstr*10) + "░" * (10-int(fstr*10))
                clr = "🟣" if fstr>0.8 else ("🔵" if fstr>0.65 else "⚪")
                st.markdown(f"{clr} **{fname}** `{bar}` {fstr:.0%}")
        st.markdown("---")
    st.dataframe(df_show, use_container_width=True, hide_index=True)
else:
    st.dataframe(df_all, use_container_width=True, hide_index=True)

st.download_button(
    label="📥 Download Full Influence Data (CSV)",
    data=df_all.to_csv(index=False),
    file_name="auracelle_influence_map_data.csv",
    mime="text/csv"
)

if trace:
    st.markdown("---")
    st.subheader("📋 Round-by-Round Stress Log")
    df_trace = pd.DataFrame(trace)
    df_trace["reward"]     = df_trace["reward"].apply(lambda x: f"{x*100:.1f}%")
    df_trace["risk"]       = df_trace["risk"].apply(lambda x: f"{x*100:.1f}%")
    df_trace["tension"]    = df_trace["tension"].apply(lambda x: f"{x*100:.1f}%")
    df_trace["confidence"] = df_trace["confidence"].apply(lambda x: f"{x*100:.1f}%")
    df_trace["alignment"]  = df_trace["alignment"].apply(lambda x: f"{x*100:.0f}%")
    st.dataframe(df_trace, use_container_width=True, hide_index=True)
    st.download_button(
        label="📥 Download Round Log (CSV)",
        data=pd.DataFrame(trace).to_csv(index=False),
        file_name="auracelle_stress_round_log.csv",
        mime="text/csv"
    )

st.markdown("---")
st.info("💡 **Tip**: Maximize the 3D viewer (⛶ button), select a country in the left panel, then run a stress-test round — the map will pulse the active actors and update the Country Focus card in real time.")

