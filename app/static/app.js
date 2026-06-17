"use strict";
// ── JLL Bid Copilot — full interactive enterprise dashboard ──

// ═══════════════ DEMO DATA ══════════════════════════════════
const DEMO_CLIENT = {
  client_name: "ABC Tech Pvt. Ltd.",
  stage: "PROPOSAL_DRAFTING",
  requirements: {
    transaction_type: "lease", property_type: "office",
    locations: ["Bengaluru ORR", "Whitefield"],
    budget: { min_amount: 130, max_amount: 150, currency: "INR", basis: "per_sqft" },
    timeline: { target_date: "2026-09-30", flexibility: "flexible" },
    seats: 250, lease_term_months: 60,
    must_have_facilities: ["Parking", "Pantry", "Power Backup", "24/7 Security"],
    nice_to_have_facilities: ["Conference Rooms", "Gym", "Cafeteria"],
    industry: "IT / ITES",
  },
};

const DEMO_PROPERTIES = [
  { id:"P-BLR-01", name:"Prestige Tech Park", sublocation:"whitefield", location:"Whitefield, Bengaluru", rent:138, size:50000, seats:280, availability:"Jul 2026", availDate:"2026-07-01", fit:92, grade:"A+", landlord:"Prestige Group", yearBuilt:2019, totalFloors:12, highlight:true, color:"linear-gradient(135deg,#1e3a5f,#2d6a9f)", amenities:["Parking","24/7 Security","Power Backup","Pantry","Conference Rooms","Gym","Cafeteria"], matchReasons:["Rent ₹138 is within ₹130–₹150 budget","280 seats exceeds 250-seat requirement (12% headroom)","All 4 must-have facilities available","Available Jul 2026 — on schedule for Q3 target"] },
  { id:"P-BLR-02", name:"Embassy Manyata Business Park", sublocation:"orr", location:"Outer Ring Road, Bengaluru", rent:143, size:60000, seats:340, availability:"Aug 2026", availDate:"2026-08-01", fit:88, grade:"A+", landlord:"Embassy Group", yearBuilt:2017, totalFloors:10, highlight:false, color:"linear-gradient(135deg,#1a3a4f,#1a6f8a)", amenities:["Parking","24/7 Security","Power Backup","Pantry","Conference Rooms","ATM","Food Court"], matchReasons:["Large 60,000 sqft plate accommodates growth","340 seats — 36% buffer above requirement","Tier-1 campus with Metro connectivity","Slightly higher rent (₹143) within budget"] },
  { id:"P-BLR-03", name:"RMZ Ecoworld", sublocation:"bellandur", location:"Bellandur, Bengaluru", rent:135, size:45000, seats:255, availability:"Jun 2026", availDate:"2026-06-01", fit:85, grade:"A", landlord:"RMZ Corp", yearBuilt:2016, totalFloors:9, highlight:false, color:"linear-gradient(135deg,#2d1f47,#5a3d8a)", amenities:["Parking","24/7 Security","Power Backup","Pantry","Gym","Creche"], matchReasons:["Lowest rent in shortlist at ₹135 — best cost efficiency","Earliest availability (Jun 2026)","LEED Gold green-certified building","Slightly smaller (45,000 sqft) — limited expansion room"] },
  { id:"P-BLR-04", name:"Bagmane Tech Park", sublocation:"orr", location:"CV Raman Nagar, Bengaluru", rent:128, size:55000, seats:310, availability:"Sep 2026", availDate:"2026-09-01", fit:78, grade:"A", landlord:"Bagmane Group", yearBuilt:2014, totalFloors:8, highlight:false, color:"linear-gradient(135deg,#1b4332,#2d6a4f)", amenities:["Parking","24/7 Security","Power Backup","Food Court","ATM"], matchReasons:["Best value at ₹128/sq.ft — 14.7% below budget ceiling","310 seats — substantial growth headroom","Pantry not available — client must-have gap","Sep 2026 availability on the edge of Q3 target"] },
  { id:"P-BLR-05", name:"Brigade Tech Garden", sublocation:"whitefield", location:"Whitefield, Bengaluru", rent:141, size:48000, seats:270, availability:"Oct 2026", availDate:"2026-10-01", fit:74, grade:"A", landlord:"Brigade Group", yearBuilt:2020, totalFloors:14, highlight:false, color:"linear-gradient(135deg,#4a1942,#8b2fc9)", amenities:["Parking","24/7 Security","Power Backup","Pantry","Conference Rooms"], matchReasons:["Newest building in shortlist (2020)","Good conference room capacity","Availability Oct 2026 — misses Q3 timeline","No gym or food court — lower amenity score"] },
];

const DEMO_COMPETITORS = [
  { id:"cbre",      name:"CBRE",                   rent:145, strengths:"Strong market coverage",      risk:"high",   details:"CBRE is the incumbent broker in the ORR submarket with 3 active Grade A listings. Typically offer 2–3 month rent-free + higher TI allowances (₹500/sqft).",                                   weakness:"Higher headline rent (₹145 vs JLL ₹138–₹145). No integrated FM — client must source separately, adding coordination overhead." },
  { id:"colliers",  name:"Colliers",                rent:140, strengths:"Flexible lease terms",        risk:"medium", details:"Colliers targets IT companies with headcount uncertainty — offers 3+3 year lock-in vs standard 5-year. Won a 45,000 sqft deal in Whitefield at ₹138 recently.",                       weakness:"Smaller Bengaluru property network. No FM integration — client must manage FM separately." },
  { id:"knightfrank",name:"Knight Frank",           rent:148, strengths:"Premium properties & advisory",risk:"low",   details:"Knight Frank focuses on premium deals above ₹145/sqft with Grade A+ landlords. Less competitive in the ₹130–₹150 segment. Typically targets deals above 100,000 sqft.",            weakness:"Highest quoted rent (₹148) — above budget ceiling. Less likely to match on price. No FM offering." },
  { id:"cwakefield",name:"Cushman & Wakefield",     rent:146, strengths:"Strong FM capabilities",     risk:"medium", details:"C&W is the nearest competitor on FM. They sometimes subsidize FM pricing to win the leasing deal. Recent deal in Manyata: ₹142 rent + FM at ₹2.8L/month.",                            weakness:"FM offered as separate contract — client has two vendors vs JLL's single integrated model. FM pricing typically 10–15% above market." },
];

const DEMO_FM_SERVICES = [
  { id:"pantry",     name:"Pantry Management",      amt:120000, ico:"☕", bg:"#fff3e0", color:"#f57c00", checked:true },
  { id:"stationery", name:"Stationery & Supplies",  amt:40000,  ico:"✎", bg:"#e8f5e9", color:"#388e3c", checked:true },
  { id:"washroom",   name:"Washroom Services",      amt:60000,  ico:"⬥", bg:"#e3f2fd", color:"#1976d2", checked:true },
  { id:"electrical", name:"Electrical Maintenance", amt:75000,  ico:"⚡", bg:"#fffde7", color:"#f9a825", checked:true },
  { id:"plumbing",   name:"Plumbing Services",      amt:50000,  ico:"⚙", bg:"#f3e5f5", color:"#7b1fa2", checked:true },
  { id:"generalops", name:"General Ops Support",    amt:100000, ico:"👥", bg:"#fce4ec", color:"#c62828", checked:true },
];

