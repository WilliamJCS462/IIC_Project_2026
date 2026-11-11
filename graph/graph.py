from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List
from pathlib import Path
from dotenv import load_dotenv

from graph.nodes.generate_sql import generate_sql
from graph.nodes.run_sql import run_sql
from graph.nodes.generate_response import generate_response

base_dir = Path(__file__).resolve().parent.parent

#graph state
class State(TypedDict):
    user_message: str
    sql_query: str | None
    sql_data: str | None
    ai_response: str | None

#function wrappers
def call_generate_sql(state: State):
    result = generate_sql(state["user_message"])
    return result

def call_run_sql(state: State):
    result = run_sql(state["sql_query"])
    return result

def call_generate_response(state: State):
    result = generate_response(state["user_message"], state["sql_data"])
    return result

#build graph
graph = StateGraph(State)

graph.add_node("generate_sql", call_generate_sql)
graph.add_node("run_sql", call_run_sql)
graph.add_node("generate_response", call_generate_response)

graph.add_edge(START, "generate_sql")
graph.add_edge("generate_sql", "run_sql")
graph.add_edge("run_sql", "generate_response")
graph.add_edge("generate_response", END)

#run graph
def run_graph(user_input: str):
    state = {
        "user_message": user_input,
        "sql_query": None,
        "sql_data": None,
        "ai_response": None
    }

    chatbot = graph.compile()
    graph_result = chatbot.invoke(state)

    return graph_result["ai_response"]
