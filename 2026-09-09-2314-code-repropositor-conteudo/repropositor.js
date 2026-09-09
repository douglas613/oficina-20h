#!/usr/bin/env node
'use strict';
/**
 * Repropositor de Conteudo — transforma um texto longo (artigo, post de blog,
 * transcricao) em variantes prontas para redes sociais: thread no X/Twitter,
 * post no LinkedIn e legenda no Instagram. Usa apenas o runtime padrao do
 * Node.js (nenhuma dependencia externa), com sumarizacao extrativa por
 * frequencia de palavras (estilo Luhn).
 *
 * Uso:
 *   node repropositor.js --file artigo.txt
 *   cat artigo.txt | node repropositor.js
 *   node repropositor.js --file artigo.txt --json
 *   node repropositor.js --file artigo.txt --out-dir saida/
 */

const fs = require('fs');
const path = require('path');

const TWEET_LIMIT = 280;
const LINKEDIN_TOP_SENTENCES = 5;
const INSTAGRAM_TOP_SENTENCES = 3;
const MAX_HASHTAGS = 6;

// Stopwords minimas em PT e EN — suficientes para reduzir o ruido de
// conectivos comuns sem depender de uma lib de NLP externa.
const STOPWORDS = new Set(`
a o os as um uma uns umas de do da dos das em no na nos nas para por com sem
que qual quais quem este esta estes estas esse essa esses essas isso isto
aquele aquela aqueles aquelas e ou mas nao sim se ja mais menos muito pouco
como quando onde ao aos as pelo pela pelos pelas seu sua seus suas ele ela
eles elas voce voces nos eu tu lhe lhes foi sao ser estar tem ter vai vao
entre sobre depois antes ate desde durante apos the a an of in on at to for
and or but is are was were be been being have has had do does did will
would can could should this that these those it its as from with without
not no yes so than then there here what which who whom when where why how
`.trim().split(/\s+/));