const WORKFLOW_STORIES = [
  { ico:"📋", title:"Step 1 — Requirement Intake",      text:"AI Copilot ingested ABC Tech's requirements: 250 seats in Bengaluru ORR/Whitefield, ₹130–₹150/sq.ft budget, 5-year lease, Q3 2026 move-in. Key parameters (seating, budget, zoning, facilities) were validated. The agent flagged that must-have facilities (Parking, Pantry, Power Backup, 24/7 Security) would filter the shortlist aggressively." },
  { ico:"🔍", title:"Step 2 — Property Shortlisting",   text:"Agent searched the property inventory across Bengaluru ORR and Whitefield. From 23 available properties, 5 were shortlisted. Prestige Tech Park emerged as the top match with a 92% fit score — within budget at ₹138/sq.ft, 280 seats, all facilities, Jul 2026 availability. Bagmane was flagged as missing Pantry (must-have gap)." },
  { ico:"📊", title:"Step 3 — Market & Competitor Analysis", text:"Avg. Bengaluru market rent: ₹142/sq.ft. JLL's bid range of ₹138–₹145 is at or below market. CBRE (₹145) is flagged as highest risk — they are the incumbent in ORR. Cushman & Wakefield (₹146) is the nearest FM competitor. Recommendation: lead with integrated FM bundling as the JLL differentiator." },
  { ico:"📄", title:"Step 4 — Proposal Drafting",       text:"Agent drafted a comprehensive bid proposal for Prestige Tech Park at ₹138/sq.ft. Includes: executive summary, property fit analysis, competitive positioning, JLL vs competitor comparison, 5-year total cost of occupancy (₹8.28 Cr/yr lease + ₹4.45L/mo FM = ₹13.62 Cr/yr integrated). Pending human approval before going client-ready." },
  { ico:"🤝", title:"Step 5 — Negotiation",             text:"Agent prepared negotiation talking points: (1) ₹138 is 2.8% below market average — defend as fair. (2) Offer 2-month rent-free concession rather than reducing headline rent. (3) JLL FM integration saves client ₹6–8L/year vs separate vendors. (4) If CBRE counters on TI allowance, JLL's FM bundle creates equivalent first-year savings." },
  { ico:"🏆", title:"Step 6 — Win / Loss",              text:"If Won: Agent closes out the opportunity, logs with FM bundle attached, sets 90-day client check-in. If Lost: Agent immediately pivots to FM Upsell — regardless of who wins the lease, ABC Tech still needs facility management. Standalone FM pitch at ₹4.45L/mo is prepared for immediate outreach." },
  { ico:"⚡", title:"Step 7 — FM Upsell",              text:"Win or not, JLL finds revenue. If the lease was lost, the agent drafts: 'Wherever you land, JLL can run your facility.' FM bundle (Pantry + Washroom + Electrical + Plumbing + General Ops + Stationery = ₹4,45,000/month, ₹53.4L/year) positioned independently of landlord relationship. Secondary revenue stream even on lost bids." },
];

