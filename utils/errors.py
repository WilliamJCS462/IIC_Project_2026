import duckdb
import traceback

error_codes = {
    ValueError: "VALUE_ERROR",
    duckdb.ParserException: "INVALID_SQL_SYNTAX",
    duckdb.BinderException: "INVALID_SQL_SCHEMA",
    duckdb.CatalogException: "INVALID_SQL_SCHEMA"
}

def get_error_code(error: Exception):
    if type(error) in error_codes:
        return error_codes.get(type(error))
    else:
        print (f"Unknown Error: \n{error}")
        traceback.print_exc()
        return "UNKNOWN_ERROR"