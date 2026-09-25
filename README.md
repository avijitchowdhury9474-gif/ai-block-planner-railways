# 🚆 AI‑Powered Automatic Block Planner – Indian Railways

Smart India Hackathon – Problem ID 26027  
Ministry of Railways, Government of India  

---

## 🔍 Problem

Maintenance blocks for:

- Track (TMS)  
- Signal & Telecom (SMMS)  
- Traction (TDMS)  

are currently:

- Planned manually and independently by each department  
- Requested via BDMS without full coordination  
- Not always aligned with COA (Control Office Application) block availability  

This causes:

- Multiple separate blocks on the same corridor  
- Reduced asset availability for train operations  
- Difficulty in prioritising safety‑critical defects  
- Limited visibility for control/safety officers  

---

## 💡 Our Solution (Summary)

A **web‑based AI block planning and monitoring application** that:

- Integrates maintenance tasks from TMS / SMMS / TDMS and block windows from COA  
- Calculates an AI priority score for each task  
- Automatically schedules tasks into optimal blocks (weekly / monthly)  
- Enforces a human safety/control officer approval before notifications  
- Provides dashboards, visualisations and monitoring for supervisors  

Goal: **maximize asset availability and passenger safety** through a  
**data‑driven, coordinated and reviewable** block planning process.

---

## 🧠 AI Logic (Prioritisation)

Each task has three key attributes:

- criticality (1–5): how safety‑critical the defect is  
- overdue_days: how long the task has been pending  
- traffic_importance (1–5): importance of that corridor for traffic  

The priority_score is a weighted sum of these factors, with higher weight for:

- criticality (safety)  
- then overdue_days (backlog / risk)  
- then traffic_importance (operational impact)  

Sliders in the UI let control tune how much they care about safety vs backlog vs traffic.  
Tasks are then sorted by priority and passed to the scheduling engine.

---

## 📅 Scheduling Engine (High Level)

Inputs:

- Integrated maintenance tasks (from TMS, SMMS, TDMS)  
- Block windows (from COA / timetable; corridor, date, start_time, end_time, max_tasks)  

Process (per corridor):

1. Sort tasks by priority_score (highest first).  
2. For each task, find the earliest block on the same corridor that:
   - Has enough remaining time  
   - Has not exceeded max_tasks  
3. If such a block exists, assign the task to that block.  
4. If not, the task is listed as an **Unassigned High‑Priority Task**.  

This is an explainable greedy algorithm, suitable for a prototype and easy to extend to OR‑Tools or MILP later.

---

## 👨‍✈️ Human‑in‑the‑Loop Safety Review

The AI only recommends a plan. A **human** must approve it.

On the **Block Plan** tab:

- All scheduled blocks and unassigned tasks are visible.  
- Safety‑critical unassigned tasks are highlighted separately.  
- A control/safety officer:
  - Enters name and review notes  
  - Clicks “Approve plan for notifications”  

Only after approval:

- The **Notifications & Monitoring** tab is enabled.  
- Notifications for PWI / JE / SSE can be sent (simulated in prototype).  

This guarantees that any residual safety risk is reviewed by a human before execution.

---

## 📊 Main Features in the UI

1. **Maintenance Tasks**  
   - Integrated view of tasks from TMS/SMMS/TDMS  
   - Fields: task_id, department, corridor, asset_type, description, criticality, overdue_days, est_duration_min, can_share_block, traffic_importance, owner_name, owner_phone  
   - Computed priority_score based on AI weights  

2. **Block Plan**  
   - Generate optimized weekly/monthly plan with one click  
   - Shows scheduled tasks per block and unassigned tasks  
   - Human approval section with name, notes and status  

3. **KPIs & Insights**  
   - Total tasks and tasks covered  
   - Block time utilization  
   - Number of safety‑critical tasks and how many are covered  
   - Unscheduled high‑priority tasks and corridor‑wise coverage  

4. **Visualizations**  
   - 2D timeline (corridor vs time, coloured by department)  
   - 3D view (corridor index × time × priority)  
   - Risk per corridor (number and ratio of high‑priority tasks)  

5. **Notifications & Monitoring**  
   - Auto‑generated messages per block and per owner_name / owner_phone  
   - Simulated sending (status Pending → Sent)  
   - Workload summary for each supervisor: number of blocks and notifications  

In a real deployment, these messages would go through the official Railway SMS/Email gateway.

---

## 🧱 Data & Integration

### maintenance_tasks.csv

Represents integrated exports from TMS/SMMS/TDMS. Canonical columns:

- task_id  
- department (ENG / SNT / TRD)  
- corridor  
- asset_type  
- description  
- criticality  
- overdue_days  
- est_duration_min  
- can_share_block  
- traffic_importance  
- owner_name  
- owner_phone  

### block_windows.csv

Represents block opportunities from COA:

- block_id  
- corridor  
- date  
- start_time  
- end_time  
- max_tasks  

### Robust CSV Loader

The app uses a loader that:

- Normalises column names (lower‑case, trimmed)  
- Maps common alternate names from departments, for example:  
  - section → corridor  
  - severity → criticality  
  - days_overdue → overdue_days  
  - duration_min → est_duration_min  
  - owner → owner_name, phone → owner_phone  
- Validates that all required fields are present  
- Shows a clear error if essential fields are missing  

This lets different departments export data with their own headers while still working with one standard schema.

---

## 🛠️ Tech Stack

- **Frontend / UI**: Streamlit  
- **Backend / Logic**: Python (priority scoring, greedy scheduler)  
- **Visualization**: Plotly Express  
- **Data**: CSV (prototype), easily replaceable with databases/APIs in production  

---

## ▶️ How to Run Locally

1. Install dependencies:

   `pip install -r requirements.txt`

2. Start the app:

   `python -m streamlit run app.py`

3. Open the URL shown in the terminal (usually `http://localhost:8501`).

You can use the included sample CSV files or upload integrated exports from real systems.

---

## 🚀 Future Enhancements

- Direct API/DB integration with live TMS/SMMS/TDMS/COA  
- Advanced optimisation (MILP / OR‑Tools) for larger corridors and constraints  
- Real SMS/Email notifications via official Railway gateways  
- Role‑based access for Control, Zones, Divisions and Departments  
- Learning from historical plans, failures and delays to improve recommendations  

---

## 👥 Team & Contributions

This project was built as part of the **Smart India Hackathon**.  
Contributions and suggestions are welcome via Issues and Pull Requests.
