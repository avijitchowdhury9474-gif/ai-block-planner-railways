import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# -----------------------------
# SESSION STATE & PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="AI Block Planner – Indian Railways",
    page_icon="🚆",
    layout="wide"
)

if "notif_status" not in st.session_state:
    st.session_state["notif_status"] = {}
if "plan_approved" not in st.session_state:
    st.session_state["plan_approved"] = False
if "approver_name" not in st.session_state:
    st.session_state["approver_name"] = ""
if "approver_notes" not in st.session_state:
    st.session_state["approver_notes"] = ""

st.title("🚆 AI‑Powered Automatic Block Planner")
st.caption("Smart India Hackathon – Problem ID 26027 | Ministry of Railways")

st.info(
    "Step 1: Upload integrated CSV or use sample data. "
    "Step 2: Open 'Block Plan' and click 'Generate Plan'. "
    "Step 3: A human safety/control officer reviews and approves the plan. "
    "Step 4: Use 'KPIs', 'Visualizations' and 'Notifications & Monitoring'."
)

# -----------------------------
# CSV LOADER WITH COLUMN MAPPING
# -----------------------------
REQUIRED_TASK_COLUMNS = [
    "task_id",
    "department",
    "corridor",
    "asset_type",
    "description",
    "criticality",
    "overdue_days",
    "est_duration_min",
    "can_share_block",
    "traffic_importance",
]
OPTIONAL_TASK_COLUMNS = ["owner_name", "owner_phone"]

# many possible aliases from different departments → canonical names (lowercase)
TASK_COLUMN_ALIASES = {
    "taskid": "task_id",
    "task_no": "task_id",
    "task_no.": "task_id",

    "dept": "department",
    "department_name": "department",

    "section": "corridor",
    "sec": "corridor",
    "line_section": "corridor",

    "asset": "asset_type",
    "assettype": "asset_type",

    "defect_desc": "description",
    "defect_description": "description",
    "desc": "description",

    "severity": "criticality",
    "priority": "criticality",
    "crit": "criticality",

    "days_overdue": "overdue_days",
    "overdue": "overdue_days",
    "overdue_days": "overdue_days",

    "duration_min": "est_duration_min",
    "duration": "est_duration_min",
    "time_required_min": "est_duration_min",

    "share_block": "can_share_block",
    "shareblock": "can_share_block",

    "traffic_importance_index": "traffic_importance",
    "traffic_importance_score": "traffic_importance",

    "owner": "owner_name",
    "contact_person": "owner_name",
    "responsible_person": "owner_name",

    "phone": "owner_phone",
    "mobile": "owner_phone",
    "contact_number": "owner_phone",
}


def load_tasks_csv(source):
    """
    Read maintenance CSV and normalise/match columns from various departments.
    Accepts a file path string OR an UploadedFile.
    """
    # Try default UTF‑8; if that fails, fallback to latin-1
    try:
        df = pd.read_csv(source)
    except UnicodeDecodeError:
        df = pd.read_csv(source, encoding="latin-1")

    # normalise header names
    df.columns = [c.strip().lower() for c in df.columns]

    # apply alias mapping
    for old, new in TASK_COLUMN_ALIASES.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    # check required columns
    missing = [c for c in REQUIRED_TASK_COLUMNS if c not in df.columns]
    if missing:
        st.error(
            "Uploaded maintenance CSV is missing required columns: "
            + ", ".join(missing)
            + ".\n\nExpected at least: "
            + ", ".join(REQUIRED_TASK_COLUMNS)
            + ".\nIf this is real TMS/SMMS/TDMS data, an integration script "
            "should map its internal fields to this standard schema."
        )
        st.stop()

    # create optional columns if missing
    for col in OPTIONAL_TASK_COLUMNS:
        if col not in df.columns:
            df[col] = None

    return df


