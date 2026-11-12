import openai
import os
from dotenv import load_dotenv
from database.database import connection
from utils.errors import get_error_code

load_dotenv()

def generate_sql(prompt: str):
    try:
        #fetch database schema
        schema = connection.execute("DESCRIBE superstore").fetchall()

        system_prompt = """
            TASK

            You are a SQL assistant

            Your role is to generate some SQL to query a flat file database to help answer a user question

            Rules:
            - Return an ONLY an SQL query and nothing else
            - Do not include markdown, '''sql fences or any text that is not SQL
            - Only use the table superstore
            - Only use columns from the schema
            - The returned SQL query must be syntactically correct
            - Generate a query that answers the question as best as possible
            - Limit all responses to 10 rows maximum
        """

        user_prompt = f"""

            User Question:

            {prompt}

            Database Schema:

            {schema}

        """

        full_prompt = user_prompt + system_prompt

        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=full_prompt
        )

        sql_raw = response.output_text
        sql_trimmed = sql_raw.replace("'''sql", "")
        sql_trimmed = sql_trimmed.replace("'''", "")
        sql_trimmed = sql_trimmed.strip()

        return {"sql_query": sql_trimmed}

    except Exception as e:
        return {
            "safe": False,
            "error_code": get_error_code(e)
        }