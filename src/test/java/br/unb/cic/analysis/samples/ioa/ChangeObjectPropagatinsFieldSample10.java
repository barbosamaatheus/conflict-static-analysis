package br.unb.cic.analysis.samples.ioa;

// Conflict: [left, main():9] --> [right, main():11]
public class ChangeObjectPropagatinsFieldSample10 {
    Point c = new Point();
    Point d = new Point();

    public void main(String[] args) {
        ChangeObjectPropagatinsFieldSample10 test = new ChangeObjectPropagatinsFieldSample10();
        test.c.z = d; // LEFT
        int base = 0;
        test.right(); // RIGHT
    }

    public void right() {
        this.c.z.y = 5;
    }
}