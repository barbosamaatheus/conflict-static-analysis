package br.unb.cic.analysis.df;

import br.unb.cic.analysis.AbstractMergeConflictDefinition;
import org.junit.Before;
import soot.*;
import soot.options.Options;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class SourceSinkVariableAttributionWithAutoIncrementTaintedConfluentTest {

    private ConfluentTaintedAnalysis analysis;

    @Before
    public void configure() {
        G.reset();
        Collector.instance().clear();

        AbstractMergeConflictDefinition definition = new AbstractMergeConflictDefinition() {
            @Override
            protected Map<String, List<Integer>> sourceDefinitions() {
                Map<String, List<Integer>> res = new HashMap<>();
                List<Integer> lines = new ArrayList<>();
                lines.add(9);
                res.put("br.unb.cic.analysis.samples.SourceSinkVariableAttributionWithAutoIncrement", lines);
                return res;
            }

            @Override
            protected Map<String, List<Integer>> sinkDefinitions() {
                Map<String, List<Integer>> res = new HashMap<>();
                List<Integer> lines = new ArrayList<>();
                lines.add(11);
                res.put("br.unb.cic.analysis.samples.SourceSinkVariableAttributionWithAutoIncrement", lines);
                return res;
            }
        };

        PackManager.v().getPack("jtp").add(
            new Transform("jtp.confluence", new BodyTransformer() {
            @Override
            protected void internalTransform(Body body, String phaseName, Map<String, String> options) {
                    analysis = new ConfluentTaintedAnalysis(body, definition);
                    }
                }));
        String cp = "target/test-classes";
        String targetClass = "br.unb.cic.analysis.samples.SourceSinkVariableAttributionWithAutoIncrement";

        Options.v().setPhaseOption("jb", "optimize:false");

        Main.main(new String[] {"-w", "-allow-phantom-refs", "-f", "J", "-keep-line-number", "-cp", cp, targetClass});
    }

/*
    @Test
    public void testDataFlowAnalysisExpectingOneConflict() {
        Assert.assertEquals(1, analysis.getConflicts().size());
    }
*/
}
