package rs.in.paxy.HTTPBench;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.Socket;
import java.net.UnknownHostException;

public class HTTPclient {
    Socket client;
    String webServer;
    int port;

    public HTTPclient(String webServer, int port)
            throws UnknownHostException, IOException {
        this.webServer = webServer;
        this.client = new Socket(webServer, port);
        this.port=port;
    }

    public String get(String url) throws IOException, InterruptedException {
        PrintWriter out = new PrintWriter(client.getOutputStream(), true);
        BufferedReader in = new BufferedReader(
                new InputStreamReader(client.getInputStream()));

        out.println("GET " + url + " HTTP/1.1" + "\r");
        out.println("Host: " + webServer + "\r");
        out.println("Connection: Keep-Alive" + "\r");
        out.println("Accept: image/gif, image/jpeg, */*" + "\r");
        out.println("Accept-Language: us-en" + "\r");

        out.println("\r");

        String msg = "";
        if (!in.ready())
            for (int i = 1; i < 50; i++) {
                if (in.ready())
                    break;
                    Thread.currentThread().sleep(100);
            }
        if(!in.ready()) {
            System.out.println("Brake, reconnecting");
            this.client = new Socket(webServer, port);
        }

        while (in.ready())
            msg += in.readLine() + "\n";
        return msg;
    }

}
