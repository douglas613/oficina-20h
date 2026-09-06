#!/usr/bin/env python3
"""Gera um CHANGELOG.md a partir do histórico de commits de um repositório git,
interpretando mensagens no padrão Conventional Commits (https://www.conventionalcommits.org/).

Uso:
    python3 changelog_gen.py [--repo CAMINHO] [--range REV_RANGE] [--title TITULO] [--output ARQUIVO]

Exemplos:
    python3 changelog_gen.py
    python3 changelog_gen.py --range v1.0.0..HEAD --title "v1.1.0"
    python3 changelog_gen.py --repo ../outro-projeto --output CHANGELOG.md
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field

# Tipos reconhecidos pelo Conventional Commits e a seção do changelog em que caem.
# A ordem do dicionário define a ordem de exibição das seções.
SECTIONS: dict[str, str] = {
    "feat": "✨ Funcionalidades",
    "fix": "🐛 Correções",
    "perf": "⚡ Performance",
    "refactor": "♻️ Refatoração",
    "docs": "📚 Documentação",
    "test": "🧪 Testes",
    "build": "🔧 Build & CI",
    "ci": "🔧 Build & CI",
    "chore": "🧹 Manutenção",
    "style": "🧹 Manutenção",
    "revert": "🧹 Manutenção",
}
OTHER_SECTION = "📦 Outras mudanças"
BREAKING_SECTION = "🚨 Breaking Changes"

# type(scope)!: descrição
HEADER_RE = re.compile(
    r"^(?P<type>[a-zA-Z]+)(\((?P<scope>[^)]+)\))?(?P<breaking>!)?:\s*(?P<description>.+)$"
)
BREAKING_FOOTER_RE = re.compile(r"BREAKING[ -]CHANGE:\s*(.+)", re.IGNORECASE)


@dataclass
class Commit:
    hash: str
    subject: str
    body: str = ""


@dataclass
class ParsedCommit:
    hash: str
    type: str
    scope: str | None
    description: str
    breaking: bool
    breaking_description: str | None = field(default=None)


def parse_commit(commit: Commit) -> ParsedCommit:
    """Interpreta uma única mensagem de commit no padrão Conventional Commits.

    Commits que não seguem o padrão caem em type="other" com a descrição
    igual ao assunto (subject) inteiro, para nunca perder informação.
    """
    match = HEADER_RE.match(commit.subject.strip())

    breaking_footer_match = BREAKING_FOOTER_RE.search(commit.body or "")

    if not match:
        return ParsedCommit(
            hash=commit.hash,
            type="other",
            scope=None,
            description=commit.subject.strip(),
            breaking=bool(breaking_footer_match),
            breaking_description=breaking_footer_match.group(1).strip()
            if breaking_footer_match
            else None,
        )

    commit_type = match.group("type").lower()
    if commit_type not in SECTIONS:
        commit_type = "other"

    breaking = bool(match.group("breaking")) or bool(breaking_footer_match)
    breaking_description = None
    if breaking_footer_match:
        breaking_description = breaking_footer_match.group(1).strip()
    elif match.group("breaking"):
        breaking_description = match.group("description").strip()

    return ParsedCommit(
        hash=commit.hash,
        type=commit_type,
        scope=match.group("scope"),
        description=match.group("description").strip(),
        breaking=breaking,
        breaking_description=breaking_description,
    )


def group_commits(parsed_commits: list[ParsedCommit]) -> dict[str, list[ParsedCommit]]:
    """Agrupa commits já interpretados em seções do changelog, na ordem de exibição.

    Commits com breaking change aparecem tanto na seção de Breaking Changes
    quanto na sua seção normal, pois ambas as informações são relevantes.
    """
    groups: dict[str, list[ParsedCommit]] = {}

    breaking = [c for c in parsed_commits if c.breaking]
    if breaking:
        groups[BREAKING_SECTION] = breaking

    for commit_type, section_name in SECTIONS.items():
        matching = [c for c in parsed_commits if c.type == commit_type]
        if matching:
            groups.setdefault(section_name, []).extend(matching)

    other = [c for c in parsed_commits if c.type == "other"]
    if other:
        groups.setdefault(OTHER_SECTION, []).extend(other)

    return groups


def format_commit_line(commit: ParsedCommit) -> str:
    scope_part = f"**{commit.scope}**: " if commit.scope else ""
    short_hash = commit.hash[:7] if commit.hash else ""
    hash_part = f" (`{short_hash}`)" if short_hash else ""
    if commit.breaking and commit.breaking_description and commit.breaking_description != commit.description:
        return f"- {scope_part}{commit.description} — **BREAKING:** {commit.breaking_description}{hash_part}"
    return f"- {scope_part}{commit.description}{hash_part}"


def render_markdown(groups: dict[str, list[ParsedCommit]], title: str) -> str:
    lines = [f"## {title}", ""]

    if not groups:
        lines.append("_Nenhum commit encontrado no intervalo informado._")
        lines.append("")
        return "\n".join(lines)

    for section_name, commits in groups.items():
        lines.append(f"### {section_name}")
        lines.append("")
        for commit in commits:
            lines.append(format_commit_line(commit))
        lines.append("")

    return "\n".join(lines)


# Separadores improváveis de aparecer dentro de uma mensagem de commit real,
# usados para dividir com segurança a saída de `git log` em campos e registros.
_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"


def read_commits_from_git(repo: str, rev_range: str | None) -> list[Commit]:
    """Lê o histórico de commits de um repositório git via subprocess.

    Levanta RuntimeError com uma mensagem clara se o git falhar (repo inválido,
    range inexistente, repositório sem nenhum commit, etc).
    """
    pretty_format = f"%H{_FIELD_SEP}%s{_FIELD_SEP}%b{_RECORD_SEP}"
    cmd = ["git", "-C", repo, "log", f"--pretty=format:{pretty_format}"]
    if rev_range:
        cmd.append(rev_range)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git log falhou: {result.stderr.strip()}")

    raw = result.stdout.strip("\n")
    if not raw:
        return []

    commits = []
    for record in raw.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(_FIELD_SEP)
        commit_hash = parts[0] if len(parts) > 0 else ""
        subject = parts[1] if len(parts) > 1 else ""
        body = parts[2] if len(parts) > 2 else ""
        commits.append(Commit(hash=commit_hash, subject=subject, body=body))
    return commits


def generate_changelog(repo: str, rev_range: str | None, title: str) -> str:
    commits = read_commits_from_git(repo, rev_range)
    parsed = [parse_commit(c) for c in commits]
    groups = group_commits(parsed)
    return render_markdown(groups, title)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default=".", help="Caminho do repositório git (padrão: diretório atual)")
    parser.add_argument(
        "--range",
        dest="rev_range",
        default=None,
        help="Intervalo de revisões do git, ex: v1.0.0..HEAD (padrão: histórico completo)",
    )
    parser.add_argument("--title", default="Unreleased", help="Título da seção gerada (padrão: Unreleased)")
    parser.add_argument("--output", default=None, help="Arquivo de saída (padrão: stdout)")
    args = parser.parse_args(argv)

    try:
        markdown = generate_changelog(args.repo, args.rev_range, args.title)
    except RuntimeError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(markdown)
    else:
        print(markdown)

    return 0


if __name__ == "__main__":
    sys.exit(main())
