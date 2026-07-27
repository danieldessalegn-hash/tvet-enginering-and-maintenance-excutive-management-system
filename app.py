import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
import hashlib
import re
import qrcode
from io import BytesIO
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ---------------------------------------------------------
# 1. STREAMLIT PAGE CONFIG & RESPONSIVE CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="የፌደራል ቲቬት የምህንድስና እና ጥገና ስራ አስፈፃሚ የማነጅመንት ሲስተም | Federal TVET System v14.1", 
    layout="wide", 
    page_icon="🏗️"
)

# Dark-Navy theme with responsive forced PC-style layout rules for Mobile Devices
st.markdown("""
<style>
    @viewport { width: 1200px; zoom: 1.0; }
    
    .stApp { background-color: #0F172A; color: #F8FAFC; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #38BDF8 !important; }
    
    .top-bar-title {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: #F8FAFC;
        padding: 18px 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
        border-bottom: 4px solid #38BDF8;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
    }
    
    .top-bar-title h2 {
        font-size: 1.4rem;
        margin: 0;
        font-weight: 700;
        color: #F8FAFC;
    }
    .top-bar-title h4 {
        font-size: 1.0rem;
        margin-top: 5px;
        font-weight: 400;
        color: #94A3B8;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        background-color: #2563EB;
        color: white;
        border: none;
    }
    .stButton > button:hover {
        background-color: #1D4ED8;
        color: white;
    }
    
    .narrative-card {
        background-color: #1E293B;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #38BDF8;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# HELPER FUNCTIONS & SECURITY
# ---------------------------------------------------------
SALT = "TVET_CMMS_ENTERPRISE_SALT_2026"

def hash_password(password: str) -> str:
    return hashlib.sha256((password + SALT).encode('utf-8')).hexdigest()

def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "የይለፍ ቃል ቢያንስ 8 ቁምፊዎች ሊኖረው ይገባል!"
    if not re.search(r"\d", password):
        return False, "የይለፍ ቃል ቢያንስ አንድ ቁጥር (0-9) ማካተት አለበት!"
    if not re.search(r"[A-Z]", password):
        return False, "የይለፍ ቃል ቢያንስ አንድ ትልቅ እንግሊዝኛ ሌተር (A-Z) ማካተት አለበት!"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "የይለፍ ቃል ቢያንስ አንድ ልዩ ምልክት (@, #, $, %, ...) ማካተት አለበት!"
    return True, "Strong"

def sanitize_input(text: str) -> str:
    if not isinstance(text, str):
        return text
    clean_text = re.sub(r'<[^>]*>', '', text)
    return clean_text.replace('"', '&quot;').replace("'", "&#39;").strip()

def send_welcome_email(to_email: str, username: str, temp_pass: str):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "your-system-email@gmail.com"
    sender_password = "your-app-password"

    subject = "🔑 Federal TVET Executive System - Account Credentials"
    body = f"""
    ሰላም፣
    በ ፌደራል ቲቬት የምህንድስና እና ጥገና ስራ አስፈፃሚ የማነጅመንት ሲስተም ላይ አካውንትዎ ተፈጥሯል።
    
    Username: {username}
    Temporary Password: {temp_pass}
    
    እባክዎን ሲስተሙ እንደገቡ የይለፍ ቃልዎን ይቅየሩ።
    """
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception:
        return False

# ---------------------------------------------------------
# DATA FILES & AUTOMATED SEED DATA
# ---------------------------------------------------------
USER_FILE = "tvet_users.csv"
ANNUAL_PLAN_FILE = "tvet_annual_plan.csv"
ASSETS_FILE = "tvet_asset_register.csv"
INVENTORY_FILE = "tvet_inventory.csv"
PREVENTIVE_FILE = "tvet_preventive_maint.csv"
CORRECTIVE_FILE = "tvet_corrective_maint.csv"
PROGRESS_LOG_FILE = "tvet_progress_logs.csv"

user_cols = ["Full Name", "Department", "Job Title / Responsibility", "Role Privilege", "Username", "Password", "Email", "Registered Date"]
plan_cols = ["Plan ID", "Department", "Work Category", "Task Title", "Location", "Quarter", "Execution Mode", "Contractor Name", "Contract Ref No", "Contract Terms", "Start Date", "End Date", "Priority Level", "Assigned Team", "Budget (ETB)", "Progress (%)", "Status"]
asset_cols = ["Asset ID", "Asset Name", "Category", "Department", "Location", "Purchase Date", "Cost (ETB)", "Condition", "Status", "QR Code Data"]
inventory_cols = ["Item Code", "Item Name", "Category", "Quantity In Stock", "Min Reorder Level", "Unit Cost (ETB)", "Total Value (ETB)", "Storage Bin"]
preventive_cols = ["PM ID", "Asset ID / Title", "Frequency", "Assigned Technician", "Last Service Date", "Next Scheduled Date", "Status"]
corrective_cols = ["Work Order ID", "Asset / Location", "Issue Description", "Reported By", "Reported Date", "Priority", "Technician Assigned", "Status"]
progress_cols = ["Plan ID", "Update Date", "Added Progress (%)", "Total Progress (%)", "General Status", "Good Aspects", "Problems Faced", "Solutions Applied", "Unresolved Issues", "Updated By"]

def seed_initial_data():
    if not os.path.exists(USER_FILE):
        df_users = pd.DataFrame([
            ["System Administrator", "Engineering Exec", "System Admin", "Admin", "admin", hash_password("Admin@1234"), "admin@tvet.gov.et", "2026-01-01"],
            ["አበበ በቀለ", "Construction", "Project Manager", "Editor", "abebe", hash_password("User@1234"), "abebe@tvet.gov.et", "2026-02-10"],
            ["ሰላም ተስፋዬ", "Electrical", "Inspector", "Viewer", "selam", hash_password("User@1234"), "selam@tvet.gov.et", "2026-03-15"]
        ], columns=user_cols)
        df_users.to_csv(USER_FILE, index=False)

    if not os.path.exists(ANNUAL_PLAN_FILE):
        df_plan = pd.DataFrame([
            ["PLAN-101", "Construction", "New Project", "የአዲስ ግንባታ", "ብሎክ A", "Q1", "In-House (በውስጥ አቅም)", "N/A", "N/A", "N/A", "2026-01-10", "2026-06-30", "🔴 High / Emergency", "ቡድን A", 450000.0, 75, "In Progress"],
            ["PLAN-102", "Electrical", "Maintenance", "ትራንስፎርመር ጥገና", "ዋና ግቢ", "Q2", "Outsourced / Contract (በጨረታ)", "ኢትዮ ኤሌክትሪክ", "CNT-2026-09", "የ 1 ዓመት ዋስትና", "2026-02-01", "2026-04-15", "🔴 High / Emergency", "የውጭ ኮንትራክተር", 120000.0, 100, "Completed"]
        ], columns=plan_cols)
        df_plan.to_csv(ANNUAL_PLAN_FILE, index=False)

    if not os.path.exists(ASSETS_FILE):
        df_assets = pd.DataFrame([
            ["AST-101", "CNC Lathe Machine", "Machinery", "Mechanical", "ዎርክሾፕ 2", "2024-05-12", 850000.0, "Good", "Active", "ASSET-AST-101-CNC Lathe"],
            ["AST-102", "3D Printer Industrial", "IT Equipment", "IT/Admin", "ላብራቶሪ 1", "2025-01-20", 320000.0, "Excellent", "Active", "ASSET-AST-102-3D Printer"]
        ], columns=asset_cols)
        df_assets.to_csv(ASSETS_FILE, index=False)

    if not os.path.exists(INVENTORY_FILE):
        df_inv = pd.DataFrame([
            ["SKU-101", "MCB Breaker 3-Phase 63A", "Electrical Spare", 45, 10, 1200.0, 54000.0, "Bin-E04"],
            ["SKU-102", "PPR Pipe 32mm", "Sanitary Fitting", 8, 15, 450.0, 3600.0, "Bin-S01"]
        ], columns=inventory_cols)
        df_inv.to_csv(INVENTORY_FILE, index=False)

    if not os.path.exists(PREVENTIVE_FILE):
        df_prev = pd.DataFrame([
            ["PM-101", "CNC Lathe Machine", "Monthly", "ኢንጂነር ካሳሁን", "2026-06-01", "2026-07-01", "Scheduled"]
        ], columns=preventive_cols)
        df_prev.to_csv(PREVENTIVE_FILE, index=False)

    if not os.path.exists(CORRECTIVE_FILE):
        df_corr = pd.DataFrame([
            ["WO-101", "ላብራቶሪ 1 - AC Unit", "ቅዝቃዜ ማቆም", "ጥበቡ ከበደ", "2026-07-20", "🟡 High", "ፍስሐ ኃይሉ", "Open"]
        ], columns=corrective_cols)
        df_corr.to_csv(CORRECTIVE_FILE, index=False)

    if not os.path.exists(PROGRESS_LOG_FILE):
        df_prog = pd.DataFrame(columns=progress_cols)
        df_prog.to_csv(PROGRESS_LOG_FILE, index=False)

seed_initial_data()

def load_data(file_path, columns):
    try:
        df = pd.read_csv(file_path)
        for col in columns:
            if col not in df.columns:
                df[col] = "N/A"
        return df
    except Exception:
        return pd.DataFrame(columns=columns)

def save_data(df, file_path):
    df.to_csv(file_path, index=False)

users_df = load_data(USER_FILE, user_cols)
plan_df = load_data(ANNUAL_PLAN_FILE, plan_cols)
assets_df = load_data(ASSETS_FILE, asset_cols)
inventory_df = load_data(INVENTORY_FILE, inventory_cols)
preventive_df = load_data(PREVENTIVE_FILE, preventive_cols)
corrective_df = load_data(CORRECTIVE_FILE, corrective_cols)
progress_df = load_data(PROGRESS_LOG_FILE, progress_cols)

def process_and_sort_plans(df):
    if df.empty:
        return df
    df["Progress (%)"] = pd.to_numeric(df["Progress (%)"], errors='coerce').fillna(0).astype(int)
    df["Budget (ETB)"] = pd.to_numeric(df["Budget (ETB)"], errors='coerce').fillna(0.0)
    priority_weights = {"🔴 High / Emergency": 3, "🟡 Medium": 2, "🟢 Low": 1}
    df["Priority_Score"] = df["Priority Level"].map(priority_weights).fillna(1)
    df["Temp_End_Date"] = pd.to_datetime(df["End Date"], errors='coerce')
    df = df.sort_values(by=["Status", "Priority_Score", "Temp_End_Date"], ascending=[True, False, True]).drop(columns=["Priority_Score", "Temp_End_Date"])
    return df

plan_df = process_and_sort_plans(plan_df)

# ---------------------------------------------------------
# AUTHENTICATION & SESSION STATE
# ---------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
if 'failed_attempts' not in st.session_state:
    st.session_state.failed_attempts = 0
if 'form_key_suffix' not in st.session_state:
    st.session_state.form_key_suffix = 0
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "📊 Dashboard"

def reset_form_inputs():
    st.session_state.form_key_suffix += 1

def login():
    st.title("🏗️ የፌደራል ቲቬት የምህንድስና እና ጥገና ስራ አስፈፃሚ የማነጅመንት ሲስተም")
    st.caption("Federal TVET Engineering & Maintenance Executive Management System")
    
    users_df = load_data(USER_FILE, user_cols)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔑 የመግቢያ ፎርም")
        if st.session_state.failed_attempts >= 5:
            st.error("⛔ በተደጋጋሚ የተሳሳተ የይለፍ ቃል በመሞከርዎ አካውንቱ ተቆልፏል!")
            st.stop()

        input_user = sanitize_input(st.text_input("የተጠቃሚ ስም (Username):"))
        input_pass = st.text_input("የመተላለፊያ ቃል (Password):", type="password")

        if st.button("ወደ ሲስተሙ ግባ (Secure Login)", use_container_width=True):
            input_user_clean = input_user.strip()
            input_pass_clean = input_pass.strip()
            salted_hash = hash_password(input_pass_clean)

            user_match = users_df[
                (users_df["Username"].astype(str).str.strip() == input_user_clean) & 
                ((users_df["Password"].astype(str).str.strip() == salted_hash) | 
                 (users_df["Password"].astype(str).str.strip() == input_pass_clean))
            ]

            if not user_match.empty:
                st.session_state.logged_in = True
                st.session_state.user_info = user_match.iloc[0].to_dict()
                st.session_state.failed_attempts = 0
                st.success(f"እንኳን በደህና መጡ {st.session_state.user_info.get('Full Name', 'Admin')}!")
                st.rerun()
            else:
                st.session_state.failed_attempts += 1
                remaining_attempts = 5 - st.session_state.failed_attempts
                st.error(f"⛔ የተሳሳተ የተጠቃሚ ስም ወይም የይለፍ ቃል! (የቀረዎት ሙከራ፦ {remaining_attempts})")

if not st.session_state.logged_in:
    login()
    st.stop()

user = st.session_state.user_info
user_role = user.get("Role Privilege", "Viewer") 
if "Admin" in user_role:
    role = "Admin"
elif "Editor" in user_role:
    role = "Editor"
else:
    role = "Viewer"

# ---------------------------------------------------------
# TOP BAR TITLE
# ---------------------------------------------------------
st.markdown("""
<div class='top-bar-title'>
    <h2>የፌደራል ቲቬት የምህንድስና እና ጥገና ስራ አስፈፃሚ የማነጅመንት ሲስተም</h2>
    <h4>Federal TVET Engineering & Maintenance Executive Management System</h4>
</div>
""", unsafe_allow_html=True)

tab_names = [
    "📊 Dashboard", 
    "🛠️ Maintenance", 
    "📅 Preventive", 
    "🏷️ Assets & QR", 
    "📊 Projects", 
    "📦 Inventory", 
    "📈 Reports", 
    "👥 Users", 
    "⚙️ Settings"
]

cols = st.columns(len(tab_names))
for i, tab in enumerate(tab_names):
    btn_type = "primary" if st.session_state.active_tab == tab else "secondary"
    if cols[i].button(tab, key=f"top_tab_{i}", type=btn_type, use_container_width=True):
        st.session_state.active_tab = tab
        st.rerun()

st.markdown("---")

# SIDEBAR USER PROFILE
st.sidebar.title(f"👤 {user['Full Name']}")
st.sidebar.info(f"**ክፍል:** {user['Department']}\n\n**ስልጣን:** `{role}`")
if role in ["Admin", "Editor"]:
    st.sidebar.success("✏️ የኤዲቲንግ ባለስልጣን (Editor Privilege) አለዎት።")

if st.sidebar.button("🚪 ውጣ (Logout)", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.rerun()

st.sidebar.markdown("---")

active = st.session_state.active_tab

def render_editable_df(df, key_prefix="df"):
    if role in ["Admin", "Editor"]:
        st.caption("✏️ *የኤዲቲንግ ስልጣን ስለሎት በሰንጠረዡ ላይ በቀጥታ በመጫን ማስተካከል ይችላሉ*")
        edited_df = st.data_editor(df, use_container_width=True, key=f"{key_prefix}_editor")
        return edited_df
    else:
        st.dataframe(df, use_container_width=True)
        return df

# ---------------------------------------------------------
# ROUTING & MODULES
# ---------------------------------------------------------

# --- 1. DASHBOARD ---
if active == "📊 Dashboard":
    st.sidebar.markdown("### 📊 Dashboard Sub-Menu")
    sub_dash = st.sidebar.radio("ምረጥ:", ["የአጠቃላይ ሁኔታ (Overview)", "የእያንዳንዱ ስራ አፈፃፀም", "ፈጣን KPIs"])
    st.title("📊 Executive Dashboard Analytics")
    
    if sub_dash == "የአጠቃላይ ሁኔታ (Overview)":
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        tot_plans = len(plan_df)
        comp_plans = len(plan_df[plan_df["Status"] == "Completed"]) if not plan_df.empty else 0
        prog_plans = len(plan_df[plan_df["Status"] == "In Progress"]) if not plan_df.empty else 0
        tot_budget = plan_df["Budget (ETB)"].sum() if not plan_df.empty else 0
        avg_prog = plan_df["Progress (%)"].mean() if not plan_df.empty else 0
        tot_assets = len(assets_df)

        k1.metric("ጠቅላላ ፕሮጀክቶች", tot_plans)
        k2.metric("የተጠናቀቁ", comp_plans)
        k3.metric("በሂደት ላይ ያሉ", prog_plans)
        k4.metric("አማካይ አፈፃፀም", f"{avg_prog:.1f}%")
        k5.metric("ጠቅላላ በጀት", f"{tot_budget:,.0f} ETB")
        k6.metric("የተመዘገቡ ንብረቶች", tot_assets)

        st.markdown("---")
        
        c_g1, c_g2 = st.columns([1, 2])
        with c_g1:
            st.subheader("🎯 አጠቃላይ ፕሮጀክት Progress Indicator")
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = avg_prog,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Average Completion Rate"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "#38BDF8"},
                    'steps': [
                        {'range': [0, 40], 'color': "#EF4444"},
                        {'range': [40, 75], 'color': "#F59E0B"},
                        {'range': [75, 100], 'color': "#10B981"}
                    ]
                }
            ))
            fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font={'color': "white"})
            st.plotly_chart(fig_gauge, use_container_width=True)

        with c_g2:
            st.subheader("📌 በስራ ዘርፍ እና አይነት የተሰሩ ስራዎች")
            if not plan_df.empty:
                fig1 = px.histogram(plan_df, x="Department", color="Work Category", barmode="group", text_auto=True, template="plotly_dark")
                st.plotly_chart(fig1, use_container_width=True)

    elif sub_dash == "የእያንዳንዱ ስራ አፈፃፀም":
        st.subheader("📋 የእያንዳንዱ ስራ አፈፃፀም ከነ ስሙ (Individual Project Progress)")
        if not plan_df.empty:
            fig_bar = px.bar(
                plan_df, 
                x="Progress (%)", 
                y="Task Title", 
                color="Department", 
                text="Progress (%)",
                orientation='h',
                title="የእያንዳንዱ ስራ የአፈፃፀም ፐርሰንት",
                template="plotly_dark",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.markdown("### 🔍 ዝርዝር የአፈፃፀም ሰንጠረዥ")
            disp_df = plan_df[["Plan ID", "Task Title", "Department", "Assigned Team", "Budget (ETB)", "Progress (%)", "Status"]].copy()
            render_editable_df(disp_df, key_prefix="dash_indiv")

    elif sub_dash == "ፈጣን KPIs":
        st.subheader("⚡ ፈጣን የስራ አፈፃፀም መላኪያዎች (KPIs)")
        c1, c2, c3 = st.columns(3)
        c1.metric("የተጠናቀቁ ጥገናዎች", len(corrective_df[corrective_df["Status"]=="Completed"]) if not corrective_df.empty else 0)
        c2.metric("ክፍት የጥገና ጥያቄዎች", len(corrective_df[corrective_df["Status"]=="Open"]) if not corrective_df.empty else 0)
        
        if not inventory_df.empty:
            inv_stock = pd.to_numeric(inventory_df["Quantity In Stock"], errors="coerce").fillna(0)
            inv_min = pd.to_numeric(inventory_df["Min Reorder Level"], errors="coerce").fillna(0)
            low_stock_count = len(inventory_df[inv_stock <= inv_min])
        else:
            low_stock_count = 0
            
        c3.metric("ያለቁ የመጋዘን እቃዎች", low_stock_count)

# --- 2. MAINTENANCE ---
elif active == "🛠️ Maintenance":
    st.sidebar.markdown("### 🛠️ Maintenance Sub-Menu")
    menu_options = ["የጥገና ጥያቄዎች (Requests)"]
    if role in ["Admin", "Editor"]:
        menu_options.append("አዲስ የጥገና ጥያቄ")
        
    sub_maint = st.sidebar.radio("ምረጥ:", menu_options)
    st.title("🛠️ Maintenance CMMS - የጥገና ስራዎች")
    
    if sub_maint == "የጥገና ጥያቄዎች (Requests)":
        st.subheader("📋 የጥገና ጥያቄዎች ዝርዝር")
        edited_maint = render_editable_df(corrective_df, key_prefix="maint_req")
        if role in ["Admin", "Editor"] and st.button("💾 የጥገና ለውጦችን ሴቭ አድርግ"):
            save_data(edited_maint, CORRECTIVE_FILE)
            st.success("✅ ለውጦቹ ተቀምጠዋል!")
            st.rerun()

    elif sub_maint == "አዲስ የጥገና ጥያቄ" and role in ["Admin", "Editor"]:
        k = st.session_state.form_key_suffix
        with st.form(f"corrective_form_{k}"):
            st.subheader("📝 አዲስ የጥገና ጥያቄ አስገባ")
            c1, c2 = st.columns(2)
            with c1:
                asset_loc = sanitize_input(st.text_input("የንብረቱ/ቦታው መግለጫ*", key=f"c_loc_{k}"))
                rep_by = sanitize_input(st.text_input("ሪፖርት ያደረገው ሰው/ክፍል*", key=f"c_rep_{k}"))
                priority = st.selectbox("የአስቸኳይነት ደረጃ*", ["🔴 Emergency", "🟡 High", "🟢 Normal"], key=f"c_prio_{k}")
            with c2:
                tech = sanitize_input(st.text_input("የተመደበው ባለሙያ/ቡድን*", key=f"c_tech_{k}"))
                desc = sanitize_input(st.text_area("የብልሽቱ አይነት መግለጫ*", key=f"c_desc_{k}"))
            
            if st.form_submit_button("💾 ጥያቄውን መዝግብ"):
                if asset_loc and desc:
                    w_id = f"WO-{len(corrective_df) + 101}"
                    new_row = pd.DataFrame([[
                        w_id, asset_loc, desc, rep_by, datetime.now().strftime("%Y-%m-%d"), priority, tech, "Open"
                    ]], columns=corrective_cols)
                    corrective_df = pd.concat([corrective_df, new_row], ignore_index=True)
                    save_data(corrective_df, CORRECTIVE_FILE)
                    st.success(f"✅ የጥገና ጥያቄው ተመዝግቧል! Work Order ID: `{w_id}`")
                    reset_form_inputs()
                    st.rerun()

# --- 3. PREVENTIVE MAINTENANCE ---
elif active == "📅 Preventive":
    st.sidebar.markdown("### 📅 Preventive Sub-Menu")
    menu_options = ["የጥገና መርሃ-ግብር (Schedules)"]
    if role in ["Admin", "Editor"]:
        menu_options.append("አዲስ መርሃግብር ጨምር")
        
    sub_prev = st.sidebar.radio("ምረጥ:", menu_options)
    st.title("📅 Preventive Maintenance (የቅድመ-መከላከል ጥገና)")
    
    if sub_prev == "የጥገና መርሃ-ግብር (Schedules)":
        st.subheader("📋 የቅድመ-መከላከል ጥገና መርሃግብሮች")
        edited_prev = render_editable_df(preventive_df, key_prefix="prev_sched")
        if role in ["Admin", "Editor"] and st.button("💾 የመርሃግብር ለውጦችን ሴቭ አድርግ"):
            save_data(edited_prev, PREVENTIVE_FILE)
            st.success("✅ ለውጦቹ ተቀምጠዋል!")
            st.rerun()

    elif sub_prev == "አዲስ መርሃግብር ጨምር" and role in ["Admin", "Editor"]:
        k = st.session_state.form_key_suffix
        with st.form(f"pm_form_{k}"):
            st.subheader("➕ አዲስ የቅድመ-መከላከል መርሃግብር መመዝገቢያ")
            c1, c2 = st.columns(2)
            with c1:
                pm_asset = sanitize_input(st.text_input("የንብረቱ ID ወይም አርእስት*", key=f"pm_ast_{k}"))
                freq = st.selectbox("የጥገና ድግግሞሽ*", ["Weekly", "Monthly", "Quarterly", "Annual"], key=f"pm_freq_{k}")
            with c2:
                tech = sanitize_input(st.text_input("ኃላፊ ባለሙያ*", key=f"pm_tech_{k}"))
                next_d = st.date_input("ቀጣይ የጥገና ቀን*", value=date.today(), key=f"pm_next_{k}")
                
            if st.form_submit_button("💾 መርሃግብር መዝግብ"):
                if pm_asset:
                    pm_id = f"PM-{len(preventive_df) + 101}"
                    new_row = pd.DataFrame([[
                        pm_id, pm_asset, freq, tech, datetime.now().strftime("%Y-%m-%d"), str(next_d), "Scheduled"
                    ]], columns=preventive_cols)
                    preventive_df = pd.concat([preventive_df, new_row], ignore_index=True)
                    save_data(preventive_df, PREVENTIVE_FILE)
                    st.success(f"✅ የቅድመ-መከላከል መርሃግብር ተመዝግቧል! PM ID: `{pm_id}`")
                    reset_form_inputs()
                    st.rerun()

# --- 4. ASSETS & ADVANCED QR GENERATOR ---
elif active == "🏷️ Assets & QR":
    st.sidebar.markdown("### 🏷️ Assets Sub-Menu")
    menu_options = ["የተመዘገቡ ንብረቶች መዝገብ", "የ QR Code Generator"]
    if role in ["Admin", "Editor"]:
        menu_options.append("አዲስ ንብረት መመዝገቢያ")
        
    sub_asset = st.sidebar.radio("ምረጥ:", menu_options)
    st.title("🏷️ Asset Register & Advanced QR Code Generator")
    
    if sub_asset == "የተመዘገቡ ንብረቶች መዝገብ":
        st.subheader("📋 የተመዘገቡ ንብረቶች መዝገብ")
        edited_asset = render_editable_df(assets_df, key_prefix="asset_reg")
        if role in ["Admin", "Editor"] and st.button("💾 የንብረት ለውጦችን ሴቭ አድርግ"):
            save_data(edited_asset, ASSETS_FILE)
            st.success("✅ ለውጦቹ ተቀምጠዋል!")
            st.rerun()

    elif sub_asset == "የ QR Code Generator":
        st.subheader("🖨️ የንብረቶች QR Code ማፍለቂያ እና ማውረጃ (Dynamic PNG)")
        if not assets_df.empty:
            selected_asset_id = st.selectbox("QR Code የሚሰራለትን ንብረት ይምረጡ:", assets_df["Asset ID"].tolist())
            asset_data = assets_df[assets_df["Asset ID"] == selected_asset_id].iloc[0]
            
            qr_string = f"Asset ID: {asset_data['Asset ID']}\nName: {asset_data['Asset Name']}\nDept: {asset_data['Department']}\nCond: {asset_data['Condition']}"
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(qr_string)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buf = BytesIO()
            img.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            c_q1, c_q2 = st.columns(2)
            with c_q1:
                st.image(byte_im, caption=f"QR for {asset_data['Asset Name']}", width=250)
            with c_q2:
                st.write(f"**የንብረቱ ስም:** {asset_data['Asset Name']}")
                st.write(f"**መለያ ቁጥር:** {asset_data['Asset ID']}")
                st.download_button(
                    label="📥 የ QR ኮዱን በ Image (PNG) አውርድ",
                    data=byte_im,
                    file_name=f"QR_{selected_asset_id}.png",
                    mime="image/png"
                )

    elif sub_asset == "አዲስ ንብረት መመዝገቢያ" and role in ["Admin", "Editor"]:
        k = st.session_state.form_key_suffix
        with st.form(f"asset_form_{k}"):
            st.subheader("➕ አዲስ ንብረት መዝግብ")
            c1, c2 = st.columns(2)
            with c1:
                a_name = sanitize_input(st.text_input("የንብረቱ ስም*", key=f"a_name_{k}"))
                a_cat = st.selectbox("ምድብ*", ["Machinery", "Vehicle", "Electrical Unit", "Sanitary Infrastructure", "IT Equipment"], key=f"a_cat_{k}")
                a_dept = st.selectbox("የስራ ክፍል*", ["Construction", "Electrical", "Sanitary", "IT/Admin"], key=f"a_dept_{k}")
                a_cost = st.number_input("የተገዛበት ዋጋ (ETB)*", min_value=0.0, step=1000.0, key=f"a_cost_{k}")
            with c2:
                a_loc = sanitize_input(st.text_input("የሚገኝበት ቦታ/ህንፃ*", key=f"a_loc_{k}"))
                a_pdate = st.date_input("የተገዛበት ቀን*", value=date.today(), key=f"a_pdate_{k}")
                a_cond = st.selectbox("የአሁን ሁኔታ*", ["Excellent", "Good", "Needs Maintenance", "Critical"], key=f"a_cond_{k}")
                
            if st.form_submit_button("💾 ንብረቱን መዝግብ"):
                if a_name and a_loc:
                    ast_id = f"AST-{len(assets_df) + 101}"
                    qr_data = f"ASSET-{ast_id}-{a_name}"
                    new_row = pd.DataFrame([[
                        ast_id, a_name, a_cat, a_dept, a_loc, str(a_pdate), a_cost, a_cond, "Active", qr_data
                    ]], columns=asset_cols)
                    assets_df = pd.concat([assets_df, new_row], ignore_index=True)
                    save_data(assets_df, ASSETS_FILE)
                    st.success(f"✅ ንብረቱ በስኬት ተመዝግቧል! Asset ID: `{ast_id}`")
                    reset_form_inputs()
                    st.rerun()

# --- 5. PROJECTS ---
elif active == "📊 Projects":
    st.sidebar.markdown("### 📊 Project Sub-Menu")
    menu_options = ["የስራዎች መዝገብና ኤዲት ማድረጊያ"]
    if role in ["Admin", "Editor"]:
        menu_options.extend(["አዲስ ስራ መመዝገቢያ", "በኤክስኤል (Excel) እቅድ ማስገቢያ", "የፕሮግረስ እና ናሬሽን ማዘመኛ"])
        
    sub_proj = st.sidebar.radio("ምረጥ:", menu_options)
    st.title("📊 Projects Management")
    
    if sub_proj == "የስራዎች መዝገብና ኤዲት ማድረጊያ":
        st.subheader("📋 ሁሉም የተመዘገቡ ስራዎች")
        edited_plan = render_editable_df(plan_df, key_prefix="projects_reg")
        if role in ["Admin", "Editor"] and st.button("💾 የስራዎች ለውጦችን ሴቭ አድርግ"):
            save_data(edited_plan, ANNUAL_PLAN_FILE)
            st.success("✅ ለውጦቹ ተቀምጠዋል!")
            st.rerun()

    elif sub_proj == "አዲስ ስራ መመዝገቢያ" and role in ["Admin", "Editor"]:
        k = st.session_state.form_key_suffix
        with st.form(f"manual_task_form_{k}"):
            st.subheader("📝 በእጅ አዲስ ስራ መመዝገቢያ")
            c1, c2 = st.columns(2)
            with c1:
                t_dept = st.selectbox("የስራ ዘርፍ", ["Construction", "Electrical", "Sanitary"], key=f"t_dept_{k}")
                t_cat = st.selectbox("የስራ አይነት", ["New Project", "Maintenance"], key=f"t_cat_{k}")
                t_title = sanitize_input(st.text_input("የስራው መግለጫ / አርእስት*", key=f"t_title_{k}"))
                t_loc = sanitize_input(st.text_input("የሚሰራበት ቦታ / ህንፃ*", key=f"t_loc_{k}"))
                t_mode = st.selectbox("የአሰራር ሁኔታ*", ["In-House (በውስጥ አቅም)", "Outsourced / Contract (በጨረታ)"], key=f"t_mode_{k}")
                t_team = sanitize_input(st.text_input("ኃላፊነት የተሰጠው ቡድን/ባለሙያ*", key=f"t_team_{k}"))
            
            with c2:
                t_qtr = st.selectbox("Quarter", ["Q1", "Q2", "Q3", "Q4"], key=f"t_qtr_{k}")
                t_start = st.date_input("Start Date", value=date.today(), key=f"t_start_{k}")
                t_end = st.date_input("End Date", value=date.today(), key=f"t_end_{k}")
                t_prio = st.selectbox("የአስቸኳይነት ደረጃ*", ["🔴 High / Emergency", "🟡 Medium", "🟢 Low"], key=f"t_prio_{k}")
                t_budget = st.number_input("የተመደበ በጀት (ETB)", min_value=0.0, step=1000.0, key=f"t_budget_{k}")

            c_name = sanitize_input(st.text_input("የኮንትራክተር ስም (ካለ)", value="N/A", key=f"c_name_{k}"))
            c_ref = sanitize_input(st.text_input("የውል ስምምነት ቁጥር (ካለ)", value="N/A", key=f"c_ref_{k}"))
            c_terms = sanitize_input(st.text_area("የውል አስፈላጊ ሁኔታዎች", value="N/A", key=f"c_terms_{k}"))

            if st.form_submit_button("💾 ስራውን መዝግብ"):
                if t_title and t_loc:
                    new_id = f"PLAN-{len(plan_df) + 101}"
                    new_task_row = pd.DataFrame([[
                        new_id, t_dept, t_cat, t_title, t_loc, t_qtr, 
                        t_mode, c_name, c_ref, c_terms,
                        str(t_start), str(t_end), t_prio, t_team, t_budget, 0, "Open"
                    ]], columns=plan_cols)
                    
                    plan_df = pd.concat([plan_df, new_task_row], ignore_index=True)
                    plan_df = process_and_sort_plans(plan_df)
                    save_data(plan_df, ANNUAL_PLAN_FILE)
                    st.success(f"✅ ስራው በስኬት ተመዝግቧል! ID: `{new_id}`")
                    reset_form_inputs()
                    st.rerun()

    elif sub_proj == "በኤክስኤል (Excel) እቅድ ማስገቢያ" and role in ["Admin", "Editor"]:
        st.subheader("📁 የዓመት እቅድ በ Excel / CSV አፕሎድ ማድረጊያ (Batch Import)")
        st.info("💡 የኤክስኤል ወይም CSV ፋይልዎ የሚከተሉትን ኮለምኖች (Columns) ማካተት አለበት፦ " + ", ".join(plan_cols[1:-2]))
        
        uploaded_file = st.file_uploader("የእቅድ ፋይል ይምረጡ (.xlsx ወይም .csv):", type=["xlsx", "csv"])
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    import_df = pd.read_csv(uploaded_file)
                else:
                    import_df = pd.read_excel(uploaded_file)
                
                st.write("📄 **የተጫነው ፋይል ቅድመ-እይታ (Preview):**")
                st.dataframe(import_df.head(), use_container_width=True)
                
                if st.button("🚀 እቅዶቹን ወደ ሲስተሙ አስገባ (Import All)"):
                    added_count = 0
                    for index, row in import_df.iterrows():
                        new_id = f"PLAN-{len(plan_df) + 101 + added_count}"
                        
                        new_row = pd.DataFrame([[
                            new_id,
                            row.get("Department", "Engineering Exec"),
                            row.get("Work Category", "New Project"),
                            row.get("Task Title", "Untitled Plan"),
                            row.get("Location", "Main Campus"),
                            row.get("Quarter", "Q1"),
                            row.get("Execution Mode", "In-House"),
                            row.get("Contractor Name", "N/A"),
                            row.get("Contract Ref No", "N/A"),
                            row.get("Contract Terms", "N/A"),
                            str(row.get("Start Date", date.today())),
                            str(row.get("End Date", date.today())),
                            row.get("Priority Level", "🟡 Medium"),
                            row.get("Assigned Team", "Team A"),
                            float(row.get("Budget (ETB)", 0.0)),
                            0,
                            "Open"
                        ]], columns=plan_cols)
                        
                        plan_df = pd.concat([plan_df, new_row], ignore_index=True)
                        added_count += 1
                        
                    plan_df = process_and_sort_plans(plan_df)
                    save_data(plan_df, ANNUAL_PLAN_FILE)
                    st.success(f"✅ በስኬት {added_count} አዳዲስ እቅዶች ከኤክስኤል ገብተዋል!")
                    st.rerun()
            except Exception as e:
                st.error(f"⛔ ፋይሉን ማስገባት አልተቻለም፦ {e}")

    elif sub_proj == "የፕሮግረስ እና ናሬሽን ማዘመኛ" and role in ["Admin", "Editor"]:
        st.subheader("🔄 የሥራ ፕሮግረስ እና የናሬሽን ማዘመኛ")
        if not plan_df.empty:
            sel_p = st.selectbox("የሚሰሩበትን ስራ ይምረጡ:", plan_df["Plan ID"].dropna().tolist(), key="p_sel_narrative")
            p_data = plan_df[plan_df["Plan ID"] == sel_p].iloc[0]
            curr_prog = int(p_data.get("Progress (%)", 0))
            
            st.info(f"📌 **የተመረጠው ስራ:** {p_data['Task Title']} | **ያሁኑ ፕሮግረስ:** {curr_prog}%")
            
            k = st.session_state.form_key_suffix
            with st.form(f"prog_update_form_{k}"):
                c_pr1, c_pr2 = st.columns(2)
                with c_pr1:
                    added_p = st.number_input("ተጨማሪ ፕሮግረስ (%) ይደመሩ:*", min_value=0, max_value=(100-curr_prog), value=0)
                    new_tot = curr_prog + added_p
                    st.write(f"📈 **አዲስ ድምር ፕሮግረስ የሚሆነው:** `{new_tot}%`")
                with c_pr2:
                    st.write("📝 **የስራ ሁኔታ ናሬሽን (Narrative Entry):**")
                
                status_gen = st.text_area("A. ስለስራው ጠቅላላ ሁኔታ*", key=f"p_a_{k}")
                good_aspects = st.text_area("B. የነበረው መልካም ነገር", key=f"p_b_{k}")
                probs = st.text_area("C. የነበሩ ችግሮች", key=f"p_c_{k}")
                solns = st.text_area("D. ችግሮቹ የተፈቱበት መንገድ", key=f"p_d_{k}")
                unsolved = st.text_area("E. ያልተፈታ ችግር ካለ", key=f"p_e_{k}")
                
                if st.form_submit_button("💾 አዲሱን ፕሮግረስ እና ናሬሽን አስገባ"):
                    auto_st = "Open" if new_tot == 0 else ("In Progress" if new_tot < 100 else "Completed")
                    
                    plan_df.loc[plan_df["Plan ID"] == sel_p, "Progress (%)"] = new_tot
                    plan_df.loc[plan_df["Plan ID"] == sel_p, "Status"] = auto_st
                    save_data(plan_df, ANNUAL_PLAN_FILE)
                    
                    new_log = pd.DataFrame([[
                        sel_p, datetime.now().strftime("%Y-%m-%d %H:%M"), added_p, new_tot,
                        status_gen, good_aspects, probs, solns, unsolved, user["Full Name"]
                    ]], columns=progress_cols)
                    
                    progress_df = pd.concat([progress_df, new_log], ignore_index=True)
                    save_data(progress_df, PROGRESS_LOG_FILE)
                    
                    st.success(f"✅ ፕሮግረሱ ወደ {new_tot}% አድጓል፤ የናሬሽን ሪፖርቱም ተመዝግቧል!")
                    reset_form_inputs()
                    st.rerun()

            st.markdown("---")
            st.subheader("📜 የቀደሙ የናሬሽን ሪፖርቶች ታሪክ")
            history_logs = progress_df[progress_df["Plan ID"] == sel_p]
            if not history_logs.empty:
                for idx, log in history_logs.iterrows():
                    st.markdown(f"""
                    <div class='narrative-card'>
                        <b>📅 ቀን፦</b> {log.get('Update Date', 'N/A')} | <b>በ፦</b> {log.get('Updated By', 'N/A')} | <b>የነበረው አዲስ ድምር፦</b> {log.get('Total Progress (%)', 0)}%<br>
                        <b>A. ጠቅላላ ሁኔታ፦</b> {log.get('General Status', 'N/A')}<br>
                        <b>B. መልካም ነገር፦</b> {log.get('Good Aspects', 'N/A')}<br>
                        <b>C. የነበሩ ችግሮች፦</b> {log.get('Problems Faced', 'N/A')}<br>
                        <b>D. የተፈቱበት መንገድ፦</b> {log.get('Solutions Applied', 'N/A')}<br>
                        <b>E. ያልተፈታ ችግር፦</b> {log.get('Unresolved Issues', 'N/A')}
                    </div>
                    """, unsafe_allow_html=True)

# --- 6. INVENTORY ---
elif active == "📦 Inventory":
    st.sidebar.markdown("### 📦 Inventory Sub-Menu")
    menu_options = ["የመጋዘን እቃዎች መዝገብ"]
    if role in ["Admin", "Editor"]:
        menu_options.append("አዲስ እቃ መመዝገቢያ")
        
    sub_inv = st.sidebar.radio("ምረጥ:", menu_options)
    st.title("📦 Inventory Management - የእቃና መለዋወጫ መጋዘን")
    
    if not inventory_df.empty:
        inventory_df["Quantity In Stock"] = pd.to_numeric(inventory_df["Quantity In Stock"], errors="coerce").fillna(0)
        inventory_df["Unit Cost (ETB)"] = pd.to_numeric(inventory_df["Unit Cost (ETB)"], errors="coerce").fillna(0)
        inventory_df["Total Value (ETB)"] = inventory_df["Quantity In Stock"] * inventory_df["Unit Cost (ETB)"]

    if sub_inv == "የመጋዘን እቃዎች መዝገብ":
        st.subheader("📋 የመጋዘን እቃዎች መዝገብ")
        edited_inv = render_editable_df(inventory_df, key_prefix="inv_reg")
        if role in ["Admin", "Editor"] and st.button("💾 የመጋዘን ለውጦችን ሴቭ አድርግ"):
            save_data(edited_inv, INVENTORY_FILE)
            st.success("✅ ለውጦቹ ተቀምጠዋል!")
            st.rerun()
            
        tot_inv_val = inventory_df["Total Value (ETB)"].sum() if not inventory_df.empty else 0
        st.metric("💰 ጠቅላላ የመጋዘን እቃዎች ዋጋ:", f"{tot_inv_val:,.2f} ETB")

    elif sub_inv == "አዲስ እቃ መመዝገቢያ" and role in ["Admin", "Editor"]:
        k = st.session_state.form_key_suffix
        with st.form(f"inv_form_{k}"):
            st.subheader("➕ አዲስ የመጋዘን እቃ መዝግብ")
            c1, c2 = st.columns(2)
            with c1:
                i_name = sanitize_input(st.text_input("የእቃው ስም*", key=f"i_name_{k}"))
                i_cat = st.selectbox("ምድብ*", ["Electrical Spare", "Sanitary Fitting", "Civil Material", "Tools"], key=f"i_cat_{k}")
                i_qty = st.number_input("ብዛት (Quantity)*", min_value=0, value=10, key=f"i_qty_{k}")
            with c2:
                i_min = st.number_input("አነስተኛ የማሳወቂያ መጠን (Min Reorder Level)*", min_value=0, value=5, key=f"i_min_{k}")
                i_cost = st.number_input("የአንዱ ዋጋ (Unit Cost ETB)*", min_value=0.0, step=10.0, key=f"i_cost_{k}")
                i_bin = sanitize_input(st.text_input("የተቀመጠበት ቦታ/Bin*", key=f"i_bin_{k}"))

            if st.form_submit_button("💾 እቃውን መዝግብ"):
                if i_name:
                    item_code = f"SKU-{len(inventory_df) + 101}"
                    tot_val = i_qty * i_cost
                    new_row = pd.DataFrame([[
                        item_code, i_name, i_cat, i_qty, i_min, i_cost, tot_val, i_bin
                    ]], columns=inventory_cols)
                    inventory_df = pd.concat([inventory_df, new_row], ignore_index=True)
                    save_data(inventory_df, INVENTORY_FILE)
                    st.success(f"✅ እቃው በስኬት ተመዝግቧል! Item Code: `{item_code}`")
                    reset_form_inputs()
                    st.rerun()

# --- 7. REPORTS (FIXED DATE FILTERING) ---
elif active == "📈 Reports":
    st.sidebar.markdown("### 📈 Reports Sub-Menu")
    sub_rep = st.sidebar.radio("ምረጥ:", ["የላቀ ሪፖርቶች ማውጫ", "የተሰሩ የናሬሽን ሪፖርቶች"])
    st.title("📈 Executive Reports & Narrative Analytics")
    
    if sub_rep == "የላቀ ሪፖርቶች ማውጫ":
        st.subheader("🎯 የሪፖርት መስፈርት እና የጊዜ ገደብ ይምረጡ")
        
        r_col1, r_col2, r_col3 = st.columns(3)
        with r_col1:
            start_d = st.date_input("📅 ከዚህ ቀን (Start Date):", value=date(2026, 1, 1))
            end_d = st.date_input("📅 እስከዚ ቀን (End Date):", value=date.today())
        with r_col2:
            dept_filter = st.selectbox(
                "🏢 የሥራ ክፍል (Department):", 
                ["ሁሉም ክፍሎች (All)", "Construction", "Electrical", "Sanitary", "Engineering Exec"]
            )
        with r_col3:
            module_filter = st.selectbox(
                "🛠️ የሪፖርት አይነት (Module):", 
                ["የፕሮጀክት ስራዎች (Projects Plan)", "የጥገና ስራዎች (Maintenance Orders)", "የቅድመ-መከላከል ጥገና (Preventive)", "የንብረት መዝገብ (Asset Register)"]
            )
            
        st.markdown("---")
        
        # Convert date range safely to pandas Timestamps
        start_ts = pd.to_datetime(start_d)
        end_ts = pd.to_datetime(end_d) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
        
        filtered_data = pd.DataFrame()
        if module_filter == "የፕሮጀክት ስራዎች (Projects Plan)":
            df_temp = plan_df.copy()
            df_temp["DT_Col"] = pd.to_datetime(df_temp["Start Date"], errors='coerce')
            filtered_data = df_temp[(df_temp["DT_Col"] >= start_ts) & (df_temp["DT_Col"] <= end_ts)].drop(columns=["DT_Col"])
        elif module_filter == "የጥገና ስራዎች (Maintenance Orders)":
            df_temp = corrective_df.copy()
            df_temp["DT_Col"] = pd.to_datetime(df_temp["Reported Date"], errors='coerce')
            filtered_data = df_temp[(df_temp["DT_Col"] >= start_ts) & (df_temp["DT_Col"] <= end_ts)].drop(columns=["DT_Col"])
        elif module_filter == "የቅድመ-መከላከል ጥገና (Preventive)":
            df_temp = preventive_df.copy()
            df_temp["DT_Col"] = pd.to_datetime(df_temp["Last Service Date"], errors='coerce')
            filtered_data = df_temp[(df_temp["DT_Col"] >= start_ts) & (df_temp["DT_Col"] <= end_ts)].drop(columns=["DT_Col"])
        elif module_filter == "የንብረት መዝገብ (Asset Register)":
            df_temp = assets_df.copy()
            df_temp["DT_Col"] = pd.to_datetime(df_temp["Purchase Date"], errors='coerce')
            filtered_data = df_temp[(df_temp["DT_Col"] >= start_ts) & (df_temp["DT_Col"] <= end_ts)].drop(columns=["DT_Col"])

        if dept_filter != "ሁሉም ክፍሎች (All)" and "Department" in filtered_data.columns:
            filtered_data = filtered_data[filtered_data["Department"] == dept_filter]

        st.markdown(f"### 📊 1. የሰንጠረዥ ሪፖርት (Table Report) — ከ {start_d} እስከ {end_d}")
        st.caption(f"የተገኙ መረጃዎች ብዛት፦ {len(filtered_data)}")
        render_editable_df(filtered_data, key_prefix="rep_results")
        
        st.markdown("---")
        st.markdown("### 📝 2. የናሬሽን ሪፖርት ማጠቃለያ (Narrative Summary Report)")
        
        narrative_logs = progress_df.copy()
        if not narrative_logs.empty and "Update Date" in narrative_logs.columns:
            narrative_logs["Log_DT"] = pd.to_datetime(narrative_logs["Update Date"], errors='coerce')
            filtered_narratives = narrative_logs[
                (narrative_logs["Log_DT"] >= start_ts) & 
                (narrative_logs["Log_DT"] <= end_ts)
            ].drop(columns=["Log_DT"])
            
            if not filtered_narratives.empty:
                for idx, log in filtered_narratives.iterrows():
                    st.markdown(f"""
                    <div class='narrative-card'>
                        📌 <b>ስራ መለያ (Plan ID)፦</b> {log.get('Plan ID', 'N/A')} | <b>የዘገባው ቀን፦</b> {log.get('Update Date', 'N/A')} | <b>ሪፖርት አቅራቢ፦</b> {log.get('Updated By', 'N/A')}<br>
                        • <b>A. ስለስራው ጠቅላላ ሁኔታ፦</b> {log.get('General Status', 'N/A')}<br>
                        • <b>B. የነበረው መልካም ነገር፦</b> {log.get('Good Aspects', 'N/A')}<br>
                        • <b>C. የነበሩ ችግሮች፦</b> {log.get('Problems Faced', 'N/A')}<br>
                        • <b>D. ችግሮቹ የተፈቱበት መንገድ፦</b> {log.get('Solutions Applied', 'N/A')}<br>
                        • <b>E. ያልተፈታ ችግር ካለ፦</b> {log.get('Unresolved Issues', 'N/A')}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("⚠️ በተመረጠው የጊዜ ክልል ውስጥ የገባ የናሬሽን ሪፖርት የለም።")
        else:
            st.info("ℹ️ ምንም የተቀመጠ የናሬሽን መረጃ የለም።")

    elif sub_rep == "የተሰሩ የናሬሽን ሪፖርቶች":
        st.subheader("📜 ሁሉም የተመዘገቡ የናሬሽን ሪፖርቶች")
        render_editable_df(progress_df, key_prefix="all_narratives")

# --- 8. USERS MANAGEMENT ---
elif active == "👥 Users":
    st.sidebar.markdown("### 👥 User Sub-Menu")
    menu_options = ["የእኔ አካውንትና የይለፍ ቃል"]
    if role == "Admin":
        menu_options.append("አዲስ ተጠቃሚ መመዝገቢያ")
        
    sub_user = st.sidebar.radio("ምረጥ:", menu_options)
    st.title("👥 User Management (የተጠቃሚዎች አስተዳደር)")
    
    if sub_user == "የእኔ አካውንትና የይለፍ ቃል":
        st.subheader("👤 የእርስዎ መረጃ")
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            st.write(f"**ሙሉ ስም:** {user['Full Name']}")
            st.write(f"**የስራ ክፍል:** {user['Department']}")
        with col_u2:
            st.write(f"**የተጠቃሚ ስም (Username):** `{user['Username']}`")
            st.write(f"**የስልጣን ደረጃ:** `{role}`")

    elif sub_user == "አዲስ ተጠቃሚ መመዝገቢያ" and role == "Admin":
        st.subheader("👥 አዲስ ተጠቃሚ መመዝገቢያ (ከኢሜይል ማሳወቂያ ጋር)")
        k = st.session_state.form_key_suffix
        with st.form(f"reg_u_form_{k}"):
            f_name = sanitize_input(st.text_input("ሙሉ ስም*", key=f"u_fname_{k}"))
            u_email = sanitize_input(st.text_input("የኢሜይል አድራሻ (Email)*", key=f"u_email_{k}"))
            u_dept = st.selectbox("የሥራ ክፍል*", ["Engineering Exec", "Construction Department", "Electrical Department", "Sanitary Department"], key=f"u_dept_{k}")
            j_title = sanitize_input(st.text_area("የሥራ ድርሻ*", key=f"u_jtitle_{k}"))
            u_role = st.selectbox("የስልጣን ደረጃ*", ["Viewer", "Editor", "Admin"], key=f"u_role_{k}")
            u_name = sanitize_input(st.text_input("Username*", key=f"u_uname_{k}"))
            u_pass = st.text_input("Password*", type="password", key=f"u_pass_{k}")
            
            if st.form_submit_button("🔒 ተጠቃሚውን መዝግብ እና ኢሜይል ላክ"):
                is_valid, msg = validate_password_strength(u_pass)
                if not is_valid:
                    st.error(f"⛔ የደህንነት ስጋት፦ {msg}")
                elif u_name in users_df["Username"].values:
                    st.error("⛔ ይህ Username ቀደም ሲል ተይዟል!")
                elif f_name and u_name and u_pass and u_email:
                    secure_pass = hash_password(u_pass)
                    new_u = pd.DataFrame([[f_name, u_dept, j_title, u_role, u_name, secure_pass, u_email, datetime.now().strftime("%Y-%m-%d")]], columns=user_cols)
                    users_df = pd.concat([users_df, new_u], ignore_index=True)
                    save_data(users_df, USER_FILE)
                    
                    email_status = send_welcome_email(u_email, u_name, u_pass)
                    if email_status:
                        st.success(f"✅ ተጠቃሚ {f_name} ተመዝግቧል፤ የመግቢያ መረጃ ወደ {u_email} በኢሜይል ተልኳል!")
                    else:
                        st.success(f"✅ ተጠቃሚ {f_name} ተመዝግቧል! (ማስታወሻ፦ ኢሜይሉን ለመላክ የ SMTP ቅንብር ያስፈልጋል)")
                    reset_form_inputs()
                    st.rerun()

# --- 9. SETTINGS ---
elif active == "⚙️ Settings":
    st.sidebar.markdown("### ⚙️ Settings Sub-Menu")
    sub_set = st.sidebar.radio("ምረጥ:", ["የሲስተም ቅንብሮች እና Backup"])
    st.title("⚙️ System Settings & Security")
    st.success("✅ Federal TVET Executive System v14.1 System Status: Online & Operational.")
