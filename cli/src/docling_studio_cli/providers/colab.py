"""Google Colab conversion provider implementation."""

from __future__ import annotations

import sys
import uuid
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from docling_studio_cli.models import (
    ColabAuthMethod,
    ColabGpuType,
    ColabProviderSettings,
    ProviderCheckResult,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from docling_studio_cli.providers.base import PromptFn, ProviderSession
    from docling_studio_cli.settings import CliSettings


def _colab_api(auth: str):
    try:
        from colab_cli.auth import AuthProvider, get_credentials
        from colab_cli.client import Accelerator, Client, Prod, Variant
        from colab_cli.contents import ContentsClient
        from colab_cli.runtime import ColabRuntime
        from colab_cli.state import SessionState
    except ImportError as exc:
        raise RuntimeError(
            "Install google-colab-cli in this Python environment; see docs/cloud-conversion.md"
        ) from exc

    client = Client(Prod(), get_credentials(provider=AuthProvider(auth)))
    return client, Accelerator, Variant, ContentsClient, ColabRuntime, SessionState


def _execute(runtime, code: str, expected_marker: str, *, timeout: int = 900) -> None:
    outputs = runtime.execute_code(code, timeout=timeout)
    for item in outputs:
        if item.get("output_type") == "error":
            raise RuntimeError(f"Colab execution failed: {item.get('evalue') or item}")
    if not any(expected_marker in str(item.get("text", "")) for item in outputs):
        raise RuntimeError(f"Colab did not report {expected_marker}")


class _ColabSession:
    """Single active Colab runtime session with the source PDF uploaded and Docling initialized."""

    def __init__(self, run_id: str, remote_pdf: str, runtime, contents) -> None:
        self._run_id = run_id
        self._remote_pdf = remote_pdf
        self._runtime = runtime
        self._contents = contents

    def convert_range(
        self,
        page_range: tuple[int, int] | None,
        output_path: Path,
    ) -> None:
        if page_range is None:
            remote_json = f"/content/{self._run_id}.docling.json"
            script = (
                f"result = converter.convert({self._remote_pdf!r})\n"
                f"Path({remote_json!r}).write_text("
                "json.dumps(result.document.export_to_dict()), encoding='utf-8')\n"
                "print('DOCLING_CONVERTED')\n"
            )
            _execute(self._runtime, script, "DOCLING_CONVERTED", timeout=3600)
            self._contents.download(remote_json, str(output_path))
            return

        start, end = page_range
        remote_part = f"/content/{self._run_id}-{start}-{end}.docling.json"
        script = (
            f"result = converter.convert({self._remote_pdf!r}, page_range=({start}, {end}))\n"
            f"Path({remote_part!r}).write_text("
            "json.dumps(result.document.export_to_dict()), encoding='utf-8')\n"
            "del result\n"
            "gc.collect()\n"
            "print('DOCLING_CONVERTED')\n"
        )
        _execute(self._runtime, script, "DOCLING_CONVERTED")
        self._contents.download(remote_part, str(output_path))


class ColabProvider:
    """Conversion provider that runs Docling on an ephemeral Google Colab CPU/GPU runtime."""

    name = "colab"
    description = "Google Colab CPU/GPU runtime via google-colab-cli (single or parallel workers)"
    settings_model = "ColabProviderSettings"

    @contextmanager
    def open_session(
        self,
        pdf: Path,
        settings: CliSettings,
    ) -> Iterator[ProviderSession]:
        cfg: ColabProviderSettings = settings.colab
        gpu_str = cfg.gpu.value if cfg.gpu else None
        auth_str = cfg.auth.value

        client, accelerator_cls, variant_cls, contents_cls, runtime_cls, state_cls = _colab_api(
            auth_str
        )
        run_id = f"docling-{uuid.uuid4().hex[:10]}"
        remote_pdf = f"/content/{run_id}-{pdf.name}"
        endpoint = None
        runtime = None
        try:
            print("Allocating Colab runtime...", flush=True)
            assigned = client.assign(
                uuid.uuid4(),
                variant=variant_cls.GPU if gpu_str else variant_cls.DEFAULT,
                accelerator=(accelerator_cls(gpu_str.upper()) if gpu_str else accelerator_cls.NONE),
            )
            endpoint = assigned.endpoint
            info = assigned.runtime_proxy_info
            state = state_cls(name=run_id, token=info.token, url=info.url, endpoint=endpoint)
            contents = contents_cls(state)
            runtime = runtime_cls(info.url, info.token)
            contents.upload(str(pdf), remote_pdf)
            print("Installing Docling on Colab...", flush=True)
            _execute(
                runtime,
                "import importlib.util, subprocess, sys\n"
                "if importlib.util.find_spec('docling') is None:\n"
                "    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', "
                f"{cfg.docling_version_spec!r}])\n"
                "print('DOCLING_READY')\n",
                "DOCLING_READY",
            )
            print("Converting PDF on Colab...", flush=True)
            gpu_check = (
                "import torch\n"
                "if not torch.cuda.is_available():\n"
                "    raise RuntimeError('Colab GPU is unavailable')\n"
                if gpu_str
                else ""
            )
            setup = (
                "import json, os, gc\n"
                "from pathlib import Path\n"
                f"os.environ['DOCLING_DEVICE'] = {'cuda' if gpu_str else 'cpu'!r}\n"
                f"{gpu_check}"
                "from docling.document_converter import DocumentConverter\n"
                "converter = DocumentConverter()\n"
                "print('DOCLING_READY_TO_CONVERT')\n"
            )
            _execute(runtime, setup, "DOCLING_READY_TO_CONVERT")
            yield _ColabSession(run_id, remote_pdf, runtime, contents)
        finally:
            if runtime is not None:
                try:
                    runtime.stop(shutdown_kernel=True)
                except Exception as exc:
                    print(
                        f"Warning: Colab kernel cleanup failed: {exc}",
                        file=sys.stderr,
                    )
            if endpoint is not None:
                client.unassign(endpoint)
                print("Colab runtime released", flush=True)

    def is_transient_capacity_error(self, error: Exception) -> bool:
        return "Precondition Failed" in str(error)

    def configure_interactive(
        self,
        current: CliSettings,
        prompt: PromptFn,
    ) -> dict[str, Any]:
        auth_choices = "/".join(a.value for a in ColabAuthMethod)
        gpu_choices = "/".join([*(g.value for g in ColabGpuType), "cpu"])
        default_auth = current.colab.auth.value
        default_gpu = current.colab.gpu.value if current.colab.gpu else "T4"

        auth_val = prompt(
            f"Colab authentication method [{auth_choices}]",
            default_auth,
        )
        gpu_val = prompt(
            f"Default Colab accelerator [{gpu_choices}]",
            default_gpu,
        )
        validated = ColabProviderSettings(
            auth=ColabAuthMethod(auth_val.strip().lower()),
            gpu=None if gpu_val.strip().lower() in {"cpu", "none", ""} else gpu_val.strip().upper(),
            docling_version_spec=current.colab.docling_version_spec,
        )
        return {"colab": validated.model_dump(mode="json")}

    def verify(self, settings: CliSettings) -> ProviderCheckResult:
        cfg = settings.colab
        try:
            client, *_ = _colab_api(cfg.auth.value)
            details: dict[str, Any] = {
                "auth": cfg.auth.value,
                "gpu": cfg.gpu.value if cfg.gpu else "CPU",
            }
            if hasattr(client, "list_assignments"):
                assignments = client.list_assignments()
                details["active_runtimes"] = len(assignments)
            if hasattr(client, "get_consumption_user_info"):
                info = client.get_consumption_user_info()
                balance = getattr(info, "paid_compute_units_balance", None)
                if balance is not None:
                    details["compute_units_balance"] = round(float(balance), 3)
            balance_str = (
                f", balance={details['compute_units_balance']} compute units"
                if "compute_units_balance" in details
                else ""
            )
            active_str = (
                f", active_runtimes={details['active_runtimes']}"
                if "active_runtimes" in details
                else ""
            )
            return ProviderCheckResult(
                provider=self.name,
                ok=True,
                summary=f"Authenticated with Google Colab ({cfg.auth.value}, default accelerator={details['gpu']}{balance_str}{active_str})",
                details=details,
            )
        except Exception as exc:
            return ProviderCheckResult(
                provider=self.name,
                ok=False,
                summary=f"Google Colab verification failed: {exc}",
                details={"auth": cfg.auth.value},
            )
