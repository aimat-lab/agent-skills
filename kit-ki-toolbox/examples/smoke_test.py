#!/usr/bin/env python3
"""List current KIT KI Toolbox models and optionally run one chat completion."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from toolbox_client import (KIToolboxClient, extract_connection_type, model_scope)

try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    Console = Table = None


def display_models(models: list[dict[str, Any]]) -> None:
    rows = []
    for model in models:
        model_id = model["id"]
        connection = extract_connection_type(model)
        rows.append((model_id, str(model.get("name") or model_id),
                     model_scope(model_id, connection), connection))
    if Console and Table:
        table = Table(title="KIT KI Toolbox Models")
        for label in ("Model ID", "Name", "Scope", "Connection"):
            table.add_column(label)
        for row in rows:
            table.add_row(*row)
        Console().print(table)
    else:
        print("Model ID\tName\tScope\tConnection")
        for row in rows:
            print("\t".join(row))
    print("local-by-name uses KIT ID conventions; confirm routing in KIT documentation.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Catalogue ID to test; defaults to an available local chat model")
    parser.add_argument("--allow-external", action="store_true",
                        help="Allow the explicitly selected model with external or unknown routing")
    parser.add_argument("--list-only", action="store_true",
                        help="List accessible models without running a completion")
    args = parser.parse_args()
    try:
        with KIToolboxClient(model=args.model, allow_external=args.allow_external) as client:
            display_models(client.list_models())
            if args.list_only:
                return
            answer = client.prompt("Explain chiral symmetry in one sentence.", max_tokens=256)
            print(f"\nModel: {client.model}\nResponse:\n{answer}")
    except Exception as exc:
        print(f"Toolbox check failed ({type(exc).__name__}). Check KIT_KI_API, connectivity, "
              "model availability and routing; external or unknown routing requires --allow-external.",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
