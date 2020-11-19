package rs.in.paxy.HTTPSrv;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.Socket;

public class ServerThread implements Runnable {

    Socket sock;

    public ServerThread(Socket sock) {
        this.sock = sock;
    }

    @Override
    public void run() {

        try {

            BufferedReader in = new BufferedReader(
                    new InputStreamReader(sock.getInputStream()));
            PrintWriter out = new PrintWriter(sock.getOutputStream(), true);

            while(sock.isConnected()) {
                String msg="";
                msg=in.readLine()+"\n";

                int nr=(int)(Math.random()*1024);
                String txt="";
                for(int i=0;i<nr;i++){
                    txt+=i;
                }
                out.println(txt);

            }


            sock.close();
        } catch (IOException e) {
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
    }

}
