#include <stdlib.h>

double** allocate_matrix(int n) {
    double** M = (double**) malloc(n * sizeof(double*));
    for (int i = 0; i < n; i++) {
        M[i] = (double*) malloc(n * sizeof(double));
    }
    return M;
}

void free_matrix(double** M, int n) {
    for (int i = 0; i < n; i++) {
        free(M[i]);
    }
    free(M);
}

void matrix_multiply(double** A, double** B, double** C, int n) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            double sum = 0.0;
            for (int k = 0; k < n; k++) {
                sum += A[i][k] * B[k][j];
            }
            C[i][j] = sum;
        }
    }
}
