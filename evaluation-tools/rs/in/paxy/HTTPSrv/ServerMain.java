package rs.in.paxy.HTTPSrv;

import java.net.ServerSocket;
import java.net.Socket;

public class ServerMain {

    public ServerMain() throws Exception{

        ServerSocket ss=new ServerSocket(8000);
        while(true) {
            Socket sock=ss.accept();
            ServerThread w=new ServerThread(sock);
            new Thread(w).start();
        }


    }

    public static void main(String[] args) throws Exception {
        new ServerMain();

    }

}
