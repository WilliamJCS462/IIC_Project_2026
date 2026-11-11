import streamlit as st
import requests
import os
from dotenv import load_dotenv, dotenv_values
from graph.graph import run_graph
from database.database import database_init

load_dotenv()

#start database
database_init()

st.set_page_config(
    page_title="SQL Assistant",
    page_icon="👾",
    layout="wide"
)

st.title("SQL Assistant")
st.caption("AI Powered SQL Assistant")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask the assistant a question")

if prompt:
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    response = run_graph(prompt)

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

    with st.chat_message("assistant"):
        st.markdown(response)

