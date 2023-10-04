package br.unb.cic.analysis.samples.ioa;

// Conflict: [left, main():9] --> [right, main():11]
public class ChangeObjectPropagatinsFieldSample7 {

    public static void main(String[] args) {
        Point c = new Point();
        Point d = new Point();
        c.z = d; // LEFT
        Point z = c.z; // LEFT
        int base = 0;
        z.y = 5; // RIGHT
    }
}