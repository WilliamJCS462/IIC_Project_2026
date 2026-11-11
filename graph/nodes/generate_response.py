import openai
import os
from dotenv import load_dotenv

load_dotenv()

def generate_response(query: str, data: str):
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