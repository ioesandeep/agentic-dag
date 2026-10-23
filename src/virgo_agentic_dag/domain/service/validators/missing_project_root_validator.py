from virgo_agentic_dag.domain.graph.graph import Graph
from virgo_agentic_dag.domain.service.validators.graph_validator import GraphValidator
from virgo_agentic_dag.domain.validation.validation_error import ValidationError
from virgo_agentic_dag.labels.en import LABELS


class MissingProjectRootValidator(GraphValidator):
    """Requires a repository directory for the DAG."""

    def validate(self, graph: Graph) -> list[ValidationError]:
        """Return a blocking error when the DAG has no repository directory."""
        if graph.project_root is not None:
            return []

        return [
            ValidationError(
                code="missing-project-root",
                message=LABELS["missingProjectRoot"],
            )
        ]
