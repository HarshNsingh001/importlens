from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from importlens.config import AnalysisConfig
from importlens.models import ParseAnomaly, TargetKind, TargetSpec, TimingRecord

IMPORT_TIME_RE = re.compile(
    r"^import time:\s*(?P<self>\d+)\s*\|\s*(?P<cumulative>\d+)\s*\|\s*(?P<module>.+)$"
)
IMPORT_TIME_HEADER = "import time: self [us] | cumulative | imported package"


class ProfileError(ValueError):
    """Raised when the runtime profile request cannot be fulfilled."""


@dataclass(frozen=True, slots=True)
class ProfileResult:
    target: TargetSpec
    timing_records: tuple[TimingRecord, ...]
    limitations: tuple[str, ...]
    parse_anomalies: tuple[ParseAnomaly, ...] = ()


def is_url_target(value: str) -> bool:
    return "://" in value


@contextmanager
def prepend_sys_path(path: Path) -> Iterator[None]:
    inserted = str(path)
    sys.path.insert(0, inserted)
    try:
        yield
    finally:
        try:
            sys.path.remove(inserted)
        except ValueError:
            pass


def resolve_target(raw_target: str, working_directory: Path) -> TargetSpec:
    if is_url_target(raw_target):
        raise ProfileError("Unsupported target: URLs are not accepted.")

    candidate_path = (working_directory / raw_target).resolve()
    if candidate_path.exists():
        if candidate_path.is_file():
            if candidate_path.suffix != ".py":
                raise ProfileError("Unsupported target: expected a Python script ending in .py.")
            return TargetSpec(
                raw_target=raw_target,
                target_kind=TargetKind.SCRIPT,
                resolved_path=candidate_path,
                package_root=candidate_path.parent,
                internal_prefixes=discover_internal_prefixes(candidate_path.parent),
            )
        if candidate_path.is_dir():
            if not any(candidate_path.rglob("*.py")):
                raise ProfileError(
                    "Unsupported target: package directory contains no Python files."
                )
            return TargetSpec(
                raw_target=raw_target,
                target_kind=TargetKind.PACKAGE,
                resolved_path=candidate_path,
                package_root=candidate_path,
                internal_prefixes=(candidate_path.name,),
            )
        raise ProfileError("Unsupported target: target path is neither a file nor a directory.")

    if raw_target.endswith(".py") or "/" in raw_target or "\\" in raw_target:
        raise ProfileError(f"Unsupported target: path does not exist: {raw_target}")

    if "." not in raw_target:
        raise ProfileError(
            "Unsupported target: module targets must be fully qualified, for example pkg.module."
        )

    with prepend_sys_path(working_directory):
        spec = importlib.util.find_spec(raw_target)
    if spec is None:
        raise ProfileError(
            f"Unsupported target: module target could not be resolved locally: {raw_target}"
        )

    return TargetSpec(
        raw_target=raw_target,
        target_kind=TargetKind.MODULE,
        resolved_path=Path(spec.origin).resolve() if spec.origin else None,
        package_root=working_directory,
        internal_prefixes=(raw_target.split(".", maxsplit=1)[0],),
    )


def discover_internal_prefixes(root: Path) -> tuple[str, ...]:
    prefixes: list[str] = []
    for child in root.iterdir():
        if child.is_dir() and (child / "__init__.py").is_file():
            prefixes.append(child.name)
    if not prefixes:
        return ()
    return tuple(sorted(prefixes))


def build_profile_command(target: TargetSpec) -> tuple[str, ...]:
    if target.target_kind is TargetKind.SCRIPT:
        assert target.resolved_path is not None
        return (sys.executable, "-X", "importtime", str(target.resolved_path))
    if target.target_kind is TargetKind.MODULE:
        return (sys.executable, "-X", "importtime", "-m", target.raw_target)
    raise ProfileError("Package directory targets are not executable by the profile command yet.")


