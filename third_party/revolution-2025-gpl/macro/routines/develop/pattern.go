package develop

import (
	. "github.com/nosyliam/revolution/pkg/common"
	. "github.com/nosyliam/revolution/pkg/control/actions"
)

const ExecuteDevelopmentPatternRoutineKind RoutineKind = "execute-development-pattern"

var ExecuteDevelopmentPatternRoutine = Actions{
	Info("Executing Pattern: %s", V[string]("PatternToExecute"))(Status),
	ExecutePattern(V[string]("PatternToExecute")),
}

func init() {
	ExecuteDevelopmentPatternRoutine.Register(ExecuteDevelopmentPatternRoutineKind)
}
