import openai
import os
import yaml
import sqlglot
from sqlglot import exp
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel
from enum import Enum
from utils.errors import get_error_code
from database.database import connection

load_dotenv()

base_dir = Path(__file__).resolve().parent.parent.parent

#Using a structured output for robustness
class AnswerResponse(BaseModel):
    answer: str
    reasoning: str

class AuditStatus(str, Enum):
    PASS = "pass"
    SQL_FAIL = "sql_fail"
    RESPONSE_FAIL = "response_fail"

class AuditResponse(BaseModel):
    status: AuditStatus
    issues: list[str]

#generate an answer to the question given the data provided by the SQL query
def generate_answer_response(query: str, data: str, trust_measures: dict):
    try: 
        system_prompt = """
            TASK

            You are an SQL assistant

            Your role is to answer the users prompt using only the data returned from the database query.

            Rules:
            1. Only use the database data provided
            2. Do not invent/hallucenate infomation
            3. Do not make assumptions about missing or incomplete data
            4. Keep responses consice
            5. Do not include a table in your response
            6. If you cannot answer the question from the results, let the user know
            7. Provide a breif explaintion of how the answer was derived from the provided data

        """

        user_prompt = f"""

            User Question:

            {query}

            Database Results:

            {data}

        """

        full_prompt = user_prompt + system_prompt

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=full_prompt,
            text_format=AnswerResponse
        )

        result = response.output_parsed

        reasoning = f"\n\nAnswer Generation Reasoning:  \n{result.reasoning}"
        trust_measures["reasoning"] += reasoning #append to reasoning
        return {"ai_response": result.answer, "trust_measures": trust_measures}

    except Exception as e:
        return{
            "safe": False, 
            "error_code": get_error_code(e)
            }

def generate_error_response(error_code: str):
    try:
        system_prompt = """
            TASK

            You are an SQL assistant

            An error has occured in the pipeline. Apologise and explain breifly in simple terms to a user that an error has occured. Do not  assume the users input is the cause of the error.
        """

        user_prompt = f"""

        Error Code:

        {error_code}

        """

        full_prompt = user_prompt + system_prompt

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=full_prompt
        )

        return {"ai_response": response.output_text}

    #fallback if error handling fails
    except Exception as e:
        return {"ai_response": f"ERROR - Error Codes: {error_code}, ERROR_HANDLING_FAILURE, {get_error_code(e)}"}

def audit_response(query: str, sql: str, data: str, response: str, trust_measures: dict):
    try:
        auditing_status = "pass"
        auditing_issues = []
        audit_flag = 0
        improvements_path = base_dir / "config" / "improvements.yaml"
        if improvements_path.exists():
            with open(improvements_path, "r") as file:
                improvements = yaml.safe_load(file) or {}
                if "secondary_auditing" in improvements and improvements["secondary_auditing"]:
                    schema = connection.execute("DESCRIBE superstore").fetchall()
                    system_prompt = """
                        TASK

                        You are an SQL assistant

                        Your role is check a response against a set of criteria
                        You then need to return whether the response passes these criteria
                        If it does not, you must select which criteria category it invalidates
                        You must then return the specific issue(s) you have identified, where in the SQL or response this violation occurs and document the number and critiera verbatim that has been violated
                        An issue with the SQL takes priority over an issue with the response
                        You only need to check against the below critera
                        Do not create your own criteria or apply any other rules when checking

                        Reponse Criteria:
                        1. All claims in the response must be supported by the data. Consider the SQL to understand the data. A lack of data that has been filtered out by the SQL is still evidence and does support the response.
                        2. Numerical values used must exactly match the data (allow rounding, capitalization and formatting changes)
                        3. The response must not contradict the SQL results
                        4. The response must not contradict itself
                        6. The response must not contain speculations about data, it should only contain factual claims backed by the data from the database

                        SQL Criteria:
                        10. Column names should match those in the schema
                        11. An allias e.g. (COUNT(*) AS count for example) is not a column name and should be allowed. This applies if the allias (count for example) is used later in the query. Alliases used in this query are examples, other alliases of different formats are allowed
                        11. * refers to all columns and must be allowed
                        12. Do not check capitalisation differences between the SQL and schema
                        13. superstore is the table name. This must be allowed



                    """

                    #strip and parse query
                    parsed = sqlglot.parse_one(sql)
                    inner = parsed.find(exp.Subquery)
                    if inner:
                        query_stripped = inner.this.sql()
                    else:
                        query_stripped = sql

                    user_prompt = f"""

                        User Question:

                        {query}

                        Schema:

                        {schema}

                        SQL Query:

                        {query_stripped}

                        Database Results:

                        {data}

                        Generated Reponse:

                        {response}

                    """

                    full_prompt = user_prompt + system_prompt

                    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                    response = client.responses.parse(
                        model="gpt-4o-mini",
                        input=full_prompt,
                        text_format=AuditResponse
                    )

                    result = response.output_parsed
                    auditing_status = result.status.value
                    auditing_issues = result.issues
                    audit_flag = 1
                
        trust_measures["auditing_status"] = auditing_status
        trust_measures["auditing_issues"] = auditing_issues
        trust_measures["auditing_count"] += audit_flag
        return {"trust_measures": trust_measures}
    


    except Exception as e:
        return{
            "safe": False, 
            "error_code": get_error_code(e)
            }

def repair_response(query: str, data: str, response: str, trust_measures: dict):
    try:
        system_prompt = """
            TASK

            You are an SQL assistant

            Your role is to answer the users prompt using only the data returned from the database query
            The original reponse has been audited and one or more issues have been identified with it.
            Your task is to repair the response to address the issues

            Rules:
            1. Only use the database data provided
            2. Do not invent/hallucenate infomation
            3. Do not make assumptions about missing or incomplete data
            4. Keep the response consice
            5. Do not include a table in your response
            6. If you cannot answer the question from the results, let the user know
            7. Provided a breif explaintion of how the answer was derived from the provided data (reasoning)
            8. Only modify content necessary to fix the reported issues
            9. Do not mention the review or repair process or explain your changes
        """


        user_prompt = f"""

            User Question:

            {query}

            Database Results:

            {data}

            Original Reponse:

            {response}

            Issues:

            {trust_measures["auditing_issues"]}

        """

        full_prompt = user_prompt + system_prompt

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=full_prompt,
            text_format=AnswerResponse
        )

        result = response.output_parsed

        reasoning = f"\n\nAnswer Generation Reasoning:  \n{result.reasoning}"
        trust_measures["reasoning"] += reasoning #append to reasoning
        return {"ai_response": result.answer, "trust_measures": trust_measures}

    except Exception as e:
        return{
            "safe": False, 
            "error_code": get_error_code(e)
            }