#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
  #include <windows.h>
  #include <psapi.h>
  #include <direct.h>   
  #define MKDIR(p) _mkdir(p)
  #define PATH_SEP '\\'
  static long get_memory_used_mb() {
      PROCESS_MEMORY_COUNTERS pmc;
      if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
          return (long)(pmc.WorkingSetSize / (1024 * 1024));
      }
      return 0;
  }
#else
  #include <sys/time.h>
  #include <sys/stat.h>
  #include <unistd.h>
  #define MKDIR(p) mkdir(p, 0755)
  #define PATH_SEP '/'
  static long get_memory_used_mb() {
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
  }
#endif

// ---------- Production Code -----------
double** allocate_matrix(int n) {
    double **M = (double**)malloc(n * sizeof(double*));
    for (int i = 0; i < n; ++i) M[i] = (double*)malloc(n * sizeof(double));
    return M;
}
void free_matrix(double **M, int n) {
    for (int i = 0; i < n; ++i) free(M[i]);
    free(M);
}
void fill_random(double **M, int n) {
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            M[i][j] = (double)rand() / RAND_MAX;
}
void matrix_multiply(double **A, double **B, double **C, int n) {
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            double s = 0.0;
            for (int k = 0; k < n; ++k) s += A[i][k] * B[k][j];
            C[i][j] = s;
        }
    }
}
// --------------------------------------

// Return seconds (double) wall-clock
static double now_seconds() {
#ifdef _WIN32
    LARGE_INTEGER freq, ctr;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&ctr);
    return (double)ctr.QuadPart / (double)freq.QuadPart;
#else
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec * 1e-6;
#endif
}

// Create parent directory of path (simple split on last / or \)
static void ensure_parent_dir(const char *path) {
    size_t len = strlen(path);
    if (len == 0) return;
    char *tmp = (char*)malloc(len + 1);
    strcpy(tmp, path);
    for (int i = (int)len - 1; i >= 0; --i) {
        if (tmp[i] == '/' || tmp[i] == '\\') {
            tmp[i] = '\0';
            MKDIR(tmp); // ignore errors if exists
            break;
        }
    }
    free(tmp);
}

// Choose CSV path: env var RESULTS_CSV or ../data/results.csv
static void resolve_csv_path(char *out, size_t outsz) {
    const char *env = getenv("RESULTS_CSV");
    if (env && env[0] != '\0') {
        snprintf(out, outsz, "%s", env);
        return;
    }
    // default relative to running from C/ (NOT from build/)
    snprintf(out, outsz, "..%cdata%cresults.csv", PATH_SEP, PATH_SEP);
}

// ensure file exists and has header
static void ensure_csv(const char *path) {
    ensure_parent_dir(path);
    FILE *f = fopen(path, "r");
    if (f) { fclose(f); return; }
    f = fopen(path, "w");
    if (!f) {
        perror("[ERROR] fopen header");
        fprintf(stderr, "Tried path: %s\n", path);
        return;
    }
    fprintf(f, "language,matrix_size,run_index,elapsed_sec,memory_used_mb,timestamp_iso\n");
    fclose(f);
}

static void append_csv(const char *path, int n, int run_index, double elapsed, long mem_used_mb) {
    FILE *f = fopen(path, "a");
    if (!f) {
        perror("[ERROR] fopen append");
        fprintf(stderr, "Tried path: %s\n", path);
        return;
    }
    time_t t = time(NULL);
    struct tm *tm = localtime(&t);
    char iso[32];
    strftime(iso, sizeof(iso), "%Y-%m-%dT%H:%M:%S", tm);
    fprintf(f, "C,%d,%d,%.6f,%ld,%s\n", n, run_index, elapsed, mem_used_mb, iso);
    fclose(f);
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        printf("Usage: %s <matrix_size> <num_runs>\n", argv[0]);
        return 1;
    }
    int n = atoi(argv[1]);
    int runs = atoi(argv[2]);
    srand((unsigned)time(NULL));

    char csv_path[1024];
    resolve_csv_path(csv_path, sizeof(csv_path));
    ensure_csv(csv_path);
    printf("[INFO] CSV path: %s\n", csv_path);

    // build matrices once (como en Java/Python)
    double **A = allocate_matrix(n);
    double **B = allocate_matrix(n);
    double **C = allocate_matrix(n);
    fill_random(A, n);
    fill_random(B, n);

    printf("=========== C BENCHMARK ===========\n");
    printf("Matrix size: %dx%d | Runs: %d\n", n, n, runs);
    printf("-----------------------------------\n");

    double total = 0.0;
    for (int r = 1; r <= runs; ++r) {
        long mem_before = get_memory_used_mb();
        double t0 = now_seconds();
        matrix_multiply(A, B, C, n);
        double t1 = now_seconds();
        long mem_after = get_memory_used_mb();

        double elapsed = t1 - t0;
        long mem_used = mem_after - mem_before;
        if (mem_used < 0) mem_used = 0;

        total += elapsed;
        append_csv(csv_path, n, r, elapsed, mem_used);
        printf("Run %d: %.6f s | Memory used: %ld MB\n", r, elapsed, mem_used);
    }

    printf("-----------------------------------\n");
    printf("Average time: %.6f s\n", total / runs);
    printf("===================================\n");

    free_matrix(A, n);
    free_matrix(B, n);
    free_matrix(C, n);
    return 0;
}
