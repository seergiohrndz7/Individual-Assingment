def matrix_multiply(A, B, n):
    C = [[0.0 for _ in range(n)] for _ in range(n)]
    for i in range(n):
        Ai = A[i]
        Ci = C[i]
        for j in range(n):
            s = 0.0
            for k in range(n):
                s += Ai[k] * B[k][j]
            Ci[j] = s
    return C
