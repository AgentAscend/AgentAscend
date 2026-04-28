import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nixpacks_builds_node_payment_helper_before_runtime():
    config_path = ROOT / "nixpacks.toml"
    assert config_path.exists(), "nixpacks.toml must define legacy Railway/Nixpacks build/runtime packaging"

    config = tomllib.loads(config_path.read_text())
    providers = config.get("providers") or []
    assert "python" in providers
    assert "node" in providers

    install_commands = "\n".join(config.get("phases", {}).get("install", {}).get("cmds", []))
    build_commands = "\n".join(config.get("phases", {}).get("build", {}).get("cmds", []))
    start_command = config.get("start", {}).get("cmd", "")

    assert "python -m pip install -r requirements.txt" in install_commands
    assert "cd node-payment-helper && npm ci" in install_commands
    assert "cd node-payment-helper && npm run build" in build_commands
    assert "uvicorn backend.app.main:app" in start_command
    assert "$PORT" in start_command


def test_railpack_builds_and_deploys_node_payment_helper_runtime_artifacts():
    config_path = ROOT / "railpack.json"
    assert config_path.exists(), "Railway now uses Railpack, so railpack.json must package the Node helper"

    config = json.loads(config_path.read_text())
    assert config.get("$schema") == "https://schema.railpack.com"
    packages = config.get("packages") or {}
    assert packages.get("node") == "22"

    helper_step = (config.get("steps") or {}).get("node-payment-helper") or {}
    commands = "\n".join(
        command.get("cmd", "") if isinstance(command, dict) else str(command)
        for command in helper_step.get("commands", [])
    )
    deploy_outputs = helper_step.get("deployOutputs") or []
    deploy_includes = {
        item
        for output in deploy_outputs
        if isinstance(output, dict)
        for item in output.get("include", [])
    }
    start_command = (config.get("deploy") or {}).get("startCommand", "")

    assert "cd node-payment-helper && npm ci" in commands
    assert "cd node-payment-helper && npm run build" in commands
    assert "python scripts/check_node_payment_helper_runtime.py" in commands
    assert "node-payment-helper/dist" in deploy_includes
    assert "node-payment-helper/node_modules" in deploy_includes
    assert "uvicorn backend.app.main:app" in start_command
    assert "$PORT" in start_command


def test_runtime_helper_check_script_is_scoped_and_secret_safe():
    script_path = ROOT / "scripts" / "check_node_payment_helper_runtime.py"
    assert script_path.exists(), "runtime helper check script must exist"

    content = script_path.read_text()
    assert "node-payment-helper" in content
    assert "dist" in content
    assert "cli.js" in content
    assert "SOLANA_RPC_URL" not in content
    assert "DATABASE_URL" not in content
    assert "print(os.environ" not in content
