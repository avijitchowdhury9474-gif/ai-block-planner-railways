# 🚆 AI‑Powered Automatic Block Planner – Indian Railways

**Smart India Hackathon 2026 – Problem ID 26027**  
Ministry of Railways, Government of India  

Team: **SMART SAFAR**  

---

## 🌍 1. Background & Motivation

Indian Railways manages one of the largest railway networks in the world.  
Every day, thousands of trains run over fixed infrastructure that must be **safely maintained**:

- **Track & Structures** – rails, sleepers, turnouts, bridges (TMS)  
- **Signals & Telecom** – signal heads, track circuits, relays, point machines (SMMS)  
- **Traction & OHE** – overhead equipment, feeders, sectioning posts (TDMS)  

To perform maintenance, departments request **blocks** – time windows when no trains are allowed on a section.  
Today, this block planning has several challenges:

1. Each department raises requests **independently** (via BDMS).  
2. The **Control Office Application (COA)** separately manages train movements and block availability.  
3. There is no single AI system which looks at **all defects across departments + block windows** together.  
4. Prioritisation of **safety‑critical** vs. routine work is mostly manual.  
5. Coordination is difficult: three separate blocks may be taken on the same corridor where one coordinated block would be enough.

This can lead to:

- Multiple small blocks instead of **one coordinated block**  
- Lower **asset availability** of tracks, signals and OHE  
- Risk that some **critical safety defects** are delayed  
- Extra work for control‑room staff and safety officers

---

## 🎯 2. Our Objective

We aim to build an **AI‑assisted block planning system** that:

- Integrates maintenance tasks from **TMS, SMMS and TDMS**  
- Integrates block windows from **COA / timetable**  
- Uses **AI‑based prioritisation** to sort tasks by safety, urgency and traffic impact  
- Automatically recommends **coordinated block plans** for weekly and monthly horizons  
- Keeps a **human safety/control officer in the loop** to review and approve plans  
- Provides **intuitive dashboards and visualisations** for planners, safety officers and management  
- Supports **notifications** to responsible PWIs / JEs / SSEs and tracks their workload

In short: **data‑driven, coordinated and safety‑aware block planning.**

---

## 🏗️ 3. High‑Level Architecture

**Data Sources**

- **TMS (Track)** – track defects, geometry issues, renewals  
- **SMMS (S&T)** – signal failures, track circuits, relays, point machines  
- **TDMS (Traction)** – OHE defects, patrolling, insulators, feeders  
- **COA / Timetable** – block corridors, dates, free slots, max tasks per slot

**Integration Layer**

- All maintenance tasks are converted to a **canonical schema** and stored in `maintenance_tasks.csv` (prototype).
- Block windows are stored in `block_windows.csv`.

**AI Planner**

- Calculates **priority_score** for each task using criticality, overdue_days and traffic_importance.  
- A **greedy scheduling engine** assigns tasks to suitable block windows corridor‑wise.

**Human‑in‑the‑Loop**

- Control / safety officer **reviews** and **approves** the suggested plan.
- Only approved plans can generate notifications.

**UI / Web App**

- Built with **Streamlit** and **Plotly**.
- Tabs for Tasks, Block Plan, KPIs, Visualizations, Notifications & Monitoring.

In production, CSVs will be replaced by direct **database or API connections** to TMS, SMMS, TDMS and COA.

---

## 🧾 4. Data Model & Robust CSV Handling

### 4.1 Canonical Task Schema (`maintenance_tasks.csv`)

Each row is one maintenance task with fields:

- `task_id` – unique maintenance ID  
- `department` – `ENG`, `SNT`, `TRD`  
- `corridor` – line section / block section (e.g., SECT‑AB)  
- `asset_type` – Track, Signal, OHE, etc.  
- `description` – brief description of work  
- `criticality` – 1 to 5 (5 = safety‑critical)  
- `overdue_days` – how many days overdue (0 if not)  
- `est_duration_min` – estimated required block time (minutes)  
- `can_share_block` – TRUE / FALSE (can this be done with others)  
- `traffic_importance` – 1 to 5 (importance of this corridor for traffic)  
- `owner_name` – responsible PWI / JE / SSE  
- `owner_phone` – contact number for notifications

### 4.2 Block Windows Schema (`block_windows.csv`)

Each row is one potential block window:

- `block_id`  
- `corridor`  
- `date`  
- `start_time` (HH:MM)  
- `end_time` (HH:MM)  
- `max_tasks` – maximum tasks allowed in this block

### 4.3 Robust CSV Loader

Different systems may export different header names.  
Our function `load_tasks_csv()`:

