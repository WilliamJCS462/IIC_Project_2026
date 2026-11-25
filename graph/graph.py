import yaml
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, List
from pathlib import Path
from dotenv import load_dotenv
from graph.nodes.query_generation import generate_sql, calculate_complexity, gather_expanded_context, repair_sql
from graph.nodes.data_execution import run_sql, generate_drill_down_data
from graph.nodes.response_generation import generate_answer_response, generate_error_response, audit_response, repair_response

base_dir = Path(__file__).resolve().parent.parent

#graph state
class State(TypedDict):
    user_message: str #user's inputted prompt
    sql_query: str | None #SQL query generated to answer prompt
    sql_data: str | None #Data returned from the SQL query
    ai_response: str | None #AI generated response to user prompt
    safe: bool #False when an error has occured
    error_code: str | None #Code to indicate which error has occured
    trust_measures: dict | None #Stores any trust measure data, dictionary so data can be added depending on trust measures selected

#function wrappers, these just call functions from the nodes
def dummy_function(state: State): #used by the start node
    return state

def call_gather_expanded_context(state: State):
    result = gather_expanded_context(state["trust_measures"])
    return result

def call_generate_sql(state: State):
    result = generate_sql(state["user_message"], state["trust_measures"])
    return result

def call_calculate_complexity(state: State):
    result = calculate_complexity(state["sql_query"], state["trust_measures"])
    return result

def call_run_sql(state: State):
    result = run_sql(state["sql_query"], state["trust_measures"])
    return result

def call_generate_drill_down_data(state: State):
    result = generate_drill_down_data(state["sql_query"], state["trust_measures"])
    return result

def call_generate_answer_response(state: State):
    result = generate_answer_response(state["user_message"], state["sql_data"], state["trust_measures"])
    return result

def call_audit_response(state: State):
    result = audit_response(state["user_message"], state["sql_query"], state["sql_data"], state["ai_response"], state["trust_measures"])
    return result

def call_repair_sql(state: State):
    print("Repairing SQL")
    result = repair_sql(state["user_message"], state["sql_query"], state["trust_measures"])
    return result

def call_repair_response(state: State):
    print("Repairing Response")
    result = repair_response(state["user_message"], state["sql_data"], state["ai_response"], state["trust_measures"])
    return result

def call_generate_error_response(state: State):
    result = generate_error_response(state["error_code"])
    return result

#routing function for safety checking, applied to all conditional edges
def route_error(state: State, next_node: str):
    if state["safe"]:
        return next_node
    return "generate_error_response"

#routing function for auditing, also handles error routing
def route_audit(state: State):
    if state["safe"]:
        if state["trust_measures"]["auditing_count"] >= 3: #can only audit 3 times before we force exit
            return "end_node"
        if state["trust_measures"]["auditing_status"] == "pass":
            return "end_node"
        elif state["trust_measures"]["auditing_status"] == "sql_fail":
            return "repair_sql"
        elif state["trust_measures"]["auditing_status"] == "response_fail":
            return "repair_response"
    return "generate_error_response"

#build graph
graph = StateGraph(State)

graph.add_node("start_node", dummy_function) #for logging
graph.add_node("gather_expanded_context", call_gather_expanded_context)
graph.add_node("generate_sql", call_generate_sql)
graph.add_node("calculate_complexity", call_calculate_complexity)
graph.add_node("run_sql", call_run_sql)
graph.add_node("generate_drill_down_data", call_generate_drill_down_data)
graph.add_node("generate_answer_response", call_generate_answer_response)
graph.add_node("audit_response", call_audit_response)
graph.add_node("repair_sql", call_repair_sql)
graph.add_node("repair_response", call_repair_response)
graph.add_node("generate_error_response", call_generate_error_response)
graph.add_node("end_node", dummy_function) #for logging

