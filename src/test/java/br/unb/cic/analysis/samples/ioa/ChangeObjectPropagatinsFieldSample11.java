package br.unb.cic.analysis.samples.ioa;

// Conflict: [left, main():9] --> [right, main():11]
public class ChangeObjectPropagatinsFieldSample11 {

    public static void main(String[] args) {
        Point c = new Point();
        Point d = new Point();

        c.z.x = 6; // LEFT
        int base = 0;
        c.z.y = 5; // RIGHT
    }
}