package br.unb.cic.analysis.df;

import br.unb.cic.analysis.AbstractMergeConflictDefinition;
import br.unb.cic.analysis.SootWrapper;
import org.junit.Before;
import soot.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class ReachDefinitionAnalysisOneConflictTest {

    private ReachDefinitionAnalysis analysisExpectingOneConflict;

    @Before
    public void configure() {
        G.reset();
        Collector.instance().clear();

        AbstractMergeConflictDefinition definition = new AbstractMergeConflictDefinition() {
            @Override
            protected Map<String, List<Integer>> sourceDefinitions() {
                Map<String, List<Integer>> res = new HashMap<>();
                List<Integer> lines = new ArrayList<>();
                lines.add(6);
                res.put("br.unb.cic.analysis.samples.IntraproceduralDataFlow", lines);
                return res;
            }

            @Override
            protected Map<String, List<Integer>> sinkDefinitions() {
                Map<String, List<Integer>> res = new HashMap<>();
                List<Integer> lines = new ArrayList<>();
                lines.add(11);
                res.put("br.unb.cic.analysis.samples.IntraproceduralDataFlow", lines);
                return res;
            }
        };

        PackManager.v().getPack("jtp").add(
                new Transform("jtp.oneConflict", new BodyTransformer() {
                    @Override
                    protected void internalTransform(Body body, String phaseName, Map<String, String> options) {
                        analysisExpectingOneConflict = new ReachDefinitionAnalysis(body, definition);
                    }
                }));
        String cp = "target/test-classes";
        String targetClass = "br.unb.cic.analysis.samples.IntraproceduralDataFlow";

        SootWrapper.builder().withClassPath(cp).addClass(targetClass).build().execute();
    }

/*    @Test
    public void testDataFlowAnalysisExpectingOneConflict() {
        Assert.assertNotNull(analysisExpectingOneConflict);
        Assert.assertNotNull(analysisExpectingOneConflict.getConflicts());
        Assert.assertEquals(1, analysisExpectingOneConflict.getConflicts().size());
    }*/
}