// ═══════════════ DEMO WORKFLOW STEPS ════════════════════════
const DEMO_STEPS = [
  { pct:8,  label:"Creating new bid...",
    log:["🎯 <span class='demo-log-thinking'>Initializing new opportunity: ABC Tech Pvt Ltd</span>","→ opportunity_id: OPP-2026-0089 created","→ stage: INTAKE | owner: Neha Sharma"],
    output:`<div class="demo-output-card"><div class="demo-output-card-title">📁 New Opportunity Created</div><div class="demo-output-row"><span>Opportunity ID</span><span>OPP-2026-0089</span></div><div class="demo-output-row"><span>Client</span><span class="demo-output-highlight">ABC Tech Pvt Ltd</span></div><div class="demo-output-row"><span>Stage</span><span>INTAKE</span></div><div class="demo-output-row"><span>Owner</span><span>Neha Sharma</span></div></div>` },
  { pct:20, label:"Extracting requirements...",
    log:["📋 <span class='demo-log-tool'>TOOL CALL: get_opportunity_state</span>","→ Parsing client requirements from conversation...","→ Extracted: 250 seats, Bengaluru ORR/Whitefield","→ Budget: ₹130–₹150/sqft (All Inclusive)","→ Lease: 5 years | Timeline: Q3 2026","→ Must-haves: Parking, Pantry, Power Backup, 24/7 Security"],
    output:`<div class="demo-output-card"><div class="demo-output-card-title">📋 Requirements Extracted</div><div class="demo-output-row"><span>Location</span><span>Bengaluru ORR / Whitefield</span></div><div class="demo-output-row"><span>Seats</span><span class="demo-output-highlight">250 seats</span></div><div class="demo-output-row"><span>Budget</span><span>₹130–₹150/sqft</span></div><div class="demo-output-row"><span>Lease Term</span><span>5 Years (60 months)</span></div><div class="demo-output-row"><span>Move-in</span><span>Q3 2026</span></div><div class="demo-output-row"><span>Must-Haves</span><span style="color:#f59e0b">4 facilities flagged</span></div></div>` },
  { pct:33, label:"Searching property inventory...",
    log:["🔍 <span class='demo-log-tool'>TOOL CALL: search_properties</span>","→ params: { locations: ['Bengaluru ORR', 'Whitefield'], budget_max: 150, seats_min: 250 }","→ Searching 847 properties in inventory...","→ Pre-filter applied: availability ≤ Q3 2026","→ Found <span class='demo-output-highlight'>23 candidate properties</span>","→ Applying must-have facility filters...","→ Narrowed to 5 qualifying properties"],
    output:`<div class="demo-output-card"><div class="demo-output-card-title">🔍 Property Search Results</div><div class="demo-output-row"><span>Total inventory checked</span><span>847 properties</span></div><div class="demo-output-row"><span>After location filter</span><span>67 properties</span></div><div class="demo-output-row"><span>After budget filter</span><span>23 properties</span></div><div class="demo-output-row"><span>After facility filter</span><span class="demo-output-highlight">5 shortlisted</span></div></div>` },
  { pct:45, label:"Scoring shortlisted properties...",
    log:["🏆 <span class='demo-log-tool'>TOOL CALL: score_shortlist</span>","→ Applying 8 scoring dimensions:","  • Budget fit (weight: 0.25) ✓","  • Location match (weight: 0.20) ✓","  • Facility coverage (weight: 0.20) ✓","  • Timeline availability (weight: 0.15) ✓","  • Seat headroom (weight: 0.10) ✓","  • Grade & quality (weight: 0.05) ✓","  • Expansion potential (weight: 0.05) ✓","→ Top match: Prestige Tech Park → <span class='demo-output-highlight'>Fit Score: 92%</span>"],
    output:`<div class="demo-output-card"><div class="demo-output-card-title">🏆 Shortlist Scored</div><div class="demo-output-row"><span>Prestige Tech Park</span><span class="demo-output-highlight">92% ★ TOP PICK</span></div><div class="demo-output-row"><span>Embassy Manyata BP</span><span>88%</span></div><div class="demo-output-row"><span>RMZ Ecoworld</span><span>85%</span></div><div class="demo-output-row"><span>Bagmane Tech Park</span><span style="color:#f59e0b">78% ⚠ Pantry gap</span></div><div class="demo-output-row"><span>Brigade Tech Garden</span><span>74%</span></div></div>` },
  { pct:55, label:"Fetching market benchmarks...",
    log:["📊 <span class='demo-log-tool'>TOOL CALL: get_market_benchmark</span>","→ params: { location: 'Bengaluru ORR', property_type: 'commercial_office' }","→ Q1 2025 market data loaded:","  • Avg. rent: ₹142/sqft (All Inclusive)","  • Vacancy rate: 17.2%","  • YoY rent growth: +4.8%","  • Supply next 12 months: 26.5 Mn sqft"],
    output:`<div class="demo-output-card"><div class="demo-output-card-title">📊 Market Benchmark — Bengaluru ORR</div><div class="demo-output-row"><span>Avg. Market Rent</span><span class="demo-output-highlight">₹142/sqft (All Incl.)</span></div><div class="demo-output-row"><span>JLL Bid (Prestige)</span><span style="color:#10b981">₹138 → 2.8% below market</span></div><div class="demo-output-row"><span>Vacancy Rate</span><span>17.2%</span></div><div class="demo-output-row"><span>Rent Growth YoY</span><span>+4.8%</span></div></div>` },
  { pct:65, label:"Analysing competitor intelligence...",
    log:["🕵️ <span class='demo-log-tool'>TOOL CALL: get_competitor_intel</span>","→ Fetching active competitor bids for ORR/Whitefield...","→ CBRE: ₹145/sqft | Risk: HIGH (incumbent, ORR stronghold)","→ Colliers: ₹140/sqft | Risk: MEDIUM (flex lease pitch)","→ Knight Frank: ₹148/sqft | Risk: LOW (premium segment)","→ C&W: ₹146/sqft | Risk: MEDIUM (partial FM capability)","→ JLL advantage: 2.8–7% below all competitors","→ Differentiator: <span class='demo-output-highlight'>Integrated FM bundle</span>"],
    output:`<div class="demo-output-card"><div class="demo-output-card-title">🕵️ Competitor Analysis</div><div class="demo-output-row"><span>CBRE</span><span style="color:#ef4444">₹145 — HIGH RISK</span></div><div class="demo-output-row"><span>Cushman & Wakefield</span><span style="color:#f59e0b">₹146 — MEDIUM</span></div><div class="demo-output-row"><span>Colliers</span><span style="color:#f59e0b">₹140 — MEDIUM</span></div><div class="demo-output-row"><span>Knight Frank</span><span style="color:#10b981">₹148 — LOW</span></div><div class="demo-output-row"><span>JLL Bid</span><span class="demo-output-highlight">₹138 — BEST VALUE</span></div></div>` },
  { pct:76, label:"Drafting bid proposal...",
    log:["📄 <span class='demo-log-tool'>TOOL CALL: save_draft_artifact</span>","→ artifact_type: BID_PROPOSAL","→ Generating executive summary...","→ Appending property fit analysis...","→ Building competitive positioning table...","→ Calculating 5-year TCO:","  • Lease: ₹8.28 Cr/year","  • FM Bundle: ₹4.45L/month (₹5.34 Cr/year)","  • Total TCO: ₹13.62 Cr/year integrated","→ Draft saved — status: PENDING_APPROVAL"],
    output:`<div class="demo-output-card"><div class="demo-output-card-title">📄 Bid Proposal Draft</div><div class="demo-output-row"><span>Property</span><span>Prestige Tech Park</span></div><div class="demo-output-row"><span>Rent Quote</span><span class="demo-output-highlight">₹138/sqft</span></div><div class="demo-output-row"><span>Annual Lease</span><span>₹8.28 Cr/year</span></div><div class="demo-output-row"><span>FM Bundle</span><span>₹4.45L/month</span></div><div class="demo-output-row"><span>5-Year TCO</span><span class="demo-output-highlight">₹68.1 Cr integrated</span></div><div class="demo-output-row"><span>Win Probability</span><span style="color:#10b981">73%</span></div></div>` },
  { pct:86, label:"Requesting human approval...",
    log:["✅ <span class='demo-log-tool'>TOOL CALL: request_human_approval</span>","→ artifact_id: BID_PROPOSAL_OPP-2026-0089","→ reviewer: Neha Sharma (Bid Manager)","→ summary: 'Prestige Tech Park @ ₹138/sqft — 92% fit'","→ Status: PENDING_APPROVAL","→ <span class='demo-log-thinking'>⏸ Workflow paused — awaiting human decision</span>","→ Approval button now active in UI"],
    output:`<div class="demo-output-card" style="border-color:rgba(245,158,11,.4)"><div class="demo-output-card-title">✅ Approval Required</div><div class="demo-output-row"><span>Approver</span><span>Neha Sharma</span></div><div class="demo-output-row"><span>Artifact</span><span>Bid Proposal — ABC Tech</span></div><div class="demo-output-row"><span>Status</span><span style="color:#f59e0b">⏸ Pending Review</span></div><div style="margin-top:10px;font-size:11px;color:#64748b">Nothing is sent to the client until you approve. The agent waits here.</div></div>` },
  { pct:93, label:"FM upsell pitch ready...",
    log:["💡 <span class='demo-log-tool'>TOOL CALL: get_fm_catalog</span>","→ Selecting FM services for 250-seat office...","→ Bundle: Pantry + Washroom + Electrical + Plumbing + General Ops + Stationery","→ Total: ₹4,45,000/month","→ Annual FM commitment: ₹53.4L/year","→ <span class='demo-log-thinking'>If lease is lost → FM-only pitch auto-prepared</span>","→ FM pitch template: 'Wherever you land, JLL runs the facility'"],
    output:`<div class="demo-output-card"><div class="demo-output-card-title">💡 FM Services Bundle</div><div class="demo-output-row"><span>Pantry Management</span><span>₹1,20,000</span></div><div class="demo-output-row"><span>Washroom Services</span><span>₹60,000</span></div><div class="demo-output-row"><span>Electrical</span><span>₹75,000</span></div><div class="demo-output-row"><span>Plumbing</span><span>₹50,000</span></div><div class="demo-output-row"><span>General Ops</span><span>₹1,00,000</span></div><div class="demo-output-row"><span>Stationery</span><span>₹40,000</span></div><div class="demo-output-row" style="border-top:1px solid rgba(255,255,255,.1);margin-top:6px;padding-top:6px"><span><strong>Monthly FM Total</strong></span><span class="demo-output-highlight">₹4,45,000</span></div></div>` },
  { pct:100, label:"✓ Demo complete — bid ready for approval",
    log:["🎉 <span class='demo-log-thinking'>Workflow complete!</span>","→ <span class='demo-log-tool'>TOOL CALL: log_pipeline_event</span>","→ event: PROPOSAL_READY","→ stage: PROPOSAL_DRAFTING → NEGOTIATION (pending approval)","→ Opportunity fully processed in 10 steps","→ Ready for: Neha Sharma to review and approve"],
    output:`<div class="demo-output-card" style="border-color:rgba(16,185,129,.4)"><div class="demo-output-card-title" style="color:#10b981">🎉 Bid Ready — Summary</div><div class="demo-output-row"><span>Client</span><span>ABC Tech Pvt Ltd</span></div><div class="demo-output-row"><span>Recommendation</span><span class="demo-output-highlight">Prestige Tech Park</span></div><div class="demo-output-row"><span>JLL Quote</span><span>₹138/sqft</span></div><div class="demo-output-row"><span>Vs Market Avg</span><span style="color:#10b981">2.8% below</span></div><div class="demo-output-row"><span>Win Probability</span><span style="color:#10b981">73%</span></div><div class="demo-output-row"><span>FM Revenue</span><span style="color:#10b981">₹4,45,000/month</span></div><div class="demo-output-row"><span>Next Action</span><span style="color:#f59e0b">Approve Proposal →</span></div></div>` },
];

// ═══════════════ VIEW CONFIG ═════════════════════════════════
const VIEW_CONFIG = {
  "copilot":         { title:"JLL Bid Copilot",    sub:"AI-Powered Bidding & Office Leasing Assistant" },
  "dashboard":       { title:"Dashboard",          sub:"Performance Overview & Activity Summary" },
  "opportunities":   { title:"Opportunities",      sub:"Active Bid Pipeline — 12 opportunities" },
  "requirements":    { title:"Requirements",       sub:"Client Requirement Management" },
  "property-search": { title:"Property Search",    sub:"Available Inventory — Bengaluru" },
  "comparisons":     { title:"Comparisons",        sub:"Property & Competitor Comparison Matrix" },
  "proposals":       { title:"Proposals",          sub:"Draft & Submitted Proposals" },
  "negotiations":    { title:"Negotiations",       sub:"Active Negotiation Strategy" },
  "fm-services":     { title:"FM Services",        sub:"Facility Management Catalog & Bundles" },
  "winloss":         { title:"Win / Loss",         sub:"Deal Outcome Analysis & FM Upsell Tracking" },
  "pipeline":        { title:"Pipeline",           sub:"Revenue Funnel — FY 2026" },
  "reports":         { title:"Reports",            sub:"Management Reports — Q2 FY2026" },
  "knowledge":       { title:"Knowledge Center",   sub:"Market Data, Templates & Past Deals" },
};

