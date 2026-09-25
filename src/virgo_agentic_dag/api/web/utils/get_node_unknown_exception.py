"""The 404 error for a dag or a node that is unknown on this host."""

from __future__ import annotations

from fastapi import HTTPException, status
from virgo_agentic_dag.labels.en import LABELS
from virgo_agentic_dag.utils.format_label import format_label


def get_node_unknown_exception(dag_name: str, node_id: str) -> HTTPException:
    """Return the 404 error for a dag or a node that is unknown on this host."""
    values = {"dag": dag_name, "node": node_id}

    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=format_label(LABELS["nodeUnknown"], values),
    )
