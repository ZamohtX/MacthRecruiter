/**
 * Percorre o fluxo completo no navegador e captura cada tela.
 *
 * Não é a suíte de testes — é a verificação de que o frontend conversa com a
 * API de verdade e de que o layout não quebra: monta um time de exploradores,
 * aplica o diagnóstico, abre a vaga e compara um candidato complementar com um
 * espelho do time.
 *
 * Uso: node scripts/e2e-demo.mjs [baseUrl]
 */
import { mkdir } from "node:fs/promises";
import { chromium } from "playwright";

const BASE = process.argv[2] ?? "http://localhost:5173";
const API = `${BASE}/api/v1`;
const SHOTS = "screenshots";

// Preferências de traço que definem cada persona. A escolha em cada cenário é a
// conduta mais alinhada, com um leve rodízio entre fatores para que o
// respondente simulado não seja perfeitamente consistente.
const TRAITS = [
  "Abertura à Experiência",
  "Conscienciosidade",
  "Extroversão",
  "Amabilidade",
  "Estabilidade Emocional",
];

const EXPLORER = {
  "Abertura à Experiência": 1.4,
  Conscienciosidade: 0.5,
  Extroversão: 0.2,
  Amabilidade: 0.1,
  "Estabilidade Emocional": 0.2,
};

const CONNECTOR = {
  Amabilidade: 1.4,
  Extroversão: 1.0,
  "Estabilidade Emocional": 0.8,
  Conscienciosidade: 0.4,
  "Abertura à Experiência": 0.1,
};

/** Cargas por texto de alternativa — a API não as expõe, e é assim de propósito. */
let LOADINGS = null;

async function loadKey() {
  const { readFile } = await import("node:fs/promises");
  const source = await readFile("../backend/app/core/big_five.py", "utf8");
  const map = new Map();
  const optionRe = /SJTOption\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*\{([^}]*)\}/gs;
  for (const match of source.matchAll(optionRe)) {
    const text = match[1].replace(/\\"/g, '"');
    const loads = {};
    for (const pair of match[2].matchAll(/_([OCEAN]):\s*([\d.]+)/g)) {
      const trait = { O: TRAITS[0], C: TRAITS[1], E: TRAITS[2], A: TRAITS[3], N: TRAITS[4] }[pair[1]];
      loads[trait] = Number(pair[2]);
    }
    map.set(text, loads);
  }
  LOADINGS = map;
  if (map.size === 0) throw new Error("Não consegui ler a chave de correção do instrumento.");
}

function pickOption(question, pref, index) {
  const boosted = TRAITS[index % TRAITS.length];
  let best = question.options[0];
  let bestScore = -Infinity;
  for (const option of question.options) {
    const loads = LOADINGS.get(option.text) ?? {};
    let score = 0;
    for (const [trait, weight] of Object.entries(loads)) {
      score += ((pref[trait] ?? 0) + (trait === boosted ? 0.35 : 0)) * weight;
    }
    if (score > bestScore) {
      bestScore = score;
      best = option;
    }
  }
  return best.id;
}