// ═══════════════ STATE ════════════════════════════════════════
let activeId = null;
let isDemoMode = false;
let currentProperties = [...DEMO_PROPERTIES];
let currentView = "copilot";
let demoRunning = false;
let demoTimer = null;
let nbCurrentStep = 1;

// ═══════════════ DOM ══════════════════════════════════════════
const $ = id => document.getElementById(id);
const toast = (msg) => {
  const el = document.createElement("div");
  el.className = "toast"; el.textContent = msg;
  $("toastContainer").appendChild(el);
  setTimeout(() => el.remove(), 3200);
};

// ═══════════════ NAVIGATION ══════════════════════════════════
function switchView(name) {
  if (!$(`view-${name}`)) return;
  document.querySelectorAll(".view").forEach(v => v.classList.remove("view--active"));
  $(`view-${name}`).classList.add("view--active");
  document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
  const nav = document.querySelector(`[data-view="${name}"]`);
  if (nav) nav.classList.add("active");
  const cfg = VIEW_CONFIG[name] || {};
  if ($("viewTitle")) $("viewTitle").textContent = cfg.title || name;
  if ($("viewSub"))   $("viewSub").textContent   = cfg.sub   || "";
  currentView = name;
  if (name === "property-search") renderPropertyCards();
  if (name === "fm-services") renderFmServicesView();
}

document.querySelectorAll(".nav-item[data-view]").forEach(item => {
  item.addEventListener("click", () => switchView(item.dataset.view));
});

// ═══════════════ DONUT HELPER ════════════════════════════════
function donutSvg(pct, size = 44) {
  const r = 19, c = 2 * Math.PI * r;
  const dash = (pct / 100) * c, gap = c - dash, off = c / 4;
  const color = pct >= 85 ? "#10b981" : pct >= 70 ? "#f59e0b" : "#ef4444";
  const txtColor = pct >= 85 ? "#065f46" : pct >= 70 ? "#92400e" : "#991b1b";
  return `<svg viewBox="0 0 48 48" width="${size}" height="${size}">
    <circle cx="24" cy="24" r="${r}" fill="none" stroke="#e2e8f0" stroke-width="4.5"/>
    <circle cx="24" cy="24" r="${r}" fill="none" stroke="${color}" stroke-width="4.5"
      stroke-dasharray="${dash.toFixed(1)} ${gap.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}" stroke-linecap="round"/>
    <text x="24" y="28" text-anchor="middle" font-size="10" font-weight="700" fill="${txtColor}">${pct}%</text>
  </svg>`;
}

// ═══════════════ CHAT ════════════════════════════════════════
function appendMsg(role, text) {
  const greet = $("chatGreet"); if (greet) greet.style.display = "none";
  const el = document.createElement("div");
  el.className = role === "user" ? "msg-user" : role === "error" ? "msg-error" : role === "system" ? "msg-system" : "msg-agent";
  el.textContent = text;
  $("chatWin").appendChild(el);
  $("chatWin").scrollTop = $("chatWin").scrollHeight;
}
function appendThinking() {
  const greet = $("chatGreet"); if (greet) greet.style.display = "none";
  const el = document.createElement("div");
  el.className = "msg-thinking";
  el.innerHTML = `Copilot is thinking&hellip;<div class="dot-pulse"><span></span><span></span><span></span></div>`;
  $("chatWin").appendChild(el);
  $("chatWin").scrollTop = $("chatWin").scrollHeight;
  return el;
}
function appendApprovalCard(approval) {
  const greet = $("chatGreet"); if (greet) greet.style.display = "none";
  const card = document.createElement("div");
  card.className = "approval-card"; card.id = `apr-${approval.approval_id}`;
  const typeName = (approval.artifact_type || "artifact").replace(/_/g, " ");
  if (approval.status === "pending") {
    card.innerHTML = `<div class="apr-type">Approval required: ${typeName}</div><div class="apr-id">${approval.approval_id}</div>${approval.summary ? `<div style="font-size:11.5px;color:#64748b;margin-bottom:7px">${approval.summary}</div>` : ""}<div class="apr-btns"><button class="btn-approve" data-aid="${approval.approval_id}">Approve</button><button class="btn-reject" data-aid="${approval.approval_id}">Reject</button></div>`;
    card.querySelector(".btn-approve").addEventListener("click", () => decideApproval(approval.approval_id, "approve"));
    card.querySelector(".btn-reject").addEventListener("click",  () => decideApproval(approval.approval_id, "reject"));
  } else {
    const cls = approval.status === "approved" ? "apr-status-approved" : "apr-status-rejected";
    card.innerHTML = `<div class="apr-type">${typeName}</div><div class="apr-id">${approval.approval_id}</div><div class="${cls}">${approval.status.charAt(0).toUpperCase() + approval.status.slice(1)}</div>`;
  }
  $("chatWin").appendChild(card);
  $("chatWin").scrollTop = $("chatWin").scrollHeight;
}

// ═══════════════ STEPPER ════════════════════════════════════
const STEPS = [
  { label:"Requirements",  stages:["INTAKE"] },
  { label:"Shortlisting",  stages:["SHORTLISTING"] },
  { label:"Analysis",      stages:["COMPARISON"] },
  { label:"Proposal",      stages:["PROPOSAL_DRAFTING","FM_BUNDLING"] },
  { label:"Negotiation",   stages:["NEGOTIATION","OUTCOME_PENDING"] },
  { label:"Win / Loss",    stages:["WON_CLOSEOUT","LOST_FM_UPSELL"] },
  { label:"FM Upsell",     stages:["LOGGED"] },
];
function stageToStep(stage) { for (let i=0;i<STEPS.length;i++) if (STEPS[i].stages.includes(stage)) return i; return -1; }

function renderStepper(currentStage) {
  const activeIdx = currentStage ? stageToStep(currentStage) : (isDemoMode ? 3 : -1);
  const el = $("stepper"); el.innerHTML = "";
  STEPS.forEach((step, i) => {
    if (i > 0) { const conn = document.createElement("div"); conn.className = "step-conn" + (i <= activeIdx ? " step-conn--done" : ""); el.appendChild(conn); }
    const item = document.createElement("div");
    let cls = "step-item";
    if (i < activeIdx) cls += " step-item--done";
    if (i === activeIdx) cls += " step-item--active";
    item.className = cls; item.dataset.stepIdx = i;
    const dot = document.createElement("div"); dot.className = "step-dot"; dot.textContent = i < activeIdx ? "✓" : (i+1).toString();
    const label = document.createElement("div"); label.className = "step-label"; label.textContent = step.label;
    item.appendChild(dot); item.appendChild(label);
    item.addEventListener("click", () => showStepStory(i, activeIdx));
    el.appendChild(item);
  });
}
function showStepStory(idx, activeIdx) {
  if (idx > activeIdx && !isDemoMode) return;
  const story = WORKFLOW_STORIES[idx]; if (!story) return;
  $("storyIco").textContent   = story.ico;
  $("storyTitle").textContent = story.title;
  $("storyText").textContent  = story.text;
  $("storyPanel").style.display = "flex";
}

