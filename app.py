import streamlit as st
from groq import Groq
import sqlite3
from datetime import datetime
from pypdf import PdfReader
import io

# Read API key from Streamlit Cloud Secrets
api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=api_key)

DB_FILE = "applications.db"

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

def call_groq(prompt):
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

init_db()

st.set_page_config(page_title="AI-Powered Job Application Assistant", layout="wide")
st.title("AI-Powered Job Application Assistant")
st.write("Powered by **Groq AI** | Deployed on Streamlit Cloud")

with st.sidebar:
    st.header("📄 Your Profile")
    upload_method = st.radio("Choose how to add your CV:", ["Upload PDF", "Paste Text"])
    cv_text = ""
    if upload_method == "Upload PDF":
        uploaded_file = st.file_uploader("Upload your CV (PDF):", type=["pdf"])
        if uploaded_file is not None:
            try:
                reader = PdfReader(io.BytesIO(uploaded_file.read()))
                for page in reader.pages:
                    cv_text += page.extract_text()
                st.success(f"✅ CV Loaded! ({len(cv_text)} characters)")
                with st.expander("👁️ View your CV"):
                    st.text(cv_text[:1500] + "...")
            except Exception as e:
                st.error(f"Error reading PDF: {e}")
    else:
        cv_text = st.text_area("Paste your CV here:", height=300)
        if cv_text:
            with st.expander("👁️ View your CV"):
                st.text(cv_text[:1500] + "...")
    st.session_state['cv_text'] = cv_text

tab1, tab2 = st.tabs(["✍️ Generate Application", "📊 Tracker Dashboard"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input("🏢 Company Name:")
    with col2:
        job_role = st.text_input("💼 Job Role:")
    job_description = st.text_area("📋 Paste the Job Description here:", height=200)

    col_btn1, col_btn2, col_btn3 = st.columns(3)
    with col_btn1:
        generate_cover = st.button("📝 Cover Letter", use_container_width=True)
    with col_btn2:
        generate_cv = st.button("📄 CV Summary", use_container_width=True)
    with col_btn3:
        analyze_jd = st.button("🔍 Analyse Job", use_container_width=True)

    if generate_cover or generate_cv or analyze_jd:
        missing = []
        if not company_name: missing.append("Company Name")
        if not job_role: missing.append("Job Role")
        if not job_description: missing.append("Job Description")

        if missing:
            st.error(f"❌ Missing fields: {missing}")
        else:
            cv_context = st.session_state.get('cv_text', '')
            with st.spinner("🤖 Groq AI is writing..."):
                try:
                    if analyze_jd:
                        prompt = f"List the top 7 required skills from this job description as a bulleted list:\n\n{job_description}"
                        task = "Job Analysis"
                    elif generate_cover:
                        prompt = f"Write a short, tailored cover letter (under 300 words).\n\nCV: {cv_context}\n\nJob: {job_description}"
                        task = "Cover Letter"
                    else:
                        prompt = f"Rewrite the professional summary and top 5 skills to match this job. Make it ATS-friendly.\n\nCV: {cv_context}\n\nJob: {job_description}"
                        task = "CV Summary"

                    result_text = call_groq(prompt)

                    if not analyze_jd:
                        add_application(company_name, job_role, result_text)
                        st.success(f"✅ {task} Generated & Application Saved!")
                    else:
                        st.success("✅ Job Analysis Complete!")
                    st.write("---")
                    st.subheader(f"Your {task}")
                    st.write(result_text)
                except Exception as e:
                    st.error(f"❌ AI CALL FAILED: {type(e).__name__}: {e}")

with tab2:
    st.subheader("📊 Your Application Dashboard")
    total, interviewing, offers, rejected = get_metrics()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Applied", total)
    m2.metric("Interviewing", interviewing)
    m3.metric("Offers", offers)
    m4.metric("Rejected", rejected)
    st.write("---")
    applications = get_applications()
    if applications:
        for app in applications:
            app_id, company, role, date, status, letter = app
            with st.expander(f"**{company}** — {role}  |  Status: {status}"):
                st.write(f"📅 Applied on: {date}")
                st.write(letter)
    else:
        st.info("No applications tracked yet.")
