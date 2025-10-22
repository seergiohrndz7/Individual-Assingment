import java.nio.file.*;
import java.io.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class Benchmark {

    // ----- CSV Utilities -----
    private static Path resolveCsv() throws IOException {
        String env = System.getenv("RESULTS_CSV");
        Path p = (env != null && !env.isBlank())
                ? Paths.get(env)
                : Paths.get("..", "data", "results.csv");
        Files.createDirectories(p.toAbsolutePath().getParent());
        if (!Files.exists(p)) {
            try (BufferedWriter w = Files.newBufferedWriter(p)) {
                w.write("language,matrix_size,run_index,elapsed_sec,memory_used_mb,timestamp_iso");
                w.newLine();
            }
        }
        return p;
    }

    private static void appendCsv(Path csv, String line) throws IOException {
        try (BufferedWriter w = Files.newBufferedWriter(csv,
                StandardOpenOption.CREATE, StandardOpenOption.APPEND)) {
            w.write(line);
            w.newLine();
        }
    }

    private static long usedBytes() {
        Runtime rt = Runtime.getRuntime();
        return rt.totalMemory() - rt.freeMemory();
    }

    // ----- Generation and multiplication of matrix -----
    private static double[][] randomMatrix(int n) {
        java.util.Random rnd = new java.util.Random();
        double[][] M = new double[n][n];
        for (int i = 0; i < n; i++) {
            double[] Mi = M[i];
            for (int j = 0; j < n; j++) {
                Mi[j] = rnd.nextDouble();
            }
        }
        return M;
    }

    private static double[][] multiply(double[][] A, double[][] B) {
        int n = A.length;
        double[][] C = new double[n][n];
        for (int i = 0; i < n; i++) {
            double[] Ai = A[i];
            double[] Ci = C[i];
            for (int j = 0; j < n; j++) {
                double s = 0.0;
                for (int k = 0; k < n; k++) {
                    s += Ai[k] * B[k][j];
                }
                Ci[j] = s;
            }
        }
        return C;
    }

    // ----- Main Program -----
    public static void main(String[] args) {
        try {
            if (args.length < 2) {
                System.out.println("Usage: java Benchmark <matrix_size> <num_runs>");
                return;
            }
            int n = Integer.parseInt(args[0]);
            int runs = Integer.parseInt(args[1]);

            Path CSV = resolveCsv();
            double[][] A = randomMatrix(n);
            double[][] B = randomMatrix(n);

            System.out.println("=========== JAVA BENCHMARK ===========");
            System.out.printf("Matrix size: %dx%d | Runs: %d%n", n, n, runs);
            System.out.println("---------------------------------------");

            double total = 0.0;
            for (int r = 1; r <= runs; r++) {
                long memBefore = usedBytes();
                long t0 = System.nanoTime();
                double[][] C = multiply(A, B);
                long t1 = System.nanoTime();
                long memAfter = usedBytes();

                double elapsed = (t1 - t0) / 1e9;
                double memUsedMB = Math.max(0.0, (memAfter - memBefore) / (1024.0 * 1024.0));
                total += elapsed;

                String ts = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
                String line = String.join(",",
                        "Java",
                        Integer.toString(n),
                        Integer.toString(r),
                        Double.toString(elapsed),
                        Double.toString(memUsedMB),
                        ts
                );

                appendCsv(CSV, line);

                // Console Log
                System.out.printf("Run %d: %.6f s | Memory used: %.2f MB%n", r, elapsed, memUsedMB);

                // Avoid the compiler deleting variable
                if (C.length == 0) System.out.print("");
            }

            System.out.println("---------------------------------------");
            System.out.printf("Average time: %.6f s%n", total / runs);
            System.out.println("=======================================");

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