// ═══════════════ REQUIREMENTS PANEL ═════════════════════════
const REQ_META = {
  location:{ bg:"#fff3e0",ico:"📍" }, seats:{ bg:"#e8f5e9",ico:"👥" },
  budget:{ bg:"#fff3e0",ico:"💰" },   lease_term:{ bg:"#f3e5f5",ico:"📅" },
  timeline:{ bg:"#e3f2fd",ico:"🗓" }, facilities:{ bg:"#e8f5e9",ico:"✓" },
  optional:{ bg:"#f0f7ff",ico:"◎" },  industry:{ bg:"#fce4ec",ico:"🏢" },
  transaction:{ bg:"#e8eaf6",ico:"🔄" }, sqft:{ bg:"#e0f2f1",ico:"📐" },
};
function mkReqRow(type, label, value) {
  const { bg, ico } = REQ_META[type] || { bg:"#f0f0f0",ico:"•" };
  const row = document.createElement("div"); row.className = "req-row";
  row.innerHTML = `<span class="req-ico" style="background:${bg}">${ico}</span><div><div class="req-key">${label}</div><div class="req-val">${value}</div></div>`;
  return row;
}
function renderRequirements(r) {
  const panel = $("reqPanel"); if (!r) { panel.innerHTML = `<div class="placeholder-hint">Describe the client's requirements in chat to populate this panel.</div>`; return; }
  panel.innerHTML = "";
  if (r.locations?.length)            panel.appendChild(mkReqRow("location","Location",r.locations.join(" · ")));
  if (r.seats != null)                panel.appendChild(mkReqRow("seats","Seating Capacity",`${r.seats} Seats`));
  if (r.budget) { const cur=r.budget.currency==="INR"?"₹":""; const lo=r.budget.min_amount!=null?`${cur}${r.budget.min_amount}`:null; const hi=`${cur}${r.budget.max_amount}`; const basis=r.budget.basis?` / ${r.budget.basis.replace(/_/g," ")}` :""; panel.appendChild(mkReqRow("budget","Budget",lo?`${lo} – ${hi}${basis}`:`Up to ${hi}${basis}`)); }
  if (r.lease_term_months!=null) { const yrs=r.lease_term_months/12; panel.appendChild(mkReqRow("lease_term","Lease Term",Number.isInteger(yrs)?`${yrs} Year${yrs!==1?"s":""}` :`${r.lease_term_months} months`)); }
  if (r.timeline) { let t=r.timeline.target_date||""; if(r.timeline.flexibility) t+=` (${r.timeline.flexibility})`; panel.appendChild(mkReqRow("timeline","Move-in Timeline",t)); }
  if (r.must_have_facilities?.length)    panel.appendChild(mkReqRow("facilities","Must Have",r.must_have_facilities.join(", ")));
  if (r.nice_to_have_facilities?.length) panel.appendChild(mkReqRow("optional","Nice-to-Have",r.nice_to_have_facilities.join(", ")));
  if (r.industry)                        panel.appendChild(mkReqRow("industry","Industry",r.industry));
  if (r.transaction_type)               panel.appendChild(mkReqRow("transaction","Transaction",r.transaction_type==="lease"?"Lease":"Purchase"));
}

// ═══════════════ COMPETITOR TABLE ════════════════════════════
const expandedComps = new Set();
function renderCompetitors(competitors) {
  const tbody = $("compTbody"); tbody.innerHTML = "";
  competitors.forEach(comp => {
    const riskClass = `risk-${comp.risk}`;
    const isOpen = expandedComps.has(comp.id);
    const row = document.createElement("tr");
    row.className = isOpen ? "comp-row expanded" : "comp-row";
    row.dataset.compId = comp.id;
    row.innerHTML = `<td>${comp.name} <svg class="expand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg></td><td>&#8377;${comp.rent}</td><td>${comp.strengths}</td><td><span class="${riskClass}">${comp.risk.toUpperCase()}</span></td>`;
    row.addEventListener("click", () => toggleComp(comp.id, competitors));
    const detailRow = document.createElement("tr");
    detailRow.className = "comp-detail-row"; detailRow.id = `comp-detail-${comp.id}`;
    detailRow.style.display = isOpen ? "" : "none";
    detailRow.innerHTML = `<td colspan="4"><div class="comp-detail-inner"><strong>Strategy:</strong> ${comp.details}<div class="comp-detail-weakness"><strong>JLL Advantage:</strong> ${comp.weakness}</div></div></td>`;
    tbody.appendChild(row); tbody.appendChild(detailRow);
  });
  const jllRow = document.createElement("tr"); jllRow.className = "tr-jll";
  jllRow.innerHTML = `<td><strong>JLL (Our Bid)</strong></td><td class="td-jll-price">&#8377;138 &ndash; &#8377;145</td><td class="td-jll-str">Integrated leasing + FM</td><td><span style="color:#10b981;font-size:10px;font-weight:600">OUR BID</span></td>`;
  tbody.appendChild(jllRow);
}
function toggleComp(id, competitors) {
  expandedComps.has(id) ? expandedComps.delete(id) : expandedComps.add(id);
  renderCompetitors(competitors);
}

// ═══════════════ PROPERTIES TABLE ════════════════════════════
function renderPropertiesTable(props) {
  const tbody = $("propsTbody"); tbody.innerHTML = "";
  const count = $("filterCount"); if (count) count.textContent = `Showing ${props.length} propert${props.length!==1?"ies":"y"}`;
  if (!props.length) { tbody.innerHTML = `<tr class="no-results-row"><td colspan="8">No properties match the selected filters.</td></tr>`; return; }
  props.forEach(prop => {
    const tr = document.createElement("tr"); if (prop.highlight) tr.classList.add("prop-highlight");
    tr.innerHTML = `<td class="td-thumb"><div class="prop-thumb" style="background:${prop.color}"></div></td><td class="td-propname">${prop.name}${prop.highlight?' <span style="background:var(--red);color:#fff;font-size:9px;padding:1px 5px;border-radius:3px;vertical-align:middle">TOP</span>':""}</td><td style="color:#64748b;font-size:12px">${prop.location}</td><td><span class="rent-fig">&#8377; ${prop.rent}</span><br><span class="rent-note">All Inclusive</span></td><td style="font-size:12px">${prop.size.toLocaleString()}</td><td style="font-size:12px">${prop.availability}</td><td>${donutSvg(prop.fit,44)}</td><td><button class="btn-view" data-prop-id="${prop.id}">View</button></td>`;
    tr.querySelector(".btn-view").addEventListener("click", () => openPropertyModal(prop));
    tbody.appendChild(tr);
  });
}
function applyFilters() {
  const loc    = $("filterLocation").value;
  const budget = $("filterBudget").value;
  const seats  = parseInt($("filterSeats").value) || 0;
  const sort   = $("filterSort").value;
  let filtered = currentProperties.slice();
  if (loc)           filtered = filtered.filter(p => p.sublocation === loc || p.location.toLowerCase().includes(loc));
  if (budget==="low")  filtered = filtered.filter(p => p.rent < 135);
  if (budget==="mid")  filtered = filtered.filter(p => p.rent >= 135 && p.rent <= 145);
  if (budget==="high") filtered = filtered.filter(p => p.rent > 145);
  if (seats)         filtered = filtered.filter(p => (p.seats||0) >= seats);
  if (sort==="fit")       filtered.sort((a,b) => b.fit - a.fit);
  if (sort==="rent_asc")  filtered.sort((a,b) => a.rent - b.rent);
  if (sort==="rent_desc") filtered.sort((a,b) => b.rent - a.rent);
  if (sort==="avail")     filtered.sort((a,b) => new Date(a.availDate) - new Date(b.availDate));
  renderPropertiesTable(filtered);
}
["filterLocation","filterBudget","filterSeats","filterSort"].forEach(id => { const el=$(id); if(el) el.addEventListener("change", applyFilters); });

// Property cards for Property Search view
function renderPropertyCards() {
  const grid = $("propCardsGrid"); if (!grid) return; grid.innerHTML = "";
  DEMO_PROPERTIES.forEach(prop => {
    const card = document.createElement("div"); card.className = "prop-card";
    card.innerHTML = `<div class="pc-header" style="background:${prop.color}"></div><div class="pc-body"><div class="pc-name">${prop.name}</div><div class="pc-loc">&#128205; ${prop.location}</div><div class="pc-stats"><div class="pc-stat"><strong>&#8377;${prop.rent}</strong>/sqft</div><div class="pc-stat"><strong>${prop.seats}</strong> seats</div><div class="pc-stat">${donutSvg(prop.fit,36)}</div></div></div>`;
    card.addEventListener("click", () => openPropertyModal(prop));
    grid.appendChild(card);
  });
}

