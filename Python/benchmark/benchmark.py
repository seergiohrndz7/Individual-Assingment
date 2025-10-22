import os, sys, time, random, psutil, csv
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.matrix_mult import matrix_multiply

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, "..", "..", "data", "results.csv"))

def ensure_csv():
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    if not os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["language", "matrix_size", "run_index", "elapsed_sec", "memory_used_mb", "timestamp_iso"])

def log_csv(n, run_index, elapsed_sec, mem_used_mb):
    with open(RESULTS_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Python", n, run_index, f"{elapsed_sec:.6f}",
                         f"{mem_used_mb:.2f}", datetime.now().isoformat(timespec="seconds")])

def create_matrix(n):
    return [[random.random() for _ in range(n)] for _ in range(n)]

def get_memory_mb():
    return psutil.Process(os.getpid()).memory_info().rss / (1024**2)

def run_experiment(n, runs):
    ensure_csv()
    A = create_matrix(n)
    B = create_matrix(n)

    print("=========== PYTHON BENCHMARK ===========")
    print(f"Matrix size: {n}x{n} | Runs: {runs}")

    total = 0.0
    for r in range(1, runs + 1):
        mem_before = get_memory_mb()
        t0 = time.perf_counter()
        C = matrix_multiply(A, B, n)
        t1 = time.perf_counter()
        mem_after = get_memory_mb()

        elapsed = t1 - t0
        mem_used = max(0.0, mem_after - mem_before)
        total += elapsed

        print(f"Run {r}: {elapsed:.6f} s | Memory used: {mem_used:.2f} MB")
        log_csv(n, r, elapsed, mem_used)

        # prevent C from being optimized away by interpreter (noop read)
        if C and C[0] and C[0][0] == float("nan"):
            print("", end="")

    print("---------------------------------------")
    print(f"Average time: {total / runs:.6f} s")
    print("=======================================")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python benchmarks/benchmark.py <matrix_size> <num_runs>")
        sys.exit(1)
    n = int(sys.argv[1])
    runs = int(sys.argv[2])
    run_experiment(n, runs)