const SENTENCE_SPLIT_RE = /(?<=[.!?])\s+(?=[A-ZÀ-Ú0-9"'])/;
const WORD_RE = /[A-Za-zÀ-ÿ]{3,}/g;

function splitSentences(text) {
  const normalized = text.replace(/\s+/g, ' ').trim();
  if (!normalized) return [];
  return normalized
    .split(SENTENCE_SPLIT_RE)
    .map((s) => s.trim())
    .filter(Boolean);
}

/**
 * Ranqueia sentencas por frequencia de palavras, com um bonus decrescente
 * por posicao — sentencas de abertura costumam carregar a tese do texto,
 * entao empatam menos com trechos de exemplo no meio do artigo.
 */
function scoreSentences(sentences) {
  const wordCounts = new Map();
  const tokenized = sentences.map((sentence) => {
    const words = (sentence.match(WORD_RE) || [])
      .map((w) => w.toLowerCase())
      .filter((w) => !STOPWORDS.has(w));
    for (const w of words) wordCounts.set(w, (wordCounts.get(w) || 0) + 1);
    return words;
  });

  const maxCount = Math.max(1, ...wordCounts.values());
  const n = Math.max(sentences.length, 1);
  const scores = tokenized.map((words, i) => {
    if (words.length === 0) return 0;
    const freqScore = words.reduce((sum, w) => sum + wordCounts.get(w) / maxCount, 0) / words.length;
    const positionBonus = 1 - (i / n) * 0.3;
    return freqScore * positionBonus;
  });

  const rankedIdx = sentences.map((_, i) => i).sort((a, b) => scores[b] - scores[a]);
  const rankedSentences = rankedIdx.map((i) => sentences[i]);
  const keywords = [...wordCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([w]) => w);

  return { rankedSentences, keywords };
}

function makeHashtags(keywords, limit = MAX_HASHTAGS) {
  const tags = [];
  const seen = new Set();
  for (const kw of keywords) {
    const tag = kw.replace(/[^A-Za-zÀ-ÿ0-9]/g, '').toLowerCase();
    if (tag.length < 4 || seen.has(tag)) continue;
    seen.add(tag);
    tags.push(`#${tag}`);
    if (tags.length >= limit) break;
  }
  return tags;
}

function analyze(text) {
  const sentences = splitSentences(text);
  const { rankedSentences, keywords } = scoreSentences(sentences);
  const hashtags = makeHashtags(keywords);
  return { sentences, rankedSentences, keywords, hashtags };
}

/** Quebra uma sentenca maior que o limite em pedacos por palavra inteira. */
function splitLongSentence(sentence, limit) {
  const words = sentence.split(' ');
  const chunks = [];
  let current = '';
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (candidate.length > limit) {
      if (current) chunks.push(current);
      current = word;
    } else {
      current = candidate;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

/**
 * Empacota sentencas em tweets numerados "(i/N)", respeitando o limite de
 * caracteres e evitando cortar uma sentenca no meio quando ela cabe inteira.
 */
function buildTwitterThread(sentences, limit = TWEET_LIMIT) {
  if (!sentences.length) return [];
  const suffixRoom = limit - 8; // reserva espaco para " (99/99)"

  const rawChunks = [];
  for (const sentence of sentences) {
    if (sentence.length <= suffixRoom) {
      rawChunks.push(sentence);
    } else {
      rawChunks.push(...splitLongSentence(sentence, suffixRoom));
    }
  }

  const tweets = [];
  let current = '';
  for (const chunk of rawChunks) {
    const candidate = current ? `${current} ${chunk}` : chunk;
    if (candidate.length <= suffixRoom) {
      current = candidate;
    } else {
      if (current) tweets.push(current);
      current = chunk;
    }
  }
  if (current) tweets.push(current);

  const total = tweets.length;
  return tweets.map((tweet, i) => `${tweet} (${i + 1}/${total})`);
}

function buildLinkedInPost(analysisResult) {
  const { sentences, rankedSentences, hashtags } = analysisResult;
  if (!sentences.length) return '';
  const [hook, ...rest] = rankedSentences;
  const body = rest.slice(0, LINKEDIN_TOP_SENTENCES - 1);
  const lines = [hook, ''];
  for (const s of body) lines.push(`→ ${s}`);
  lines.push('', 'O que voce acha? Comenta aqui embaixo.');
  if (hashtags.length) lines.push('', hashtags.slice(0, 5).join(' '));
  return lines.join('\n');
}

function buildInstagramCaption(analysisResult) {
  const { sentences, rankedSentences, hashtags } = analysisResult;
  if (!sentences.length) return '';
  const [hook, ...rest] = rankedSentences;
  const bullets = rest.slice(0, INSTAGRAM_TOP_SENTENCES);
  const lines = [`${hook} ✨`, ''];
  for (const b of bullets) lines.push(`• ${b}`);
  lines.push('', 'Salva esse post pra nao perder 🔖');
  if (hashtags.length) lines.push('', hashtags.join(' '));
  return lines.join('\n');
}

function repurpose(text) {
  const result = analyze(text);
  return {
    // a thread segue a ordem original do texto (narrativa), diferente do
    // linkedin/instagram que usam as sentencas ranqueadas por relevancia
    twitterThread: buildTwitterThread(result.sentences),
    linkedinPost: buildLinkedInPost(result),
    instagramCaption: buildInstagramCaption(result),
    keywords: result.keywords.slice(0, 10),
    hashtags: result.hashtags,
  };
}

function parseArgs(argv) {
  const args = { file: null, json: false, outDir: null };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--file' || arg === '-f') args.file = argv[++i];
    else if (arg === '--json') args.json = true;
    else if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--help' || arg === '-h') args.help = true;
  }
  return args;
}

function readInput(args) {
  if (args.file) return fs.readFileSync(args.file, 'utf8');
  return fs.readFileSync(0, 'utf8');
}

function main(argv) {
  const args = parseArgs(argv);
  if (args.help) {
    console.log(
      'Uso: node repropositor.js [--file artigo.txt] [--json] [--out-dir saida/]\n' +
        'Sem --file, le o texto do stdin.'
    );
    return 0;
  }

  let text;
  try {
    text = readInput(args);
  } catch (err) {
    console.error(`Erro ao ler entrada: ${err.message}`);
    return 1;
  }

  if (!text || !text.trim()) {
    console.error('Erro: nenhum texto de entrada fornecido.');
    return 1;
  }

  const result = repurpose(text);

  if (args.outDir) {
    fs.mkdirSync(args.outDir, { recursive: true });
    fs.writeFileSync(path.join(args.outDir, 'twitter.txt'), result.twitterThread.join('\n\n'));
    fs.writeFileSync(path.join(args.outDir, 'linkedin.txt'), result.linkedinPost);
    fs.writeFileSync(path.join(args.outDir, 'instagram.txt'), result.instagramCaption);
    console.log(`Arquivos escritos em ${args.outDir}/`);
    return 0;
  }

  if (args.json) {
    console.log(JSON.stringify(result, null, 2));
    return 0;
  }

  console.log('=== THREAD X/TWITTER ===');
  for (const tweet of result.twitterThread) {
    console.log(tweet);
    console.log();
  }
  console.log('=== POST LINKEDIN ===');
  console.log(result.linkedinPost);
  console.log();
  console.log('=== LEGENDA INSTAGRAM ===');
  console.log(result.instagramCaption);
  return 0;
}

module.exports = {
  splitSentences,
  scoreSentences,
  makeHashtags,
  analyze,
  buildTwitterThread,
  buildLinkedInPost,
  buildInstagramCaption,
  repurpose,
};

if (require.main === module) {
  process.exitCode = main(process.argv.slice(2));
}