- Normalises header names to lower‑case without spaces.  
- Maps common aliases:

  - `section` → `corridor`  
  - `severity` / `priority` → `criticality`  
  - `days_overdue` / `overdue` → `overdue_days`  
  - `duration_min` / `duration` → `est_duration_min`  
  - `share_block` → `can_share_block`  
  - `owner` / `contact_person` → `owner_name`  
  - `phone` / `mobile` → `owner_phone`

- Checks that all **required** fields exist; if not, shows a clear error and stops:

  > “Uploaded maintenance CSV is missing required columns: criticality, overdue_days, …”

This makes the planner **robust to different department exports** and avoids silent mistakes.

---

## 🧠 5. AI Prioritisation Logic

To decide which tasks deserve earlier blocks, we combine three factors:

1. **Criticality** – safety impact if not done (1–5)  
2. **Overdue Days** – how long the task has been overdue  
3. **Traffic Importance** – how important that corridor is for train traffic (1–5)

We compute a **priority score** as a weighted sum:

- Criticality weight (default 0.5)  
- Overdue weight (default 0.3)  
- Traffic weight (default 0.2)

`overdue_days` is normalised to a 0–5 range (capped at 30 days) so that all three factors are comparable.

In the UI, the control room can **adjust the weights via sliders**:

- If there has been a safety incident, they can shift to **safety‑first**.  
- If backlog is high, they can emphasise **overdue tasks**.  
- For busy festivals or peak season, they may emphasise **traffic importance**.

The resulting **priority_score** becomes the basis for scheduling.

---

## 📅 6. Automatic Block Scheduling

The scheduling engine works as follows (per planning horizon):

**Inputs:**

- Prioritised tasks (with `priority_score`)  
- Block windows per corridor with `start_time`, `end_time`, `max_tasks`

**Process:**

1. **Sort tasks** by `priority_score` in descending order.  
2. For each task:
   - Filter candidate blocks on the **same corridor**.  
   - For each block, check:
     - remaining time ≥ `est_duration_min`  
     - number of tasks < `max_tasks`
   - Choose the **earliest** feasible block and assign the task.  
3. If no block can host the task, mark it as **Unassigned High‑Priority Task**.

**Output:**

- A block plan table with **block_id, corridor, date, time, department, task_id, priority_score, duration**  
- A list of **unassigned tasks** that need extra attention (e.g., additional or emergency blocks)

This algorithm is:

- Simple and explainable  
- Efficient for typical corridor sizes  
- Easy to upgrade later to more complex optimisation techniques.

---

## 👨‍✈️ 7. Human Safety Review & Approval

Because this problem directly affects **passenger safety**, we enforce a **human‑in‑the‑loop** step.

On the **Block Plan** tab:

- All scheduled blocks are visible.  
- Unassigned tasks are clearly listed.  
- **Safety‑critical unassigned tasks** (e.g. priority ≥ 4) are highlighted.

A control or safety officer must:

1. Review the suggested plan and unassigned high‑risk tasks.  
2. Enter their **name** and **review notes** (for traceability).  
3. Explicitly click **“Approve plan for notifications”**.

We store this status in session state.  
Until the plan is **approved**, the Notifications & Monitoring tab remains locked.  
Approval can also be **revoked** if conditions or priorities change.

This ensures that the AI is used as a **decision‑support tool**, but final responsibility lies with human officers.

---

## 📊 8. KPIs & Visual Insights

To help planners and management understand the impact of a plan, we provide a **KPIs & Insights** tab.

**Key KPIs:**

- Total number of maintenance tasks  
- Number of tasks covered in the current plan  
- **Block time utilisation** (%) – how efficiently block time is used  
- Number of **safety‑critical tasks** (e.g. criticality ≥ 4)  
- Number of **safety‑critical tasks covered** in this plan  
- Number of **unassigned high‑priority tasks**

**Corridor‑wise Summary:**

- For each corridor, how many tasks are scheduled.  
- Easy to see if any corridor is underserved.

This gives a quick **health check** for the plan:

- Are we using blocks efficiently?  
- Are we prioritising safety correctly?  
- Where do we still have risk?

---

## 🗺️ 9. Visualisations for Control Room

Visual understanding is crucial for control‑room staff.  
Our **Visualizations** tab provides:

### 9.1 2D Block Timeline

- X‑axis: time  
- Y‑axis: corridor / section  
- Each bar: a block window  
- Color: department (ENG, SNT, TRD)

This immediately shows:

- When blocks are taken on each corridor  
- How different departments share or overlap blocks  
- Whether blocks are too fragmented or too sparse

### 9.2 3D Maintenance Space

