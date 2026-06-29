"""Export OpenAPI schema to JSON file for frontend type generation.

Usage:
    cd backend && . .venv/bin/activate && python scripts/export_openapi.py

Output: ../frontend/src/types/openapi.json
"""
import json
import sys
from pathlib import Path

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.openapi.utils import get_openapi
from app.main import app

schema = get_openapi(
    title=app.title,
    version=app.version,
    description=app.description or "",
    routes=app.routes,
)

output = Path(__file__).resolve().parents[2] / "frontend" / "src" / "types" / "openapi.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(schema, indent=2, ensure_ascii=False))
print(f"OpenAPI schema exported to {output} ({len(schema.get('paths', {}))} paths)")
