import subprocess
import textwrap

import pytest

from changelog_gen import (
    Commit,
    generate_changelog,
    group_commits,
    parse_commit,
    render_markdown,
)


# --- testes unitários do parser -------------------------------------------------

def test_parse_simple_feat():
    parsed = parse_commit(Commit(hash="abc1234", subject="feat: adiciona login por email"))
    assert parsed.type == "feat"
    assert parsed.scope is None
    assert parsed.description == "adiciona login por email"
    assert parsed.breaking is False


def test_parse_with_scope():
    parsed = parse_commit(Commit(hash="abc1234", subject="fix(auth): corrige expiração de token"))
    assert parsed.type == "fix"
    assert parsed.scope == "auth"
    assert parsed.description == "corrige expiração de token"


def test_parse_breaking_change_via_bang():
    parsed = parse_commit(Commit(hash="abc1234", subject="feat(api)!: remove endpoint legado"))
    assert parsed.breaking is True
    assert parsed.breaking_description == "remove endpoint legado"


def test_parse_breaking_change_via_footer():
    body = "Detalhes da mudança.\n\nBREAKING CHANGE: o campo `id` agora é string, não inteiro."
    parsed = parse_commit(Commit(hash="abc1234", subject="refactor: normaliza tipos de id", body=body))
    assert parsed.breaking is True
    assert parsed.breaking_description == "o campo `id` agora é string, não inteiro."


def test_unrecognized_conventional_type_falls_back_to_other_but_keeps_description():
    # "wip" tem o formato de um Conventional Commit, mas não é um tipo reconhecido:
    # a seção vira "other", mas a descrição já vem sem o prefixo "wip: ".
    parsed = parse_commit(Commit(hash="abc1234", subject="wip: experimento ainda não pronto"))
    assert parsed.type == "other"
    assert parsed.description == "experimento ainda não pronto"


def test_parse_non_conventional_message_falls_back_to_other():
    parsed = parse_commit(Commit(hash="abc1234", subject="ajustes rápidos no README"))
    assert parsed.type == "other"
    assert parsed.description == "ajustes rápidos no README"
    assert parsed.breaking is False


# --- testes de agrupamento e renderização ---------------------------------------

def test_group_commits_orders_sections_and_includes_breaking_twice():
    commits = [
        parse_commit(Commit("h1", "feat!: quebra compatibilidade")),
        parse_commit(Commit("h2", "fix: corrige bug simples")),
        parse_commit(Commit("h3", "docs: atualiza README")),
    ]
    groups = group_commits(commits)

    assert "🚨 Breaking Changes" in groups
    assert groups["🚨 Breaking Changes"][0].hash == "h1"
    # o commit breaking também deve aparecer na seção normal de features
    assert any(c.hash == "h1" for c in groups["✨ Funcionalidades"])
    assert any(c.hash == "h2" for c in groups["🐛 Correções"])
    assert any(c.hash == "h3" for c in groups["📚 Documentação"])


def test_render_markdown_empty_group_has_placeholder():
    markdown = render_markdown({}, title="Unreleased")
    assert "## Unreleased" in markdown
    assert "Nenhum commit encontrado" in markdown


def test_render_markdown_includes_scope_and_hash():
    commits = [parse_commit(Commit("abcdef1234567", "fix(auth): corrige bug"))]
    groups = group_commits(commits)
    markdown = render_markdown(groups, title="v1.0.0")

    assert "## v1.0.0" in markdown
    assert "**auth**: corrige bug" in markdown
    assert "`abcdef1`" in markdown


# --- teste de integração com um repositório git real (temporário) --------------

def _run_git(repo_path, *args):
    subprocess.run(["git", "-C", str(repo_path), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def temp_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _run_git(repo, "init", "-q")
    _run_git(repo, "config", "user.email", "teste@example.com")
    _run_git(repo, "config", "user.name", "Teste")

    (repo / "a.txt").write_text("1")
    _run_git(repo, "add", "a.txt")
    _run_git(repo, "commit", "-q", "-m", "feat: primeira funcionalidade")

    (repo / "a.txt").write_text("2")
    _run_git(repo, "add", "a.txt")
    _run_git(repo, "commit", "-q", "-m", "fix(core): corrige cálculo incorreto")

    (repo / "a.txt").write_text("3")
    _run_git(repo, "add", "a.txt")
    _run_git(
        repo,
        "commit",
        "-q",
        "-m",
        "feat(api)!: renomeia campo de resposta\n\nBREAKING CHANGE: `nome` agora se chama `name`.",
    )

    return repo


def test_generate_changelog_end_to_end_against_real_git_repo(temp_git_repo):
    markdown = generate_changelog(str(temp_git_repo), rev_range=None, title="Unreleased")

    assert "## Unreleased" in markdown
    assert "🚨 Breaking Changes" in markdown
    assert "primeira funcionalidade" in markdown
    assert "**core**: corrige cálculo incorreto" in markdown
    assert "renomeia campo de resposta" in markdown
    assert "`nome` agora se chama `name`." in markdown


def test_generate_changelog_respects_rev_range(temp_git_repo):
    # pega o hash do primeiro commit para usar como início do intervalo (exclusivo)
    log = subprocess.run(
        ["git", "-C", str(temp_git_repo), "log", "--reverse", "--pretty=format:%H"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    first_commit_hash = log[0]

    markdown = generate_changelog(
        str(temp_git_repo), rev_range=f"{first_commit_hash}..HEAD", title="v0.2.0"
    )

    assert "primeira funcionalidade" not in markdown
    assert "corrige cálculo incorreto" in markdown


def test_generate_changelog_raises_on_invalid_repo(tmp_path):
    with pytest.raises(RuntimeError):
        generate_changelog(str(tmp_path / "nao-existe"), rev_range=None, title="Unreleased")
