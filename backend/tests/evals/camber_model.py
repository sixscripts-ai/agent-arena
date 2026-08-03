import asyncio
import json
import os
import shutil
import subprocess
from typing import Optional, Tuple, Union

from pydantic import BaseModel

from deepeval.models import DeepEvalBaseLLM
from deepeval.models.llms.utils import trim_and_load_json


class CamberModel(DeepEvalBaseLLM):
    """DeepEval judge backed by `camber chat` (Camber Cloud agents)."""

    def __init__(
        self,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        camber_bin: Optional[str] = None,
        timeout_s: int = 180,
    ):
        self.agent = agent or os.environ.get(
            "CAMBER_EVAL_AGENT", "@nova.snowflake"
        )
        self.timeout_s = timeout_s
        self.camber_bin = (
            camber_bin
            or shutil.which("camber")
            or os.path.expanduser("~/.camber/bin/camber")
        )
        super().__init__(model or f"camber:{self.agent}")

    def load_model(self, *args, **kwargs):
        return self

    def get_model_name(self, *args, **kwargs) -> str:
        return self.name

    def _chat(self, prompt: str) -> str:
        if not os.path.isfile(self.camber_bin):
            raise RuntimeError(
                f"camber binary not found at {self.camber_bin}. "
                "Install CLI: curl -sL https://cli.cambercloud.com/install-v2.sh | bash"
            )
        cmd = [
            self.camber_bin,
            "chat",
            "-a",
            self.agent,
            "-m",
            prompt,
            "-o",
            "json",
        ]
        api_key = os.environ.get("CAMBER_API_KEY")
        if api_key:
            cmd.extend(["--api-key", api_key])
        env = os.environ.copy()
        camber_home = os.path.expanduser("~/.camber/bin")
        env["PATH"] = f"{camber_home}:{env.get('PATH', '')}"
        # Prefer dotenv-local key if shell env missing
        if not env.get("CAMBER_API_KEY"):
            local_env = os.path.join(
                os.path.dirname(__file__), "..", "..", "..", ".env.local"
            )
            local_env = os.path.abspath(local_env)
            if os.path.isfile(local_env):
                with open(local_env) as f:
                    for line in f:
                        if line.startswith("CAMBER_API_KEY=") and not env.get(
                            "CAMBER_API_KEY"
                        ):
                            env["CAMBER_API_KEY"] = line.split("=", 1)[1].strip()
                            if "--api-key" not in cmd:
                                cmd.extend(["--api-key", env["CAMBER_API_KEY"]])
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            env=env,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"camber chat failed ({proc.returncode}): "
                f"{proc.stderr.strip() or proc.stdout.strip()}"
            )
        line = proc.stdout.strip().splitlines()[-1]
        payload = json.loads(line)
        result = payload.get("result")
        if result is None:
            raise RuntimeError(f"camber chat missing result: {payload}")
        return str(result)

    def generate(
        self, prompt: str, schema: Optional[BaseModel] = None
    ) -> Tuple[Union[str, BaseModel], float]:
        if schema is not None:
            schema_prompt = (
                f"{prompt}\n\n"
                "Return ONLY valid JSON matching this schema. "
                "No markdown fences, no commentary.\n"
                f"Schema: {json.dumps(schema.model_json_schema())}"
            )
            raw = self._chat(schema_prompt)
            data = trim_and_load_json(raw)
            return schema.model_validate(data), 0.0
        return self._chat(prompt), 0.0

    async def a_generate(
        self, prompt: str, schema: Optional[BaseModel] = None
    ) -> Tuple[Union[str, BaseModel], float]:
        return await asyncio.to_thread(self.generate, prompt, schema)
