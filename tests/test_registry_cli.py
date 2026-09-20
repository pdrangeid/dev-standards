"""End-to-end CLI behaviour: add, generate, refresh, rollup, check."""

import yaml
from typer.testing import CliRunner

from dev_standards.main import app

runner = CliRunner()


def run(*args):
    return runner.invoke(app, ["registry", *args])


def test_add_generates_links_and_rolls_up(make_repo, fake_llm, tmp_path):
    hub = tmp_path / "hub"
    root = make_repo("my-repo")
    result = run("add", str(root), "--hub", str(hub), "--llm-cmd", fake_llm.cmd)
    assert result.exit_code == 0, result.output
    assert (root / "my_repo_registry.yaml").is_file()
    assert (hub / "my_repo_registry.yaml").is_symlink()
    assert [e["repo"] for e in yaml.safe_load((hub / "registry.yaml").read_text())] == [
        "my-repo"
    ]


def test_add_no_generate_skips_the_llm(make_repo, fake_llm, tmp_path):
    root = make_repo("my-repo")
    run("add", str(root), "--hub", str(tmp_path / "hub"), "--no-generate")
    assert fake_llm.calls == 0


def test_refresh_only_regenerates_changed_repos(make_repo, fake_llm, tmp_path):
    hub = tmp_path / "hub"
    a, b = make_repo("repo-a"), make_repo("repo-b")
    for r in (a, b):
        run("add", str(r), "--hub", str(hub), "--llm-cmd", fake_llm.cmd)
    assert fake_llm.calls == 2

    (a / "README.md").write_text("# Changed\n")
    result = run("refresh", "--hub", str(hub), "--llm-cmd", fake_llm.cmd)
    assert result.exit_code == 0, result.output
    assert fake_llm.calls == 3  # only repo-a
    assert "repo-a: updated" in result.output and "repo-b: skipped" in result.output

    again = run("refresh", "--hub", str(hub), "--llm-cmd", fake_llm.cmd)
    assert again.exit_code == 0 and fake_llm.calls == 3
    assert "rollup unchanged" in again.output


def test_refresh_continues_past_a_failing_repo_and_reports_it(
    make_repo, fake_llm, tmp_path
):
    hub = tmp_path / "hub"
    good, broken = make_repo("good"), make_repo("broken")
    for r in (good, broken):
        run("add", str(r), "--hub", str(hub), "--llm-cmd", fake_llm.cmd)
    (good / "README.md").write_text("# Changed\n")
    (broken / "README.md").unlink()  # its only doc: generation must now fail
    result = run("refresh", "--hub", str(hub), "--llm-cmd", fake_llm.cmd)
    assert result.exit_code == 1
    assert "good: updated" in result.output  # the other repo was still processed
    assert "failed: ['broken']" in result.output


def test_check_reports_schema_failures_and_rollup_drift(make_repo, fake_llm, tmp_path):
    hub = tmp_path / "hub"
    root = make_repo("my-repo")
    run("add", str(root), "--hub", str(hub), "--llm-cmd", fake_llm.cmd)
    assert run("check", "--hub", str(hub)).exit_code == 0

    (root / "my_repo_registry.yaml").write_text("repo: my-repo\npurpose: ''\n")
    bad = run("check", "--hub", str(hub))
    assert bad.exit_code == 1 and "purpose" in bad.output

    (root / "my_repo_registry.yaml").unlink()
    assert run("check", "--hub", str(hub)).exit_code == 1

    fixed = run("rollup", "--hub", str(hub))
    assert fixed.exit_code == 1  # the broken link is still reported by rollup
    assert "my_repo_registry.yaml" in fixed.output


def test_check_detects_a_stale_rollup(make_repo, fake_llm, tmp_path):
    hub = tmp_path / "hub"
    root = make_repo("my-repo")
    run("add", str(root), "--hub", str(hub), "--llm-cmd", fake_llm.cmd)
    (root / "README.md").write_text("# Changed\n")
    run(
        "generate", str(root), "--llm-cmd", fake_llm.cmd
    )  # file changes, rollup not rebuilt
    stale = run("check", "--hub", str(hub))
    assert stale.exit_code == 1 and "out of date" in stale.output
    run("rollup", "--hub", str(hub))
    assert run("check", "--hub", str(hub)).exit_code == 0


def test_generate_reports_failure_with_exit_code(make_repo, fake_llm):
    fake_llm.mode("fail")
    result = run("generate", str(make_repo()), "--llm-cmd", fake_llm.cmd)
    assert result.exit_code == 1 and "exited 3" in result.output
