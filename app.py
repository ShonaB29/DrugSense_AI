import streamlit as st
import numpy as np
from sklearn.linear_model import LogisticRegression

# -------------------------------------------------------
# ⚠️ IMPORTANT DISCLAIMER
# -------------------------------------------------------
# This app is ONLY a DEMO.
# It uses synthetic (fake) data and a simple ML model.
# It is NOT a real medical tool.
# DO NOT use it for diagnosis, treatment, or prescriptions.
# Always consult a qualified doctor.
# -------------------------------------------------------

# ---------- Helper: build a tiny synthetic dataset ---------

def build_synthetic_data(n_samples: int = 800):
    """
    Create synthetic (fake) patient data to train a demo model.
    Features:
        [age, sex(0/1), systolic_bp, diastolic_bp,
         weight, diabetes(0/1), smoker(0/1), symptom_score]
    Target:
        1 = "needs urgent medical review / possible prescription"
        0 = "low immediate risk"
    """
    rng = np.random.default_rng(42)

    # Random but somewhat realistic ranges
    age = rng.integers(18, 90, size=n_samples)
    sex = rng.integers(0, 2, size=n_samples)  # 0 = female, 1 = male
    sbp = rng.integers(90, 190, size=n_samples)   # systolic
    dbp = rng.integers(50, 120, size=n_samples)   # diastolic
    weight = rng.integers(40, 130, size=n_samples)
    diabetes = rng.integers(0, 2, size=n_samples)
    smoker = rng.integers(0, 2, size=n_samples)
    symptom_score = rng.integers(0, 10, size=n_samples)

    # Simple rule-based formula to generate labels (fake logic)
    risk_raw = (
        (age > 60).astype(int) * 1.0 +
        (sbp > 150).astype(int) * 1.0 +
        (dbp > 95).astype(int) * 0.5 +
        (diabetes == 1).astype(int) * 1.2 +
        (smoker == 1).astype(int) * 0.8 +
        (symptom_score / 10.0) * 2.0
    )

    # Convert risk score to binary target with sigmoid-ish threshold
    prob = 1 / (1 + np.exp(-(risk_raw - 2.5)))
    y = (prob > 0.5).astype(int)

    X = np.column_stack(
        [age, sex, sbp, dbp, weight, diabetes, smoker, symptom_score]
    )
    return X, y


@st.cache_resource
def train_demo_model():
    X, y = build_synthetic_data()
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    return model


# ------------- Streamlit UI starts here -------------------

st.set_page_config(
    page_title="AI Prescription Risk Demo",
    page_icon="🩺",
    layout="centered"
)

st.title("🩺 AI Prescription Risk Demo (NOT real medical tool)")
st.caption(
    "Educational demo using synthetic data and a simple ML model. "
    "Do **NOT** use for any real medical decisions."
)

st.markdown("---")

st.subheader("Patient Details")

col1, col2 = st.columns(2)

with col1:
    age = st.slider("Age (years)", 18, 90, 35)
    sex_label = st.selectbox("Sex", ["Female", "Male"])
    weight = st.slider("Weight (kg)", 35, 150, 65)

with col2:
    sbp = st.slider("Systolic BP (mmHg)", 80, 200, 120)
    dbp = st.slider("Diastolic BP (mmHg)", 40, 120, 80)
    diabetes_label = st.selectbox("Diabetes", ["No", "Yes"])

st.subheader("Lifestyle & Symptoms")

col3, col4 = st.columns(2)

with col3:
    smoker_label = st.selectbox("Smoker", ["No", "Yes"])

with col4:
    symptom_score = st.slider(
        "Overall symptom severity",
        0, 10, 3,
        help="0 = no symptoms, 10 = very severe"
    )

st.markdown("---")

if st.button("🔍 Predict Risk (Demo)"):
    # Encode categorical variables
    sex = 1 if sex_label == "Male" else 0
    diabetes = 1 if diabetes_label == "Yes" else 0
    smoker = 1 if smoker_label == "Yes" else 0

    # Build feature vector
    X_input = np.array([[age, sex, sbp, dbp, weight, diabetes, smoker, symptom_score]])

    # Load / train demo model
    model = train_demo_model()

    # Predict probability
    prob = model.predict_proba(X_input)[0, 1]
    pred = model.predict(X_input)[0]

    risk_percent = float(prob * 100)

    st.subheader("Result (Demo Only)")

    # Simple text feedback
    if risk_percent < 25:
        level = "Low"
        color = "🟢"
    elif risk_percent < 60:
        level = "Moderate"
        color = "🟡"
    else:
        level = "High"
        color = "🔴"

    st.metric(
        label="Estimated risk of needing medical review / prescription (DEMO)",
        value=f"{risk_percent:.1f} %"
    )

    st.write(f"**Risk level (demo): {color} {level}**")

    # Some generic, safe suggestions
    st.markdown("### What this means (in this demo)")
    if level == "Low":
        st.write(
            "- In this *demo*, your inputs look **low risk**.\n"
            "- In real life, even low risk people can have serious issues."
        )
    elif level == "Moderate":
        st.write(
            "- In this *demo*, your inputs show **moderate risk**.\n"
            "- In real life, a doctor may want to review your case."
        )
    else:  # High
        st.write(
            "- In this *demo*, your inputs show **high risk**.\n"
            "- In real life, you should seek medical attention from a professional."
        )

    st.markdown("---")
    st.markdown(
        "⚠️ **Strong Warning:**\n"
        "- This tool is a classroom / demo project only.\n"
        "- It is **not** based on real clinical guidelines.\n"
        "- It must **never** replace a doctor or real medical advice."
    )
else:
    st.info("Fill the details above and click **Predict Risk (Demo)** to see the demo AI output.")
