"""Windsurf adapter — generates .windsurf/rules/*.md.

Windsurf uses markdown rule files stored in ``.windsurf/rules/``.  Each file
may carry a YAML frontmatter block that controls how Cascade activates it.

Windsurf rule frontmatter format::

    ---
    trigger: always_on | model_decision | glob | manual
    description: <natural-language hint used when trigger=model_decision>
    globs: "**/*.py"  # used when trigger=glob
    ---
    <rule body>

Agent definitions are mapped to Windsurf rules as follows:

* Each agent becomes one ``.windsurf/rules/<name>.md`` file.
* ``trigger`` is always ``"model_decision"``: Cascade applies the rule when
  it decides the agent's description matches the current context.
* The agent's ``description`` is used as the natural-language hint.
* ``prompt_content`` becomes the rule body.

Notes:

* Windsurf does not support per-agent model selection in rule files; the
  model is chosen globally in Windsurf settings, so ``model_map`` is
  ignored.
* Built-in Cascade tools are always available; fine-grained ``capabilities``
  are not expressed in the output file.  Include capability requirements in
  the agent's system-prompt body if needed.
* To change the trigger mode (e.g. to ``always_on`` or ``glob``), edit the
  generated ``.windsurf/rules/<name>.md`` file directly after casting.
"""

from __future__ import annotations

from role_forge.adapters.base import BaseAdapter, _yaml_quote
from role_forge.models import AgentDef, TargetConfig

TRIGGER = "model_decision"


class WindsurfAdapter(BaseAdapter):
    name = "windsurf"
    base_dir = ".windsurf/rules"
    file_suffix = ".md"
    requires_model_map = False

    def _serialize_frontmatter(self, description: str) -> str:
        """Emit Windsurf rule frontmatter."""
        lines = ["---", f"trigger: {TRIGGER}"]
        if description:
            lines.append(f"description: {_yaml_quote(description)}")
        lines.append("---")
        return "\n".join(lines)

    def render_agent(
        self,
        agent: AgentDef,
        config: TargetConfig,
        delegates: list[str],
    ) -> str:
        del config, delegates
        fm = self._serialize_frontmatter(agent.description)
        return self._compose_document(fm, agent.prompt_content)
