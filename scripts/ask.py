"""Phase 2-4: CLI test — python scripts/ask.py INC-test "RDS CPU at 98%" """
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph.builder import run_incident_query  # noqa: E402

if __name__ == "__main__":
    incident_id, question = sys.argv[1], " ".join(sys.argv[2:])
    result = run_incident_query(incident_id, question)
    print(result["generation"])
    print("\nroute:", " -> ".join(result["route_trace"]))
    print("web_used:", result.get("web_used", False))