- X: corridor index  
- Y: block start time  
- Z: `priority_score`  
- Size: task duration

This view shows:

- Where **high‑priority tasks** are concentrated in time and space  
- Which corridors have many high‑risk tasks in a short time window

### 9.3 Risk by Corridor

- Bar chart with:
  - `high_priority_tasks` per corridor  
  - ratio of high‑priority to total tasks

This helps decide where upcoming blocks should be focused.

---

## 🔔 10. Notifications & Monitoring

Once the plan is **approved**, we enable the **Notifications & Monitoring** tab.

### 10.1 Automatic Notification Generation

Using the `owner_name` and `owner_phone` fields, for every block and department we auto‑generate messages like:

> “Dear \<owner_name\>, a maintenance block is scheduled on \<corridor\> from \<start_time\> to \<end_time\> on \<date\>. Tasks assigned: \<list of task_ids\>. – Control Office”

These appear in the **Notification Preview** table with status:

- `Pending` initially  
- After simulation, `Sent`

### 10.2 Simulation in Prototype

In this prototype:

- We **simulate sending** by clicking a single button  
- The status changes from `Pending` to `Sent`  
- This avoids needing SMS gateways in the hackathon phase, but proves that we know what would be sent and to whom.

In real deployment, this step would be replaced by:

- Calls to Railway‑approved **SMS / Email gateways**  
- Logging of success/failure for each notification.

### 10.3 Owner Workload Summary

We also summarise workload per supervisor:

- department  
- owner_name  
- owner_phone  
- `blocks_assigned` – number of blocks they are scheduled to work in  
- `notifications` – number of messages for them

This ensures:

- No PWI / JE / SSE is overloaded unknowingly  
- Control can check that **every responsible owner** has been notified.

---

## 🧱 11. Tech Stack

- **Frontend & UI**:  
  - [Streamlit](https://streamlit.io/) – fast prototyping of data apps

- **Backend Logic**:  
  - Python – priority scoring, scheduling, CSV integration

- **Data Visualisation**:  
  - Plotly Express – interactive 2D and 3D charts

- **Data Storage (Prototype)**:  
  - CSV files – `maintenance_tasks.csv`, `block_windows.csv`

In production, CSV files would be replaced by:

- PostgreSQL or existing Railway databases  
- REST APIs to TMS/SMMS/TDMS/COA

---

## ▶️ 12. How to Run Locally

1. Clone or download this repository.

2. Install dependencies:

   ```bash
   pip install -r requirements.txt

   Start the app:

Bash

python -m streamlit run app.py
Open the URL printed in the terminal (usually http://localhost:8501).

You can:

Use the sample CSV files included in the repo, or
Upload your own integrated maintenance and block window files via the sidebar.
🚀 13. Impact & Future Scope
Expected Impact:

Fewer fragmented blocks and more coordinated multi‑department blocks
Higher asset availability for trains
Transparent handling of safety‑critical defects and overdue tasks
Reduced manual effort and chance of human error in block planning
Better situational awareness for control room and safety officers
Clear responsibilities and workload view for each supervisor
Future Enhancements:

Direct DB/API integration with live TMS, SMMS, TDMS and COA
More advanced optimisation using MILP or OR‑Tools for large‑scale corridors
Real‑time notifications via official Railway SMS and email gateways
Mobile app interface for PWIs / JEs / SSEs to see upcoming blocks and tasks
ML‑based learning from historical data to recommend even better block patterns. 

Start the app:

Bash

python -m streamlit run app.py
Open the URL printed in the terminal (usually http://localhost:8501).

You can:

Use the sample CSV files included in the repo, or
Upload your own integrated maintenance and block window files via the sidebar.
🚀 13. Impact & Future Scope
Expected Impact:

Fewer fragmented blocks and more coordinated multi‑department blocks
Higher asset availability for trains
Transparent handling of safety‑critical defects and overdue tasks
Reduced manual effort and chance of human error in block planning
Better situational awareness for control room and safety officers
Clear responsibilities and workload view for each supervisor
Future Enhancements:

Direct DB/API integration with live TMS, SMMS, TDMS and COA
More advanced optimisation using MILP or OR‑Tools for large‑scale corridors
Real‑time notifications via official Railway SMS and email gateways
Mobile app interface for PWIs / JEs / SSEs to see upcoming blocks and tasks
ML‑based learning from historical data to recommend even better block patterns.

## 👥 14. Team SMART SAFAR

- Avijit Chowdhury  
- Nagoori Mohammed Asif  
- G B Sai Vikranth  
- Nagabattula Sharon Sydney  
- Ediga Sri Rohith  
- Ankita Ghosh  

**Mentor**

- Akiladevi G
