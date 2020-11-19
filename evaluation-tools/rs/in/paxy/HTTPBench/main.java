package rs.in.paxy.HTTPBench;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.PrintWriter;
import java.util.Arrays;
import java.util.Vector;

public class main {

    Vector<Long> stats=new Vector<>();

    public main() throws InterruptedException, FileNotFoundException {

        int concurrent = 1;
        int max = 100;
        int inc=5; // inkrement svake 2 sekunde

        PrintWriter out=new PrintWriter(new File("out.txt"));

//        Thread thread = new Thread(new jobQuery(this));
//        thread.start();
        int cnt=0;
        while (concurrent < max) {
//            if(cnt%inc==0)
//            {
                Thread thread = new Thread(new jobQuery(this));
                thread.start();
                concurrent++;
//                cnt=0;
//            }
            Thread.currentThread().sleep(inc*1000);
            cnt++;
            System.out.println("Concurrent: " + (concurrent-1)+", Avg: "+findAverageUsingStream(stats.toArray(new Long[stats.size()]))+"ms, TpS: "+(stats.size()*1.0/inc));
            out.println("Concurrent: " + (concurrent-1)+", Avg: "+findAverageUsingStream(stats.toArray(new Long[stats.size()]))+"ms, TpS: "+(stats.size()*1.0/inc));
            out.flush();
            stats.clear();


        }
        out.close();
        System.out.println("Done");
        System.exit(0);

    }

    public static void main(String[] args) throws Exception {
        new main();

    }

    public void report(long time) {
       stats.add(time);

    }

    public static double findAverageUsingStream(Long[] objects) {
        long[] longArray = toPrimitives(objects);
        return Arrays.stream(longArray).average().orElse(Double.NaN);
    }
    public static long[] toPrimitives(Long[] objects) {

        long[] primitives = new long[objects.length];
        for (int i = 0; i < objects.length; i++)
             primitives[i] = objects[i];

        return primitives;
    }
}