// ═══════════════ PROPERTY MODAL ══════════════════════════════
function openPropertyModal(prop) {
  const r=19, c=2*Math.PI*r, dash=(prop.fit/100)*c, gap=c-dash, off=c/4;
  const annualCr=((prop.rent*prop.size)/10000000).toFixed(2);
  $("modalBody").innerHTML = `<div class="modal-prop-header" style="background:${prop.color}"><div class="modal-grade-badge">Grade ${prop.grade}</div><div class="modal-prop-title">${prop.name}</div><div class="modal-prop-loc">&#128205; ${prop.location}</div></div>
<div class="modal-content">
  <div class="modal-kpis">
    <div class="m-kpi"><div class="m-kpi-val">&#8377;${prop.rent}</div><div class="m-kpi-lbl">/ sq.ft / month</div></div>
    <div class="m-kpi"><div class="m-kpi-val">${prop.size.toLocaleString()}</div><div class="m-kpi-lbl">sq.ft area</div></div>
    <div class="m-kpi"><div class="m-kpi-val">${prop.seats}</div><div class="m-kpi-lbl">seat capacity</div></div>
    <div class="m-kpi"><svg viewBox="0 0 48 48" width="48" height="48" style="display:block;margin:0 auto 4px"><circle cx="24" cy="24" r="${r}" fill="none" stroke="#e2e8f0" stroke-width="4.5"/><circle cx="24" cy="24" r="${r}" fill="none" stroke="#10b981" stroke-width="4.5" stroke-dasharray="${dash.toFixed(1)} ${gap.toFixed(1)}" stroke-dashoffset="${off.toFixed(1)}" stroke-linecap="round"/><text x="24" y="28" text-anchor="middle" font-size="10" font-weight="700" fill="#065f46">${prop.fit}%</text></svg><div class="m-kpi-lbl">Fit Score</div></div>
  </div>
  <div class="modal-section"><div class="modal-section-title">Property Details</div>
    <div class="modal-detail-grid">
      <div class="md-row"><span class="md-key">Landlord</span><span class="md-val">${prop.landlord}</span></div>
      <div class="md-row"><span class="md-key">Grade</span><span class="md-val">${prop.grade}</span></div>
      <div class="md-row"><span class="md-key">Year Built</span><span class="md-val">${prop.yearBuilt}</span></div>
      <div class="md-row"><span class="md-key">Total Floors</span><span class="md-val">${prop.totalFloors}</span></div>
      <div class="md-row"><span class="md-key">Availability</span><span class="md-val">${prop.availability}</span></div>
      <div class="md-row"><span class="md-key">Annual Rent</span><span class="md-val">&#8377;${annualCr} Cr</span></div>
    </div>
  </div>
  <div class="modal-section"><div class="modal-section-title">Amenities</div><div class="amenity-chips">${prop.amenities.map(a=>`<span class="a-chip">${a}</span>`).join("")}</div></div>
  <div class="modal-section"><div class="modal-section-title">Why this matches ABC Tech</div><ul class="match-list">${prop.matchReasons.map(r=>`<li>${r}</li>`).join("")}</ul></div>
  <div class="modal-actions">
    <button class="btn-modal-primary" id="modalAddBtn">Add to Proposal</button>
    <button class="btn-modal-secondary" onclick="closePropertyModal()">Close</button>
  </div>
</div>`;
  $("modalAddBtn").addEventListener("click", () => { closePropertyModal(); if (activeId) sendMsg(`Add ${prop.name} to the bid proposal`); else { appendMsg("agent",`${prop.name} (₹${prop.rent}/sq.ft, Fit: ${prop.fit}%) selected as primary recommendation.`); toast(`${prop.name} added to proposal ✓`); } });
  $("propModal").classList.add("open");
  document.body.style.overflow = "hidden";
}
function closePropertyModal() { $("propModal").classList.remove("open"); document.body.style.overflow = ""; }
$("modalBackdrop").addEventListener("click", closePropertyModal);
$("modalCloseBtn").addEventListener("click", closePropertyModal);
document.addEventListener("keydown", e => { if (e.key === "Escape") { closePropertyModal(); closeDemoModal(); closeNewBidModal(); } });

// ═══════════════ FM SERVICES ═════════════════════════════════
function renderFmServices(services, listId, totalId, displayId) {
  const list = $(listId || "fmList"); if (!list) return;
  list.innerHTML = "";
  services.forEach(svc => {
    const row = document.createElement("div"); row.className = "fm-row" + (svc.checked ? "" : " fm-row--disabled");
    row.innerHTML = `<input type="checkbox" class="fm-cb" ${svc.checked?"checked":""} data-fm-id="${svc.id}" /><span class="fm-ico" style="background:${svc.bg};color:${svc.color}">${svc.ico}</span><span class="fm-rname">${svc.name}</span><span class="fm-ramt">&#8377; ${svc.amt.toLocaleString()} / month</span>`;
    row.querySelector(".fm-cb").addEventListener("change", e => { svc.checked = e.target.checked; row.classList.toggle("fm-row--disabled", !svc.checked); recalcFm(services, totalId, displayId); });
    list.appendChild(row);
  });
  recalcFm(services, totalId, displayId);
}
function recalcFm(services, totalId, displayId) {
  const total = services.filter(s=>s.checked).reduce((s,x)=>s+x.amt,0);
  const fmt = `₹ ${total.toLocaleString()} / month`;
  const tEl = $(totalId||"fmTotalAmt"); if (tEl) tEl.textContent = fmt;
  const dEl = $(displayId||"fmTotalDisplay"); if (dEl) dEl.textContent = fmt;
}
function renderFmServicesView() {
  renderFmServices(DEMO_FM_SERVICES, "fmListView", "fmTotalAmtView", null);
}

// ═══════════════ PIPELINE ════════════════════════════════════
function updatePipelineActive(stage) {
  const MAP = { INTAKE:"Requirements", SHORTLISTING:"Shortlisting", COMPARISON:"Shortlisting", PROPOSAL_DRAFTING:"Proposal", FM_BUNDLING:"Proposal", NEGOTIATION:"Negotiation", OUTCOME_PENDING:"Negotiation", WON_CLOSEOUT:"Won", LOGGED:"Won", LOST_FM_UPSELL:"FM Upsell" };
  const label = MAP[stage] || "";
  document.querySelectorAll(".pp").forEach(el => {
    const name = el.childNodes[0]?.textContent?.trim().split(" ")[0];
    const active = label && label.startsWith(name);
    el.classList.toggle("pp--active", active);
    const badge = el.querySelector(".pp-n"); if (badge) badge.classList.toggle("pp-n--active", active);
  });
}

// ═══════════════ DEMO WORKFLOW MODAL ════════════════════════
function openDemoModal() {
  $("demoModal").classList.add("open");
  document.body.style.overflow = "hidden";
  $("demoLog").innerHTML = "";
  $("demoOutput").innerHTML = "";
  $("demoProgressFill").style.width = "0%";
  $("demoProgressLabel").textContent = "Starting...";
  runDemoWorkflow();
}
function closeDemoModal() {
  if (demoTimer) { clearTimeout(demoTimer); demoTimer = null; }
  demoRunning = false;
  $("demoModal").classList.remove("open");
  document.body.style.overflow = "";
}
function runDemoWorkflow() {
  demoRunning = true;
  let stepIdx = 0;
  function playStep() {
    if (!demoRunning || stepIdx >= DEMO_STEPS.length) { demoRunning = false; return; }
    const step = DEMO_STEPS[stepIdx++];
    $("demoProgressFill").style.width = step.pct + "%";
    $("demoProgressLabel").textContent = step.label;
    step.log.forEach((line, i) => {
      demoTimer = setTimeout(() => {
        const entry = document.createElement("div"); entry.className = "demo-log-entry";
        const now = new Date(); const ts = now.toTimeString().slice(0,8);
        entry.innerHTML = `<span class="demo-log-time">${ts}</span> ${line}`;
        $("demoLog").appendChild(entry);
        $("demoLog").scrollTop = $("demoLog").scrollHeight;
      }, i * 280);
    });
    demoTimer = setTimeout(() => {
      const outEl = document.createElement("div"); outEl.innerHTML = step.output;
      $("demoOutput").appendChild(outEl);
      $("demoOutput").scrollTop = $("demoOutput").scrollHeight;
      demoTimer = setTimeout(playStep, 800);
    }, step.log.length * 280 + 200);
  }
  playStep();
}