# -----------------------------
# HELPER FUNCTIONS (AI & SCHEDULER)
# -----------------------------
def parse_date(date_value):
    date_str = str(date_value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {date_str}")


def compute_block_duration(block):
    dt = parse_date(block["date"])
    start = datetime.strptime(str(block["start_time"]).strip(), "%H:%M").time()
    end = datetime.strptime(str(block["end_time"]).strip(), "%H:%M").time()
    dt_start = datetime.combine(dt, start)
    dt_end = datetime.combine(dt, end)
    return (dt_end - dt_start).total_seconds() / 60


def compute_priority_from_row(row, weights):
    c = int(row["criticality"])
    overdue = int(row["overdue_days"])
    t = int(row["traffic_importance"])
    norm_overdue = min(overdue / 30.0, 1.0) * 5.0
    score = weights["crit"] * c + weights["over"] * norm_overdue + weights["traffic"] * t
    return round(score, 2)


def compute_priority_from_task(task, weights):
    return compute_priority_from_row(task, weights)


def block_sort_key(block):
    d = parse_date(block["date"])
    t = datetime.strptime(str(block["start_time"]).strip(), "%H:%M").time()
    return datetime.combine(d, t)


def run_scheduler(tasks_df, blocks_df, weights):
    tasks = tasks_df.to_dict(orient="records")
    blocks = blocks_df.to_dict(orient="records")

    for t in tasks:
        t["criticality"] = int(t["criticality"])
        t["overdue_days"] = int(t["overdue_days"])
        t["est_duration_min"] = int(t["est_duration_min"])
        t["traffic_importance"] = int(t["traffic_importance"])
        t["can_share_block"] = str(t["can_share_block"]).upper() == "TRUE"
        t["priority_score"] = compute_priority_from_task(t, weights)

    for b in blocks:
        b["max_tasks"] = int(b["max_tasks"])
        b["duration_min"] = compute_block_duration(b)
        b["remaining_time_min"] = b["duration_min"]
        b["assigned_tasks"] = []

    tasks_sorted = sorted(tasks, key=lambda x: x["priority_score"], reverse=True)
    blocks_sorted = sorted(blocks, key=block_sort_key)

    unassigned = []
    for task in tasks_sorted:
        candidates = []
        for block in blocks_sorted:
            if block["corridor"] != task["corridor"]:
                continue
            if block["remaining_time_min"] < task["est_duration_min"]:
                continue
            if len(block["assigned_tasks"]) >= block["max_tasks"]:
                continue
            candidates.append(block)

        if not candidates:
            unassigned.append(task)
            continue

        chosen = candidates[0]
        chosen["assigned_tasks"].append(task)
        chosen["remaining_time_min"] -= task["est_duration_min"]

    plan_rows = []
    for block in blocks_sorted:
        if not block["assigned_tasks"]:
            continue
        for task in block["assigned_tasks"]:
            plan_rows.append(
                {
                    "block_id": block["block_id"],
                    "corridor": block["corridor"],
                    "date": block["date"],
                    "start_time": block["start_time"],
                    "end_time": block["end_time"],
                    "task_id": task["task_id"],
                    "department": task["department"],
                    "description": task["description"],
                    "priority_score": task["priority_score"],
                    "task_duration_min": task["est_duration_min"],
                }
            )

    plan_df = pd.DataFrame(plan_rows)

    if unassigned:
        un_df = pd.DataFrame(
            [
                {
                    "task_id": t["task_id"],
                    "corridor": t["corridor"],
                    "priority_score": t["priority_score"],
                    "est_duration_min": t["est_duration_min"],
                }
                for t in unassigned
            ]
        )
    else:
        un_df = pd.DataFrame(columns=["task_id", "corridor", "priority_score", "est_duration_min"])

    return plan_df, un_df


# -----------------------------
# SIDEBAR – DATA & AI WEIGHTS
# -----------------------------
st.sidebar.header("Data Inputs")
st.sidebar.write("Upload integrated CSV (TMS + SMMS + TDMS) or use sample data.")

tasks_file = st.sidebar.file_uploader(
    "Integrated maintenance tasks CSV", type=["csv"], key="tasks"
)
blocks_file = st.sidebar.file_uploader(
    "Block windows CSV (from COA)", type=["csv"], key="blocks"
)

if tasks_file is not None:
    tasks_df = load_tasks_csv(tasks_file)
else:
    tasks_df = load_tasks_csv("maintenance_tasks.csv")

if blocks_file is not None:
    blocks_df = pd.read_csv(blocks_file)
else:
    blocks_df = pd.read_csv("block_windows.csv")

st.sidebar.markdown("### AI Priority Weights")
w_crit = st.sidebar.slider("Criticality weight", 0.0, 1.0, 0.5, 0.05)
w_over = st.sidebar.slider("Overdue weight", 0.0, 1.0, 0.3, 0.05)
w_traffic = st.sidebar.slider("Traffic importance weight", 0.0, 1.0, 0.2, 0.05)

total_w = w_crit + w_over + w_traffic
if total_w == 0:
    weights = {"crit": 1 / 3, "over": 1 / 3, "traffic": 1 / 3}
else:
    weights = {
        "crit": w_crit / total_w,
        "over": w_over / total_w,
        "traffic": w_traffic / total_w,
    }

st.sidebar.caption(
    f"Normalized weights → Criticality: {weights['crit']:.2f}, "
    f"Overdue: {weights['over']:.2f}, Traffic: {weights['traffic']:.2f}"
)

horizon = st.sidebar.selectbox("Planning Horizon", ["Weekly Plan", "Monthly Plan (prototype)"])

# -----------------------------
# TABS
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Maintenance Tasks", "📅 Block Plan", "📈 KPIs & Insights", "🗺 Visualizations", "🔔 Notifications & Monitoring"]
)

