"""Entry point for Hugging Face Spaces / Streamlit Community Cloud.

Both platforms auto-detect a top-level ``streamlit_app.py``. The actual app
lives in ``scripts/scanner_app.py``; this thin wrapper runs it. ``runpy`` is used
(not ``import``) so the script re-executes on every Streamlit rerun rather than
being cached as an already-imported module.
"""
import os
import runpy
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
runpy.run_path(os.path.join(ROOT, "scripts", "scanner_app.py"), run_name="__main__")
