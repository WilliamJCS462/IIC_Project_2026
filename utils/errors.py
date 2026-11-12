import duckdb

error_codes = {
    ValueError: "VALUE_ERROR",
    duckdb.ParserException: "INVALID_SQL_SYNTAX",
    duckdb.BinderException: "INVALID_SQL_SCHEMA",
    duckdb.CatalogException: "INVALID_SQL_SCHEMA"
}

def get_error_code(error: Exception):
    return error_codes.get(type(error), "UNKNOWN_ERROR")