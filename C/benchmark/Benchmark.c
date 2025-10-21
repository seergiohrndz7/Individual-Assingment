#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/time.h>

#ifdef _WIN32
  #include <windows.h>
  #include <psapi.h>
  #include <direct.h>
#else
  #include <sys/stat.h>
  #include <unistd.h>
#endif

#include "../src/matrix_mult.c"

// ---------------- Helper functions ---------------- //

static void fill_random(double **M, int n) {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++)
            M[i][j] = (double)rand() / RAND_MAX;
}

static double wall_time() {
    struct timeval t;
    gettimeofday(&t, NULL);
    return t.tv_sec + t.tv_usec * 1e-6;
}

static long get_memory_used_mb() {
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS pmc;
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        return (long)(pmc.WorkingSetSize / (1024 * 1024));
    }
    return 0;
#else
    FILE *f = fopen("/proc/self/statm", "r");
    if (!f) return 0;
    long total_pages, resident_pages;
    if (fscanf(f, "%ld %ld", &total_pages, &resident_pages) != 2) {
        fclose(f);
        return 0;
    }
    fclose(f);
    long page_size = sysconf(_SC_PAGESIZE);
    long rss_bytes = resident_pages * page_size;
    return rss_bytes / (1024 * 1024);
#endif
}

static void ensure_csv(const char *path) {
#ifdef _WIN32
    _mkdir("..\\data");
#else
    mkdir("../data", 0755);
#endif
    FILE *check = fopen(path, "r");
    if (check) { fclose(check); return; }

    FILE *f = fopen(path, "w");
    if (!f) return;
    fprintf(f, "language,matrix_size,run_index,elapsed_sec,memory_used_mb,timestamp_iso\n");
    fclose(f);
}

static void log_csv(const char *path, int n, int run_index, double elapsed, long mem_used) {
    FILE *f = fopen(path, "a");
    if (!f) return;

    time_t now = time(NULL);
    struct tm *tm = localtime(&now);
    char buf[32];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", tm);

    fprintf(f, "C,%d,%d,%.6f,%ld,%s\n", n, run_index, elapsed, mem_used, buf);
    fclose(f);
}

// ---------------- Main benchmark ---------------- //

int main(int argc, char *argv[]) {
    if (argc < 3) {
        printf("Usage: %s <matrix_size> <num_runs>\n", argv[0]);
        return 1;
    }

    int n = atoi(argv[1]);
    int runs = atoi(argv[2]);
    const char *RESULTS_PATH = "../data/results.csv";

    ensure_csv(RESULTS_PATH);

    srand((unsigned int)time(NULL));

    double **A = allocate_matrix(n);
    double **B = allocate_matrix(n);
    double **C = allocate_matrix(n);
    fill_random(A, n);
    fill_random(B, n);

    printf("=========== C BENCHMARK ===========\n");
    printf("Matrix size: %dx%d | Runs: %d\n", n, n, runs);

    double total = 0.0;
    for (int r = 0; r < runs; r++) {
        long mem_before = get_memory_used_mb();
        double start = wall_time();

        matrix_multiply(A, B, C, n);

        double end = wall_time();
        long mem_after = get_memory_used_mb();

        double elapsed = end - start;
        long mem_used = mem_after - mem_before;
        if (mem_used < 0) mem_used = 0;

        total += elapsed;
        printf("Run %d: %.6f s | Memory used: %ld MB\n", r + 1, elapsed, mem_used);
        log_csv(RESULTS_PATH, n, r + 1, elapsed, mem_used);
    }

    printf("-----------------------------------\n");
    printf("Average time: %.6f s\n", total / runs);
    printf("===================================\n");

    free_matrix(A, n);
    free_matrix(B, n);
    free_matrix(C, n);

    return 0;
}