async function call(path, { token, method = "GET", body } = {}) {
  const response = await fetch(`${API}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`${method} ${path} → ${response.status} ${await response.text()}`);
  return response.json();
}

const login = (suffix, extra = {}) =>
  call("/auth/google", { method: "POST", body: { id_token: `mock_google_token_${suffix}`, ...extra } });

async function answer(token, questionnaireId, pref) {
  const questionnaire = await call(`/questionnaires/${questionnaireId}`, { token });
  const answers = questionnaire.questions.map((question, index) => ({
    question_id: question.id,
    selected_option_id: pickOption(question, pref, index),
  }));
  return call(`/questionnaires/${questionnaireId}/answers`, { method: "POST", token, body: { answers } });
}

async function seedScenario() {
  const stamp = Date.now().toString(36);
  const boss = await login(`chefe${stamp}`);
  const team = await call("/teams", { method: "POST", token: boss.access_token, body: { name: "Squad Explorador" } });
  const questionnaire = await call("/questionnaires/default", { token: boss.access_token });
  const invite = await call(`/teams/${team.id}/invites`, { method: "POST", token: boss.access_token });

  // O recrutador é responsável, não integrante: não responde o teste e não
  // entra na média. Todos os respondentes do diagnóstico entram por convite.
  let member = null;
  for (const suffix of ["m1", "m2", "m3", "m4"]) {
    member = await login(`${suffix}${stamp}`, { invite_token: invite.invite_token });
    await answer(member.access_token, questionnaire.id, EXPLORER);
  }

  const job = await call("/jobs", {
    method: "POST",
    token: boss.access_token,
    body: { title: "Pessoa Desenvolvedora Backend Pleno", team_id: team.id },
  });

  for (const [suffix, pref] of [
    [`conector${stamp}`, CONNECTOR],
    [`espelho${stamp}`, EXPLORER],
  ]) {
    const candidate = await login(suffix, { job_id: job.id });
    await answer(candidate.access_token, questionnaire.id, pref);
  }

  // Time recém-criado, para conferir o estado vazio agora que quem cria não
  // entra como integrante.
  const emptyTeam = await call("/teams", {
    method: "POST",
    token: boss.access_token,
    body: { name: "Squad Recém-Criado" },
  });

  const ranking = await call(`/jobs/${job.id}/candidates`, { token: boss.access_token });

  // Integrante que ainda não respondeu nada: é com ele que a mecânica de jogo
  // (trilha, feedback, checkpoint) pode ser percorrida na interface.
  const rookie = await login(`novato${stamp}`, { invite_token: invite.invite_token });

  return { boss, member, rookie, team, job, ranking, emptyTeam };
}

async function main() {
  await mkdir(SHOTS, { recursive: true });
  await loadKey();

  console.log("→ montando o cenário via API…");
  const { boss, member, rookie, team, job, ranking, emptyTeam } = await seedScenario();
  console.log(`  time=${team.id}`);
  console.log(`  vaga=${job.id}`);
  for (const candidate of ranking) {
    console.log(
      `  ${candidate.candidate_name}: fit=${candidate.fit_score} suplementar=${candidate.supplementary_fit_index} ${candidate.verdict}`,
    );
  }

  const browser = await chromium.launch();
  const failures = [];

  for (const theme of ["light", "dark"]) {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 1000 },
      deviceScaleFactor: 2,
      colorScheme: theme,
      locale: "pt-BR",
    });
    const page = await context.newPage();

    page.on("console", (message) => {
      if (message.type() === "error") failures.push(`[console ${theme}] ${message.text()}`);
    });
    page.on("pageerror", (error) => failures.push(`[pageerror ${theme}] ${error.message}`));

    // Injeta a sessão do recrutador antes do primeiro render.
    await page.addInitScript(
      ([token, mode]) => {
        localStorage.setItem("matchrecruiter.token", token);
        localStorage.setItem("matchrecruiter.theme", mode);
      },
      [boss.access_token, theme],
    );

    const shots = [
      ["01-times", "/"],
      ["02-time-diagnostico", `/times/${team.id}`],
      ["03-vaga-ranking", `/vagas/${job.id}`],
      ["04-simulacao", `/vagas/${job.id}/candidatos/${ranking[0].candidate_id}`],
      ["06-time-vazio", `/times/${emptyTeam.id}`],
    ];

    for (const [name, path] of shots) {
      await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
      await page.waitForTimeout(400);
      await page.screenshot({ path: `${SHOTS}/${name}-${theme}.png`, fullPage: true });
      console.log(`  ✓ ${name}-${theme}.png`);
    }

    await context.close();
  }

  // Tela do teste: sessão de um integrante. O recrutador não responde o
  // diagnóstico, então capturá-la com a sessão dele mostraria algo inexistente.
  const memberContext = await browser.newContext({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 2 });
  const memberPage = await memberContext.newPage();
  memberPage.on("pageerror", (error) => failures.push(`[pageerror integrante] ${error.message}`));
  await memberPage.addInitScript((token) => localStorage.setItem("matchrecruiter.token", token), member.access_token);
  await memberPage.goto(`${BASE}/meu-teste`, { waitUntil: "networkidle" });
  await memberPage.waitForTimeout(500);
  await memberPage.screenshot({ path: `${SHOTS}/05-teste-integrante.png`, fullPage: true });
  console.log("  ✓ 05-teste-integrante.png");
  await memberContext.close();

  // Primeiro nível respondido pela interface.
  //
  // O resto deste script responde o teste pela API, que é rápido mas passa ao
  // largo da camada de jogo. Trilha de níveis, confirmação de escolha e
  // checkpoint só existem na tela — sem clicar, ninguém verifica que funcionam.
  const gameContext = await browser.newContext({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 2 });
  const gamePage = await gameContext.newPage();
  gamePage.on("console", (message) => {
    if (message.type() === "error") failures.push(`[console jogo] ${message.text()}`);
  });
  gamePage.on("pageerror", (error) => failures.push(`[pageerror jogo] ${error.message}`));
  await gamePage.addInitScript((token) => localStorage.setItem("matchrecruiter.token", token), rookie.access_token);
  await gamePage.goto(`${BASE}/meu-teste`, { waitUntil: "networkidle" });

  const LEVEL_SIZE = 5;
  for (let scenario = 1; scenario <= LEVEL_SIZE; scenario += 1) {
    await gamePage.waitForSelector(`text=${scenario} de 20`, { timeout: 15_000 });
    if (scenario === 1) {
      await gamePage.screenshot({ path: `${SHOTS}/08-teste-nivel-1.png`, fullPage: true });
    }
    // `click` e não `check`: o avanço automático troca o cenário logo depois de
    // salvar, e `check` falharia ao reconferir o estado de um campo que já saiu
    // da tela. O clique espera o campo ficar habilitado, que é o que importa —
    // durante o salvamento o fieldset inteiro fica desabilitado.
    await gamePage.locator('fieldset input[type="radio"]').first().click();
  }

  // Fechar o quinto cenário tem que abrir o checkpoint, não o sexto cenário.
  await gamePage.waitForSelector("text=Nível 1 concluído", { timeout: 15_000 });
  await gamePage.screenshot({ path: `${SHOTS}/09-checkpoint.png`, fullPage: true });
  console.log("  ✓ 08-teste-nivel-1.png / 09-checkpoint.png");

  await gamePage.getByRole("button", { name: "Continuar" }).click();
  // Continuar precisa cair no primeiro cenário em aberto do bloco seguinte.
  await gamePage.waitForSelector("text=Nível 2 de 4", { timeout: 15_000 });
  await gamePage.waitForSelector("text=6 de 20", { timeout: 15_000 });
  console.log("  ✓ checkpoint → nível 2 no cenário 6");
  await gameContext.close();

  // Tela do candidato: sessão própria, sem os privilégios do recrutador.
  const candidateContext = await browser.newContext({ viewport: { width: 1280, height: 1000 }, deviceScaleFactor: 2 });
  const candidatePage = await candidateContext.newPage();
  candidatePage.on("pageerror", (error) => failures.push(`[pageerror candidato] ${error.message}`));
  await candidatePage.goto(`${BASE}/login?vaga=${job.id}&next=/vaga/${job.id}`, { waitUntil: "networkidle" });
  await candidatePage.screenshot({ path: `${SHOTS}/06-login-candidato.png`, fullPage: true });
  await candidatePage.fill("#suffix", `novocandidato${Date.now().toString(36)}`);
  await candidatePage.click('button[type="submit"]');
  await candidatePage.waitForURL(/\/vaga\//, { timeout: 15_000 });
  await candidatePage.waitForTimeout(1200);
  await candidatePage.screenshot({ path: `${SHOTS}/07-candidato-teste.png`, fullPage: true });
  console.log("  ✓ 06-login-candidato.png / 07-candidato-teste.png");
  await candidateContext.close();

  await browser.close();

  if (failures.length > 0) {
    console.error("\nErros no navegador:");
    for (const failure of failures) console.error(`  ${failure}`);
    process.exit(1);
  }
  console.log("\nFluxo completo percorrido sem erro de console.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
