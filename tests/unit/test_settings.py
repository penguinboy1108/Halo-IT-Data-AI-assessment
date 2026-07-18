from pathlib import Path

from agent.settings import Settings, resolve_project_root


def test_resolve_project_root_prefers_runtime_workdir_over_site_packages(tmp_path):
    runtime_root = tmp_path / "app"
    package_root = tmp_path / "usr" / "local" / "lib" / "python3.12" / "site-packages"
    (runtime_root / "agent" / "config").mkdir(parents=True)
    (runtime_root / "data" / "processed").mkdir(parents=True)
    (package_root / "agent" / "config").mkdir(parents=True)

    resolved = resolve_project_root(cwd=runtime_root, package_root=package_root, env_root="")

    assert resolved == runtime_root


def test_path_settings_support_explicit_agent_env_aliases(tmp_path):
    db_path = tmp_path / "data" / "processed" / "halo_analytics.duckdb"
    data_dir = db_path.parent
    prompts_dir = tmp_path / "agent" / "prompts"
    config_dir = tmp_path / "agent" / "config"
    traces_dir = tmp_path / "traces"

    settings = Settings(
        AGENT_DB_PATH=db_path,
        AGENT_DATA_DIR=data_dir,
        AGENT_PROMPTS_DIR=prompts_dir,
        AGENT_CONFIG_DIR=config_dir,
        AGENT_TRACES_DIR=traces_dir,
    )

    assert settings.db_path == db_path
    assert settings.data_dir == data_dir
    assert settings.prompts_dir == prompts_dir
    assert settings.config_dir == config_dir
    assert settings.traces_dir == traces_dir


def test_project_root_env_override_is_respected(tmp_path):
    assert resolve_project_root(env_root=str(tmp_path)) == Path(tmp_path).resolve()
