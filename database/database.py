import duckdb

connection = duckdb.connect()

def database_init():
    
    connection.execute("""
    CREATE OR REPLACE VIEW superstore AS
    SELECT * 
    FROM read_csv_auto('data/SampleSuperstore.csv') 
    """)

    return connection