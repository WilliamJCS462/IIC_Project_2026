import streamlit as st
import os
import yaml
from dotenv import load_dotenv, dotenv_values
from pathlib import Path
from graph.graph import run_graph
from database.database import database_init
from utils.errors import get_error_code
from tests.tests import run_accuracy_tests

base_dir = Path(__file__).resolve().parent
load_dotenv()

#start database
database_init()

#import styles
styles = Path("utils/styles.css")
st.markdown(f"<style>{styles.read_text()}</style>", unsafe_allow_html=True)

#load the yaml which might not exist yet
def load_metrics():
    metrics_path = base_dir / "tests" / "metrics.yaml"
    if metrics_path.exists():
        with open(metrics_path, "r") as file:
            metrics = yaml.safe_load(file) or {}
    else:
        metrics = {}
    if "accuracy" in metrics:
        accuracy_message = f"Current Accuracy: {int(round(metrics['accuracy'], 2) * 100)}%"
    else:
        accuracy_message = f"Current Accuracy: Untested"
    return accuracy_message

st.set_page_config(
    page_title="SQL Assistant",
    page_icon="👾",
    layout="wide"
)

with st.container(key="chatbot"):

    with st.container(key="title_bar"):
        with st.container(key="chatbot_pfp"):
            st.markdown("👾")

        with st.container(key="title_caption"):
            st.title("SQL Assistant")
            st.caption("AI Powered SQL Assistant")

        if st.button(label="Calculate Accuracy", key="accuracy_button"):
            st.session_state.calc_accuracy = True #delay button function for streamlit ordering :(

        with st.container(key="accuracy_score", width="content"):
            accuracy_placeholder = st.empty() #switches between progress bar and content score

            if st.session_state.get("calc_accuracy", False):
                test_progress = accuracy_placeholder.progress(0, text="Starting tests...") #progress bar, inserted into the accuracy placeholder

                #create a function to use as a callback
                def update_progress(current, total):
                    test_progress.progress(current / total, text="Running tests...")

                run_accuracy_tests(update_progress) #actually runs the tests, updates the progress bar internally

                st.session_state.calc_accuracy = False #reset button

                accuracy_placeholder.markdown(load_metrics()) #when finished load

            else:
                accuracy_placeholder.markdown(load_metrics()) #be default load

    #being slightly clever here. Inserting into messsages container both before and after prompt as this needs to be outside messages so it pins to the bottom
    messages = st.container(key="messages", height=300, border=None)

    with messages:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    with st.container(key="prompt_bar"):
        prompt = st.chat_input("Ask the assistant a question...")

    if prompt:
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        with messages:
            with st.chat_message("user", avatar=":material/account_circle:"):
                st.markdown(prompt)

            with st.chat_message("assistant", avatar=":material/robot_2:"):
                response_placeholder = st.empty() #I don't know why this works but found this solution to duplicate chat messages appearing under the assistant
                with response_placeholder.container():
                    with st.spinner("Thinking..."):
                        try:
                            response = run_graph(prompt)
                        except Exception as e:
                            reponse = f"ERROR - Error Codes: GRAPH_RUN_FAILURE, {get_error_code(e)}"

                    response_placeholder.markdown(response)

        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

