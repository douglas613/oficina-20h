#!/usr/bin/env node
"use strict";

/**
 * Scanner ATS — compara um curriculo com uma descricao de vaga e produz um
 * relatorio de compatibilidade no mesmo espirito de ferramentas comerciais
 * como Jobscan/ResumeWorded, usando apenas o runtime padrao do Node.js
 * (nenhuma dependencia externa).
 */

const fs = require("node:fs");

// Lista curta de stopwords PT/EN — suficiente para não inflar o placar com
// artigos, preposições e conectivos, sem precisar de um pacote de NLP.
const STOPWORDS = new Set([
  "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "um",
  "uma", "para", "com", "por", "no", "na", "nos", "nas", "que", "se",
  "ao", "aos", "à", "às", "ou", "como", "mais", "menos", "muito", "sua",
  "seu", "suas", "seus", "foi", "ser", "estar", "ter", "tem", "são",
  "the", "an", "of", "in", "on", "for", "and", "or", "to", "with",
  "is", "are", "be", "as", "at", "by", "from", "this", "that", "will",
  "your", "you", "we", "our",
]);

// Permite pontuação interna (ex.: "node.js", "c#", "c++") mas nunca no final
// da palavra, evitando capturar o ponto final de uma frase junto do token.
const WORD_RE = /[a-zA-ZÀ-ÖØ-öø-ÿ][a-zA-ZÀ-ÖØ-öø-ÿ0-9+#]*(?:[.-][a-zA-ZÀ-ÖØ-öø-ÿ0-9+#]+)*/g;

const SECTION_ALIASES = {
  experiencia: ["experiencia", "experiência", "experience", "profissional"],
  educacao: ["educacao", "educação", "education", "formacao", "formação", "academica"],
  habilidades: ["habilidades", "skills", "competencias", "competências"],
};

const EMAIL_RE = /[\w.+-]+@[\w-]+\.[\w.-]+/;
const PHONE_RE = /(\+?\d[\d\s()-]{7,}\d)/;

function tokenize(text) {
  const words = text.match(WORD_RE) || [];
  return words
    .map((w) => w.toLowerCase())
    .filter((w) => w.length > 1 && !STOPWORDS.has(w));
}

function keywordFrequencies(text) {
  const freq = new Map();
  for (const word of tokenize(text)) {
    freq.set(word, (freq.get(word) || 0) + 1);
  }
  return freq;
}

/**
 * Score ponderado: soma a frequencia de cada palavra-chave da vaga que
 * aparece no curriculo, dividida pela soma total de frequencias da vaga.
 * Retorna um numero entre 0.0 e 100.0. Vaga sem palavras-chave -> 0.0.
 */
function computeMatchScore(resumeText, jobText) {
  const jobFreq = keywordFrequencies(jobText);
  if (jobFreq.size === 0) return 0.0;

  const resumeWords = new Set(tokenize(resumeText));
  let total = 0;
  let matched = 0;
  for (const [word, freq] of jobFreq) {
    total += freq;
    if (resumeWords.has(word)) matched += freq;
  }
  return Math.round((matched / total) * 1000) / 10;
}

/** Palavras-chave da vaga, ausentes no curriculo, ordenadas por frequencia. */
function missingKeywords(resumeText, jobText, topN = 10) {
  const jobFreq = keywordFrequencies(jobText);
  const resumeWords = new Set(tokenize(resumeText));
  const missing = [...jobFreq.entries()].filter(([word]) => !resumeWords.has(word));
  missing.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return missing.slice(0, topN).map(([word]) => word);
}

function hasSection(text, aliases) {
  const lowered = text.toLowerCase();
  return aliases.some((alias) => lowered.includes(alias));
}

/**
 * Sinaliza padroes conhecidos por atrapalhar parsers de ATS:
 * - ausencia de e-mail/telefone identificaveis
 * - secoes padrao (experiencia, educacao, habilidades) ausentes
 * - uso de colunas/tabelas (varios espacos/tabs seguidos numa linha)
 * - curriculo curto ou longo demais
 */
function detectFormattingIssues(resumeText) {
  const issues = [];
  const wordCount = tokenize(resumeText).length;

  if (!EMAIL_RE.test(resumeText)) {
    issues.push("Nenhum e-mail detectado — ATS pode falhar em extrair contato.");
  }
  if (!PHONE_RE.test(resumeText)) {
    issues.push("Nenhum telefone detectado — inclua um número de contato visível.");
  }

  for (const [section, aliases] of Object.entries(SECTION_ALIASES)) {
    if (!hasSection(resumeText, aliases)) {
      issues.push(`Seção '${section}' não encontrada (título padrão ajuda o parser).`);
    }
  }

  const columnedLines = resumeText
    .split("\n")
    .filter((line) => /\t| {3,}/.test(line.trim()));
  if (columnedLines.length >= 2) {
    issues.push(
      "Layout com múltiplas colunas/tabs detectado — muitos ATS leem tabelas " +
        "fora de ordem ou as ignoram."
    );
  }

  if (wordCount < 150) {
    issues.push("Currículo muito curto (<150 palavras relevantes) — pode faltar detalhe.");
  } else if (wordCount > 1200) {
    issues.push("Currículo muito longo (>1200 palavras relevantes) — considere resumir.");
  }

  return issues;
}

function generateReport(resumeText, jobText, topN = 10) {
  return {
    score_compatibilidade: computeMatchScore(resumeText, jobText),
    palavras_chave_faltando: missingKeywords(resumeText, jobText, topN),
    problemas_de_formatacao: detectFormattingIssues(resumeText),
  };
}

function formatReportText(report) {
  const lines = [];
  lines.push(`Score de compatibilidade ATS: ${report.score_compatibilidade}%`);
  lines.push("");
  if (report.palavras_chave_faltando.length > 0) {
    lines.push("Palavras-chave da vaga ausentes no currículo (mais frequentes primeiro):");
    for (const kw of report.palavras_chave_faltando) lines.push(`  - ${kw}`);
  } else {
    lines.push("Nenhuma palavra-chave relevante da vaga está faltando.");
  }
  lines.push("");
  if (report.problemas_de_formatacao.length > 0) {
    lines.push("Problemas de formatação encontrados:");
    for (const issue of report.problemas_de_formatacao) lines.push(`  - ${issue}`);
  } else {
    lines.push("Nenhum problema de formatação óbvio encontrado.");
  }
  return lines.join("\n");
}

function parseArgs(argv) {
  const args = { top: 10, json: false };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--resume") args.resume = argv[++i];
    else if (arg === "--job") args.job = argv[++i];
    else if (arg === "--top") args.top = parseInt(argv[++i], 10);
    else if (arg === "--json") args.json = true;
  }
  return args;
}

function main(argv) {
  const args = parseArgs(argv);
  if (!args.resume || !args.job) {
    console.error("Uso: node ats_scanner.js --resume <arquivo> --job <arquivo> [--top N] [--json]");
    return 1;
  }

  const resumeText = fs.readFileSync(args.resume, "utf-8");
  const jobText = fs.readFileSync(args.job, "utf-8");
  const report = generateReport(resumeText, jobText, args.top);

  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    console.log(formatReportText(report));
  }
  return 0;
}

if (require.main === module) {
  process.exitCode = main(process.argv.slice(2));
}

module.exports = {
  tokenize,
  keywordFrequencies,
  computeMatchScore,
  missingKeywords,
  detectFormattingIssues,
  generateReport,
  formatReportText,
};
