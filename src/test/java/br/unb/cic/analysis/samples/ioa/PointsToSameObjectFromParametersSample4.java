package br.unb.cic.analysis.samples.ioa;

// Conflict: [left, m():7] --> [right, m():9]
public class PointsToSameObjectFromParametersSample4 {

    public void m(Point p1, Point p2) {
        p1.x = new Integer(10); // LEFT
        p2 = p1; //base
        p2.x = new Integer(20);  // RIGHT
    }
}


// p1 = new e p2 = new (p cara param vazio = new). na pratica podem ser iguais.
// todos poinsTo vazio, coloca na abs, add coringa (constante inventado). um por tipo.