# News Collection Page

import streamlit as st
import subprocess
import time
import sys
import os
import tempfile
import threading
import queue

# Initialize session state for confirmation dialog
if 'show_extract_confirmation' not in st.session_state:
    st.session_state.show_extract_confirmation = False

# Set page config
st.set_page_config(
    page_title="News Collection and Pre-Processing",
    page_icon="📡",
    layout="wide"
)

# Title and description
st.title("News Collection and Pre-Processing")
st.markdown("### This feature will be implemented in a future update")

# Add some placeholder content
st.info("This page will allow you to collect news from various sources including Economic Times, Mint, and The Hindu.")

# Create a sample UI for news collection
st.markdown("### Collect news articles from various sources")

# Source selection
sources = ['Economic Times', 'Mint', 'The Hindu', 'All Sources']
selected_sources = st.multiselect('Select News Sources', sources, default=['All Sources'])

# Create two columns for buttons
col1, col2 = st.columns(2)

# Collection button in first column
with col1:
    collect_button = st.button("Collect News", key="collect_news", type="primary", use_container_width=True)

# Extract Themes button in second column with same styling
with col2:
    # This button only sets the state to show confirmation
    extract_button = st.button("Extract Themes and Topics", key="extract_topics", type="primary", use_container_width=True)
    if extract_button:
        st.session_state.show_extract_confirmation = True

