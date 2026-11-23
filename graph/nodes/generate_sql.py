import openai
import os
import sqlglot
import json
from sqlglot import exp
from pydantic import BaseModel
from dotenv import load_dotenv
from database.database import connection
from utils.errors import get_error_code

load_dotenv()

#Using a structured output for robustness
class SQLResponse(BaseModel):
    sql: str
    reasoning: str

def generate_sql(prompt: str, trust_measures: dict):
    try:
        #fetch database schema
        schema = connection.execute("DESCRIBE superstore").fetchall()

        system_prompt = """
            TASK

            You are a SQL assistant

            Your role is to generate some SQL to query a flat file database to help answer a user question and explain why you have chosen to generate the query the way you have

            Rules:
            - Return an ONLY an SQL query and nothing else
            - Do not include markdown, '''sql fences or any text that is not SQL
            - Only use the table superstore
            - Only use columns from the schema
            - The returned SQL query must be syntactically correct
            - Generate a query that answers the question as best as possible
            - Provide a breif explaination of how the query was generated
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
            input=full_prompt,
            text_format=SQLResponse
        )

        result = response.output_parsed

        sql_raw = result.sql
        sql_trimmed = sql_raw.replace("'''sql", "")
        sql_trimmed = sql_trimmed.replace("'''", "")
        sql_trimmed = sql_trimmed.strip()

        #strip the query of the trailing ; and then wrap in a limiter
        sql_limited = f"""
            SELECT * 
            FROM (
                {sql_trimmed.rstrip(';')}
            ) t
            LIMIT 10;
        """

        trust_measures["reasoning"] = f"SQL Generation Reasoning:  \n{result.reasoning}"
        trust_measures["sql_query"] = sql_trimmed #easier to pass the non limited query for reability
        return {"sql_query": sql_limited, "trust_measures": trust_measures}

    except Exception as e:
        return {
            "safe": False,
            "error_code": get_error_code(e)
        }

def calculate_complexity(query: str, trust_measures: dict):
    try:
        """
        SCORING SYSTEM
        1. Aggregation (30%)
            None - 0 (*, columns)
            Count - 10
            Distinct - 15
            SUM/AVG/MIN/MAX - 20
            GROUP BY - 25
            Multiple (COUNT + AVG w/ GROUP BY) - 30
        
        2. Filtering (30%)
            None - 0
            Single Equality - 15
            Multiple Equalities - 20
            Inequalities - 25
            Complex Conditions - 30

        3. Orders and Limits (20%)
            None - 0
            LIMIT - 5
            ORDER - 15
            LIMIT + ORDER - 20
        
        4. Combinatorics (20%)
            None - 0
            Sub-queries - 10
            Multiple Set Results - 20
        """

        agg_score = 0
        filt_score = 0
        ord_score = 0
        comb_score = 0

        #strip and parse query
        pre = """
            SELECT * 
            FROM (
        """

        suf = """
            ) t
            LIMIT 10;
        """
        query_stripped = query.removeprefix(pre).removesuffix(suf)
        parsed = sqlglot.parse_one(query_stripped)

        #Aggregate Score
        select = parsed.find(exp.Select) #only search select for aggregates
        aggregates = list(select.find_all(exp.AggFunc))
        if len(aggregates) > 1:
            agg_score = 30 #multiple aggregates
        elif parsed.find(exp.Group) is not None:
            agg_score = 25 #group by
        elif len(aggregates) == 1 and not isinstance(aggregates[0], exp.Count):
            agg_score = 20 #aggregate that isnt count
        elif select.args.get("distinct") is not None or select.find(exp.Distinct) is not None: #distinct can appear as "DISTINCT column1" or COUNT(DISTINCT column1), both must be caught
            agg_score = 15 #distinct
        elif len(aggregates) == 1:
            agg_score = 10 #if an aggregate still exists it must be count

        #Filtering Score
        where = parsed.find(exp.Where)
        if where is not None:
            equalities = list(where.find_all(exp.EQ))
            inequalities = list(where.find_all(exp.GT))
            inequalities += list(where.find_all(exp.GTE))
            inequalities += list(where.find_all(exp.LT))
            inequalities += list(where.find_all(exp.LTE))
            inequalities += list(where.find_all(exp.NEQ))
            if where.find(exp.And) is not None and where.find(exp.Or) is not None:
                filt_score = 30 #and and or both present is a complex filter
            if len(inequalities) > 0:
                filt_score = 25 #ineqalities
            if len(equalities) > 1:
                filt_score = 20 #multiple equalities
            if len(equalities) == 1:
                filt_score = 15

        #Order/Limit Score
        if parsed.find(exp.Limit) is not None and parsed.find(exp.Order) is not None:
            ord_score = 20
        elif parsed.find(exp.Order) is not None:
            ord_score = 15
        elif parsed.find(exp.Limit) is not None:
            ord_score = 5

        #Combinatorics Score
        if parsed.find(exp.Union) is not None:
            comb_score = 20
        elif parsed.find_all(exp.Subquery) is not None:
            comb_score = 10

        total_score = agg_score + filt_score + ord_score + comb_score
        trust_measures["complexity_score"] = total_score
        return trust_measures

    except Exception as e:
        print (e)
        return {
            "safe": False,
            "error_code": get_error_code(e)
        }
    