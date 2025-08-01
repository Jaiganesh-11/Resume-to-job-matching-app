import streamlit as st
import pandas as pd
import fitz
import smtplib
import time
import matplotlib.pyplot as plt
from email.mime.text import MIMEText
import re
from io import BytesIO
from PIL import Image
import os

# ----- Page Configuration -----
st.set_page_config(page_title="Resume to Job Matcher", layout="centered")

# ----- Custom CSS Styling -----
st.markdown("""
    <style>
        .stApp {
            background-image: url('background.jpg');
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
            background-position: center;
        }
        .title-text {
            font-size: 35px;
            font-weight: bold;
            color: #000000;
            text-align: center;
            margin-bottom: 20px;
        }
        .desc-text {
            font-size: 20px;
            color: #A9A9A9;
            text-align: center;
            margin-bottom: 30px;
        }
    </style>
""", unsafe_allow_html=True)

# ----- Banner Image (Top) -----
if os.path.exists("banner.png"):
    try:
        image = Image.open("banner.png")
        resized_image = image.resize((800, 250))  # (width, height)
        st.image(resized_image)
    except Exception as e:
        st.warning(f"Failed to load banner image: {e}")
else:
    st.info("Banner image not found. Please add 'banner.png' to the app folder.")

# ----- Title and Description -----
st.markdown('<div class="title-text">📄 Resume to Job Matcher</div>', unsafe_allow_html=True)
st.markdown('<div class="desc-text">Upload resumes in PDF format and automatically extract job titles, skills, and more!</div>', unsafe_allow_html=True)

# ----- Helper: Extract text from PDF -----
def extract_text_from_pdf(uploaded_pdf):
    text = ""
    try:
        with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text

# ----- Helper: Extract field -----
def extract_field(text, field_name):
    pattern = rf"{field_name}:\s*(.*)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""

# ----- Helper: Extract experience -----
def extract_experience(text):
    pattern = r"experience_years:\s*(\d+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0

# ----- Helper: Send Email -----
def send_email(recipient_email, subject, body):
    sender_email = st.secrets.get("EMAIL")
    sender_password = st.secrets.get("PASSWORD")

    if not sender_email or not sender_password:
        st.error("Email credentials not found in Streamlit secrets!")
        return False

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.warning(f"Error sending email to {recipient_email}: {e}")
        return False

# ----- Helper: Determine Job Title -----
def determine_title(skills_text, projects_text):
    combined = f"{skills_text} {projects_text}".lower()

    if re.search(r"\b(data science|pandas|matplotlib|data analyst)\b", combined):
        return "Data Scientist"
    elif re.search(r"\b(machine learning|regression|classification|sklearn)\b", combined):
        return "Machine Learning Engineer"
    elif re.search(r"\b(full stack|react|node\.js|frontend|backend)\b", combined):
        return "Full Stack Developer"
    elif re.search(r"\b(web design|html|css|javascript|web designer)\b", combined):
        return "Web Designer"
    elif re.search(r"\b(artificial intelligence|deep learning)\b", combined):
        return "AI Engineer"
    elif re.search(r"\b(ui/ux|figma|adobe xd|user interface|user experience)\b", combined):
        return "UI/UX Designer"
    elif re.search(r"\b(game dev|unity|unreal|game design|game developer)\b", combined):
        return "Game Designer"
    else:
        return "Unknown"

# ----- Upload Resumes -----
st.markdown("### 📤 Upload Your Resumes (PDFs only)")
uploaded_files = st.file_uploader("Upload here", type=["pdf"], accept_multiple_files=True)

# ----- Process Resumes -----
all_resume_data = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        message_placeholder = st.empty()
        message_placeholder.success(f"✅ '{uploaded_file.name}' uploaded successfully!")
        time.sleep(1.5)
        message_placeholder.empty()

        resume_text = extract_text_from_pdf(uploaded_file)

        resume_data = {
            "name": extract_field(resume_text, "Name") or uploaded_file.name.replace(".pdf", "").title(),
            "resume_skills": extract_field(resume_text, "resume_skills"),
            "projects": extract_field(resume_text, "Projects"),
            "experience_years": extract_experience(resume_text),
            "email": extract_field(resume_text, "Email")
        }

        resume_data["resume_title"] = determine_title(resume_data["resume_skills"], resume_data["projects"])
        all_resume_data.append(resume_data)

    resume_df = pd.DataFrame(all_resume_data)

    selected_df = resume_df[resume_df["resume_title"] != "Unknown"]
    rejected_df = resume_df[resume_df["resume_title"] == "Unknown"]

    # ----- Visualization: Pie Chart of Selection Results -----
    if not resume_df.empty:
        st.subheader("📊 Resume Screening Summary")

        counts = [len(selected_df), len(rejected_df)]
        labels = ['Selected', 'Rejected']
        colors = ['#4CAF50', '#FF5252']

        fig, ax = plt.subplots()
        wedges, texts, autotexts = ax.pie(
            counts,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            textprops=dict(color="white")
        )
        ax.axis('equal')  # Equal aspect ratio ensures pie is drawn as a circle

        st.pyplot(fig)

    st.subheader("✅ Selected Candidates")
    st.dataframe(selected_df)

    st.subheader("❌ Rejected Candidates")
    st.dataframe(rejected_df)

    # ----- Job Title Distribution Chart -----
    st.subheader("📊 Job Title Distribution")
    if not resume_df.empty:
        role_counts = resume_df["resume_title"].value_counts()
        st.bar_chart(role_counts)

    # Download buttons
    if not selected_df.empty:
        excel_buffer = BytesIO()
        selected_df.to_excel(excel_buffer, index=False, engine="openpyxl")
        st.download_button("📥 Download Selected Candidates", data=excel_buffer.getvalue(), file_name="selected_candidates.xlsx")

    if not rejected_df.empty:
        reject_buffer = BytesIO()
        rejected_df.to_excel(reject_buffer, index=False, engine="openpyxl")
        st.download_button("📥 Download Rejected Candidates", data=reject_buffer.getvalue(), file_name="rejected_candidates.xlsx")

    # Send Emails
    if st.button("📧 Send Emails"):
        selected_sent = 0
        rejected_sent = 0

        for _, row in selected_df.iterrows():
            if not row["email"]:
                continue
            subject = "Congratulations! You've Been Selected"
            body = f"Hi {row['name']}, you’ve been selected for the role: {row['resume_title']}!"
            if send_email(row["email"], subject, body):
                selected_sent += 1

        for _, row in rejected_df.iterrows():
            if not row["email"]:
                continue
            subject = "Application Update"
            body = "Sorry, your profile is not matching this job. We will meet soon."
            if send_email(row["email"], subject, body):
                rejected_sent += 1

        st.success(f"Emails sent: ✅ {selected_sent} selected, ❌ {rejected_sent} rejected.")
