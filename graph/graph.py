from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List
from pathlib import Path
from dotenv import load_dotenv

from graph.nodes.generate_sql import generate_sql
from graph.nodes.run_sql import run_sql
from graph.nodes.generate_response import generate_answer_response, generate_error_response

base_dir = Path(__file__).resolve().parent.parent

#graph state
class State(TypedDict):
    user_message: str #user's inputted prompt
    sql_query: str | None #SQL query generated to answer prompt
    sql_data: str | None #Data returned from the SQL query
    ai_response: str | None #AI generated response to user prompt
    safe: bool #False when an error has occured
    error_code: str | None #Code to indicate which error has occured

#function wrappers, these just call functions from the nodes
def call_generate_sql(state: State):
    result = generate_sql(state["user_message"])
    return result

def call_run_sql(state: State):
    result = run_sql(state["sql_query"])
    return result

def call_generate_answer_response(state: State):
    result = generate_answer_response(state["user_message"], state["sql_data"])
    return result

def call_generate_error_response(state: State):
    result = generate_error_response(state["error_code"])
    return result

#routing function for safety checking, applied to all conditional edges
def route_error(state: State, next_node: str):
    if state["safe"]:
        return next_node
    return "generate_error_response"

#build graph
graph = StateGraph(State)

graph.add_node("generate_sql", call_generate_sql)
graph.add_node("run_sql", call_run_sql)
graph.add_node("generate_answer_response", call_generate_answer_response)
graph.add_node("generate_error_response", call_generate_error_response)

#conditional edges for error routing
graph.add_conditional_edges(
    START,
    lambda s: route_error(s, "generate_sql"),
    {
        "generate_sql": "generate_sql",
        "generate_error_response": "generate_error_response"
     }
)
graph.add_conditional_edges(
    "generate_sql",
    lambda s: route_error(s, "run_sql"),
    {
        "run_sql": "run_sql",
        "generate_error_response": "generate_error_response"
     }
)
graph.add_conditional_edges(
    "run_sql",
    lambda s: route_error(s, "generate_answer_response"),
    {
        "generate_answer_response": "generate_answer_response",
        "generate_error_response": "generate_error_response"
     }
)
graph.add_conditional_edges(
    "generate_answer_response",
    lambda s: route_error(s, END),
    {
        END: END,
        "generate_error_response": "generate_error_response"
     }
)

graph.add_edge("generate_error_response", END)

#run graph, called for every interaction
def run_graph(user_input: str):
    #initialise state
    state = {
        "user_message": user_input,
        "sql_query": None,
        "sql_data": None,
        "ai_response": None,
        "safe": True,
        "error_code": None
    }

    #check for empty or whitespace user input
    if not user_input or not user_input.strip():
        state["safe"] = False
        state["error_code"] = "USER_INPUT_MISSING"

    #compile and invoke graph with the intialised state
    chatbot = graph.compile()
    graph_result = chatbot.invoke(state)

    #return just the AI response
    return graph_result["ai_response"]
