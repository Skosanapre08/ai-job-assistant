import streamlit as st
import ollama
import sqlite3
from datetime import datetime
from pypdf import PdfReader
from fpdf import FPDF
import io
import os

# --- CONFIGURATION ---
CV_FILE = "my_cv.txt"
DB_FILE = "applications.db"

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS applications
                 (id INTEGER PRIMARY KEY, company TEXT, role TEXT, date TEXT, status TEXT, letter TEXT)''')
    conn.commit()
    conn.close()

def add_application(company, role, letter):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO applications (company, role, date, status, letter) VALUES (?, ?, ?, ?, ?)",
              (company, role, date, "Applied", letter))
    conn.commit()
    conn.close()

def get_applications():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM applications ORDER BY id DESC")
    data = c.fetchall()
    conn.close()
    return data

def update_status(app_id, new_status):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE applications SET status = ? WHERE id = ?", (new_status, app_id))
    conn.commit()
    conn.close()

def get_metrics():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM applications")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Interviewing'")
    interviewing = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Offer'")
    offers = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Rejected'")
    rejected = c.fetchone()[0]
    conn.close()
    return total, interviewing, offers, rejected

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.multi_cell(0, 8, txt=line)
    return pdf.output(dest='S').encode('latin-1')

# --- CV STORAGE ---
def save_cv(text):
    with open(CV_FILE, "w", encoding="utf-8") as f:
        f.write(text)

def load_cv():
    if os.path.exists(CV_FILE):
        with open(CV_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return ""

init_db()

# --- STREAMLIT UI ---
st.set_page_config(page_title="AI Job Assistant Pro", layout="wide", page_icon="🚀")

st.markdown("""
<style>
    .main-header {
        font-size: 42px; font-weight: bold; color: #4CAF50;
        text-align: center; padding-bottom: 10px;
    }
    .sub-header {
        font-size: 18px; text-align: center; color: #888;
        padding-bottom: 30px;
    }
    .metric-card {
        background-color: #1E1E2E; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center;
    }
    .stButton>button {
        width: 100%; border-radius: 8px; height: 50px;
        font-weight: bold; font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header"> AI Job Application Assistant Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Your privacy-first, local AI career co-pilot.</div>', unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("📄 Your Profile")
    uploaded_file = st.file_uploader("Upload a new CV (PDF):", type=["pdf"])
    
    if uploaded_file is not None:
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        cv_text = ""
        for page in reader.pages:
            cv_text += page.extract_text()
        save_cv(cv_text)
        st.success("✅ New CV Saved!")
    
    current_cv = load_cv()
    if current_cv:
        st.info(f"👤 Profile loaded: {len(current_cv)} characters")
        with st.expander("👁️ View your CV"):
            st.text(current_cv[:1500] + "...")
    else:
        st.warning("⚠️ No CV uploaded yet. Please upload one.")
    
    st.write("---")
    st.caption("Built with Ollama, Streamlit & Python")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["✍️ Generate Application", "📊 Tracker Dashboard", "📜 Application History"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input("🏢 Company Name:")
    with col2:
        job_role = st.text_input("💼 Job Role:")

    job_description = st.text_area("📋 Paste the Job Description here:", height=200)
    
    st.write("---")
    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        generate_cover = st.button("📝 Cover Letter")
    with col_btn2:
        generate_cv = st.button("📄 Tailored CV Summary")
    with col_btn3:
        analyze_jd = st.button("🔍 Analyze Job")

    if generate_cover or generate_cv or analyze_jd:
        if job_description and company_name and job_role:
            with st.spinner("🤖 AI is thinking... (this may take 20-40 seconds)"):
                cv_context = load_cv()
                
                if analyze_jd:
                    prompt = f"List the top 7 required skills from this job description as a bulleted list:\n\n{job_description}"
                    task = "Job Analysis"
                    file_name = "Job_Analysis"
                elif generate_cover:
                    prompt = f"Write a short, tailored cover letter (under 300 words).\n\nCV: {cv_context}\n\nJob: {job_description}"
                    task = "Cover Letter"
                    file_name = "Cover_Letter"
                else:
                    prompt = f"Rewrite the professional summary and top 5 skills to match this job. Make it ATS-friendly.\n\nCV: {cv_context}\n\nJob: {job_description}"
                    task = "CV Summary"
                    file_name = "CV_Summary"

                response = ollama.chat(model='tinyllama', messages=[{'role': 'user', 'content': prompt}])
                result_text = response['message']['content']
                
                if not analyze_jd:
                    add_application(company_name, job_role, result_text)
                    st.success(f"✅ {task} Generated & Application Saved!")
                else:
                    st.success("✅ Job Analysis Complete!")
                
                st.write("---")
                st.subheader(f"Your {task}")
                st.write(result_text)
                
                st.download_button(
                    label=f"⬇️ Download {task} as PDF",
                    data=create_pdf(result_text),
                    file_name=f"{file_name}_{company_name}.pdf",
                    mime="application/pdf"
                )
        else:
            st.warning("Please fill in Company Name, Job Role, and Job Description.")

with tab2:
    st.subheader("📊 Your Application Dashboard")
    total, interviewing, offers, rejected = get_metrics()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Applied", total)
    m2.metric("Interviewing", interviewing)
    m3.metric("Offers", offers)
    m4.metric("Rejected", rejected)
    
    st.write("---")
    st.subheader("Manage Your Applications")
    
    applications = get_applications()
    if applications:
        for app in applications:
            app_id, company, role, date, status, letter = app
            with st.expander(f"**{company}** — {role}  |  Status: {status}"):
                st.write(f"📅 Applied on: {date}")
                new_status = st.selectbox(
                    "Update Status:",
                    ["Applied", "Interviewing", "Rejected", "Offer"],
                    index=["Applied", "Interviewing", "Rejected", "Offer"].index(status),
                    key=f"status_{app_id}"
                )
                if st.button("Update Status", key=f"update_{app_id}"):
                    update_status(app_id, new_status)
                    st.rerun()
    else:
        st.info("No applications tracked yet.")

with tab3:
    st.subheader("📜 Your Application History")
    st.write("Click on any application to view the letter the AI wrote for you.")
    
    applications = get_applications()
    if applications:
        for app in applications:
            app_id, company, role, date, status, letter = app
            with st.expander(f"📄 {company} — {role} ({date})"):
                st.markdown(f"**Status:** {status}")
                st.write(letter)
                st.download_button(
                    label="⬇️ Download this letter as PDF",
                    data=create_pdf(letter),
                    file_name=f"Letter_{company}_{app_id}.pdf",
                    mime="application/pdf",
                    key=f"download_{app_id}"
                )
    else:
        st.info("No history yet. Generate a cover letter to see it here.")