# -----------------------------
# TAB 1 – MAINTENANCE TASKS
# -----------------------------
with tab1:
    st.subheader("Integrated Maintenance Task List")
    st.write(
        "Tasks combined from Track (TMS), Signal & Telecommunication (SMMS) "
        "and Traction Distribution (TDMS). Priority score is computed using the "
        "AI weights selected in the sidebar."
    )
    tasks_df_display = tasks_df.copy()
    tasks_df_display["priority_score"] = tasks_df_display.apply(
        lambda row: compute_priority_from_row(row, weights), axis=1
    )
    st.dataframe(tasks_df_display, use_container_width=True)

# -----------------------------
# TAB 2 – BLOCK PLAN (HUMAN APPROVAL)
# -----------------------------
with tab2:
    st.subheader(f"Optimized {horizon}")
    st.write(
        "The scheduler coordinates blocks across departments on each corridor, "
        "minimizing downtime while respecting the AI‑driven priorities. "
        "A human safety/control officer must review and approve the plan "
        "before any notifications are sent."
    )

    if st.button("🚀 Generate Plan"):
        st.session_state["plan_approved"] = False
        st.session_state["approver_name"] = ""
        st.session_state["approver_notes"] = ""
        st.session_state["notif_status"] = {}
        st.success("Plan regenerated with current data and AI weights. Approval required again.")

    plan_df, un_df = run_scheduler(tasks_df, blocks_df, weights)

    if plan_df.empty:
        st.warning("No tasks could be scheduled in the available blocks.")
    else:
        st.dataframe(plan_df, use_container_width=True)

    if not un_df.empty:
        st.markdown("### ⚠️ Unassigned High‑Priority Tasks")
        st.write("These tasks could not fit into any available block window.")
        st.dataframe(un_df, use_container_width=True)

        high_risk_un = un_df[un_df["priority_score"] >= 4.0]
        if not high_risk_un.empty:
            st.error(
                "There are unassigned **safety‑critical / high‑priority** tasks. "
                "The control/safety officer must review these before approval."
            )
            st.dataframe(high_risk_un, use_container_width=True)
    else:
        st.info("No unassigned tasks – all tasks fit into blocks for this horizon.")

    if not plan_df.empty:
        st.markdown("### 👤 Human Safety Review & Approval")

        st.write(
            "The AI engine only proposes a plan. A human control/safety officer "
            "must review safety‑critical tasks and explicitly approve the plan "
            "before notifications to field staff are enabled."
        )

        approver = st.text_input(
            "Control/Safety officer name",
            value=st.session_state.get("approver_name", "")
        )
        notes = st.text_area(
            "Review notes / safety considerations",
            value=st.session_state.get("approver_notes", "")
        )

        col_a, col_b = st.columns(2)
        if col_a.button("✅ Approve plan for notifications"):
            st.session_state["plan_approved"] = True
            st.session_state["approver_name"] = approver
            st.session_state["approver_notes"] = notes
            st.success(
                f"Plan approved by {approver or 'Control/Safety officer'}. "
                "Notifications are now enabled in the 'Notifications & Monitoring' tab."
            )
        if col_b.button("✖️ Revoke approval"):
            st.session_state["plan_approved"] = False
            st.warning("Plan approval revoked. Notifications are disabled until re‑approved.")

        st.info(
            "Current approval status: "
            + ("✅ Approved" if st.session_state["plan_approved"] else "❌ Not approved")
        )