$("loadDemoBtn").addEventListener("click", openDemoModal);
$("demoModalClose").addEventListener("click", closeDemoModal);
$("demoModalClose2").addEventListener("click", closeDemoModal);
$("demoRestart").addEventListener("click", () => {
  if (demoTimer) clearTimeout(demoTimer);
  $("demoLog").innerHTML = ""; $("demoOutput").innerHTML = "";
  $("demoProgressFill").style.width = "0%";
  runDemoWorkflow();
});

// ═══════════════ NEW BID MODAL ══════════════════════════════
function openNewBidModal() {
  nbCurrentStep = 1;
  renderNbSteps();
  showNbStep(1);
  $("newBidModal").classList.add("open");
  document.body.style.overflow = "hidden";
}
function closeNewBidModal() {
  $("newBidModal").classList.remove("open");
  document.body.style.overflow = "";
}
function renderNbSteps() {
  document.querySelectorAll(".nb-step").forEach(s => {
    const sn = parseInt(s.dataset.step);
    s.classList.toggle("nb-step--active", sn === nbCurrentStep);
    s.classList.toggle("nb-step--done", sn < nbCurrentStep);
  });
}
function showNbStep(n) {
  for (let i=1; i<=4; i++) { const el=$(`nbStep${i}`); if (el) el.style.display = i===n ? "block" : "none"; }
  $("nbBack").style.display = n > 1 ? "inline-flex" : "none";
  $("nbNext").textContent = n < 4 ? "Next →" : "Submit & Analyse";
}
function nbNext() {
  if (nbCurrentStep < 4) {
    nbCurrentStep++;
    renderNbSteps();
    showNbStep(nbCurrentStep);
  } else {
    submitNewBid();
  }
}
function nbBack() {
  if (nbCurrentStep > 1) { nbCurrentStep--; renderNbSteps(); showNbStep(nbCurrentStep); }
}
async function submitNewBid() {
  const company = $("nb_company").value.trim();
  if (!company) { toast("Please enter a company name."); return; }
  $("nbNext").textContent = "Analysing...";
  $("nbNext").disabled = true;
  await new Promise(r => setTimeout(r, 1800));
  closeNewBidModal();
  toast(`New bid created for ${company || "client"} — AI analysis starting`);
  try {
    const rec = await api("/opportunities", { method:"POST", body: JSON.stringify({ client_name: company }) });
    await loadOpportunities();
    $("oppSelect").value = rec.opportunity_id;
    await selectOpportunity(rec.opportunity_id);
    switchView("copilot");
  } catch (e) {
    isDemoMode = true;
    loadDemoMode();
    appendMsg("agent", `New bid for ${company} created in demo mode. AI has pre-loaded matching requirements and shortlist.`);
  } finally { $("nbNext").textContent = "Submit & Analyse"; $("nbNext").disabled = false; }
}

document.querySelectorAll("#newBidBtn, #newBidBtn2").forEach(b => b && b.addEventListener("click", openNewBidModal));
$("newBidClose").addEventListener("click",    closeNewBidModal);
$("newBidCancel").addEventListener("click",   closeNewBidModal);
$("nbNext").addEventListener("click",  nbNext);
$("nbBack").addEventListener("click",  nbBack);

// FM estimate in step 4
document.querySelectorAll("[name='nb_fm']").forEach(cb => {
  cb.addEventListener("change", () => {
    const checked = document.querySelectorAll("[name='nb_fm']:checked");
    const amts = { pantry:120000, stationery:40000, washroom:60000, electrical:75000, plumbing:50000, generalops:100000 };
    const total = Array.from(checked).reduce((s, c) => s + (amts[c.value] || 0), 0);
    const el = $("nbFmEst"); if (el) el.innerHTML = `&#8377; ${total.toLocaleString()} / month`;
  });
});

// ═══════════════ DEMO MODE ══════════════════════════════════
function loadDemoMode() {
  isDemoMode = true; activeId = null;
  $("oppSelect").value = "";
  $("chatWin").innerHTML = `<div class="chat-greet"><p>Hi Neha! 👋</p><p class="greet-sub">Demo: <strong>ABC Tech Pvt. Ltd.</strong> — Q3 2026 Office Leasing, Bengaluru</p></div><div class="msg-agent">I've analysed ABC Tech's requirements. Prestige Tech Park scores <strong>92%</strong> fit — ₹138/sq.ft (2.8% below market), 280 seats, all must-have facilities, Jul 2026. Proposal draft is ready for review.</div><div class="msg-system">★ Click any workflow step to see what the AI did at that stage</div>`;
  renderStepper(DEMO_CLIENT.stage);
  renderRequirements(DEMO_CLIENT.requirements);
  updatePipelineActive(DEMO_CLIENT.stage);
  currentProperties = [...DEMO_PROPERTIES];
  renderPropertiesTable(DEMO_PROPERTIES);
  renderCompetitors(DEMO_COMPETITORS);
  renderFmServices(DEMO_FM_SERVICES, "fmList", "fmTotalAmt", "fmTotalDisplay");
  $("fmBlock").classList.add("open");
  $("fmToggleBar").classList.add("open");
  switchView("copilot");
  toast("Demo loaded — ABC Tech Pvt. Ltd. (Bengaluru ORR / Whitefield, 250 seats, Q3 2026)");
}

// ═══════════════ OPPORTUNITY MANAGEMENT ════════════════════
async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body?.error?.message || body?.detail || `Request failed (${res.status})`);
  return body;
}
async function loadOpportunities() {
  try {
    const { opportunity_ids: ids } = await api("/opportunities");
    const sel = $("oppSelect");
    sel.innerHTML = `<option value="">— Select Opportunity —</option>`;
    (ids || []).forEach(id => { const opt=document.createElement("option"); opt.value=id; opt.textContent=id; if(id===activeId)opt.selected=true; sel.appendChild(opt); });
    $("kpiActive").textContent = ids?.length || 0;
  } catch(e) { console.warn("Opportunities unavailable:", e.message); }
}
async function selectOpportunity(id) {
  if (!id) return;
  isDemoMode = false; activeId = id;
  $("chatWin").innerHTML = `<div class="chat-greet" id="chatGreet"><p>Hi Neha! 👋</p><p class="greet-sub">Loading opportunity...</p></div>`;
  renderStepper(null);
  try {
    const rec = await api(`/opportunities/${id}`);
    renderStepper(rec.stage); renderRequirements(rec.requirements);
    if (rec.stage) updatePipelineActive(rec.stage);
    const { messages } = await api(`/opportunities/${id}/messages`);
    $("chatWin").innerHTML = "";
    if (!messages.length) appendMsg("system", "New opportunity created. Describe the client's requirements to begin.");
    else messages.forEach(m => appendMsg(m.role==="assistant"?"agent":m.role, m.text));
    (rec.approvals||[]).filter(a=>a.status==="pending").forEach(appendApprovalCard);
  } catch(e) { appendMsg("error", `Failed to load opportunity: ${e.message}`); }
}
$("oppSelect").addEventListener("change", () => selectOpportunity($("oppSelect").value));
$("newOppToggle").addEventListener("click", () => { $("newOppForm").classList.toggle("open"); if ($("newOppForm").classList.contains("open")) $("newClientInput").focus(); });
$("cancelOppBtn").addEventListener("click", () => { $("newOppForm").classList.remove("open"); $("newClientInput").value=""; });
$("createOppBtn").addEventListener("click", createOpportunity);
$("newClientInput").addEventListener("keydown", e => { if (e.key==="Enter") createOpportunity(); });
async function createOpportunity() {
  const name = $("newClientInput").value.trim(); if (!name) return;
  $("createOppBtn").disabled = true;
  try {
    const rec = await api("/opportunities", { method:"POST", body: JSON.stringify({ client_name: name }) });
    $("newClientInput").value = ""; $("newOppForm").classList.remove("open");
    await loadOpportunities();
    $("oppSelect").value = rec.opportunity_id;
    await selectOpportunity(rec.opportunity_id);
  } catch(e) { toast(`Could not create: ${e.message}`); }
  finally { $("createOppBtn").disabled = false; }
}

