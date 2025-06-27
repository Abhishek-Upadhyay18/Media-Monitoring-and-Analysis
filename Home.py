# Search string

import streamlit as st
import os
import subprocess
import sys

# Set page config
st.set_page_config(
    page_title="Media Monitoring Dashboard",
    page_icon="📰",     
    layout="wide"
)

# Custom CSS to style the buttons
st.markdown("""
    <style>
    .big-button {
        padding: 20px 30px;
        background-color: #4CAF50;
        color: white;
        border: none;
        border-radius: 10px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 18px;
        margin: 10px 2px;
        cursor: pointer;
        transition-duration: 0.4s;
        width: 100%;
    }
    .big-button:hover {
        background-color: #45a049;
        box-shadow: 0 12px 16px 0 rgba(0,0,0,0.24), 0 17px 50px 0 rgba(0,0,0,0.19);
    }
    .welcome-text {
        font-size: 100px;
        text-align: center;
        margin-top: 50px;
        margin-bottom: 40px;
        color: #333;
        font-weight: bold;
    }
    .subtitle {
        font-size: 24px;
        text-align: center;
        margin-bottom: 50px;
        color: #666;
    }
    </style>
""", unsafe_allow_html=True)

# Welcome title with custom styling
st.markdown('<div class="welcome-text">Welcome</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Media Monitoring Dashboard</div>', unsafe_allow_html=True)

# Container for buttons
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # Button for collecting news
    if st.button('Take Me to the Dashboard', key='collect', 
                use_container_width=True, type="primary"):
        # Navigate to the News Collection page
        st.switch_page("pages/3_News_Dashboard_using_API.py")
        
    # Some space between buttons
    st.write("")
    
    # Button to go to dashboard - using Streamlit's page navigation
    #if st.button('Take Me to the Dashboard', key='dashboard', 
    #            use_container_width=True):
    #   # Navigate to the Dashboard page
    #    st.switch_page("pages/3_News_Dashboard_using_API.py")
    #    # Alternatively, we can launch the dashboard script
    #    # subprocess.Popen(["streamlit", "run", "dashboard.py"]) 
        
    # Some space between buttons
    st.write("") 