import java.util.Random;

public class MatrixMultiplier {

    public static double[][] multiply(double[][] A, double[][] B) {
        int n = A.length;
        double[][] C = new double[n][n];
        for (int i = 0; i < n; i++) {
            double[] Ai = A[i];
            for (int j = 0; j < n; j++) {
                double sum = 0.0;
                for (int k = 0; k < n; k++) {
                    sum += Ai[k] * B[k][j];
                }
                C[i][j] = sum;
            }
        }
        return C;
    }

    public static double[][] randomMatrix(int n) {
        Random rnd = new Random();
        double[][] M = new double[n][n];
        for (int i = 0; i < n; i++) {
            double[] Mi = M[i];
            for (int j = 0; j < n; j++) {
                Mi[j] = rnd.nextDouble();
            }
        }
        return M;
    }
}
