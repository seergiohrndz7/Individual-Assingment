import java.util.Random;
import java.lang.management.ManagementFactory;
import java.lang.management.MemoryUsage;
import java.lang.management.MemoryMXBean;

public class Benchmark {

    public static double[][] randomMatrix(int n) {
        Random rand = new Random();
        double[][] M = new double[n][n];
        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++)
                M[i][j] = rand.nextDouble();
        return M;
    }

    public static long getMemoryUsedMB() {
        MemoryMXBean memoryBean = ManagementFactory.getMemoryMXBean();
        MemoryUsage heapUsage = memoryBean.getHeapMemoryUsage();
        return heapUsage.getUsed() / (1024 * 1024);
    }

    public static void main(String[] args) {
        if (args.length < 2) {
            System.out.println("Usage: java Benchmark <matrix_size> <num_runs>");
            return;
        }

        int n = Integer.parseInt(args[0]);
        int runs = Integer.parseInt(args[1]);

        System.out.println("=========== JAVA BENCHMARK ===========");
        System.out.println("Matrix size: " + n + "x" + n + " | Runs: " + runs);

        double[][] A = randomMatrix(n);
        double[][] B = randomMatrix(n);

        double total = 0;
        for (int r = 0; r < runs; r++) {
            long memBefore = getMemoryUsedMB();
            long start = System.nanoTime();
            double[][] C = MatrixMultiplier.multiply(A, B, n);
            long end = System.nanoTime();
            long memAfter = getMemoryUsedMB();

            double elapsed = (end - start) / 1e9;
            total += elapsed;
            System.out.printf("Run %d: %.6f s | Memory used: %d MB%n",
                    r + 1, elapsed, (memAfter - memBefore));
        }

        double avg = total / runs;
        System.out.println("---------------------------------------");
        System.out.printf("Average time: %.6f s%n", avg);
        System.out.println("=======================================");
    }
}