def run_importtime(target: TargetSpec) -> str:
    command = build_profile_command(target)
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=str(target.package_root) if target.package_root is not None else None,
        )
    except OSError as exc:
        raise ProfileError(f"Unable to execute Python runtime profiling: {exc}") from exc

    output = completed.stderr.strip()
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise ProfileError(f"Runtime profiling failed: {stderr}")
    if not output:
        raise ProfileError("Runtime profiling returned no import timing output.")
    return output


def parse_importtime_output(
    output: str,
) -> tuple[tuple[TimingRecord, ...], tuple[ParseAnomaly, ...]]:
    records: list[TimingRecord] = []
    anomalies: list[ParseAnomaly] = []
    for line_number, raw_line in enumerate(output.splitlines(), start=1):
        line = raw_line.rstrip()
        if not line:
            continue
        if line.strip() == IMPORT_TIME_HEADER:
            continue
        match = IMPORT_TIME_RE.match(line)
        if match is None:
            anomalies.append(
                ParseAnomaly(
                    line_number=line_number,
                    content=line,
                    message="Line did not match the expected importtime format.",
                )
            )
            continue
        module_field = match.group("module")
        module_name = module_field.strip()
        indent = len(module_field) - len(module_field.lstrip())
        records.append(
            TimingRecord(
                module_name=module_name,
                self_time_us=int(match.group("self")),
                cumulative_time_us=int(match.group("cumulative")),
                import_depth=max(indent // 2, 0),
            )
        )
    if not records:
        raise ProfileError("No import timing records could be parsed from the runtime output.")
    return tuple(records), tuple(anomalies)


def filter_timing_records(
    records: tuple[TimingRecord, ...],
    config: AnalysisConfig,
    internal_prefixes: tuple[str, ...],
) -> tuple[TimingRecord, ...]:
    filtered = list(records)
    if config.include:
        filtered = [
            record
            for record in filtered
            if any(pattern in record.module_name for pattern in config.include)
        ]
    if config.exclude:
        filtered = [
            record
            for record in filtered
            if not any(pattern in record.module_name for pattern in config.exclude)
        ]
    if config.internal_only and internal_prefixes:
        filtered = [
            record
            for record in filtered
            if any(
                record.module_name == prefix or record.module_name.startswith(f"{prefix}.")
                for prefix in internal_prefixes
            )
        ]
    return tuple(sorted(filtered, key=lambda record: record.cumulative_time_us, reverse=True))


def deduplicate_timing_records(records: tuple[TimingRecord, ...]) -> tuple[TimingRecord, ...]:
    deduped: list[TimingRecord] = []
    seen_modules: set[str] = set()
    for record in records:
        if record.module_name in seen_modules:
            continue
        seen_modules.add(record.module_name)
        deduped.append(record)
    return tuple(deduped)


def summarize_timing_records(
    records: tuple[TimingRecord, ...],
    internal_prefixes: tuple[str, ...],
    limit: int = 10,
) -> tuple[TimingRecord, ...]:
    if not records:
        return ()

    def is_internal(record: TimingRecord) -> bool:
        return any(
            record.module_name == prefix or record.module_name.startswith(f"{prefix}.")
            for prefix in internal_prefixes
        )

    internal_records = deduplicate_timing_records(
        tuple(record for record in records if is_internal(record))
    )
    if internal_records:
        return tuple(internal_records[:limit])
    return deduplicate_timing_records(records)[:limit]


def profile_target(
    raw_target: str,
    config: AnalysisConfig,
    working_directory: Path,
    runner: Callable[[TargetSpec], str] | None = None,
) -> ProfileResult:
    target = resolve_target(raw_target, working_directory=working_directory)
    if target.target_kind is TargetKind.PACKAGE:
        raise ProfileError(
            "Package directory targets are not executable by the profile command yet."
        )
    execute = run_importtime if runner is None else runner
    output = execute(target)
    records, anomalies = parse_importtime_output(output)
    filtered = filter_timing_records(
        records,
        config=config,
        internal_prefixes=target.internal_prefixes,
    )
    limitations = (
        (
            "Runtime timings are measured but environment-dependent and "
            "should not be treated as stable benchmarks."
        ),
    )
    return ProfileResult(
        target=target,
        timing_records=filtered,
        limitations=limitations,
        parse_anomalies=anomalies,
    )
