import streamlit as st
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import os

# -----------------------------
# CONFIG
# -----------------------------

EMAIL = "dhanushsanjeevi75300@gmail.com"
APP_PASSWORD = "xucb ztsm phli xxxw"

st.set_page_config(page_title="JD Matching System", layout="wide")
st.markdown("<h1 style='text-align: center; color: #4CAF50;'>🤖 Infomates AI JD Matching System</h1>", unsafe_allow_html=True)
st.markdown("---")


# -----------------------------
# FILE UPLOAD (TOP)
# -----------------------------

uploaded_file = st.file_uploader("📂 Upload Student Excel", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
else:
    st.warning("⚠️ Please upload student file")
    st.stop()

# -----------------------------
# INPUT SECTION
# -----------------------------

jd_text = st.text_area("Paste Job Description")

col1, col2 = st.columns(2)
company_name = col1.text_input("Company Name")
location_filter = col2.text_input("Location Filter")

threshold = st.slider("Match Threshold (%)", 0, 100, 20)

# -----------------------------
# BUTTONS
# -----------------------------

run = st.button("🔍 Run Matching")
send = st.button("📧 Send Emails")

# -----------------------------
# MATCH FUNCTION
# -----------------------------

def match_candidates(df, jd_text):

    # Auto detect skills column
    if "Skills (Structured Format)" in df.columns:
        df["combined"] = df["Skills (Structured Format)"].astype(str)
    elif "Specialization" in df.columns:
        df["combined"] = df["Specialization"].astype(str)
    elif "Skills" in df.columns:
        df["combined"] = df["Skills"].astype(str)
    else:
        st.error("❌ No skills column found in Excel")
        st.write("Available columns:", df.columns)
        st.stop()

    documents = df["combined"].tolist()
    documents.append(jd_text)

    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(documents)

    similarity = cosine_similarity(tfidf[-1], tfidf[:-1])

    df["Match %"] = similarity[0] * 100

    return df

# -----------------------------
# RUN MATCHING
# -----------------------------

if run:

    if jd_text.strip() == "":
        st.warning("⚠️ Enter Job Description")
    else:
        result = match_candidates(df, jd_text)

        if location_filter:
            result = result[result["Preferred Job Location"]
                            .str.contains(location_filter, case=False, na=False)]

        result = result.sort_values("Match %", ascending=False)

        st.session_state["result"] = result

        st.subheader("📊 Matching Results")
        st.dataframe(result)

        st.download_button(
            "⬇ Download Results",
            result.to_csv(index=False),
            file_name="matched_results.csv"
        )

# -----------------------------
# SEND EMAIL
# -----------------------------

if send:

    if "result" not in st.session_state:
        st.warning("⚠️ Run matching first")
    else:
        result = st.session_state["result"]
        top_candidates = result[result["Match %"] > threshold]
        
        if not result.empty:
            top_candidate = result.iloc[0]
            st.success(f"🏆 Top Candidate: {top_candidate['Name']} | Match: {round(top_candidate['Match %'],2)}%")

        if top_candidates.empty:
            st.warning("No candidates above threshold")
        else:

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(EMAIL, APP_PASSWORD)

            log_data = []

            for _, row in top_candidates.iterrows():

                body = f"""
Dear {row['Name']},

You are shortlisted for {company_name}.

Regards,
Placement Team
"""
top_candidate = result.iloc[0]

                msg = MIMEText(body)
                msg['Subject'] = f"Job Opportunity - {company_name}"
                msg['From'] = EMAIL
                msg['To'] = row["Email"]

                server.send_message(msg)

                log_data.append([
                    row["Name"],
                    row["Email"],
                    company_name,
                    datetime.now()
                ])

            server.quit()

            log_df = pd.DataFrame(
                log_data,
                columns=["Name", "Email", "Company", "Date"]
            )

            if os.path.exists("report_log.xlsx"):
                old = pd.read_excel("report_log.xlsx")
                log_df = pd.concat([old, log_df])

            log_df.to_excel("report_log.xlsx", index=False)

            st.success("✅ Emails Sent & Report Updated")
