package rs.in.paxy.HTTPBench;

import java.io.IOException;
import java.net.URI;
import java.net.UnknownHostException;
import java.net.http.HttpClient;
import java.net.http.HttpClient.Version;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpResponse.BodyHandlers;


public class jobQuery implements Runnable {

    private final String webServer = "192.168.100.222";
    //private final String webServer = "localhost";
    private final String webServer1 = "192.168.100.247";
    private final String webServer2 = "192.168.100.248";

    private boolean random = false;
    private boolean log = false;

    private main main;
    HttpClient client;
    HttpRequest request1;
    HttpRequest request2;
    HttpRequest request0;

    public jobQuery(main main) {
        this.main = main;
    }

    public void run() {
        HTTPclient client = null;
        try {
            client=new HTTPclient(srv(), 8000);
        } catch (UnknownHostException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        } catch (IOException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }

        while (true) {
            long start = System.currentTimeMillis();
            long nano=System.nanoTime();
            try {
                client.get("/test.php?rnd="+rnd(3)+"&random="+rnd(65535));

                long time = System.currentTimeMillis() - start;
                if(log) System.out.println(System.nanoTime()-nano);
                if(main!=null)
                    main.report(time);

                // mysql.closeMysql();

            } catch (Exception e1) {
                // TODO Auto-generated catch block
                e1.printStackTrace();
            }

        }
    }


    private int rand(int i) {
        // TODO Auto-generated method stub
        return (int)(Math.random()*i);
    }

    private String srv() {
        int r = (int) (Math.random() * 100);
        if (r % 2 == 0)
            return webServer1;
        else
            return webServer2;
    }

    private int rnd(int i) {
        return (int)(Math.random()*i);

    }

    public static void main(String[] args) {
        jobQuery jobQuery = new jobQuery(null);
        jobQuery.run();
    }

}