# -----------------------------
# TAB 3 – KPIs & SAFETY
# -----------------------------
with tab3:
    st.subheader("Key Performance Indicators")
    plan_df, un_df = run_scheduler(tasks_df, blocks_df, weights)

    total_tasks = len(tasks_df)
    scheduled_tasks = plan_df["task_id"].nunique() if not plan_df.empty else 0
    unscheduled_tasks = total_tasks - scheduled_tasks

    total_block_time = 0
    used_block_time = 0
    for b in blocks_df.to_dict(orient="records"):
        total_block_time += compute_block_duration(b)
    for _, row in plan_df.iterrows():
        used_block_time += row["task_duration_min"]
    utilization = (used_block_time / total_block_time * 100) if total_block_time > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Maintenance Tasks", total_tasks)
    col2.metric("Tasks Covered in Plan", scheduled_tasks)
    col3.metric("Block Time Utilization", f"{utilization:0.1f}%")

    # Safety‑critical KPIs (criticality ≥ 4)
    safety_critical_tasks = (tasks_df["criticality"] >= 4).sum()
    if not plan_df.empty:
        merged_sc = plan_df.merge(
            tasks_df[["task_id", "criticality"]], on="task_id", how="left"
        )
        scheduled_sc = merged_sc[merged_sc["criticality"] >= 4]["task_id"].nunique()
    else:
        scheduled_sc = 0

    col4, col5 = st.columns(2)
    col4.metric("Safety‑critical tasks (Crit ≥ 4)", safety_critical_tasks)
    col5.metric("Safety‑critical tasks covered", scheduled_sc)

    if not un_df.empty:
        high_prio_un = (un_df["priority_score"] >= 4.0).sum()
        st.markdown("#### Risk & Backlog Overview")
        st.write(f"- Unscheduled tasks: **{unscheduled_tasks}**")
        st.write(f"- Unscheduled high‑priority tasks (score ≥ 4.0): **{high_prio_un}**")

    st.markdown("#### Corridor‑wise Breakdown (from plan)")
    if not plan_df.empty:
        corr_summary = (
            plan_df.groupby("corridor")["task_id"]
            .nunique()
            .reset_index()
            .rename(columns={"task_id": "tasks_scheduled"})
        )
        st.dataframe(corr_summary, use_container_width=True)
    else:
        st.write("No corridor summary available – plan is empty.")

# -----------------------------
# TAB 4 – VISUALIZATIONS
# -----------------------------
with tab4:
    st.subheader("Block Schedule Timeline & 3D View")
    plan_df, un_df = run_scheduler(tasks_df, blocks_df, weights)

    if plan_df.empty:
        st.info("Generate a plan from the 'Block Plan' tab to see the visualization.")
    else:
        viz_df = plan_df.copy()
        viz_df["start_dt"] = viz_df.apply(
            lambda r: datetime.combine(
                parse_date(r["date"]),
                datetime.strptime(str(r["start_time"]).strip(), "%H:%M").time()
            ),
            axis=1,
        )
        viz_df["end_dt"] = viz_df.apply(
            lambda r: datetime.combine(
                parse_date(r["date"]),
                datetime.strptime(str(r["end_time"]).strip(), "%H:%M").time()
            ),
            axis=1,
        )

        # 2D timeline
        st.markdown("#### 2D Block Timeline (Control Office View)")
        fig = px.timeline(
            viz_df,
            x_start="start_dt",
            x_end="end_dt",
            y="corridor",
            color="department",
            hover_data=[
                "block_id",
                "task_id",
                "description",
                "priority_score",
                "task_duration_min",
            ],
        )
        fig.update_yaxes(autorange="reversed")
        fig.update_layout(
            height=350,
            xaxis_title="Time",
            yaxis_title="Corridor / Section",
            legend_title_text="Department",
        )
        st.plotly_chart(fig, use_container_width=True)

        # 3D scatter
        st.markdown("#### 3D Maintenance Space (Corridor × Time × Priority)")
        corridors = sorted(viz_df["corridor"].unique())
        corr_map = {c: i for i, c in enumerate(corridors)}
        viz_df["corr_index"] = viz_df["corridor"].map(corr_map)

        fig3d = px.scatter_3d(
            viz_df,
            x="corr_index",
            y="start_dt",
            z="priority_score",
            color="department",
            size="task_duration_min",
            hover_data=[
                "corridor",
                "block_id",
                "task_id",
                "description",
                "priority_score",
                "task_duration_min",
            ],
        )
        fig3d.update_layout(
            scene=dict(
                xaxis=dict(
                    title="Corridor",
                    tickvals=list(corr_map.values()),
                    ticktext=list(corr_map.keys()),
                ),
                yaxis_title="Start Time",
                zaxis_title="Priority Score",
            ),
            height=450,
        )
        st.plotly_chart(fig3d, use_container_width=True)

        # Risk by corridor
        st.markdown("#### Maintenance Risk by Corridor")
        risk_df = tasks_df.copy()
        risk_df["priority_score"] = risk_df.apply(
            lambda row: compute_priority_from_row(row, weights), axis=1
        )
        corr_risk = (
            risk_df.groupby("corridor")
            .agg(
                high_priority_tasks=("priority_score", lambda s: (s >= 4.0).sum()),
                total_tasks=("task_id", "count"),
            )
            .reset_index()
        )
        corr_risk["high_priority_ratio"] = (
            corr_risk["high_priority_tasks"] / corr_risk["total_tasks"]
        ).round(2)

        fig2 = px.bar(
            corr_risk,
            x="corridor",
            y="high_priority_tasks",
            color="high_priority_ratio",
            color_continuous_scale="Reds",
            labels={
                "high_priority_tasks": "High‑priority tasks",
                "corridor": "Corridor",
                "high_priority_ratio": "High‑priority / Total",
            },
            hover_data=["total_tasks", "high_priority_ratio"],
        )
        fig2.update_layout(height=300)
        st.plotly_chart(fig2, use_container_width=True)

