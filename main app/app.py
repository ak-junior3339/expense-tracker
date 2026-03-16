import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import datetime
import calendar

# ================================================================
# DATABASE SETUP
# ================================================================

conn = sqlite3.connect("expenses.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date TEXT,
    day TEXT,
    expense_type TEXT,
    description TEXT,
    amount REAL,
    mode TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

for col, definition in [
    ("user_id",      "INTEGER DEFAULT 1"),
    ("expense_type", "TEXT DEFAULT 'Other'"),
]:
    try:
        cursor.execute(f"ALTER TABLE expenses ADD COLUMN {col} {definition}")
        conn.commit()
    except Exception:
        pass

conn.commit()

# ================================================================
# CONSTANTS
# ================================================================

EXPENSE_TYPES = [
    "🍽️ Food & Dining",
    "🛒 Groceries",
    "🚗 Transport & Fuel",
    "🏠 Rent & Housing",
    "💡 Electricity & Utilities",
    "📱 Mobile & Internet",
    "🏥 Medical & Health",
    "💊 Medicines",
    "👕 Clothing & Shopping",
    "🎓 Education & Fees",
    "🎬 Entertainment",
    "🧹 Household Supplies",
    "💇 Personal Care & Salon",
    "🏋️ Gym & Fitness",
    "✈️ Travel & Vacation",
    "🎁 Gifts & Occasions",
    "💰 Savings & Investment",
    "🏦 Loan & EMI",
    "🛡️ Insurance",
    "📺 Subscriptions (OTT/Apps)",
    "🐾 Pets",
    "🔧 Repairs & Maintenance",
    "👶 Child Care",
    "🙏 Donations & Charity",
    "📦 Other",
]

# ================================================================
# ADMIN CONFIG
# ================================================================

ADMIN_USERNAME = st.secrets["ADMIN_USERNAME"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

# ================================================================
# HELPERS
# ================================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _ensure_admin():
    cursor.execute("SELECT id FROM users WHERE username=?", (ADMIN_USERNAME,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (ADMIN_USERNAME, hash_password(ADMIN_PASSWORD))
        )
        conn.commit()

def register_user(username: str, password: str) -> tuple[bool, str]:
    clean = username.strip().lower()
    if clean == ADMIN_USERNAME:
        return False, "That username is reserved. Please choose another."
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (clean, hash_password(password))
        )
        conn.commit()
        return True, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already taken. Please choose another."

def login_user(username: str, password: str) -> tuple[bool, str, int | None]:
    cursor.execute(
        "SELECT id FROM users WHERE username=? AND password_hash=?",
        (username.strip().lower(), hash_password(password))
    )
    row = cursor.fetchone()
    if row:
        return True, "Login successful!", row[0]
    return False, "Invalid username or password.", None

def add_expense(user_id, exp_date, day, expense_type, description, amount, mode):
    cursor.execute(
        "INSERT INTO expenses (user_id, date, day, expense_type, description, amount, mode) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, exp_date, day, expense_type, description, amount, mode)
    )
    conn.commit()

def get_expenses(user_id):
    cursor.execute(
        "SELECT id, date, day, expense_type, description, amount, mode FROM expenses WHERE user_id=? ORDER BY date DESC",
        (user_id,)
    )
    return cursor.fetchall()

def delete_expense(expense_id, user_id):
    cursor.execute("DELETE FROM expenses WHERE id=? AND user_id=?", (expense_id, user_id))
    conn.commit()


_ensure_admin()

# ================================================================
# SESSION STATE
# ================================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = False

# ================================================================
# PAGE CONFIG & GLOBAL CSS
# ================================================================

st.set_page_config(page_title="खर्चा — Expense Tracker", page_icon="💸", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

#MainMenu, footer, header { visibility: hidden; }

/* Hide sidebar completely */
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }

.block-container {
    max-width: 1080px;
    padding: 2.5rem 2rem 4rem;
}

/* ---- Top navbar ---- */
.navbar {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border: 1px solid #e94560;
    border-radius: 16px;
    padding: 1.2rem 2rem;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.navbar-left { display: flex; align-items: center; gap: 12px; }
.navbar-logo { font-size: 1.8rem; }
.navbar-title {
    font-size: 1.4rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
}
.navbar-user {
    font-size: 0.85rem;
    color: #a0a0c0;
}
.navbar-user span {
    color: #ffffff;
    font-weight: 600;
}
.admin-chip {
    display: inline-block;
    background: #e94560;
    color: white !important;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 20px;
    letter-spacing: 0.5px;
}
.page-banner {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border: 1px solid #e94560;
    border-radius: 16px;
    padding: 1.8rem 2rem;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.page-banner h1 {
    font-size: 1.6rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
    letter-spacing: -0.5px;
}
.page-banner .sub { font-size: 0.85rem; color: #a0a0c0; margin-top: 4px; }
.page-banner .badge {
    background: #e94560;
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 0.5px;
}
.stat-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.stat-card {
    flex: 1;
    background: #ffffff;
    border: 1px solid #e8eaf0;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
}
.stat-card .label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #888;
    margin-bottom: 6px;
}
.stat-card .value {
    font-size: 1.6rem;
    font-weight: 700;
    color: #1a1a2e;
    font-family: 'JetBrains Mono', monospace;
}
.stat-card .value.accent { color: #e94560; }
.stat-card .value.green  { color: #10b981; }
.section-title {
    font-size: 1rem;
    font-weight: 700;
    color: #e94560;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-left: 4px solid #e94560;
    padding-left: 10px;
    margin: 1.8rem 0 1rem;
}
.stTextInput input, .stNumberInput input {
    border-radius: 10px !important;
    border: 1.5px solid #e0e0e8 !important;
    font-family: 'Sora', sans-serif !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #e94560 !important;
    box-shadow: 0 0 0 3px rgba(233,69,96,0.08) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #e94560, #c2185b) !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(233,69,96,0.35) !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #f4f4f8;
    border-radius: 12px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 9px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    color: #444466 !important;
}
.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
    color: #e94560 !important;
}
.stDataFrame {
    border-radius: 12px !important;
    overflow: hidden;
    border: 1px solid #e8eaf0 !important;
}
.danger-box {
    border-top: 1.5px solid #fecdd3;
    padding: 1.2rem 0 0;
    margin-top: 1rem;
}
</style>
""", unsafe_allow_html=True)


# ================================================================
# LOGIN / REGISTER
# ================================================================

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"

if not st.session_state.logged_in:

    _, mid, _ = st.columns([1, 1.4, 1])

    with mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;font-size:2.6rem;margin-bottom:4px">💸</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;font-size:1.9rem;font-weight:700;color:#e94560;letter-spacing:-0.5px">खर्चा</div>', unsafe_allow_html=True)
        st.markdown('<div style="text-align:center;color:#888;font-size:0.88rem;margin-bottom:1.8rem">Your personal expense tracker — private & simple</div>', unsafe_allow_html=True)

        if st.session_state.auth_mode == "login":
            username = st.text_input("Username", placeholder="Enter your username", key="login_user")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Sign In →", width='stretch', type="primary"):
                if not username or not password:
                    st.error("Please fill in both fields.")
                else:
                    ok, msg, uid = login_user(username, password)
                    if ok:
                        st.session_state.logged_in = True
                        st.session_state.user_id = uid
                        st.session_state.username = username.strip().lower()
                        st.session_state.is_admin = (username.strip().lower() == ADMIN_USERNAME)
                        st.rerun()
                    else:
                        st.error(msg)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;color:#888;font-size:0.85rem">Don\'t have an account?</div>', unsafe_allow_html=True)
            if st.button("Create one →", width='stretch'):
                st.session_state.auth_mode = "register"
                st.rerun()

        else:
            new_user     = st.text_input("Username", placeholder="Pick a username", key="reg_user")
            new_pass     = st.text_input("Password", type="password", placeholder="Min. 6 characters", key="reg_pass")
            confirm_pass = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="reg_confirm")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Create Account →", width='stretch', type="primary"):
                if not new_user or not new_pass or not confirm_pass:
                    st.error("All fields are required.")
                elif new_pass != confirm_pass:
                    st.error("Passwords do not match.")
                elif len(new_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    ok, msg = register_user(new_user, new_pass)
                    if ok:
                        st.success(msg + " You can now sign in.")
                        st.session_state.auth_mode = "login"
                        st.rerun()
                    else:
                        st.error(msg)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("← Back to Sign In", width='stretch'):
                st.session_state.auth_mode = "login"
                st.rerun()

    st.stop()


# ================================================================
# TOP NAVBAR with Sign Out
# ================================================================

USER_ID = st.session_state.user_id

col_logo, col_user, col_signout = st.columns([3, 3, 1])

with col_logo:
    st.markdown("## 💸 खर्चा")

with col_user:
    if st.session_state.is_admin:
        st.markdown(f"<br>👤 **{st.session_state.username}** 🔴 ADMIN", unsafe_allow_html=True)
    else:
        st.markdown(f"<br>👤 **{st.session_state.username}**", unsafe_allow_html=True)

with col_signout:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Sign Out 🚪", type="primary", width='stretch'):
        for k in ["logged_in", "user_id", "username", "is_admin"]:
            st.session_state[k] = False if k != "user_id" and k != "username" else None
        st.session_state.is_admin = False
        st.rerun()

st.divider()


# ================================================================
# ADMIN PANEL
# ================================================================

if st.session_state.is_admin:
    st.markdown("""
        <div class="page-banner">
            <div>
                <div class="sub">CONTROL CENTER</div>
                <h1>Admin Panel</h1>
            </div>
            <span class="badge">ADMIN</span>
        </div>
    """, unsafe_allow_html=True)

    cursor.execute(
        "SELECT id, username, created_at FROM users WHERE username != ? ORDER BY created_at DESC",
        (ADMIN_USERNAME,)
    )
    users = cursor.fetchall()

    if not users:
        st.info("No users have registered yet.")
    else:
        df_users = pd.DataFrame(users, columns=["ID", "Username", "Joined At"])
        df_users["Joined At"] = pd.to_datetime(df_users["Joined At"]).dt.strftime("%d %b %Y, %I:%M %p")

        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-card">
                <div class="label">Registered Users</div>
                <div class="value accent">{len(df_users)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">All Users</div>', unsafe_allow_html=True)
        st.dataframe(df_users[["Username", "Joined At"]], width='stretch', hide_index=True)

        st.markdown('<div class="danger-box">', unsafe_allow_html=True)
        st.markdown("**🗑 Delete a User** — permanently removes the user and all their expenses.")
        user_to_delete = st.selectbox("Select user", df_users["Username"].tolist(), label_visibility="collapsed")
        if st.button("Delete User", type="primary"):
            cursor.execute("SELECT id FROM users WHERE username=?", (user_to_delete,))
            row = cursor.fetchone()
            if row:
                uid = row[0]
                cursor.execute("DELETE FROM expenses WHERE user_id=?", (uid,))
                cursor.execute("DELETE FROM users WHERE id=?", (uid,))
                conn.commit()
                st.warning(f"User '{user_to_delete}' deleted.")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()


# ================================================================
# MAIN NAVIGATION TABS
# ================================================================

tab_add, tab_view, tab_reports = st.tabs([
    "➕ Add Expense",
    "📋 View Expenses",
    "📊 Reports",
])


# ================================================================
# ADD EXPENSE
# ================================================================

with tab_add:
    with st.container():
        col_date, col_day = st.columns([2, 1])
        with col_date:
            expense_date = st.date_input("Date", date.today())
        with col_day:
            st.text_input("Day", value=expense_date.strftime("%A"), disabled=True)

        expense_type = st.selectbox("Expense Type", EXPENSE_TYPES)
        description  = st.text_input(
            "Description",
            placeholder="Optional — e.g. Lunch at Cafe Coffee Day, Petrol fill-up...",
        )

        col_amt, col_mode = st.columns(2)
        with col_amt:
            amount = st.number_input("Amount (₹)", min_value=0.0, format="%.2f")
        with col_mode:
            mode = st.selectbox("Payment Mode", ["Cash", "Online"])

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add Expense ✓", type="primary", width='stretch'):
            if amount <= 0:
                st.error("Amount must be greater than ₹0.")
            else:
                add_expense(USER_ID, expense_date, expense_date.strftime("%A"), expense_type, description, amount, mode)
                st.success(f"✅ ₹{amount:,.2f} added under **{expense_type}**")
                st.balloons()


# ================================================================
# VIEW EXPENSES
# ================================================================

with tab_view:
    data = get_expenses(USER_ID)
    df = pd.DataFrame(data, columns=["ID", "Date", "Day", "Type", "Description", "Amount", "Mode"])

    if df.empty:
        st.info("No expenses recorded yet. Head to **Add Expense** to get started!")
    else:
        total = df["Amount"].sum()
        count = len(df)
        avg   = total / count if count else 0

        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-card">
                <div class="label">Total Spent</div>
                <div class="value accent">₹{total:,.2f}</div>
            </div>
            <div class="stat-card">
                <div class="label">Transactions</div>
                <div class="value">{count}</div>
            </div>
            <div class="stat-card">
                <div class="label">Avg per Transaction</div>
                <div class="value">₹{avg:,.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Transaction History</div>', unsafe_allow_html=True)
        st.dataframe(
            df[["ID", "Date", "Day", "Type", "Description", "Amount", "Mode"]],
            width='stretch', hide_index=True
        )

        st.markdown('<div class="danger-box">', unsafe_allow_html=True)
        st.markdown("**🗑 Delete a Transaction** — enter the ID shown in the table above.")
        delete_id = st.number_input("Transaction ID", min_value=1, step=1, label_visibility="collapsed")
        if st.button("Delete Transaction", type="primary"):
            cursor.execute("SELECT id FROM expenses WHERE id=? AND user_id=?", (delete_id, USER_ID))
            if cursor.fetchone():
                delete_expense(delete_id, USER_ID)
                st.warning("Transaction deleted.")
                st.rerun()
            else:
                st.error("No transaction with that ID found in your records.")
        st.markdown('</div>', unsafe_allow_html=True)


# ================================================================
# REPORTS
# ================================================================

with tab_reports:
    data = get_expenses(USER_ID)
    df   = pd.DataFrame(data, columns=["ID", "Date", "Day", "Type", "Description", "Amount", "Mode"])

    if df.empty:
        st.info("No expenses recorded yet.")
    else:
        df["Date"] = pd.to_datetime(df["Date"])
        today      = datetime.date.today()

        current_month = df[
            (df["Date"].dt.month == today.month) &
            (df["Date"].dt.year  == today.year)
        ].copy()

        cm_total  = current_month["Amount"].sum() if not current_month.empty else 0
        cm_count  = len(current_month)
        cm_avg    = cm_total / max(today.day, 1)
        all_total = df["Amount"].sum()

        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-card">
                <div class="label">This Month</div>
                <div class="value accent">₹{cm_total:,.2f}</div>
            </div>
            <div class="stat-card">
                <div class="label">Transactions (Month)</div>
                <div class="value">{cm_count}</div>
            </div>
            <div class="stat-card">
                <div class="label">Daily Average</div>
                <div class="value">₹{cm_avg:,.2f}</div>
            </div>
            <div class="stat-card">
                <div class="label">All-Time Total</div>
                <div class="value green">₹{all_total:,.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Current Month Transactions</div>', unsafe_allow_html=True)
        if current_month.empty:
            st.info(f"No expenses in {today.strftime('%B %Y')} yet.")
        else:
            st.dataframe(
                current_month.drop(columns=["ID"]).reset_index(drop=True),
                width='stretch', hide_index=True
            )

        st.markdown('<div class="section-title">Visual Insights</div>', unsafe_allow_html=True)

        tab1, tab2, tab3, tab4 = st.tabs([
            "📊  Daily Spending",
            "🥧  By Category",
            "🍩  Cash vs Online",
            "🔥  Heatmap",
        ])

        CHART_BG = "rgba(0,0,0,0)"

        with tab1:
            if current_month.empty:
                st.info("No data for current month.")
            else:
                daily = current_month.groupby(current_month["Date"].dt.day)["Amount"].sum().reset_index()
                daily.columns = ["Day", "Amount"]
                all_days = pd.DataFrame({"Day": range(1, today.day + 1)})
                daily = all_days.merge(daily, on="Day", how="left").fillna(0)
                fig_bar = px.bar(
                    daily, x="Day", y="Amount",
                    labels={"Day": "Day of Month", "Amount": "Amount (₹)"},
                    color="Amount",
                    color_continuous_scale=[[0,"#fce4ec"],[0.5,"#e94560"],[1,"#880e4f"]],
                    text_auto=".0f",
                )
                fig_bar.update_layout(
                    coloraxis_showscale=False,
                    plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
                    yaxis=dict(gridcolor="#f0f0f0", title="₹ Amount"),
                    xaxis=dict(dtick=1, title="Day"),
                    height=420, font=dict(family="Sora, sans-serif"),
                    margin=dict(t=20, b=20),
                )
                fig_bar.update_traces(textposition="outside", marker_line_width=0)
                st.plotly_chart(fig_bar, width='stretch')

        with tab2:
            type_data = df.groupby("Type")["Amount"].sum().reset_index()
            type_data.columns = ["Category", "Amount"]
            type_data = type_data.sort_values("Amount", ascending=False)
            if type_data.empty:
                st.info("No data available.")
            else:
                fig_pie = px.pie(
                    type_data, names="Category", values="Amount", hole=0.42,
                    color_discrete_sequence=["#e94560","#0f3460","#533483","#e8a838","#10b981","#3b82f6","#f59e0b","#ef4444","#8b5cf6","#06b6d4","#84cc16","#f97316"],
                )
                fig_pie.update_traces(
                    textposition="inside", textinfo="percent",
                    hovertemplate="<b>%{label}</b><br>₹%{value:,.2f}  (%{percent})<extra></extra>",
                    pull=[0.03] * len(type_data),
                )
                fig_pie.update_layout(
                    showlegend=True,
                    legend=dict(orientation="v", x=1.02, font=dict(size=11)),
                    height=520, paper_bgcolor=CHART_BG,
                    font=dict(family="Sora, sans-serif"),
                    margin=dict(t=20, b=20, l=0, r=0),
                    annotations=[dict(text=f"<b>₹{df['Amount'].sum():,.0f}</b><br>total", x=0.5, y=0.5, font_size=14, font_color="#1a1a2e", showarrow=False)]
                )
                st.plotly_chart(fig_pie, width='stretch')

        with tab3:
            mode_data = df.groupby("Mode")["Amount"].sum().reset_index()
            mode_data.columns = ["Mode", "Amount"]
            if mode_data.empty:
                st.info("No data available.")
            else:
                fig_donut = px.pie(
                    mode_data, names="Mode", values="Amount", hole=0.6,
                    color_discrete_map={"Cash": "#e94560", "Online": "#0f3460"},
                )
                fig_donut.update_traces(
                    textposition="outside", textinfo="percent+label",
                    hovertemplate="<b>%{label}</b><br>₹%{value:,.2f}  (%{percent})<extra></extra>",
                )
                fig_donut.update_layout(
                    height=420, paper_bgcolor=CHART_BG,
                    font=dict(family="Sora, sans-serif"), showlegend=False,
                    margin=dict(t=20, b=20),
                    annotations=[dict(text=f"<b>₹{df['Amount'].sum():,.0f}</b><br>total", x=0.5, y=0.5, font_size=16, font_color="#1a1a2e", showarrow=False)]
                )
                st.plotly_chart(fig_donut, width='stretch')

        with tab4:
            h_col1, h_col2 = st.columns(2)
            with h_col1:
                h_month = st.selectbox(
                    "Month", range(1, 13), index=today.month - 1,
                    format_func=lambda m: datetime.date(2000, m, 1).strftime("%B"),
                    key="heatmap_month"
                )
            with h_col2:
                hmap_years = sorted(df["Date"].dt.year.unique().tolist(), reverse=True)
                h_year = st.selectbox("Year", hmap_years, key="heatmap_year")

            hmap_df = df[(df["Date"].dt.month == h_month) & (df["Date"].dt.year == h_year)].copy()

            if hmap_df.empty:
                st.info(f"No expenses in {datetime.date(h_year, h_month, 1).strftime('%B %Y')}.")
            else:
                num_days     = calendar.monthrange(h_year, h_month)[1]
                first_wday   = calendar.monthrange(h_year, h_month)[0]
                daily_totals = hmap_df.groupby(hmap_df["Date"].dt.day)["Amount"].sum().to_dict()
                grid_z, grid_text = [], []
                week_z, week_text = [None] * first_wday, [""] * first_wday
                day_num = 1
                while day_num <= num_days:
                    amt = daily_totals.get(day_num, 0)
                    week_z.append(float(amt))
                    week_text.append(f"<b>{day_num}</b><br>₹{amt:,.0f}" if amt > 0 else f"<b>{day_num}</b><br>—")
                    day_num += 1
                    if len(week_z) == 7:
                        grid_z.append(week_z); grid_text.append(week_text)
                        week_z, week_text = [], []
                while len(week_z) < 7:
                    week_z.append(None); week_text.append("")
                if any(t != "" for t in week_text):
                    grid_z.append(week_z); grid_text.append(week_text)

                fig_hmap = go.Figure(data=go.Heatmap(
                    z=grid_z, text=grid_text, texttemplate="%{text}",
                    colorscale=[[0,"#fce4ec"],[0.3,"#f48fb1"],[0.7,"#e94560"],[1,"#880e4f"]],
                    showscale=True,
                    colorbar=dict(title="₹ Spent", tickfont=dict(family="JetBrains Mono")),
                    xgap=5, ygap=5, hovertemplate="%{text}<extra></extra>",
                ))
                fig_hmap.update_layout(
                    xaxis=dict(tickmode="array", tickvals=list(range(7)), ticktext=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"], side="top", tickfont=dict(size=12, family="Sora")),
                    yaxis=dict(showticklabels=False, autorange="reversed"),
                    height=320, paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
                    margin=dict(t=50, b=10, l=10, r=60),
                    title=dict(text=f"<b>{datetime.date(h_year, h_month, 1).strftime('%B %Y')}</b>", x=0.5, font=dict(size=14, family="Sora"))
                )
                st.plotly_chart(fig_hmap, width='stretch')
                st.caption("Darker cell = more money spent that day.")

        st.markdown('<div class="section-title">Month-over-Month Trend</div>', unsafe_allow_html=True)
        monthly = df.groupby([df["Date"].dt.year.rename("Year"), df["Date"].dt.month.rename("Month")])["Amount"].sum().reset_index()
        monthly["Period"] = monthly.apply(lambda r: datetime.date(int(r["Year"]), int(r["Month"]), 1).strftime("%b %Y"), axis=1)
        monthly = monthly.sort_values(["Year", "Month"])
        if len(monthly) < 2:
            st.info("Add expenses across at least 2 months to see a spending trend.")
        else:
            fig_line = px.line(monthly, x="Period", y="Amount", markers=True, labels={"Period": "Month", "Amount": "Total Spent (₹)"}, line_shape="spline")
            fig_line.update_traces(
                line=dict(color="#e94560", width=3),
                marker=dict(size=9, color="#0f3460", line=dict(color="#e94560", width=2)),
                fill="tozeroy", fillcolor="rgba(233,69,96,0.07)",
            )
            fig_line.update_layout(
                plot_bgcolor=CHART_BG, paper_bgcolor=CHART_BG,
                yaxis=dict(gridcolor="#f0f0f0", title="₹ Amount"),
                xaxis=dict(gridcolor="#f0f0f0", title=""),
                height=380, font=dict(family="Sora, sans-serif"), margin=dict(t=20, b=20),
            )
            st.plotly_chart(fig_line, width='stretch')

        st.markdown('<div class="section-title">Browse Previous Months</div>', unsafe_allow_html=True)
        br_col1, br_col2 = st.columns(2)
        with br_col1:
            br_month = st.selectbox("Month", range(1, 13), format_func=lambda m: datetime.date(2000, m, 1).strftime("%B"), key="browse_month")
        with br_col2:
            browse_years = sorted(df["Date"].dt.year.unique().tolist(), reverse=True)
            br_year = st.selectbox("Year", browse_years, key="browse_year")

        filtered = df[(df["Date"].dt.month == br_month) & (df["Date"].dt.year == br_year)]
        if filtered.empty:
            st.info(f"No expenses in {datetime.date(br_year, br_month, 1).strftime('%B %Y')}.")
        else:
            st.dataframe(filtered.drop(columns=["ID"]).reset_index(drop=True), width='stretch', hide_index=True)
            st.markdown(f"""
            <div class="stat-row" style="margin-top:1rem">
                <div class="stat-card">
                    <div class="label">Total — {datetime.date(br_year, br_month, 1).strftime('%B %Y')}</div>
                    <div class="value accent">₹{filtered['Amount'].sum():,.2f}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Transactions</div>
                    <div class="value">{len(filtered)}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ================================================================
# FOOTER
# ================================================================

st.markdown("""
<div style="
    position: fixed;
    bottom: 0; left: 0; right: 0;
    text-align: center;
    padding: 10px;
    font-size: 0.78rem;
    color: #a0a0c0;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-top: 1px solid #0f3460;
    font-family: 'Sora', sans-serif;
    z-index: 999;
">
    Developed with ❤️ by <b style="color:#e94560">ak_junior</b>
</div>
""", unsafe_allow_html=True)
