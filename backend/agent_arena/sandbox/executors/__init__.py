from .agent_vs_agent import AgentVsAgentExecutor
from .build_and_break import BuildAndBreakExecutor
from .direct_duel import DirectDuelExecutor
from .same_target_race import SameTargetRaceExecutor
from .scripted import ScriptedExecutor

_REGISTRY = {
    "build_and_break": BuildAndBreakExecutor,
    "same_target_race": SameTargetRaceExecutor,
    "direct_duel": DirectDuelExecutor,
    "agent_vs_agent": AgentVsAgentExecutor,
    "script_vs_defense": ScriptedExecutor,
    "high_complexity": ScriptedExecutor,
}


def get_executor(engine: str):
    cls = _REGISTRY.get(engine, ScriptedExecutor)
    return cls()
