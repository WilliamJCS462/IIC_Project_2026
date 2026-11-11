import duckdb
from database.database import connection

def run_sql(query: str):
    try:
        result = connection.execute(query).df()
        return {"sql_data": result}
    except Exception as e:
        return {"sql_data": f"SQL Error: {e}"}