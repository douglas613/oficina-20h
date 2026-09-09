"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");

const {
  tokenize,
  computeMatchScore,
  missingKeywords,
  detectFormattingIssues,
} = require("./ats_scanner");

const JOB_TEXT = `
Vaga: Desenvolvedor Python Backend
Requisitos: experiência com Python, Django, PostgreSQL e Docker.
Diferencial: conhecimento em AWS e Kubernetes.
`;

const GOOD_RESUME = `
João da Silva
joao.silva@example.com
(11) 98765-4321

Experiência
Desenvolvedor Python há 4 anos, trabalhando com Django e PostgreSQL
em produção. Também usei Docker para empacotar os serviços.

Educação
Bacharelado em Ciência da Computação.

Habilidades
Python, Django, PostgreSQL, Docker, Git.
`;

const BAD_RESUME_NO_CONTACT_NO_SECTIONS =
  "Trabalhei em várias empresas fazendo coisas com computadores e sistemas.";

test("tokenize remove stopwords e coloca em minusculas", () => {
  const tokens = tokenize("O Desenvolvedor trabalha COM Python e Django");
  assert.ok(tokens.includes("desenvolvedor"));
  assert.ok(tokens.includes("python"));
  assert.ok(tokens.includes("django"));
  assert.ok(!tokens.includes("o"));
  assert.ok(!tokens.includes("com"));
  assert.ok(!tokens.includes("e"));
});

test("texto identico gera score de 100", () => {
  assert.equal(computeMatchScore(JOB_TEXT, JOB_TEXT), 100.0);
});

test("texto nao relacionado gera score baixo", () => {
  const score = computeMatchScore("Gato Cachorro Passarinho Jardim Flor", JOB_TEXT);
  assert.ok(score < 20.0, `esperado < 20, obtido ${score}`);
});

test("match parcial fica entre 0 e 100", () => {
  const score = computeMatchScore(GOOD_RESUME, JOB_TEXT);
  assert.ok(score > 0.0);
  assert.ok(score <= 100.0);
});

test("vaga vazia retorna score zero", () => {
  assert.equal(computeMatchScore(GOOD_RESUME, ""), 0.0);
});

test("encontra palavra-chave ausente no curriculo", () => {
  const missing = missingKeywords(GOOD_RESUME, JOB_TEXT, 20);
  assert.ok(missing.includes("kubernetes"));
  assert.ok(missing.includes("aws"));
});

test("palavra-chave presente nao aparece como faltando", () => {
  const missing = missingKeywords(GOOD_RESUME, JOB_TEXT, 20);
  assert.ok(!missing.includes("python"));
  assert.ok(!missing.includes("django"));
});

test("respeita o limite top_n", () => {
  const missing = missingKeywords("", JOB_TEXT, 2);
  assert.ok(missing.length <= 2);
});

test("sinaliza contato e secoes ausentes", () => {
  const issues = detectFormattingIssues(BAD_RESUME_NO_CONTACT_NO_SECTIONS);
  const joined = issues.join(" ").toLowerCase();
  assert.ok(joined.includes("e-mail"));
  assert.ok(joined.includes("telefone"));
  assert.ok(issues.some((i) => /experi[eê]ncia/i.test(i)));
});

test("curriculo bom nao aponta contato ausente", () => {
  const issues = detectFormattingIssues(GOOD_RESUME);
  const joined = issues.join(" ").toLowerCase();
  assert.ok(!joined.includes("nenhum e-mail"));
  assert.ok(!joined.includes("nenhum telefone"));
});

test("detecta layout em colunas", () => {
  const columned = "Nome\t\tCargo\nJoão\t\tDev\nMaria\t\tQA\n";
  const issues = detectFormattingIssues(columned);
  assert.ok(issues.some((i) => i.toLowerCase().includes("colunas")));
});

test("sinaliza curriculo muito curto", () => {
  const issues = detectFormattingIssues("Curto demais.");
  assert.ok(issues.some((i) => i.toLowerCase().includes("curto")));
});
