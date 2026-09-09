'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {
  splitSentences,
  scoreSentences,
  makeHashtags,
  buildTwitterThread,
  repurpose,
} = require('../repropositor');

const ARTICLE =
  'Freelancers que vendem por hora costumam perder dinheiro sem perceber. ' +
  'O motivo e simples: elas nunca calculam o custo fixo mensal antes de definir o preco. ' +
  'Um freelancer que ignora impostos e taxas de plataforma acaba trabalhando de graca em alguns meses. ' +
  'Para corrigir isso, basta somar custo fixo, horas faturaveis e margem de lucro desejada. ' +
  'Essa conta simples muda completamente a forma como voce negocia contratos novos. ' +
  'No fim, precificar bem e a diferenca entre sobreviver e crescer como autonomo.';

test('splitSentences separa por pontuacao', () => {
  const sentences = splitSentences(ARTICLE);
  assert.equal(sentences.length, 6);
  assert.ok(sentences[0].startsWith('Freelancers'));
});

test('splitSentences com texto vazio retorna lista vazia', () => {
  assert.deepEqual(splitSentences('   '), []);
});

test('scoreSentences preserva todas as sentencas e extrai keywords', () => {
  const sentences = splitSentences(ARTICLE);
  const { rankedSentences, keywords } = scoreSentences(sentences);
  assert.deepEqual([...rankedSentences].sort(), [...sentences].sort());
  assert.ok(keywords.length > 0);
  assert.ok(keywords.some((k) => k.startsWith('freelancer')));
});

test('buildTwitterThread respeita o limite de 280 caracteres por tweet', () => {
  const sentences = splitSentences(ARTICLE);
  const thread = buildTwitterThread(sentences, 280);
  assert.ok(thread.length > 0);
  for (const tweet of thread) assert.ok(tweet.length <= 280);
});

test('buildTwitterThread numera os tweets sequencialmente', () => {
  const sentences = splitSentences(ARTICLE);
  const thread = buildTwitterThread(sentences, 280);
  const total = thread.length;
  thread.forEach((tweet, i) => {
    assert.ok(tweet.endsWith(`(${i + 1}/${total})`));
  });
});

test('buildTwitterThread quebra sentenca maior que o limite', () => {
  const longSentence = 'palavra '.repeat(60).trim();
  const thread = buildTwitterThread([longSentence], 100);
  for (const tweet of thread) assert.ok(tweet.length <= 100);
  assert.ok(thread.length > 1);
});

test('buildTwitterThread com entrada vazia retorna lista vazia', () => {
  assert.deepEqual(buildTwitterThread([]), []);
});

test('makeHashtags deduplica e respeita o limite', () => {
  const keywords = ['preco', 'preco', 'cliente', 'abc', 'contrato', 'freelancer', 'negocio', 'receita'];
  const tags = makeHashtags(keywords, 3);
  assert.equal(tags.length, 3);
  assert.equal(new Set(tags).size, 3);
  for (const tag of tags) assert.ok(tag.startsWith('#'));
});

test('makeHashtags ignora palavras muito curtas', () => {
  const tags = makeHashtags(['ok', 'abc', 'precificacao']);
  assert.ok(!tags.includes('#abc'));
});

test('repurpose produz as tres secoes', () => {
  const result = repurpose(ARTICLE);
  assert.ok(result.twitterThread.length > 0);
  assert.ok(result.linkedinPost.includes('Comenta'));
  assert.ok(result.instagramCaption.includes('Salva esse post'));
});

test('repurpose com texto vazio produz secoes vazias', () => {
  const result = repurpose('');
  assert.deepEqual(result.twitterThread, []);
  assert.equal(result.linkedinPost, '');
  assert.equal(result.instagramCaption, '');
});
