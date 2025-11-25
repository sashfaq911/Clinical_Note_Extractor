import json

import streamlit as st
import pandas as pd

from clinical_extractor import extract_clinical_data  # updated schema

# --------- Page config ---------
st.set_page_config(
    page_title="Clinical Note Extractor🔎",
    layout="centered",
)

# --------- Sidebar ---------
st.sidebar.title("💡About this tool")
st.sidebar.markdown(
    """
This prototype:

- Accepts **de-identified** clinical notes  
- Works with notes exported from **Epic, Accuro, Cerner, Allscripts, OSCAR, MedAccess**, etc.  
- Uses an LLM to extract structured clinical data (JSON).

⚠️ **Not for production use.**
Do **not** paste real PHI or live patient data.
"""
)

st.sidebar.markdown("---")
st.sidebar.markdown("✅ **Ideal for:**")
st.sidebar.markdown(
    """
- Health informatics & data teams  
- Prototyping digital health tools  
- Clinical NLP experiments
"""
)


# --------- Main layout ---------
st.title("Clinical Note Information Extractor")
st.caption("Turn unstructured EMR-style clinical notes into structured JSON for analysis and prototyping.")

st.markdown(
    """
**Instructions**

1. Paste a **de-identified** clinical note (e.g., from Epic/Accuro) into the box.  
2. Click **Extract**.  
3. Review the structured summary, meds, tests, and raw JSON.
"""
)

# Text input area
note = st.text_area(
    "Clinical note (de-identified):",
    height=260,
    placeholder="Paste a clinical note here (no PHI)...",
)

col_button, _ = st.columns([1, 3])
with col_button:
    extract_clicked = st.button("🔍 Extract")

if extract_clicked:
    if not note.strip():
        st.warning("Please paste a clinical note before extracting.")
    else:
        with st.spinner("Extracting structured information from the note..."):
            try:
                result = extract_clinical_data(note)
            except Exception as e:
                st.error(f"Could not extract information: {e}")
                result = None

        if result:
            st.success("Extraction complete ✅.")

            # ---- Tabs for organized UI ----
            tab_overview, tab_meds, tab_tests, tab_json = st.tabs(
                ["📋 Overview", "💊 Medications", "🧪 Tests & Imaging", "🧾 JSON Output"]
            )

            # ---------- OVERVIEW TAB ----------
            with tab_overview:
                st.subheader("Patient Summary")

                age = result.get("patient_age")
                sex = result.get("patient_sex")
                cc = result.get("chief_complaint") or "—"
                primary_dx = result.get("primary_diagnosis") or "—"
                secondary_dx_list = result.get("secondary_diagnoses") or []
                secondary_dx = ", ".join(secondary_dx_list) if secondary_dx_list else "—"

                allergies_list = result.get("allergies") or []
                allergies_display = ", ".join(allergies_list) if allergies_list else "No allergies extracted"

                # Demographics, Diagnoses, Allergies in three columns
                col_demo, col_dx, col_all = st.columns(3)

                with col_demo:
                    st.markdown("#### Demographics")
                    demo_df = pd.DataFrame(
                        {
                            "Field": ["Age", "Sex"],
                            "Value": [
                                age if age is not None else "—",
                                sex.capitalize() if isinstance(sex, str) else "—",
                            ],
                        }
                    )
                    demo_df.index = demo_df.index + 1
                    st.table(demo_df)

                with col_dx:
                    st.markdown("#### Diagnoses")
                    dx_df = pd.DataFrame(
                        {
                            "Type": ["Primary", "Secondary"],
                            "Value": [primary_dx, secondary_dx],
                        }
                    )
                    dx_df.index = dx_df.index + 1
                    st.table(dx_df)

                with col_all:
                    st.markdown("#### Allergies")
                    all_df = pd.DataFrame(
                        {
                            "Type": ["Allergies"],
                            "Value": [allergies_display],
                        }
                    )
                    all_df.index = all_df.index + 1
                    st.table(all_df)

                st.markdown("#### Chief Complaint")
                st.write(cc)

                st.markdown("#### Follow-up & Return Precautions")
                follow_up = result.get("follow_up_instructions") or "Not specified."
                precautions = result.get("return_precautions") or "Not specified."

                col_fp, col_rp = st.columns(2)
                with col_fp:
                    st.markdown("**Follow-up instructions:**")
                    st.write(follow_up)

                with col_rp:
                    st.markdown("**Return precautions:**")
                    st.write(precautions)

                st.caption(
                    "ℹ️ Allergies are shown prominently for quick clinical awareness. "
                    "Always confirm against the source EMR."
                )

            # ---------- MEDICATIONS TAB ----------
            with tab_meds:
                st.subheader("Medications")

                current_meds = result.get("current_medications") or []
                prescribed_meds = result.get("prescribed_medications") or []

                # Current (home) medications
                st.markdown("##### Current (Home) Medications")
                if current_meds:
                    current_df = pd.DataFrame(current_meds)
                    for col in ["name", "dose", "route", "frequency", "duration"]:
                        if col not in current_df.columns:
                            current_df[col] = ""
                    current_df = current_df[["name", "dose", "route", "frequency", "duration"]]

                    current_df.index = current_df.index + 1
                    st.table(current_df)
                else:
                    st.info("No current/home medications were extracted from this note.")

                st.markdown("---")

                # Medications prescribed at this visit
                st.markdown("##### Medications Prescribed This Visit")
                if prescribed_meds:
                    prescribed_df = pd.DataFrame(prescribed_meds)
                    for col in ["name", "dose", "route", "frequency", "duration"]:
                        if col not in prescribed_df.columns:
                            prescribed_df[col] = ""
                    prescribed_df = prescribed_df[["name", "dose", "route", "frequency", "duration"]]
                    prescribed_df.index = prescribed_df.index + 1
                    st.table(prescribed_df)
                else:
                    st.info("No visit-specific prescribed medications were extracted.")

            # ---------- TESTS & IMAGING TAB ----------
            with tab_tests:
                st.subheader("Tests & Imaging")
                tests = result.get("tests_or_imaging") or []

                if tests:
                    tests_df = pd.DataFrame({"Test / Imaging Ordered": tests})
                    tests_df.index = tests_df.index + 1
                    st.table(tests_df)
                else:
                    st.info("No tests or imaging were extracted from this note.")

            # ---------- RAW JSON TAB ----------
            with tab_json:
                st.subheader("Raw JSON Output")

                json_str = json.dumps(result, indent=2)
                st.json(result, expanded=False)

                st.markdown("#### Export")

                # Download as JSON
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_str,
                    file_name="clinical_extraction.json",
                    mime="application/json",
                )

                # Download as CSV (flattened)
                try:
                    flat_df = pd.json_normalize(result)
                    csv_str = flat_df.to_csv(index=False)
                    st.download_button(
                        label="⬇️ Download CSV",
                        data=csv_str,
                        file_name="clinical_extraction.csv",
                        mime="text/csv",
                    )
                except Exception:
                    st.caption("CSV export not available for this structure.")

                st.caption(
                    "Tip: you can also select the JSON above and copy it manually if needed."
                )

            st.caption(
                """
                ---
                ⚠️ This tool is for experimentation and prototyping only. 
                It does not provide medical advice or replace clinical judgment.
                👩‍💻 *Developed by Soobiya Ashfaq*
                """
            )
