import openai
import os
from dotenv import load_dotenv
from utils.errors import get_error_code

load_dotenv()

#generate an answer to the question given the data provided by the SQL query
def generate_answer_response(query: str, data: str):
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
            input=full_prompt
        )

        return {"ai_response": response.output_text}

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