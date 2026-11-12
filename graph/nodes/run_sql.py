from database.database import connection
from utils.errors import get_error_code

def run_sql(query: str):
    try:

        connection.execute(f"EXPLAIN {query}") #worth short circuiting the error to save processing the full incorrect query

        result = connection.execute(query).df()
        return {"sql_data": result}
    
    except Exception as e:
        return {
            "safe": False,
            "error_code": get_error_code(e)
            }