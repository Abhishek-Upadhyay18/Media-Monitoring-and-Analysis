# streamlit run main.py --server.headless true
import streamlit as st
import subprocess
import os
import sys

# Check if running with specific page parameter
if len(sys.argv) > 1 and sys.argv[1] == "dashboard":
    # Run the dashboard directly
    import dashboard
else:
    # Run home page by default
    import Home

# Note: This file serves as an entry point.
# Run with: streamlit run main.py
# For direct dashboard access: streamlit run main.py dashboard 