from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from importlens.config import AnalysisConfig
from importlens.report import (
    analyze_report_target,
    render_cycles_json,
    render_cycles_text,
    render_graph_json,
    render_graph_text,
    render_profile_json,
    render_profile_text,
    render_report_json,
    render_report_text,
)
from importlens.runtime import ProfileError, profile_target
from importlens.static import analyze_static_target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="importlens")
    subparsers = parser.add_subparsers(dest="command", required=True)

    profile_parser = subparsers.add_parser("profile", help="Profile import-time behavior.")
    profile_parser.add_argument("target")
    profile_parser.add_argument("--format", choices=("text", "json"), default="text")
    profile_parser.add_argument("--include", action="append", default=[])
    profile_parser.add_argument("--exclude", action="append", default=[])
    profile_parser.add_argument("--internal-only", action="store_true")

    graph_parser = subparsers.add_parser("graph", help="Analyze static import relationships.")
    graph_parser.add_argument("target")
    graph_parser.add_argument("--format", choices=("text", "json"), default="text")
    graph_parser.add_argument("--include", action="append", default=[])
    graph_parser.add_argument("--exclude", action="append", default=[])
    graph_parser.add_argument("--internal-only", action="store_true")

    cycles_parser = subparsers.add_parser("cycles", help="Detect static import cycles.")
    cycles_parser.add_argument("target")
    cycles_parser.add_argument("--format", choices=("text", "json"), default="text")
    cycles_parser.add_argument("--include", action="append", default=[])
    cycles_parser.add_argument("--exclude", action="append", default=[])
    cycles_parser.add_argument("--internal-only", action="store_true")

    report_parser = subparsers.add_parser("report", help="Combine runtime and static findings.")
    report_parser.add_argument("target")
    report_parser.add_argument("--format", choices=("text", "json"), default="text")
    report_parser.add_argument("--include", action="append", default=[])
    report_parser.add_argument("--exclude", action="append", default=[])
    report_parser.add_argument("--internal-only", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = AnalysisConfig(
        include=tuple(args.include),
        exclude=tuple(args.exclude),
        internal_only=bool(args.internal_only),
    )
    try:
        if args.command == "profile":
            result = profile_target(
                raw_target=args.target,
                config=config,
                working_directory=Path.cwd(),
            )
            if args.format == "json":
                print(render_profile_json(result))
            else:
                print(render_profile_text(result))
        elif args.command == "graph":
            graph_result = analyze_static_target(
                raw_target=args.target,
                config=config,
                working_directory=Path.cwd(),
            )
            if args.format == "json":
                print(render_graph_json(graph_result))
            else:
                print(render_graph_text(graph_result))
        elif args.command == "cycles":
            cycles_result = analyze_static_target(
                raw_target=args.target,
                config=config,
                working_directory=Path.cwd(),
            )
            if args.format == "json":
                print(render_cycles_json(cycles_result))
            else:
                print(render_cycles_text(cycles_result))
        elif args.command == "report":
            report_result = analyze_report_target(
                raw_target=args.target,
                config=config,
                working_directory=Path.cwd(),
            )
            if args.format == "json":
                print(render_report_json(report_result))
            else:
                print(render_report_text(report_result))
        else:
            parser.error("Unsupported command.")
    except ProfileError as exc:
        parser.exit(status=2, message=f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
