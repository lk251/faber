from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _python(venv: Path) -> Path:
    windows = venv / "Scripts" / "python.exe"
    return windows if windows.is_file() else venv / "bin" / "python"


def _console(venv: Path) -> Path:
    windows = venv / "Scripts" / "faber.exe"
    return windows if windows.is_file() else venv / "bin" / "faber"


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment.pop("OPENAI_API_KEY", None)
    environment["FABER_LIVE_OPENAI_TEST"] = "0"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout[-2000:]}\n{completed.stderr[-2000:]}"
        )
    return completed


def _create_venv(path: Path, *, cwd: Path, environment: dict[str, str]) -> None:
    _run(
        [sys.executable, "-m", "venv", str(path)],
        cwd=cwd,
        environment=environment,
    )


def _install(
    venv: Path,
    requirement: str,
    *,
    cwd: Path,
    environment: dict[str, str],
    no_dependencies: bool,
) -> None:
    command = [str(_python(venv)), "-m", "pip", "install"]
    if no_dependencies:
        command.append("--no-deps")
    command.append(requirement)
    _run(command, cwd=cwd, environment=environment)


def _import_probe(
    venv: Path,
    *,
    cwd: Path,
    environment: dict[str, str],
    expect_openai: bool,
) -> dict[str, object]:
    probe = (
        "import importlib.util,json,pathlib,sys;"
        "import faber, faber.adapters;"
        "location=pathlib.Path(faber.__file__).resolve();"
        "print(json.dumps({"
        "'location':str(location),"
        "'openai_available':importlib.util.find_spec('openai') is not None,"
        "'sys_path':[str(pathlib.Path(p).resolve()) for p in sys.path if p]"
        "},sort_keys=True))"
    )
    completed = _run(
        [str(_python(venv)), "-I", "-c", probe],
        cwd=cwd,
        environment=environment,
    )
    payload = json.loads(completed.stdout)
    location = Path(payload["location"]).resolve(strict=True)
    try:
        location.relative_to(REPOSITORY_ROOT)
    except ValueError:
        pass
    else:
        raise RuntimeError("clean-install import resolved inside the repository checkout")
    if bool(payload["openai_available"]) is not expect_openai:
        raise RuntimeError("optional OpenAI dependency availability does not match the install")
    repository_source = (REPOSITORY_ROOT / "src").resolve()
    for raw_path in payload["sys_path"]:
        if Path(raw_path).resolve() == repository_source:
            raise RuntimeError("clean-install interpreter retained the checkout PYTHONPATH")
    return {
        "location_suffix": "/".join(location.parts[-3:]),
        "openai_available": payload["openai_available"],
        "checkout_pythonpath_absent": True,
    }


def _directory_metrics(path: Path) -> dict[str, int]:
    files = [item for item in path.rglob("*") if item.is_file()]
    return {
        "file_count": len(files),
        "size_bytes": sum(item.stat().st_size for item in files),
    }


def run_clean_install_audit(*, include_live_extra: bool = True) -> dict[str, object]:
    environment = _environment()
    with tempfile.TemporaryDirectory(prefix="faber-clean-install-") as temporary:
        root = Path(temporary)
        dist = root / "dist"
        workspace = root / "workspace"
        dist.mkdir()
        workspace.mkdir()
        _run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--sdist",
                "--outdir",
                str(dist),
                str(REPOSITORY_ROOT),
            ],
            cwd=workspace,
            environment=environment,
        )
        wheels = sorted(dist.glob("faber-*.whl"))
        sdists = sorted(dist.glob("faber-*.tar.gz"))
        if len(wheels) != 1 or len(sdists) != 1:
            raise RuntimeError("build did not produce exactly one wheel and one sdist")
        wheel = wheels[0]
        sdist = sdists[0]

        base_venv = root / "base-venv"
        _create_venv(base_venv, cwd=workspace, environment=environment)
        _install(
            base_venv,
            str(wheel),
            cwd=workspace,
            environment=environment,
            no_dependencies=True,
        )
        base_probe = _import_probe(
            base_venv,
            cwd=workspace,
            environment=environment,
            expect_openai=False,
        )
        faber = _console(base_venv)
        _run([str(faber), "--help"], cwd=workspace, environment=environment)
        doctor = _run([str(faber), "doctor"], cwd=workspace, environment=environment)
        if "faber doctor: ok" not in doctor.stdout:
            raise RuntimeError("installed faber doctor did not report success")
        demo_path = workspace / "demo"
        demo = _run(
            [
                str(faber),
                "demo",
                "proof",
                "--mode",
                "replay",
                "--out-dir",
                str(demo_path),
                "--json",
            ],
            cwd=workspace,
            environment=environment,
        )
        summary = json.loads(demo.stdout)
        if (
            summary.get("bad", {}).get("ordinary_tests") != "pass"
            or summary.get("bad", {}).get("verdict") != "block"
            or summary.get("repaired", {}).get("ordinary_tests") != "pass"
            or summary.get("repaired", {}).get("verdict") != "pass"
        ):
            raise RuntimeError("installed replay demo did not reproduce PASS/PASS and BLOCK/PASS")
        for relative in ("bad/report.html", "repaired/report.html"):
            if not (demo_path / relative).is_file():
                raise RuntimeError(f"installed replay demo omitted {relative}")
        privacy_path = workspace / "privacy.json"
        _run(
            [
                str(faber),
                "audit-proof-artifacts",
                str(demo_path),
                "--json-out",
                str(privacy_path),
            ],
            cwd=workspace,
            environment=environment,
        )
        privacy = json.loads(privacy_path.read_text(encoding="utf-8"))
        if privacy.get("status") != "pass":
            raise RuntimeError("installed replay artifacts failed the privacy audit")

        extra_probe: dict[str, object] | None = None
        if include_live_extra:
            live_venv = root / "live-venv"
            _create_venv(live_venv, cwd=workspace, environment=environment)
            _install(
                live_venv,
                f"{wheel}[live-openai]",
                cwd=workspace,
                environment=environment,
                no_dependencies=False,
            )
            extra_probe = _import_probe(
                live_venv,
                cwd=workspace,
                environment=environment,
                expect_openai=True,
            )

        return {
            "schema": "faber.clean_install_audit.v1",
            "status": "pass",
            "build": {
                "wheel": wheel.name,
                "wheel_size_bytes": wheel.stat().st_size,
                "sdist": sdist.name,
                "sdist_size_bytes": sdist.stat().st_size,
            },
            "base_install": base_probe,
            "live_extra_install": extra_probe,
            "demo": {
                "bad_ordinary_tests": "pass",
                "bad_verdict": "block",
                "repaired_ordinary_tests": "pass",
                "repaired_verdict": "pass",
                **_directory_metrics(demo_path),
            },
            "privacy_audit": {
                "status": privacy["status"],
                "scanned_files": privacy["scanned_files"],
                "finding_count": privacy["finding_count"],
            },
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-live-extra",
        action="store_true",
        help="Skip the network-dependent optional-extra installation probe.",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    try:
        report = run_clean_install_audit(include_live_extra=not args.skip_live_extra)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"clean-install audit failed: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