# -----------------------------
# TAB 5 – NOTIFICATIONS & MONITORING
# -----------------------------
with tab5:
    st.subheader("Notifications & Block Monitoring")

    if not st.session_state["plan_approved"]:
        st.warning(
            "Current plan has **not** been approved by a control/safety officer. "
            "Notifications are disabled until the plan is reviewed and approved in "
            "the 'Block Plan' tab."
        )
        st.stop()

    plan_df, un_df = run_scheduler(tasks_df, blocks_df, weights)

    if "owner_name" not in tasks_df.columns or "owner_phone" not in tasks_df.columns:
        st.warning("Owner information not found in dataset (owner_name / owner_phone).")
    elif plan_df.empty:
        st.info("Generate a block plan first from the 'Block Plan' tab.")
    else:
        st.success(
            f"Plan approved by {st.session_state['approver_name'] or 'Control/Safety officer'}. "
            "Notifications below are ready to be sent (simulation)."
        )
        if st.session_state["approver_notes"]:
            st.markdown(f"**Safety review notes:** {st.session_state['approver_notes']}")

        merged = plan_df.merge(
            tasks_df[["task_id", "owner_name", "owner_phone"]],
            on="task_id",
            how="left"
        )

        dept_options = ["ALL"] + sorted(merged["department"].unique().tolist())
        corridor_options = ["ALL"] + sorted(merged["corridor"].unique().tolist())

        col_f1, col_f2 = st.columns(2)
        selected_dept = col_f1.selectbox("Filter by department", dept_options)
        selected_corr = col_f2.selectbox("Filter by corridor", corridor_options)

        filtered = merged.copy()
        if selected_dept != "ALL":
            filtered = filtered[filtered["department"] == selected_dept]
        if selected_corr != "ALL":
            filtered = filtered[filtered["corridor"] == selected_corr]

        notifications = []
        for (block_id, dept), grp in filtered.groupby(["block_id", "department"]):
            corridor = grp["corridor"].iloc[0]
            date = grp["date"].iloc[0]
            start = grp["start_time"].iloc[0]
            end = grp["end_time"].iloc[0]
            task_list = ", ".join(grp["task_id"].tolist())

            for owner, phone in grp[["owner_name", "owner_phone"]].drop_duplicates().itertuples(index=False):
                if pd.isna(owner) and pd.isna(phone):
                    continue
                key = f"{block_id}|{dept}|{owner}|{phone}"
                status = st.session_state["notif_status"].get(key, "Pending")
                message = (
                    f"Dear {owner}, a maintenance block is scheduled on corridor {corridor} "
                    f"from {start} to {end} on {date}. Tasks assigned: {task_list}. – Control Office"
                )
                notifications.append({
                    "block_id": block_id,
                    "department": dept,
                    "owner_name": owner,
                    "owner_phone": phone,
                    "message": message,
                    "key": key,
                    "status": status
                })

        if not notifications:
            st.info("No owners defined for tasks; cannot generate notifications.")
        else:
            notif_df = pd.DataFrame(notifications)

            if st.button("Simulate sending all visible notifications"):
                for key in notif_df["key"]:
                    st.session_state["notif_status"][key] = "Sent"
                st.success("Notifications marked as 'Sent' (simulation).")

            notif_df["status"] = notif_df["key"].map(
                lambda k: st.session_state["notif_status"].get(k, "Pending")
            )

            st.markdown("#### Notification Preview")
            st.dataframe(
                notif_df[["block_id", "department", "owner_name", "owner_phone", "message", "status"]],
                use_container_width=True
            )

            st.caption(
                "In a production system, these messages would be sent via SMS/Email "
                "APIs to the respective PWI / JE / SSE of each department."
            )

            st.markdown("#### Owner Workload Summary")
            owner_summary = (
                notif_df
                .groupby(["department", "owner_name", "owner_phone"])
                .agg(
                    blocks_assigned=("block_id", "nunique"),
                    notifications=("message", "count")
                )
                .reset_index()
            )
            st.dataframe(
                owner_summary[["department", "owner_name", "owner_phone", "blocks_assigned", "notifications"]],
                use_container_width=True
            )