"""Records the prompt, the streamed events, and the exit code of a Codex execution."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

SPAWN_FAILURE_EXIT_CODE = 127


def write_record(transcript: TextIO, record: dict[str, Any]) -> None:
    """Persist a timestamped execution event."""
    timestamp = datetime.now(UTC).isoformat()
    serialized = json.dumps({**record, "timestamp": timestamp})
    transcript.write(serialized + "\n")
    transcript.flush()


def record_output(command: list[str], transcript: TextIO) -> int:
    """Retain the prompt and streamed events for a Codex execution."""
    execution_id = str(uuid.uuid4())
    prompt_record = {
        "type": "dag.prompt",
        "execution_id": execution_id,
        "text": command[-1],
    }
    is_resume = command[1:3] == ["exec", "resume"]
    if is_resume:
        prompt_record["thread_id"] = command[-2]

    write_record(transcript, prompt_record)
    with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as process:
        if process.stdout is not None:
            for line in process.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if isinstance(record, dict):
                    event_record = {**record, "execution_id": execution_id}
                    write_record(transcript, event_record)

        return process.wait()


def main() -> int:
    """Run Codex and persist its exit code for the controller."""
    exit_path = Path(sys.argv[1])
    transcript_path = Path(sys.argv[2])
    command = sys.argv[3:]
    exit_code = SPAWN_FAILURE_EXIT_CODE
    try:
        with transcript_path.open("a", encoding="utf-8") as transcript:
            exit_code = record_output(command, transcript)
            if exit_code < 0:
                exit_code = 128 - exit_code

    except OSError as error:
        sys.stderr.write(f"Codex execution failed: {error}\n")
    finally:
        exit_path.write_text(f"{exit_code}\n", encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
