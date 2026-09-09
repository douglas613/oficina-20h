#!/usr/bin/env python3
"""
pii_gate.py — gateway de privacidade para prompts de LLM.

Detecta e redige informação pessoal identificável (PII) em texto ANTES de
esse texto ser enviado a uma API de LLM de terceiros (OpenAI, Anthropic,
etc), e permite restaurar os valores originais depois, a partir de um mapa
guardado localmente (nunca enviado para lugar nenhum).

Só usa a biblioteca padrão do Python — nenhuma dependência externa.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Optional


# --------------------------------------------------------------------------
# Validadores (reduzem falsos positivos em sequências puramente numéricas)
# --------------------------------------------------------------------------

def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def is_valid_cpf(value: str) -> bool:
    d = _only_digits(value)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for pos in (9, 10):
        total = sum(int(d[i]) * (pos + 1 - i) for i in range(pos))
        check = (total * 10) % 11
        if check == 10:
            check = 0
        if check != int(d[pos]):
            return False
    return True


def is_valid_cnpj(value: str) -> bool:
    d = _only_digits(value)
    if len(d) != 14 or d == d[0] * 14:
        return False
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    weights2 = [6] + weights1
    for pos, weights in ((12, weights1), (13, weights2)):
        total = sum(int(d[i]) * weights[i] for i in range(pos))
        check = 11 - (total % 11)
        check = 0 if check >= 10 else check
        if check != int(d[pos]):
            return False
    return True


def is_valid_luhn(value: str) -> bool:
    """Algoritmo de Luhn — usado por número de cartão de crédito."""
    d = _only_digits(value)
    if len(d) < 12 or len(d) > 19:
        return False
    total = 0
    for i, ch in enumerate(reversed(d)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


# --------------------------------------------------------------------------
# Definição das entidades detectadas
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class EntityRule:
    name: str
    pattern: "re.Pattern[str]"
    validator: Optional[Callable[[str], bool]] = None


RULES: list[EntityRule] = [
    EntityRule(
        "EMAIL",
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    ),
    EntityRule(
        "CNPJ",
        re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|\b\d{14}\b"),
        is_valid_cnpj,
    ),
    EntityRule(
        "CPF",
        re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b"),
        is_valid_cpf,
    ),
    EntityRule(
        "CEP",
        re.compile(r"\b\d{5}-\d{3}\b"),
    ),
    EntityRule(
        "CARTAO_CREDITO",
        re.compile(r"\b(?:\d[ -]?){13,19}\b"),
        is_valid_luhn,
    ),
    EntityRule(
        "TELEFONE_BR",
        re.compile(
            r"(?:\+55\s?)?\(?\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}\b"
        ),
    ),
    EntityRule(
        "IP",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
        ),
    ),
    EntityRule(
        "TOKEN_API",
        re.compile(
            r"\bsk-[A-Za-z0-9]{20,}\b"
            r"|\bghp_[A-Za-z0-9]{30,}\b"
            r"|\bAKIA[0-9A-Z]{12,}\b"
            r"|\bxox[baprs]-[A-Za-z0-9-]{10,}\b"
        ),
    ),
]


@dataclass
class RedactionResult:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)  # placeholder -> original
    counts: dict[str, int] = field(default_factory=dict)


def _find_matches(text: str, entity_types: Optional[set[str]]) -> list[tuple[int, int, str, str]]:
    """Retorna [(start, end, tipo, valor)] de todas as regras aplicáveis."""
    matches: list[tuple[int, int, str, str]] = []
    for rule in RULES:
        if entity_types is not None and rule.name not in entity_types:
            continue
        for m in rule.pattern.finditer(text):
            value = m.group(0)
            if rule.validator is not None and not rule.validator(value):
                continue
            matches.append((m.start(), m.end(), rule.name, value))
    return matches


def _resolve_overlaps(matches: list[tuple[int, int, str, str]]) -> list[tuple[int, int, str, str]]:
    """Resolve sobreposições: começa mais cedo primeiro, empate por match mais longo."""
    ordered = sorted(matches, key=lambda m: (m[0], -(m[1] - m[0])))
    resolved: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, name, value in ordered:
        if start >= last_end:
            resolved.append((start, end, name, value))
            last_end = end
    return resolved


def redact(
    text: str,
    entity_types: Optional[set[str]] = None,
    seed_mapping: Optional[dict[str, str]] = None,
) -> RedactionResult:
    """Substitui PII no texto por placeholders como [EMAIL_1].

    `seed_mapping` (placeholder -> valor original) permite reaproveitar
    numeração de uma chamada anterior, útil ao redigir um prompt em partes.
    """
    matches = _resolve_overlaps(_find_matches(text, entity_types))

    value_to_placeholder: dict[str, str] = {}
    mapping: dict[str, str] = dict(seed_mapping or {})
    counters: dict[str, int] = {}
    for placeholder, original in mapping.items():
        base = placeholder.strip("[]").rsplit("_", 1)[0]
        counters[base] = max(counters.get(base, 0), int(placeholder.strip("[]").rsplit("_", 1)[1]))
        value_to_placeholder[original] = placeholder

    counts: dict[str, int] = {}
    out_parts: list[str] = []
    cursor = 0
    for start, end, name, value in matches:
        out_parts.append(text[cursor:start])
        if value in value_to_placeholder:
            placeholder = value_to_placeholder[value]
        else:
            counters[name] = counters.get(name, 0) + 1
            placeholder = f"[{name}_{counters[name]}]"
            value_to_placeholder[value] = placeholder
            mapping[placeholder] = value
        out_parts.append(placeholder)
        counts[name] = counts.get(name, 0) + 1
        cursor = end
    out_parts.append(text[cursor:])

    return RedactionResult(text="".join(out_parts), mapping=mapping, counts=counts)


def restore(text: str, mapping: dict[str, str]) -> str:
    """Substitui de volta os placeholders pelos valores originais."""
    # Ordena por tamanho decrescente do placeholder para evitar substituições
    # parciais acidentais (ex: [CPF_1] dentro de [CPF_10]).
    for placeholder in sorted(mapping, key=len, reverse=True):
        text = text.replace(placeholder, mapping[placeholder])
    return text


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _read_input(args: argparse.Namespace) -> str:
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            return f.read()
    return sys.stdin.read()


def _cmd_redact(args: argparse.Namespace) -> int:
    text = _read_input(args)
    entity_types = set(args.types.split(",")) if args.types else None

    seed_mapping = None
    if args.map_file and args.append:
        try:
            with open(args.map_file, "r", encoding="utf-8") as f:
                seed_mapping = json.load(f)
        except FileNotFoundError:
            seed_mapping = None

    result = redact(text, entity_types=entity_types, seed_mapping=seed_mapping)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result.text)
    else:
        print(result.text)

    if args.map_file:
        with open(args.map_file, "w", encoding="utf-8") as f:
            json.dump(result.mapping, f, ensure_ascii=False, indent=2)

    total = sum(result.counts.values())
    detail = ", ".join(f"{k}={v}" for k, v in sorted(result.counts.items()))
    print(f"[pii-gate] {total} ocorrência(s) redigida(s)" + (f" ({detail})" if detail else ""), file=sys.stderr)
    if args.map_file:
        print(f"[pii-gate] mapa de restauração salvo em: {args.map_file}", file=sys.stderr)
    elif total:
        print("[pii-gate] aviso: nenhum --map-file informado — esta redação é irreversível", file=sys.stderr)
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    text = _read_input(args)
    with open(args.map_file, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    restored = restore(text, mapping)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(restored)
    else:
        print(restored)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pii_gate.py",
        description="Redige PII de um texto antes de mandar para uma LLM, e restaura depois.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_redact = sub.add_parser("redact", help="redige PII do texto de entrada")
    p_redact.add_argument("-i", "--input", help="arquivo de entrada (padrão: stdin)")
    p_redact.add_argument("-o", "--output", help="arquivo de saída (padrão: stdout)")
    p_redact.add_argument("-m", "--map-file", help="onde salvar o mapa placeholder -> valor original")
    p_redact.add_argument(
        "--append", action="store_true",
        help="reaproveita numeração de um --map-file já existente, se houver",
    )
    p_redact.add_argument(
        "-t", "--types",
        help="lista separada por vírgula de tipos a detectar (padrão: todos). "
             "Ex: EMAIL,CPF,TELEFONE_BR",
    )
    p_redact.set_defaults(func=_cmd_redact)

    p_restore = sub.add_parser("restore", help="restaura os valores originais a partir de um mapa")
    p_restore.add_argument("-i", "--input", help="arquivo de entrada (padrão: stdin)")
    p_restore.add_argument("-o", "--output", help="arquivo de saída (padrão: stdout)")
    p_restore.add_argument("-m", "--map-file", required=True, help="arquivo de mapa gerado por 'redact'")
    p_restore.set_defaults(func=_cmd_restore)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
