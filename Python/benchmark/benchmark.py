import random
import time
import psutil
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.matrix_mult import matrix_multiply

def create_matrix(n):
    return [[random.random() for _ in range(n)] for _ in range(n)]

def get_memory_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024**2)

def run_experiment(n, runs):
    A = create_matrix(n)
    B = create_matrix(n)
    C = [[0] * n for _ in range(n)]

    print("=========== PYTHON BENCHMARK ===========")
    print(f"Matrix size: {n}x{n} | Runs: {runs}")

    total_time = 0
    for r in range(runs):
        mem_before = get_memory_mb()
        start = time.time()
        matrix_multiply(A, B, C, n)
        end = time.time()
        mem_after = get_memory_mb()

        elapsed = end - start
        total_time += elapsed
        print(f"Run {r+1}: {elapsed:.4f}s | Memory used: {mem_after - mem_before:.2f}MB")

    print("---------------------------------------")
    print(f"Average time: {total_time/runs:.4f}s")
    print("=======================================")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python benchmark.py <matrix_size> <num_runs>")
        sys.exit(1)
    n = int(sys.argv[1])
    runs = int(sys.argv[2])
    run_experiment(n, runs)
