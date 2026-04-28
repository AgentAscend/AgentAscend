import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nixpacks_builds_node_payment_helper_before_runtime():
    config_path = ROOT / "nixpacks.toml"
    assert config_path.exists(), "nixpacks.toml must define Railway build/runtime packaging"

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
