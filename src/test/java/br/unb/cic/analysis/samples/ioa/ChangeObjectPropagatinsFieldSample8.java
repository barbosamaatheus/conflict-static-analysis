package br.unb.cic.analysis.samples.ioa;

//NOT Conflict
public class ChangeObjectPropagatinsFieldSample8 {

    public static void main(String[] args) {
        Point c = new Point();
        Point d = new Point();
        c.z.y = 5; // LEFT
        int base = 0;
        c.z = d; // RIGHT
    }
}