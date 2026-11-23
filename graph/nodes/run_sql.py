from database.database import connection
from utils.errors import get_error_code

def run_sql(query: str, trust_measures: dict):
    try:

        connection.execute(f"EXPLAIN {query}") #worth short circuiting the error to save processing the full incorrect query

        result = connection.execute(query).df()
        trust_measures["sql_data"] = result
        return {"sql_data": result, "trust_measures": trust_measures}
    
    except Exception as e:
        return {
            "safe": False,
            "error_code": get_error_code(e)
            }