# Display confirmation dialog if state is True
if st.session_state.show_extract_confirmation:
    # Create a container styled like a popup
    with st.container():
        st.markdown("""
        <style>
        .confirmation-popup {
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="confirmation-popup">', unsafe_allow_html=True)
        st.warning("⚠️ Confirmation Required")
        st.markdown("Are you sure you want to extract themes and topics? This process may take some time.")
        
        # Create two columns for confirmation buttons
        conf_col1, conf_col2 = st.columns(2)
        
        with conf_col1:
            if st.button("Yes, Extract Themes", key="confirm_extract", type="primary"):
                st.session_state.show_extract_confirmation = False
                # Run the keywords_topics.py script
                st.info("Running theme extraction process. Please wait...")
                try:
                    process = subprocess.Popen(
                        [sys.executable, "keywords_topics.py"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True
                    )
                    output, _ = process.communicate()
                    if process.returncode == 0:
                        st.success("Theme extraction completed successfully!")
                    else:
                        st.error(f"Error running theme extraction: {output}")
                except Exception as e:
                    st.error(f"Failed to run theme extraction: {str(e)}")
        
        with conf_col2:
            if st.button("Cancel", key="cancel_extract"):
                st.session_state.show_extract_confirmation = False
                st.info("Theme extraction cancelled.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Create a container for the output
output_container = st.container()
output_placeholder = st.empty()

# Function to map selected sources to their corresponding scripts
def get_scripts_to_run(sources):
    scripts = []
    if 'All Sources' in sources:
        scripts = ['ET_news_integrated.py', 'mint_news_integrated.py', 'Hindu_news_integrated.py']
    else:
        if 'Economic Times' in sources:
            scripts.append('ET_news_integrated.py')
        if 'Mint' in sources:
            scripts.append('Mint_news_integrated.py')
        if 'The Hindu' in sources:
            scripts.append('Hindu_news_integrated.py')
    return scripts

# Create a more prominent progress area
st.markdown("""
<style>
.progress-container {
    margin-top: 20px;
    margin-bottom: 30px;
}
.progress-label {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 10px;
    color: #31333F;
}
.stProgress > div > div > div > div {
    height: 20px;
    background: linear-gradient(90deg, #4CAF50, #8BC34A, #4CAF50);
    background-size: 200% 100%;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0% {
        background-position: 0% 50%;
    }
    50% {
        background-position: 100% 50%;
    }
    100% {
        background-position: 0% 50%;
    }
}
.status-message {
    margin-top: 10px;
    font-style: italic;
    color: #555;
}
.log-container {
    background-color: #000;
    color: #00ff00;
    font-family: 'Courier New', monospace;
    padding: 15px;
    border-radius: 5px;
    height: 250px;
    overflow-y: auto;
    margin-top: 20px;
    margin-bottom: 20px;
    white-space: pre-wrap;
    word-wrap: break-word;
}
.log-line {
    margin: 0;
    padding: 2px 0;
}
</style>
""", unsafe_allow_html=True)

# Collection button logic
if collect_button:
    scripts_to_run = get_scripts_to_run(selected_sources)
    
    if not scripts_to_run:
        st.error("Please select at least one news source.")
    else:
        # Create an empty container for messages and progress display
        message_container = st.container()
        
        # Create a log display for script output
        log_container = st.container()
        with log_container:
            st.markdown("<h3>Script Output Log</h3>", unsafe_allow_html=True)
            log_display = st.empty()
            all_logs = []
        
        with message_container:
            progress_label = st.empty()
            progress_bar = st.progress(0)
            status_message = st.empty()  # For displaying the current status
            message_area = st.empty()
            
            total_scripts = len(scripts_to_run)
            messages = []
            
            # Calculate total progress units (5 units per script for more granular updates)
            total_progress_units = total_scripts * 5
            current_progress_unit = 0
            
            for i, script in enumerate(scripts_to_run):
                # Display which script is running
                source_name = script.replace('_news_integrated.py', '')
                progress_label.markdown(f"""
                <div class="progress-label">
                    Processing: {source_name} ({i+1}/{total_scripts})
                </div>
                """, unsafe_allow_html=True)
                
                # Add script start message
                start_message = f"🔄 Running {source_name} news collection script ({i+1}/{total_scripts})..."
                messages.append(start_message)
                message_area.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 15px; border-radius: 5px; margin-bottom: 10px;">
                    {'<br>'.join(messages)}
                </div>
                """, unsafe_allow_html=True)
                
                # Add to log
                log_line = f"[{time.strftime('%H:%M:%S')}] Starting {source_name} news collection..."
                all_logs.append(log_line)
                log_display.markdown(f'<div class="log-container">{"<br>".join(all_logs)}</div>', unsafe_allow_html=True)
                
                # Update progress - script started (1/5 of this script's total)
                current_progress_unit += 1
                progress_percent = int((current_progress_unit / total_progress_units) * 100)
                progress_bar.progress(progress_percent)
                status_message.markdown(f"""
                <div class="status-message">
                    Initializing {source_name} collection process...
                </div>
                """, unsafe_allow_html=True)
                
                # Actually run the script
                try:
                    # Create a temporary file to capture output
                    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as tmp:
                        tmp_filename = tmp.name
                    
                    # Get the absolute path to the script
                    current_dir = os.getcwd()
                    script_path = os.path.join(current_dir, script)
                    
                    # Update progress - starting to execute (2/5)
                    current_progress_unit += 1
                    progress_percent = int((current_progress_unit / total_progress_units) * 100)
                    progress_bar.progress(progress_percent)
                    status_message.markdown(f"""
                    <div class="status-message">
                        Starting execution of {source_name} script...
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add to log
                    log_line = f"[{time.strftime('%H:%M:%S')}] Executing {script_path}..."
                    all_logs.append(log_line)
                    log_display.markdown(f'<div class="log-container">{"<br>".join(all_logs)}</div>', unsafe_allow_html=True)
                    
                    # Setup process to capture output in real-time
                    process = subprocess.Popen(
                        [sys.executable, script_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    # Read output line by line and update the log in real-time
                    script_output_lines = []
                    for line in process.stdout:
                        line = line.strip()
                        if line:
                            script_output_lines.append(line)
                            log_line = f"[{time.strftime('%H:%M:%S')}] {line}"
                            all_logs.append(log_line)
                            # Update the log display with scrolling
                            log_display.markdown(f'<div class="log-container">{"<br>".join(all_logs[-100:])}</div>', unsafe_allow_html=True)
                            time.sleep(0.1)  # Small delay to simulate real-time output
                    
                    # Wait for process to complete
                    process.wait()
                    returncode = process.returncode
                    script_output = '\n'.join(script_output_lines)
                    
                    # Update progress - execution finished (3/5)
                    current_progress_unit += 1
                    progress_percent = int((current_progress_unit / total_progress_units) * 100)
                    progress_bar.progress(progress_percent)
                    status_message.markdown(f"""
                    <div class="status-message">
                        Execution completed, processing results...
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add to log
                    log_line = f"[{time.strftime('%H:%M:%S')}] Script execution completed with return code {returncode}"
                    all_logs.append(log_line)
                    log_display.markdown(f'<div class="log-container">{"<br>".join(all_logs[-100:])}</div>', unsafe_allow_html=True)
                    
                    # Update progress - processing results (4/5)
                    current_progress_unit += 1
                    progress_percent = int((current_progress_unit / total_progress_units) * 100)
                    progress_bar.progress(progress_percent)
                    status_message.markdown(f"""
                    <div class="status-message">
                        Analyzing collected data from {source_name}...
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Check if the script ran successfully
                    if returncode == 0:
                        success_message = f"✅ Successfully collected {source_name} news articles"
                        messages.append(success_message)
                        
                        # Add summary of the output
                        if script_output_lines:
                            messages.append(f"Processed {len(script_output_lines)} lines of output")
                    else:
                        error_message = f"❌ Error collecting {source_name} news (exit code {returncode})"
                        messages.append(error_message)
                        
                        # Add error details
                        log_line = f"[{time.strftime('%H:%M:%S')}] ERROR: Script failed with exit code {returncode}"
                        all_logs.append(log_line)
                        log_display.markdown(f'<div class="log-container">{"<br>".join(all_logs[-100:])}</div>', unsafe_allow_html=True)
                except Exception as e:
                    error_message = f"❌ Error executing {source_name} script: {str(e)}"
                    messages.append(error_message)
                    
                    # Add to log
                    log_line = f"[{time.strftime('%H:%M:%S')}] EXCEPTION: {str(e)}"
                    all_logs.append(log_line)
                    log_display.markdown(f'<div class="log-container">{"<br>".join(all_logs[-100:])}</div>', unsafe_allow_html=True)
                    
                    # Update status for error case
                    status_message.markdown(f"""
                    <div class="status-message" style="color: #d32f2f;">
                        Error occurred during {source_name} collection
                    </div>
                    """, unsafe_allow_html=True)
                
                # Update progress - script completed (5/5)
                current_progress_unit += 1
                progress_percent = int((current_progress_unit / total_progress_units) * 100)
                progress_bar.progress(progress_percent)
                status_message.markdown(f"""
                <div class="status-message">
                    Finished processing {source_name} ({i+1}/{total_scripts})
                </div>
                """, unsafe_allow_html=True)
                
                # Add to log
                log_line = f"[{time.strftime('%H:%M:%S')}] Completed {source_name} collection"
                all_logs.append(log_line)
                log_display.markdown(f'<div class="log-container">{"<br>".join(all_logs[-100:])}</div>', unsafe_allow_html=True)
                
                # Update the message display with the latest messages
                message_area.markdown(f"""
                <div style="background-color: #f0f2f6; padding: 15px; border-radius: 5px; margin-bottom: 10px;">
                    {'<br>'.join(messages)}
                </div>
                """, unsafe_allow_html=True)
            
            # Final progress update
            progress_label.markdown('<div class="progress-label">All scripts completed</div>', unsafe_allow_html=True)
            progress_bar.progress(100)
            status_message.markdown(f"""
            <div class="status-message" style="font-weight: bold; color: #4CAF50;">
                All collection processes complete!
            </div>
            """, unsafe_allow_html=True)
            
            # Final log entry
            log_line = f"[{time.strftime('%H:%M:%S')}] ALL SCRIPTS COMPLETED"
            all_logs.append(log_line)
            log_display.markdown(f'<div class="log-container">{"<br>".join(all_logs)}</div>', unsafe_allow_html=True)
            
            # Final message
            success_scripts = [s for s in messages if "✅" in s]
            if len(success_scripts) == total_scripts:
                st.success(f"Successfully collected news from all {total_scripts} sources!")
            else:
                st.warning(f"Completed with {len(success_scripts)} successful and {total_scripts - len(success_scripts)} failed collections.")
                
            # Add a note about where to view results
            st.info("Go to the Dashboard to view the collected articles.")
            
            # Add a button to navigate to dashboard
            if st.button("Go to Dashboard"):
                st.switch_page("pages/2_News_Dashboard.py") 