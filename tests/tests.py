import pandas as pd
import yaml
from graph.graph import run_graph
from database.database import database_init
from database.database import connection
from graph.nodes.run_sql import run_sql
from pathlib import Path
import graph.graph as graph_module

base_dir = Path(__file__).resolve().parent.parent

#tests the program against 30 examples
def run_accuracy_tests(progress_callback=None): #here we pass a streamlit progress bar obejct forward and update it from here
    try:
        base_dir = Path(__file__).resolve().parent.parent #need this inside because of moduling importing
        database_init() #need to start the database as we cant assume the app is running for tests
        test_accuracies = []
        tests = pd.read_csv(base_dir / "tests" / "test_prompts.csv")

        #since we need to capture data that isnt returned by run_graph while still running the full we need to patch functions inside graph.py
        captured = {} #using a dict for scoping
        original_run_sql = graph_module.run_sql

        #patch the interior function so we can extract sql_data
        def patched_run_sql(query, trust_measures):
            result = original_run_sql(query, trust_measures)
            if "sql_data" in result:
                #so result has same format as fetchall() result
                sql_data = result["sql_data"].itertuples(index=False, name=None)
                captured["sql_data"] = list(sql_data)
            return result
        graph_module.run_sql = patched_run_sql

        #test per prompt
        total = len(tests)
        for i, (_, row) in enumerate(tests.iterrows(), start=1):
            try:
                prompt = row["prompt"]
                query = row["query"]

                golden_data = connection.execute(query).fetchall() #using fetchall to remove column names

                #run the graph with our new patched prompt
                run_graph(prompt)
                actual_data = captured["sql_data"]

                #flatten our data
                golden_flat = [value for row in golden_data for value in row]
                actual_flat = [value for row in actual_data for value in row]

                #compare the flattened data
                hits = 0
                for value in golden_flat:
                    if value in actual_flat:
                        hits += 1
                        actual_flat.remove(value) #expect duplicate values
                test_accuracies.append(hits/len(golden_flat))

            #Error means a failed test, 0 accuracy
            except Exception as e:
                test_accuracies.append(0)

            #increment progress bar via callback
            if progress_callback:
                progress_callback(i,total)

        #unpatch the function after we have finished testing
        graph_module.run_sql = original_run_sql

        average_accuracy = sum(test_accuracies) / len(test_accuracies)

        metrics_path = base_dir / "tests" / "metrics.yaml"

        #load the yaml which might not exist yet
        if metrics_path.exists():
            with open(metrics_path, "r") as file:
                metrics = yaml.safe_load(file) or {}
        else:
            metrics = {}

        #set new accuracy
        metrics["accuracy"] = average_accuracy

        with open(metrics_path, "w") as file:
            yaml.safe_dump(metrics, file)

    #assume being done by a developer, return error in the terminal without crashing the code
    except Exception as e:
        print(f"Testing Failed with Error: {e}")

