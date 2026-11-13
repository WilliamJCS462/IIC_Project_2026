import streamlit as st
import os
from dotenv import load_dotenv, dotenv_values
from pathlib import Path
from graph.graph import run_graph
from database.database import database_init
from utils.errors import get_error_code

base_dir = Path(__file__).resolve().parent.parent
load_dotenv()

#start database
database_init()

#import styles
styles = Path("utils/styles.css")
st.markdown(f"<style>{styles.read_text()}</style>", unsafe_allow_html=True)

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

            try:
                response = run_graph(prompt)
            except Exception as e:
                reponse = f"ERROR - Error Codes: GRAPH_RUN_FAILURE, {get_error_code(e)}"


            st.session_state.messages.append({
                "role": "assistant",
                "content": response
            })

            with st.chat_message("assistant", avatar=":material/robot_2:"):
                st.markdown(response)