// ═══════════════ CHAT ════════════════════════════════════════
async function sendMsg(text) {
  if (!text) return;
  $("chatInput").value = "";
  if ($("chatGreet")) $("chatGreet").style.display = "none";
  appendMsg("user", text);
  $("sendBtn").disabled = true; $("chatInput").disabled = true;
  const thinking = appendThinking();
  try {
    if (!activeId) throw new Error("Please select or create an opportunity first.");
    const { reply } = await api(`/opportunities/${activeId}/chat`, { method:"POST", body:JSON.stringify({ message:text }) });
    thinking.remove(); appendMsg("agent", reply);
    const rec = await api(`/opportunities/${activeId}`);
    renderStepper(rec.stage); renderRequirements(rec.requirements);
    if (rec.stage) updatePipelineActive(rec.stage);
    (rec.approvals||[]).filter(a=>a.status==="pending").filter(a=>!document.getElementById(`apr-${a.approval_id}`)).forEach(appendApprovalCard);
  } catch(e) { thinking.remove(); appendMsg("error", `Error: ${e.message}`); }
  finally { $("sendBtn").disabled=false; $("chatInput").disabled=false; $("chatInput").focus(); }
}
async function decideApproval(approvalId, decision) {
  if (!activeId) return;
  try {
    await api(`/opportunities/${activeId}/approvals/${approvalId}/decision`, { method:"POST", body:JSON.stringify({ decision, reviewer:"Neha Sharma" }) });
    const card = document.getElementById(`apr-${approvalId}`);
    if (card) { const cls=decision==="approve"?"apr-status-approved":"apr-status-rejected"; card.querySelector(".apr-btns").outerHTML = `<div class="${cls}">${decision==="approve"?"Approved ✓":"Rejected"}</div>`; }
    toast(decision==="approve" ? "Approval recorded ✓" : "Rejection recorded");
  } catch(e) { appendMsg("error", `Could not record decision: ${e.message}`); }
}
$("sendBtn").addEventListener("click", () => sendMsg($("chatInput").value.trim()));
$("chatInput").addEventListener("keydown", e => { if (e.key==="Enter" && !e.shiftKey) { e.preventDefault(); sendMsg($("chatInput").value.trim()); } });
document.querySelectorAll(".qa-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    if (!activeId && !isDemoMode) { toast("Please select or create an opportunity first."); return; }
    if (activeId) { sendMsg(btn.dataset.msg); return; }
    appendMsg("user", btn.dataset.msg);
    const demoReplies = {
      "Find":        "Based on ABC Tech's requirements, Prestige Tech Park (92% fit, ₹138/sqft, Jul 2026) is the top match. Embassy Manyata (88%, ₹143) offers larger plates. RMZ Ecoworld (85%, ₹135) is the most cost-efficient. Bagmane Tech Park (78%) has a Pantry gap — flagged.",
      "Compare":     "JLL's bid (₹138–₹145) undercuts CBRE (₹145), Knight Frank (₹148), and Cushman & Wakefield (₹146). Colliers matches at ₹140 but lacks FM integration. JLL's FM bundle saves ABC Tech ₹6–8L/year vs separately sourced FM — key differentiator to lead with.",
      "Draft":       "Drafting proposal for Prestige Tech Park: ₹138/sqft, 50,000 sqft, 5-year lease, Jul 2026. Annual lease: ₹8.28 Cr. With FM bundle: ₹13.62 Cr/yr integrated. Competitive positioning: 2.8% below market average, 7% below Knight Frank. Awaiting your approval before client-ready.",
      "Recommend":   "Recommended FM bundle for 250 seats (Standard Tier): Pantry ₹1.2L + Washroom ₹60K + Electrical ₹75K + Plumbing ₹50K + General Ops ₹1L + Stationery ₹40K = ₹4,45,000/month. Annual commitment ₹53.4L. Position as integrated JLL single contract.",
      "Negotiation": "Talking points: (1) ₹138 is 2.8% below market — anchor on data. (2) Offer 2-month rent-free instead of headline rate cut. (3) JLL FM saves ₹6–8L/year vs separate vendors. (4) Prestige is only Grade A+ property with Jul 2026 availability — scarcity angle.",
    };
    const key = Object.keys(demoReplies).find(k => btn.dataset.msg.includes(k)) || "Compare";
    setTimeout(() => appendMsg("agent", demoReplies[key]), 1000);
  });
});

// ═══════════════ FM TOGGLE ════════════════════════════════════
$("fmToggleBar").addEventListener("click", () => {
  $("fmBlock").classList.toggle("open");
  $("fmToggleBar").classList.toggle("open");
});
$("fmAddToProposal").addEventListener("click", () => {
  const selected = DEMO_FM_SERVICES.filter(s=>s.checked);
  const total = selected.reduce((s,x)=>s+x.amt,0);
  if (activeId) sendMsg(`Add FM bundle (${selected.map(s=>s.name).join(", ")} — ₹${total.toLocaleString()}/month) to the bid proposal`);
  else { appendMsg("agent", `FM bundle added: ${selected.length} services, ₹${total.toLocaleString()}/month (₹${(total*12/100000).toFixed(1)}L/year).`); toast("FM bundle added to proposal ✓"); }
});
const fmAddBtn2 = $("fmAddToProposal2");
if (fmAddBtn2) fmAddBtn2.addEventListener("click", () => { appendMsg("agent","FM bundle added to proposal ✓"); toast("FM bundle added to proposal ✓"); });

// ═══════════════ STORY PANEL ══════════════════════════════════
$("storyClose").addEventListener("click", () => { $("storyPanel").style.display = "none"; });

// ═══════════════ VIEW ALL LINK ═══════════════════════════════
const viewAllLink = $("viewAllLink");
if (viewAllLink) viewAllLink.addEventListener("click", e => { e.preventDefault(); switchView("property-search"); });

// ═══════════════ KPI CARDS ═══════════════════════════════════
document.querySelectorAll(".kpi-card").forEach(card => { card.addEventListener("click", () => toast(card.dataset.tooltip || "")); });

// ═══════════════ HEALTH CHECK ═══════════════════════════════
async function checkHealth() {
  try {
    const h = await api("/healthz");
    const tag = $("copilotTag");
    if (tag) tag.textContent = h.llm_ready ? `Your AI Bidding Assistant · ${h.llm_provider}` : "Your AI Bidding Assistant · (set API key to enable chat)";
  } catch(_) {}
}

// ═══════════════ INIT ══════════════════════════════════════
(async function init() {
  renderStepper(null);
  renderFmServices(DEMO_FM_SERVICES, "fmList", "fmTotalAmt", "fmTotalDisplay");
  renderCompetitors(DEMO_COMPETITORS);
  renderPropertiesTable(DEMO_PROPERTIES.slice(0,3));
  await checkHealth();
  await loadOpportunities();
  loadDemoMode();
})();
