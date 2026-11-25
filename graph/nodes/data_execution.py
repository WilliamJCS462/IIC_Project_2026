import sqlglot
from sqlglot import exp
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


def generate_drill_down_data(query: str, trust_measures: dict):
    try:
        #strip and parse query
        parsed = sqlglot.parse_one(query)
        inner = parsed.find(exp.Subquery)
        if inner:
            query_stripped = inner.this.sql()
        else:
            query_stripped = query
        parsed = sqlglot.parse_one(query_stripped)

        #unwrap aliasses
        alias_record = []
        for alias in parsed.find_all(exp.Alias):
            alias_record.append(alias.alias) #record aliases for catching later
            alias.replace(alias.this)

        #extract grouping columns
        columns = []
        distinct_columns = []
        distinct_aggregate_columns = []
        group = parsed.find(exp.Group)
        if group is not None:
            for expr in group.expressions:
                columns.append(expr.sql())

        #extract aggregate columns
        select = parsed.find(exp.Select)
        for agg in select.find_all(exp.Sum, exp.Count, exp.Avg, exp.Min, exp.Max):
            inner = agg.this #inside the aggregation
            if isinstance(inner, exp.Star):
                continue
            if isinstance(inner, exp.Distinct):
                distinct_aggregate_columns.append(inner.expressions[0].sql())
            else:
                columns.append(inner.sql())

        #extract other columns
        select = parsed.find(exp.Select)
        if not select.args.get("distinct"):
            for expression in select.expressions:
                if isinstance(expression, exp.Column):
                    columns.append(expression.sql())

        #extract distinct non aggregate columns
        select = parsed.find(exp.Select)
        if select.args.get("distinct"):
            for expression in select.expressions:
                if isinstance(expression, exp.Column):
                    distinct_columns.append(expression.sql())

        #condtions for handling distincts
        drill_down_select = "SELECT *"
        if len(distinct_columns) > 0: #if dealing with distinct columns, all columns in drill down should be distinct
            combined_columns = ", ".join(list(set(columns + distinct_columns + distinct_aggregate_columns)))#deduplicate and merge
            drill_down_select = f"SELECT DISTINCT {combined_columns}"
        elif len(distinct_aggregate_columns) > 0 and len(columns) == 0: #if dealing with distinct aggregate columns, columns in drill down should only be distinct if no non-distinct columns are present
            combined_columns = ", ".join(list(set(distinct_aggregate_columns)))#deduplicate
            drill_down_select = f"SELECT {combined_columns}"
        elif len(columns) > 1:
            combined_columns= ", ".join(list(set(distinct_aggregate_columns + columns)))#deduplicate and merge
            drill_down_select = f"SELECT {combined_columns}"

        #static from clause
        drill_down_from = "FROM superstore"

        #extract conditions
        drill_down_where = ""
        where = parsed.find(exp.Where)
        if where is not None:
            drill_down_where = f"WHERE {where.this.sql()}"

        #ordering
        drill_down_order = ""
        order = parsed.find(exp.Order)
        if order is not None:
            valid = True #only copy the order if it only contains non-aggregate columns
            ordering = []
            for expr in order.expressions:
                inner = expr.this
                if not isinstance(inner, exp.Column) or (str(inner) in alias_record): #catch aggregations or aliases
                    valid = False
                    break
                direction = "ASC"
                if expr.args.get("desc"):
                    direction = "DESC"

                ordering.append(f"{inner.sql()} {direction}")
            if valid:
                drill_down_order = f"ORDER BY {', '.join(ordering)}"


        select = parsed.find(exp.Select)
        for agg in select.find_all(exp.Max, exp.Min): #we will hope we never have mutliple min/max aggregations, if we do we just order by the last one
            inner = agg.this
            if not isinstance(inner, exp.Star):
                if isinstance(agg, exp.Max):
                    drill_down_order = f"ORDER BY {inner.sql()} DESC" #overwrites previous
                else:
                    drill_down_order = f"ORDER BY {inner.sql()} ASC" #overwrites previous

        drill_down_sql = f"{drill_down_select} {drill_down_from} {drill_down_where} {drill_down_order} LIMIT 10;"

        #run and return data
        result = connection.execute(drill_down_sql).df()
        trust_measures["drill_down_data"] = result
        trust_measures["drill_down_sql"] = drill_down_sql
        return {"trust_measures": trust_measures}

    except Exception as e:
        print (f"Drill Down Error: \n{e}")
        return {
            "safe": False,
            "error_code": get_error_code(e)
            }