#conditional edges for error routing
graph.add_conditional_edges(
    START,
    lambda s: route_error(s, "start_node"),
    {
        "start_node": "start_node",
        "generate_error_response": "generate_error_response"
     }
)
graph.add_conditional_edges(
    "start_node",
    lambda s: route_error(s, "gather_expanded_context"),
    {
        "gather_expanded_context": "gather_expanded_context",
        "generate_error_response": "generate_error_response"
     }
)
graph.add_conditional_edges(
    "gather_expanded_context",
    lambda s: route_error(s, "generate_sql"),
    {
        "generate_sql": "generate_sql",
        "generate_error_response": "generate_error_response"
     }
)
graph.add_conditional_edges(
    "generate_sql",
    lambda s: route_error(s, "calculate_complexity"),
    {
        "calculate_complexity": "calculate_complexity",
        "generate_error_response": "generate_error_response"
     }
)
graph.add_conditional_edges(
    "calculate_complexity",
    lambda s: route_error(s, "run_sql"),
    {
        "run_sql": "run_sql",
        "generate_error_response": "generate_error_response",
     }
)
graph.add_conditional_edges(
    "run_sql",
    lambda s: route_error(s, "generate_drill_down_data"),
    {
        "generate_drill_down_data": "generate_drill_down_data",
        "generate_error_response": "generate_error_response"
     }
)
graph.add_conditional_edges(
    "generate_drill_down_data",
    lambda s: route_error(s, "generate_answer_response"),
    {
        "generate_answer_response": "generate_answer_response",
        "generate_error_response": "generate_error_response"
     }
)
graph.add_conditional_edges(
    "generate_answer_response",
    lambda s: route_error(s, "audit_response"),
    {
        "audit_response": "audit_response",
        "generate_error_response": "generate_error_response"
     }
)

graph.add_conditional_edges(
    "audit_response",
    lambda s: route_audit(s),
    {
        "end_node": "end_node",
        "repair_sql": "repair_sql",
        "repair_response": "repair_response",
        "generate_error_response": "generate_error_response"
     }
)

graph.add_conditional_edges(
    "repair_sql",
    lambda s: route_error(s, "calculate_complexity"),
    {
        "calculate_complexity": "calculate_complexity",
        "generate_error_response": "generate_error_response"
     }
)

graph.add_conditional_edges(
    "repair_response",
    lambda s: route_error(s, "audit_response"),
    {
        "audit_response": "audit_response",
        "generate_error_response": "generate_error_response"
     }
)

graph.add_edge("generate_error_response", END)
graph.add_edge("end_node", END)

#run graph, called for every interaction
def run_graph(user_input: str, status_callback=None):
    #initialise state
    default_trust_measures = {
        "complexity_score": 0,
        "reasoning": "",
        "sql_query": "",
        "sql_data": None,
        "drill_down_data": None,
        "drill_down_sql": "",
        "expanded_context": "",
        "auditing_status": "",
        "auditing_issues": [],
        "auditing_count": 0 #must not exceed 3
    }
    state = {
        "user_message": user_input,
        "sql_query": None,
        "sql_data": None,
        "ai_response": None,
        "safe": True,
        "error_code": None,
        "trust_measures": default_trust_measures
    }

    #check for empty or whitespace user input
    if not user_input or not user_input.strip():
        state["safe"] = False
        state["error_code"] = "USER_INPUT_MISSING"

    #stage logging mapping
    #we should log some nodes based on whether the user has enabled them (even if they always execute)
    expand_context_logging = "Generating SQL"
    calculate_complexity_logging = "Running SQL"
    drill_down_logging = "Generating Response"
    auditing_logging = "Generating Response"

    improvements_path = base_dir / "config" / "improvements.yaml"
    if improvements_path.exists():
        with open(improvements_path, "r") as file:
            improvements = yaml.safe_load(file) or {}
            if "expanded_context" in improvements and improvements["expanded_context"]:
                expand_context_logging = "Generating Expanded Context"
            if "complexity_scoring" in improvements and improvements["complexity_scoring"]:
                calculate_complexity_logging = "Calculating Complexity"
            if "drill_down" in improvements and improvements["drill_down"]:
                drill_down_logging = "Generating Supporting Data"
            if "secondary_auditing" in improvements and improvements["secondary_auditing"]:
                auditing_logging = "Auditing Response"

    next_node_names = {
        "start_node": expand_context_logging,
        "gather_expanded_context": "Generating SQL",
        "generate_sql": calculate_complexity_logging,
        "calculate_complexity": "Running SQL",
        "run_sql": drill_down_logging,
        "generate_drill_down_data": "Generating Response",
        "generate_answer_response": auditing_logging,
        "audit_response": auditing_logging,
        "repair_sql": "Auditing Response",
        "repair_response": "Auditing Reponse",
        "end_node": None,
        "generate_error_response": None
    }

    #compile and invoke graph with the intialised state
    chatbot = graph.compile()
    if status_callback is not None:
        for event in chatbot.stream(state):
            current_node = list(event.keys())[0]
            status_callback(next_node_names[current_node])
            graph_result = event[current_node]
    else:
        graph_result = chatbot.invoke(state)

    #return just the AI response
    return (graph_result["ai_response"], graph_result["trust_measures"])
