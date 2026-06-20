# evaluation/benchmark.py
import os
import sys
import json
import time
import datetime
from pathlib import Path
import numpy as np

# Ensure root of project is in path
sys.path.append(str(Path(__file__).parent.parent))

from pipeline.query_router import QueryRouter
from pipeline.language_registry import normalise_numerals

EVAL_DATASET_PATH = Path("evaluation/eval_dataset.json")
REPORT_JSON_PATH = Path("evaluation/benchmark_report.json")
REPORT_HTML_PATH = Path("evaluation/benchmark_report.html")

def calculate_word_overlap(str1, str2):
    # Basic word overlap for faithfulness
    w1 = set(re.findall(r"\b\w+\b", str1.lower()))
    w2 = set(re.findall(r"\b\w+\b", str2.lower()))
    if not w1 or not w2:
        return 0.0
    return len(w1.intersection(w2)) / len(w1.union(w2))

def main():
    import re
    print("Initializing Accuracy Benchmarking Pipeline...")
    
    if not EVAL_DATASET_PATH.exists():
        print(f"Error: Evaluation dataset {EVAL_DATASET_PATH} not found. Please run curation first.")
        sys.exit(1)
        
    with open(EVAL_DATASET_PATH, "r", encoding="utf-8") as f:
        eval_set = json.load(f)
        
    print(f"Loaded {len(eval_set)} evaluation test queries.")
    
    # Initialize QueryRouter
    try:
        router = QueryRouter()
        print("QueryRouter successfully loaded.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to instantiate QueryRouter: {e}")
        sys.exit(1)
        
    results = []
    latencies = []
    
    retrieval_at_1 = []
    retrieval_at_3 = []
    retrieval_at_5 = []
    sql_accuracies = []
    faithfulness_scores = []
    
    print("\nRunning benchmark suite...")
    for idx, item in enumerate(eval_set):
        question = item["question"]
        expected_type = item["expected_query_type"]
        gold_sources = item.get("gold_sources", [])
        gold_sql = item.get("gold_sql", "")
        dept = item.get("department", "General")
        
        print(f"[{idx+1}/{len(eval_set)}] Testing [{expected_type}] query for dept: {dept}")
        
        start_time = time.time()
        try:
            # Query the system gateway context
            res = router.route_and_query(question, dept, "TN")
            elapsed = (time.time() - start_time) * 1000  # ms
            latencies.append(elapsed)
            
            # Retrieval accuracy check
            source_names = [s.get("filename", "") for s in res.get("sources", [])]
            hit_1 = any(gs in source_names[:1] for gs in gold_sources) if gold_sources else True
            hit_3 = any(gs in source_names[:3] for gs in gold_sources) if gold_sources else True
            hit_5 = any(gs in source_names[:5] for gs in gold_sources) if gold_sources else True
            
            retrieval_at_1.append(hit_1)
            retrieval_at_3.append(hit_3)
            retrieval_at_5.append(hit_5)
            
            # SQL accuracy check
            sql_acc = 0.0
            if expected_type == "SQL" and gold_sql:
                # Basic normalization and comparison
                gen_sql = res.get("sql_generated", "")
                if gen_sql:
                    norm_gen = re.sub(r"\s+", " ", gen_sql.strip().lower())
                    norm_gold = re.sub(r"\s+", " ", gold_sql.strip().lower())
                    sql_acc = 1.0 if norm_gen == norm_gold or any(w in norm_gen for w in norm_gold.split() if len(w) > 4) else 0.5
                else:
                    sql_acc = 0.0
                sql_accuracies.append(sql_acc)
            
            # Faithfulness check
            faith = calculate_word_overlap(res.get("answer", ""), " ".join([c.get("text", "") for c in res.get("chunks_used", [])]))
            faithfulness_scores.append(faith)
            
            results.append({
                "question": question,
                "expected_type": expected_type,
                "latency_ms": elapsed,
                "query_type": res.get("query_type"),
                "answer": res.get("answer"),
                "sql_generated": res.get("sql_generated"),
                "retrieval_hit": hit_5,
                "sql_accuracy": sql_acc,
                "faithfulness": faith
            })
            
        except Exception as err:
            print(f"Error executing benchmark question: {err}")
            results.append({
                "question": question,
                "expected_type": expected_type,
                "error": str(err)
            })
            
    # Calculate stats
    p50 = np.percentile(latencies, 50) if latencies else 0.0
    p90 = np.percentile(latencies, 90) if latencies else 0.0
    p95 = np.percentile(latencies, 95) if latencies else 0.0
    
    ret_1_pct = np.mean(retrieval_at_1) * 100 if retrieval_at_1 else 100.0
    ret_3_pct = np.mean(retrieval_at_3) * 100 if retrieval_at_3 else 100.0
    ret_5_pct = np.mean(retrieval_at_5) * 100 if retrieval_at_5 else 100.0
    sql_acc_pct = np.mean(sql_accuracies) * 100 if sql_accuracies else 100.0
    faith_pct = np.mean(faithfulness_scores) * 100 if faithfulness_scores else 100.0
    
    # Generate JSON report
    report = {
        "run_date": datetime.datetime.now().isoformat(),
        "total_queries": len(eval_set),
        "avg_latency_ms": np.mean(latencies) if latencies else 0.0,
        "p50_ms": p50,
        "p90_ms": p90,
        "p95_ms": p95,
        "retrieval_at_1": ret_1_pct,
        "retrieval_at_3": ret_3_pct,
        "retrieval_at_5": ret_5_pct,
        "sql_accuracy": sql_acc_pct,
        "faithfulness": faith_pct,
        "results": results
    }
    
    with open(REPORT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        
    # Generate HTML report
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>BharatLLM Accuracy Benchmarking Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #f1f5f9; margin: 0; padding: 40px; }}
        .container {{ max-w: 1200px; margin: 0 auto; }}
        h1 {{ color: #10b981; border-bottom: 1px solid #1e293b; padding-bottom: 10px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin: 30px 0; }}
        .card {{ background: #1e293b; border: 1px solid #334155; padding: 20px; border-radius: 12px; text-align: center; }}
        .card h3 {{ margin: 0 0 10px 0; color: #94a3b8; font-size: 14px; text-transform: uppercase; }}
        .card .value {{ font-size: 32px; font-weight: bold; color: #34d399; }}
        table {{ w: 100%; border-collapse: collapse; margin-top: 30px; background: #1e293b; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ background: #0f172a; color: #34d399; }}
        tr:hover {{ background: #334155/50; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Accuracy Benchmarking Report (v3.1)</h1>
        <p>Executed at: {report["run_date"]}</p>
        
        <div class="metrics-grid">
            <div class="card">
                <h3>Total Queries</h3>
                <div class="value">{report["total_queries"]}</div>
            </div>
            <div class="card">
                <h3>Retrieval @ 5</h3>
                <div class="value">{ret_5_pct:.1f}%</div>
            </div>
            <div class="card">
                <h3>SQL Accuracy</h3>
                <div class="value">{sql_acc_pct:.1f}%</div>
            </div>
            <div class="card">
                <h3>Avg Latency</h3>
                <div class="value">{report["avg_latency_ms"]:.1f} ms</div>
            </div>
            <div class="card">
                <h3>P95 Latency</h3>
                <div class="value">{p95:.1f} ms</div>
            </div>
        </div>
        
        <h2>Query Log Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Question</th>
                    <th>Expected</th>
                    <th>Outcome</th>
                    <th>Latency</th>
                    <th>Faithfulness</th>
                </tr>
            </thead>
            <tbody>
    """
    for r in results:
        html_content += f"""
                <tr>
                    <td>{r["question"]}</td>
                    <td>{r.get("expected_type")}</td>
                    <td>{r.get("query_type", "ERROR")}</td>
                    <td>{r.get("latency_ms", 0.0):.1f} ms</td>
                    <td>{r.get("faithfulness", 0.0)*100:.1f}%</td>
                </tr>
        """
    
    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
    """
    
    with open(REPORT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"\nBenchmarking run complete. Reports saved to {REPORT_JSON_PATH} and {REPORT_HTML_PATH}")

if __name__ == "__main__":
    main()
