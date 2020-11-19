package rs.in.paxy.HTTPBench;

public class testHTTPclient {

    public static void main(String[] args) throws Exception {
        HTTPclient test = new HTTPclient("localhost", 8000);
        while (true) {
            long t=System.nanoTime();
            String msg = test.get("/");
            System.out.println(System.nanoTime()-t);
        }
    }

}
