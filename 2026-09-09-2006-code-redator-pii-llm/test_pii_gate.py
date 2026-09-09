import json
import subprocess
import sys

import pytest

from pii_gate import (
    is_valid_cnpj,
    is_valid_cpf,
    is_valid_luhn,
    redact,
    restore,
)


# --- validadores de checksum ------------------------------------------------

def test_cpf_valido():
    assert is_valid_cpf("529.982.247-25")


def test_cpf_invalido():
    assert not is_valid_cpf("111.111.111-11")
    assert not is_valid_cpf("123.456.789-00")


def test_cnpj_valido():
    assert is_valid_cnpj("11.222.333/0001-81")


def test_cnpj_invalido():
    assert not is_valid_cnpj("00.000.000/0000-00")


def test_luhn_valido():
    assert is_valid_luhn("4111 1111 1111 1111")  # número de teste padrão Visa


def test_luhn_invalido():
    assert not is_valid_luhn("1234 5678 9012 3456")


# --- redact() ----------------------------------------------------------------

def test_redige_email():
    result = redact("Contato: joao.silva@empresa.com.br para dúvidas.")
    assert "joao.silva@empresa.com.br" not in result.text
    assert "[EMAIL_1]" in result.text
    assert result.mapping["[EMAIL_1]"] == "joao.silva@empresa.com.br"
    assert result.counts == {"EMAIL": 1}


def test_redige_cpf_formatado():
    result = redact("O CPF do cliente é 529.982.247-25.")
    assert "529.982.247-25" not in result.text
    assert "[CPF_1]" in result.text


def test_nao_redige_numero_aleatorio_como_cpf():
    # 11 dígitos, mas dígitos verificadores inválidos: não deve virar [CPF_x]
    result = redact("código de rastreio 123.456.789-00")
    assert "[CPF_1]" not in result.text


def test_redige_cnpj_formatado():
    result = redact("CNPJ 11.222.333/0001-81 está ativo.")
    assert "[CNPJ_1]" in result.text
    assert result.mapping["[CNPJ_1]"] == "11.222.333/0001-81"


def test_redige_telefone_br():
    result = redact("Me liga no (11) 91234-5678 depois do almoço.")
    assert "[TELEFONE_BR_1]" in result.text
    assert "91234-5678" not in result.text


def test_redige_cep():
    result = redact("Endereço: Rua das Flores, CEP 01310-100.")
    assert "[CEP_1]" in result.text


def test_redige_ip():
    result = redact("O servidor respondeu do IP 192.168.1.42 às 10h.")
    assert "[IP_1]" in result.text


def test_redige_token_api():
    text = "export OPENAI_API_KEY=sk-abcdefghijklmnopqrstuvwxyz123456"
    result = redact(text)
    assert "[TOKEN_API_1]" in result.text
    assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in result.text


def test_redige_cartao_credito():
    result = redact("Cartão: 4111 1111 1111 1111, favor cobrar.")
    assert "[CARTAO_CREDITO_1]" in result.text


def test_valores_repetidos_reusam_mesmo_placeholder():
    text = "Fale com ana@x.com. Confirmando: ana@x.com de novo."
    result = redact(text)
    assert result.text.count("[EMAIL_1]") == 2
    assert result.counts == {"EMAIL": 2}  # conta ocorrências, não valores únicos
    assert len(result.mapping) == 1  # mas só 1 placeholder distinto foi criado


def test_valores_diferentes_geram_placeholders_diferentes():
    text = "ana@x.com e bruno@y.com"
    result = redact(text)
    assert "[EMAIL_1]" in result.text
    assert "[EMAIL_2]" in result.text
    assert result.counts == {"EMAIL": 2}


def test_filtro_por_tipo():
    text = "Email ana@x.com, CPF 529.982.247-25."
    result = redact(text, entity_types={"EMAIL"})
    assert "[EMAIL_1]" in result.text
    assert "529.982.247-25" in result.text  # CPF não filtrado, permanece


def test_texto_sem_pii_fica_intacto():
    text = "Este texto não tem nenhuma informação sensível."
    result = redact(text)
    assert result.text == text
    assert result.counts == {}


# --- restore() -----------------------------------------------------------

def test_restore_reverte_redacao():
    original = "Contato joao@empresa.com, CPF 529.982.247-25."
    result = redact(original)
    assert restore(result.text, result.mapping) == original


def test_restore_com_muitos_placeholders_mesmo_tipo_nao_colide():
    text = "a@x.com b@x.com c@x.com d@x.com e@x.com f@x.com g@x.com h@x.com i@x.com j@x.com k@x.com"
    result = redact(text)
    assert restore(result.text, result.mapping) == text


# --- integração via CLI ---------------------------------------------------

def run_cli(*args, input_text=""):
    return subprocess.run(
        [sys.executable, "pii_gate.py", *args],
        input=input_text,
        capture_output=True,
        text=True,
        cwd=__file__.rsplit("/", 1)[0],
    )


def test_cli_redact_e_restore_ponta_a_ponta(tmp_path):
    map_file = tmp_path / "map.json"
    original = "Meu email é carla@teste.com e meu CPF é 529.982.247-25."

    redacted = run_cli("redact", "--map-file", str(map_file), input_text=original)
    assert redacted.returncode == 0
    assert "carla@teste.com" not in redacted.stdout
    assert map_file.exists()

    mapping = json.loads(map_file.read_text(encoding="utf-8"))
    assert any(v == "carla@teste.com" for v in mapping.values())

    restored = run_cli("restore", "--map-file", str(map_file), input_text=redacted.stdout)
    assert restored.returncode == 0
    assert restored.stdout.strip() == original


def test_cli_sem_map_file_avisa_que_e_irreversivel():
    result = run_cli("redact", input_text="fale com ana@x.com")
    assert result.returncode == 0
    assert "irrevers" in result.stderr.lower()
