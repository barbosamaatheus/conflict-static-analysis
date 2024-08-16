package br.unb.cic.analysis.oa;

import br.unb.cic.analysis.AbstractAnalysis;
import br.unb.cic.analysis.AbstractMergeConflictDefinition;
import br.unb.cic.analysis.model.Statement;
import soot.Local;
import soot.Value;
import soot.ValueBox;
import soot.jimple.ArrayRef;
import soot.jimple.InstanceFieldRef;
import soot.jimple.StaticFieldRef;

import java.util.List;

public class OverrideAssignmentWithPointerAnalysis extends OverrideAssignment implements AbstractAnalysis {

    public OverrideAssignmentWithPointerAnalysis(AbstractMergeConflictDefinition definition, int depthLimit, Boolean interprocedural, List<String> entrypoints) {
        super(definition, depthLimit, interprocedural, entrypoints);
    }

    public OverrideAssignmentWithPointerAnalysis(AbstractMergeConflictDefinition definition, int depthLimit, boolean interprocedural) {
        super(definition, depthLimit, interprocedural);
    }

    public OverrideAssignmentWithPointerAnalysis(AbstractMergeConflictDefinition definition) {
        super(definition);
    }

    @Override
    protected void gen(OverrideAssignmentAbstraction in, Statement stmt) {
        Value value = stmt.getUnit().getDefBoxes().get(0).getValue();
        if (value instanceof InstanceFieldRef) {
            getPointToFromBase(((InstanceFieldRef) value).getBase(), stmt);
        } else if (value instanceof ArrayRef) {
            getPointToFromBase(((ArrayRef) value).getBase(), stmt);
        } else if (value instanceof StaticFieldRef) {
            getPointToFromStaticField(((StaticFieldRef) value).getField(), stmt);
        }
        in.add(stmt);
    }

    @Override
    protected boolean isSameStateElement(Statement stmtInAbs, Statement stmtInFlow) {
        for (ValueBox defBoxInAbs : stmtInAbs.getUnit().getDefBoxes()) {
            for (ValueBox defBoxInFlow : stmtInFlow.getUnit().getDefBoxes()) {
                Value valueInAbs = defBoxInAbs.getValue();
                Value valueInFlow = defBoxInFlow.getValue();

                if (valueInAbs instanceof Local && valueInFlow instanceof Local) {
                    return isSameLocal(stmtInAbs, stmtInFlow, valueInAbs, valueInFlow);
                } else if (valueInAbs instanceof InstanceFieldRef && valueInFlow instanceof InstanceFieldRef) {
                    return isSameFieldRef(stmtInAbs, stmtInFlow, valueInAbs, valueInFlow);
                } else if (valueInAbs instanceof ArrayRef && valueInFlow instanceof ArrayRef) {
                    return isSameArrayRef(stmtInAbs, stmtInFlow, valueInAbs, valueInFlow);
                } else if (valueInAbs instanceof StaticFieldRef && valueInFlow instanceof StaticFieldRef) {
                    return isSameStaticFieldRef(valueInAbs, valueInFlow);
                } else if (valueInAbs instanceof ArrayRef && valueInFlow instanceof Local) {
                    if (!stmtInAbs.getSootMethod().equals(stmtInFlow.getSootMethod())) {
                        return false;
                    }
                    return valueInAbs.toString().contains(valueInFlow.toString());
                }

            }
        }
        return false;
    }
}
