"""Retired — this Hugging Face Space has moved to Render.

The scanner has been replatformed as a FastAPI + React app with four
interactive tabs (Live Scanner, Attack Lab, Slice Explorer, Calibration
Dashboard). Please visit the new location.
"""
import streamlit as st

st.set_page_config(page_title="Moved — Robustness Review", page_icon="🔬")

st.title("This Space has moved")
st.markdown("""
The **Harm Classifier Robustness Scanner** has been replatformed as a
full-featured FastAPI + React app.

### New location

**[https://robustness-review.onrender.com](https://robustness-review.onrender.com)**

The new app includes:
- **Live Scanner** — toxicity gauge, FLAGGED / BORDERLINE / CLEAN verdict,
  Bloom-filter tier-0 pre-check
- **Attack Lab** — full 9-attack evasion matrix with normalization defenses
- **Slice Explorer** — 18 HateCheck slices with real missed examples
- **Calibration Dashboard** — dual reliability curves with a draggable
  threshold slider

Source code and working paper:
[github.com/Prakharanand000/TandS-harm-classifier-eval](https://github.com/Prakharanand000/TandS-harm-classifier-eval)
""")

st.info("You will be redirected automatically in a moment.")
st.markdown(
    '<meta http-equiv="refresh" content="4; url=https://robustness-review.onrender.com">',
    unsafe_allow_html=True,
)
