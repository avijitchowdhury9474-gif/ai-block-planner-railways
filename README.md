# 🚆 AI‑Powered Automatic Block Planner – Indian Railways

Smart India Hackathon – Problem ID **26027**  
Ministry of Railways, Government of India  

---

## 🔍 Problem

Today, **maintenance blocks** for Track (TMS), Signal & Telecom (SMMS) and Traction (TDMS) are:

- Planned **manually and independently** by each department  
- Requested through BDMS without full coordination  
- Not always aligned with **COA** (Control Office Application) block availability

This leads to:

- Multiple separate blocks on the same corridor  
- **Reduced asset availability** for train operations  
- Difficulty in prioritising **safety‑critical** defects  
- Limited visibility for control/safety officers

---

## 💡 Our Solution (Elevator Pitch)

We built a **web‑based AI block planning and monitoring application** that:

- Integrates maintenance tasks from **TMS / SMMS / TDMS** and block windows from **COA**
- Computes an **AI priority score** for each task (safety, urgency, traffic importance)
- Automatically generates **optimal block plans** for weekly/monthly horizons
- Enforces a **human‑in‑the‑loop safety approval** step before any notification
- Provides control‑room‑friendly **dashboards & visualizations** plus monitoring of supervisors

> **Goal:** Maximize asset availability and passenger safety with  
> **data‑driven, coordinated, and reviewable** block planning.

---

## 🧠 AI Logic – How Priorities Are Calculated

Each maintenance task has:

- `criticality` (1–5) – safety importance  
- `overdue_days` – how long it’s pending  
- `traffic_importance` (1–5) – importance of that corridor for train traffic  

We compute a **priority score** as a weighted sum:

```text
priority_score = 0.5 × criticality
               + 0.3 × normalized_overdue_days
               + 0.2 × traffic_importance
normalized_overdue_days compresses overdue into 0–5 scale (capped at 30 days)
We expose sliders in the UI so control can tune the weights (safety‑first, backlog‑first, traffic‑first, etc.)
Tasks are then sorted by priority and scheduled into available block windows.

📅 Scheduling Engine (High Level)
Inputs:

Integrated maintenance tasks (from TMS, SMMS, TDMS)
Block windows (from COA / timetable, including corridor, date, start_time, end_time, max_tasks)
Algorithm (greedy, corridor‑aware):

Sort tasks by priority_score (DESC)
For each task:
Find all candidate blocks on the same corridor that
Have enough remaining time
Have not exceeded max_tasks
Assign the task to the earliest feasible block
Any task that cannot be assigned is listed as “Unassigned High‑Priority Task”
This is simple, explainable and works well as a prototype algorithm.
It can be upgraded later to MIP / OR‑Tools or learning‑based methods.

👨‍✈️ Human‑in‑the‑Loop Safety Review
Because passenger safety is critical, the AI engine only proposes a plan.

On the “Block Plan” tab:

All scheduled blocks and unassigned tasks are shown
Safety‑critical unassigned tasks (priority ≥ threshold) are highlighted in red
A control/safety officer must:
Enter name and review notes
Explicitly click “Approve plan for notifications”
Only after approval:

The Notifications & Monitoring tab is unlocked
Notifications for PWIs / JEs / SSEs can be (simulated) as sent
This ensures human oversight on any safety‑relevant decisions.

📊 UI Tabs & Features
1. 📊 Maintenance Tasks
Integrated list of tasks from TMS/SMMS/TDMS
Fields: task_id, department, corridor, asset_type, description, criticality, overdue_days, est_duration_min, can_share_block, traffic_importance, owner_name, owner_phone
AI priority_score column computed using current slider weights
2. 📅 Block Plan
One‑click “Generate Plan” using the current AI weights and data
Shows:
Optimized weekly/monthly block plan
Unassigned tasks
Safety‑critical unassigned tasks separately
Human Safety Review & Approval section:
Approver name & notes
Approve / revoke approval buttons
Approval status indicator
3. 📈 KPIs & Insights
Key metrics:

Total maintenance tasks
Tasks covered in the plan
Block time utilization (%)
Safety‑critical tasks (Crit ≥ 4)
Safety‑critical tasks covered
Unscheduled & high‑priority backlog
Corridor‑wise task coverage
4. 🗺 Visualizations
2D Block Timeline (Control Room view)
X‑axis: time
Y‑axis: corridor / section
Color: department (ENG / SNT / TRD)
3D Maintenance Space
X: corridor index
Y: start time
Z: priority score
Size: task duration
Risk by Corridor
Bars: number of high‑priority tasks per corridor
Color intensity: high‑priority ratio
5. 🔔 Notifications & Monitoring
Only available after plan approval
For each approved plan:
Generates notification text automatically:
“Dear [owner_name], a maintenance block is scheduled on [corridor] from [start–end time] on [date]. Tasks assigned: [task_ids]. – Control Office”

Shows Notification Preview:
block_id, department, owner_name, owner_phone, message, status
“Simulate sending” button changes status Pending → Sent
Owner Workload Summary:
department, owner_name, owner_phone
number of blocks assigned
number of notifications
In production, these messages would be sent via the official Railways SMS/Email gateway; here we simulate and visualise the full flow.

🧱 Data & Integration Layer
maintenance_tasks.csv
Represents integrated exports from TMS/SMMS/TDMS.

Core columns (canonical schema):

task_id
department (ENG / SNT / TRD)
corridor
asset_type
description
criticality
overdue_days
est_duration_min
can_share_block (TRUE/FALSE)
traffic_importance
owner_name (PWI / JE / SSE)
owner_phone (contact number)
block_windows.csv
Represents COA‑derived block opportunities:

block_id
corridor
date
start_time (HH:MM, 24‑hr)
end_time (HH:MM)
max_tasks (capacity per block)
Robust CSV Loader
Because TMS/SMMS/TDMS may export different header names, we use load_tasks_csv() that:

Normalises header names (lower‑case, trimmed)
Maps common aliases, e.g.
section → corridor
severity → criticality
days_overdue → overdue_days
duration_min → est_duration_min
owner → owner_name, phone → owner_phone
Validates that all required columns are present
Shows a clear error message if something is missing, instead of crashing
This makes the planner robust to real‑world data exports.

🛠️ Tech Stack
Frontend / UI: Streamlit
Backend / Logic: Python (priority scoring, scheduling)
Visualization: Plotly Express (2D/3D charts)
Data: CSV (prototype), easily replaceable with DB/APIs in production
▶️ How to Run Locally
Clone or download this repository.

Install dependencies:

Bash

pip install -r requirements.txt
Run the Streamlit app:

Bash

python -m streamlit run app.py
Open the URL Streamlit shows (usually http://localhost:8501).

You can use the bundled sample CSV files or upload your own integrated datasets via the sidebar.

🚀 Future Enhancements
Direct database/API connection to live TMS/SMMS/TDMS/COA instead of CSV files
Advanced optimisation (MILP / OR‑Tools) for trade‑offs between safety, availability, and resource constraints
Live notifications via official Railway SMS/Email gateways
User & role management (Control, Zone, Division, Department)
Machine‑learning layer that learns from historical blocks, delays and failures to recommend even better plans
👥 Team & Contributions
This project was built as part of the Smart India Hackathon.
Contributions and suggestions are welcome via Issues and Pull Requests.

text


You can tweak the wording (team names, etc.) once it’s in GitHub, but this should give you a very clear, attractive, and professional README.
