#!/usr/bin/env node
/**
 * Smoke E2E — PERGUNTAS-SMOKE-POR-DISCIPLINA.md (70 perguntas)
 * Browser automation (Playwright). Saída em results/smoke-disciplinas-<timestamp>/
 */
import { createRequire } from "node:module";
import { mkdir, writeFile, appendFile, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const PW_ROOT =
  process.env.PLAYWRIGHT_MODULE_ROOT ||
  "/home/gaab/.npm/_npx/9833c18b2d85bc59/node_modules/playwright";
const { chromium } = require(PW_ROOT);

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const BASE_URL = process.env.SMOKE_BASE_URL || "http://127.0.0.1:8001";
const QUESTION_TIMEOUT_MS = Number(process.env.SMOKE_QUESTION_TIMEOUT_MS || 120_000);
const HEADLESS = process.env.SMOKE_HEADLESS !== "0";

const DISCIPLINES = [
  {
    id: "fluencia-ia",
    command: "/fluencia-ia",
    questions: [
      "/fluencia-ia Qual a diferença entre IA determinística, machine learning, deep learning e IA generativa?",
      "/fluencia-ia O que são tokens e embeddings e por que importam em LLMs?",
      "/fluencia-ia Como a temperatura do modelo afeta a criatividade da resposta?",
      "/fluencia-ia Quais riscos de direitos autorais e plágio ao usar IA generativa na faculdade?",
      "/fluencia-ia Como agentes de IA usam ferramentas e RAG para decidir quando buscar contexto?",
      "O que significa ter fluência em IA e por que validar o output antes de usar?",
      "Como montar um prompt com persona, objetivo e critérios de qualidade?",
      "O que é decomposição de tarefas e auditoria em técnicas avançadas de prompt?",
      "Como usar prompts estruturados para resumos de aula no NotebookLM?",
      "Por que verificação crítica e checagem de fontes são centrais no ecossistema de IAs generativas?",
    ],
  },
  {
    id: "python-processamento-dados",
    command: "/python-processamento-dados",
    questions: [
      "/python-processamento-dados Qual a diferença entre try, except, else e finally em pipelines de dados?",
      "/python-processamento-dados Como serializar e ler objetos Python em arquivos JSON?",
      "/python-processamento-dados Como fazer requisição HTTP GET e POST com a biblioteca requests?",
      "/python-processamento-dados Como expor uma rota simples em Flask para integrar com um LLM?",
      "/python-processamento-dados Para que serve pass em exceções e quando usar pdb para depurar?",
      "Como tokenizar e fatiar textos no pré-processamento de strings?",
      "Como usar list comprehension para contar e transformar tokens em uma coleção?",
      "Qual a diferença entre lista mutável e tupla imutável para registros fixos?",
      "Como abrir arquivos em disco com `with open` e qual encoding usar para CSV?",
      "Como usar conjuntos (set) para comparar vocabulários de dois textos?",
    ],
  },
  {
    id: "sql-modelagem-relacional",
    command: "/sql-modelagem-relacional",
    questions: [
      "/sql-modelagem-relacional O que é cardinalidade 1:1, 1:N e N:N em um DER?",
      "/sql-modelagem-relacional Explique primeira, segunda e terceira formas normais com exemplo de livraria.",
      "/sql-modelagem-relacional Como modelar reservas, ocupação e serviços em um sistema de hotel?",
      "/sql-modelagem-relacional Como ligar tabelas com INNER JOIN e LEFT JOIN no caso do hotel?",
      "/sql-modelagem-relacional Como usar GROUP BY e HAVING para análise temporal de ocupação?",
      "Qual a diferença entre modelo conceitual, lógico e físico na modelagem relacional?",
      "Como desenhar um DER com chave primária e estrangeira no BRModelo?",
      "Como normalizar uma planilha desnormalizada até o MER entidade-relacionamento?",
      "Como corrigir dados sujos com UPDATE e diagnosticar qualidade no SQLiteStudio?",
      "Quando usar ALTER TABLE e como fazer backup antes de excluir dados?",
    ],
  },
  {
    id: "python",
    command: "/python",
    questions: [
      "/python Como declarar variáveis e seguir snake_case no estilo Python?",
      "/python Qual a diferença entre aspas simples, duplas e strings multilinha?",
      "/python Como usar f-strings para interpolar variáveis em uma mensagem?",
      "/python Como escolher entre if, elif e else em uma regra de desconto?",
      "/python Como usar for com range e enumerate em uma tabuada?",
      "Por que Python é indicado para quem está começando em programação?",
      "O que é um algoritmo e como o Jupyter Notebook ajuda no pensamento computacional?",
      "Como converter texto em número com `int()` sem gerar ValueError?",
      "Como fazer slice em uma string para pegar os três primeiros caracteres?",
      "Como usar operadores lógicos `and` e `or` em uma condição composta?",
    ],
  },
  {
    id: "visualizacao-sql",
    command: "/visualizacao-sql",
    questions: [
      "/visualizacao-sql Como conectar um CSV ao Looker Studio e montar a primeira visualização?",
      "/visualizacao-sql Como criar gráfico de pizza e barras para tipos de transação bancária?",
      "/visualizacao-sql Qual a diferença entre WHERE e HAVING em uma agregação com GROUP BY?",
      "/visualizacao-sql Como criar tabela e inserir linhas no SQLiteStudio?",
      "/visualizacao-sql Como ordenar relatório de vendas com ORDER BY em mais de uma coluna?",
      "Como integrar Google Planilhas com Looker para relatório de conta corrente?",
      "Quais métricas e dimensões usar no dashboard da cafeteria Herman?",
      "O que são tipos de dados SQL e por que importam no CREATE TABLE?",
      "Como filtrar clientes por UF com WHERE e operadores de comparação?",
      "Como comparar vendas entre anos no mesmo dashboard Looker?",
    ],
  },
  {
    id: "projeto-bloco",
    command: "/projeto-bloco",
    questions: [
      "/projeto-bloco Qual a diferença entre metodologia tradicional em cascata e ágil em projeto de dados?",
      "/projeto-bloco Como ingerir CSV e Excel com pandas e gravar no SQLite?",
      "/projeto-bloco Como implementar CRUD em PostgreSQL a partir de Python?",
      "/projeto-bloco Como evoluir do MER ao SQLite no projeto e-commerce do bloco?",
      "/projeto-bloco O que documentar na POC de persistência antes do AT?",
      "Quais são as etapas do Projeto de Bloco na formação em dados?",
      "Como montar um laboratório local com Python, Jupyter e banco relacional?",
      "Como escolher entre PostgreSQL, MySQL e SQL Server no pipeline de dados?",
      "Qual a diferença entre perfil engenheiro de dados e cientista de dados?",
      "Como usar placeholders em INSERT para evitar concatenação insegura de SQL?",
    ],
  },
  {
    id: "planejamento-curso-carreira",
    command: "/planejamento-curso-carreira",
    questions: [
      "/planejamento-curso-carreira Como estruturar currículo para passar em ATS em vagas de tecnologia?",
      "/planejamento-curso-carreira Como aplicar análise SWOT no plano de carreira?",
      "/planejamento-curso-carreira Como otimizar título e resumo do LinkedIn para recrutadores?",
      "/planejamento-curso-carreira O que avaliar em entrevista por competências com rubrica comportamental?",
      "/planejamento-curso-carreira Como funcionam blocos, estágio e atividades complementares na graduação?",
      "Como organizar roteiro de apresentação do AT antes de montar os slides?",
      "Quais técnicas de respiração e ensaio reduzem medo de falar em público?",
      "Como dar feedback objetivo em apresentações entre pares?",
      "Como reconhecer privilégio e gatilhos emocionais em equipes diversas?",
      "Por que proatividade e hábitos de estudo impactam empregabilidade em dados?",
    ],
  },
];

function ts() {
  return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
}

async function preparePage(page) {
  await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 60_000 });
  await page.evaluate(() => {
    try {
      localStorage.setItem("kernel_onboarding_dismissed_v1", "1");
    } catch (_) {}
    document.querySelectorAll(".entrance-init-hidden").forEach((el) => {
      el.classList.remove("entrance-init-hidden");
    });
    const ob = document.getElementById("onboarding-banner");
    if (ob) ob.remove();
  });
  await page.waitForTimeout(4000);
  await waitForOnline(page);
}

async function waitForOnline(page, timeoutMs = 90_000) {
  await page.waitForFunction(
    () => {
      const send = document.getElementById("send-button");
      const input = document.getElementById("message-input");
      return send && !send.disabled && input;
    },
    { timeout: timeoutMs },
  );
}

async function newConversation(page) {
  await waitForOnline(page).catch(() => {});
  const newChat = page.locator("#sidebar-new-chat");
  if (await newChat.isVisible().catch(() => false)) {
    await newChat.click();
  } else {
    const input = page.locator("#message-input");
    await input.fill("/reset");
    await input.dispatchEvent("input");
    await page.locator("#send-button").click();
  }
  await waitForOnline(page, 120_000);
  await page.waitForTimeout(500);
}

async function askQuestion(page, question, index, disciplineId) {
  const started = Date.now();
  const consoleErrors = [];
  const pageErrors = [];
  const networkLog = [];

  const onConsole = (msg) => {
    if (msg.type() === "error") consoleErrors.push(msg.text());
  };
  const onPageError = (err) => pageErrors.push(String(err));
  const onResponse = (res) => {
    const url = res.url();
    if (url.includes("/chat") || res.status() >= 400) {
      networkLog.push({ url, status: res.status(), method: res.request().method() });
    }
  };

  page.on("console", onConsole);
  page.on("pageerror", onPageError);
  page.on("response", onResponse);

  await newConversation(page);

  const input = page.locator("#message-input");
  await input.fill(question);
  await input.dispatchEvent("input");
  await page.waitForTimeout(200);

  const feBeforeSend = await page.evaluate(() => ({
    sendReady: Boolean(document.getElementById("send-button") && !document.getElementById("send-button")?.disabled),
    activeDiscipline: document.querySelector(".silo-pill__name")?.textContent?.trim() || null,
    siloPillVisible: document.getElementById("silo-pill")?.hidden === false,
    scopeItems: document.querySelectorAll("#scope-menu-list .scope-option").length,
    sendDisabled: document.getElementById("send-button")?.disabled,
  }));

  await page.locator("#send-button").click();

  let ok = false;
  let error = null;
  let botText = "";
  let sources = [];
  let feAfter = {};

  try {
    await page.waitForSelector(".message-row.user", { timeout: 15_000 });
    await page.waitForSelector(".thinking-indicator, .message-row.bot", { timeout: 10_000 }).catch(() => {});
    await page.waitForFunction(
      () => {
        const bots = document.querySelectorAll(".message-row.bot .message");
        const last = bots[bots.length - 1];
        return last && !last.classList.contains("cursor-blink") && (last.textContent || "").length > 20;
      },
      { timeout: QUESTION_TIMEOUT_MS },
    );

    feAfter = await page.evaluate(() => {
      const botRow = [...document.querySelectorAll(".message-row.bot")].pop();
      const cards = botRow ? [...botRow.querySelectorAll(".source-card__title")].map((el) => el.textContent?.trim()) : [];
      const sourceMeta = botRow
        ? [...botRow.querySelectorAll(".source-card")].map((card) => ({
            title: card.querySelector(".source-card__title")?.textContent?.trim(),
            excerpt: !!card.querySelector(".source-card__excerpt"),
            pin: !!card.querySelector(".source-card__action--primary"),
          }))
        : [];
      return {
        userText: document.querySelector(".message-row.user .message")?.textContent?.trim(),
        botLen: botRow?.querySelector(".message")?.textContent?.length || 0,
        botPreview: (botRow?.querySelector(".message")?.textContent || "").slice(0, 400),
        botFull: botRow?.querySelector(".message")?.textContent || "",
        richSources: botRow?.querySelectorAll(".source-card--rich").length || 0,
        sourcesHeading: botRow?.querySelector(".message-sources__heading")?.textContent?.trim() || null,
        sourceMeta,
        pinVisible: document.getElementById("context-pin-badge")?.hidden === false,
        thinkingSeen: !!document.querySelector(".thinking-indicator"),
      };
    });

    botText = feAfter.botFull || feAfter.botPreview || "";
    sources = feAfter.sourceMeta || [];
    ok = feAfter.botLen > 20;
  } catch (e) {
    error = String(e.message || e);
    feAfter = await page.evaluate(() => ({
      userText: document.querySelector(".message-row.user .message")?.textContent?.trim(),
      botLen: [...document.querySelectorAll(".message-row.bot .message")].pop()?.textContent?.length || 0,
    }));
  }

  page.off("console", onConsole);
  page.off("pageerror", onPageError);
  page.off("response", onResponse);

  const hasCommand = question.trimStart().startsWith("/");
  const expectedDiscipline = hasCommand ? disciplineId : null;

  return {
    index,
    disciplineId,
    question,
    ok,
    error,
    elapsedMs: Date.now() - started,
    hasCommand,
    expectedDiscipline,
    frontend: {
      beforeSend: feBeforeSend,
      after: feAfter,
      consoleErrors,
      pageErrors,
      networkLog,
      checks: {
        sendReady: feBeforeSend.sendReady,
        userMessageMatch: feAfter.userText === question,
        gotBotReply: (feAfter.botLen || 0) > 20,
        scopeMenuPopulated: feBeforeSend.scopeItems >= 7,
        siloPillWhenCommand: !hasCommand || feBeforeSend.siloPillVisible,
        hasSources: (feAfter.richSources || 0) > 0 || (sources.length || 0) > 0,
      },
    },
    responsePreview: botText.slice(0, 500),
    responseLength: botText.length,
    sources,
  };
}

async function main() {
  const runId = ts();
  const outDir = path.join(ROOT, "results", `smoke-disciplinas-${runId}`);
  await mkdir(outDir, { recursive: true });

  const meta = {
    runId,
    startedAt: new Date().toISOString(),
    baseUrl: BASE_URL,
    questionTimeoutMs: QUESTION_TIMEOUT_MS,
    totalQuestions: DISCIPLINES.reduce((n, d) => n + d.questions.length, 0),
  };
  await writeFile(path.join(outDir, "meta.json"), JSON.stringify(meta, null, 2));

  const logPath = path.join(outDir, "run.log");
  const log = async (line) => {
    const row = `[${new Date().toISOString()}] ${line}\n`;
    await appendFile(logPath, row);
    process.stdout.write(row);
  };

  await log(`Início smoke — ${meta.totalQuestions} perguntas → ${outDir}`);

  const browser = await chromium.launch({ headless: HEADLESS });
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(QUESTION_TIMEOUT_MS);

  await preparePage(page);
  const allResults = [];

  for (const disc of DISCIPLINES) {
    const discResults = [];
    await log(`\n=== ${disc.id} (${disc.questions.length} perguntas) ===`);

    for (let i = 0; i < disc.questions.length; i++) {
      const q = disc.questions[i];
      await log(`Q${i + 1}/10 [${disc.id}]: ${q.slice(0, 72)}…`);
      const result = await askQuestion(page, q, i + 1, disc.id);
      discResults.push(result);
      allResults.push({ ...result, discipline: disc.id, command: disc.command });

      const status = result.ok ? "OK" : "FAIL";
      await log(`  → ${status} (${result.elapsedMs}ms, bot=${result.responseLength} chars, sources=${result.sources?.length || 0})`);
      if (result.error) await log(`  → erro: ${result.error}`);
      if (result.frontend.consoleErrors.length) await log(`  → console: ${result.frontend.consoleErrors.join(" | ")}`);

      await writeFile(
        path.join(outDir, `${disc.id}__q${String(i + 1).padStart(2, "0")}.json`),
        JSON.stringify(result, null, 2),
      );
    }

    await writeFile(path.join(outDir, `${disc.id}.json`), JSON.stringify(discResults, null, 2));
  }

  await browser.close();

  const passed = allResults.filter((r) => r.ok).length;
  const failed = allResults.length - passed;
  const summary = {
    ...meta,
    finishedAt: new Date().toISOString(),
    passed,
    failed,
    passRate: `${((passed / allResults.length) * 100).toFixed(1)}%`,
    frontendIssues: allResults.filter(
      (r) =>
        r.frontend.consoleErrors.length ||
        r.frontend.pageErrors.length ||
        !r.frontend.checks.sendReady ||
        !r.frontend.checks.gotBotReply,
    ).length,
    byDiscipline: DISCIPLINES.map((d) => {
      const rows = allResults.filter((r) => r.disciplineId === d.id);
      return {
        id: d.id,
        passed: rows.filter((r) => r.ok).length,
        failed: rows.filter((r) => !r.ok).length,
        avgMs: Math.round(rows.reduce((s, r) => s + r.elapsedMs, 0) / rows.length),
      };
    }),
  };

  await writeFile(path.join(outDir, "summary.json"), JSON.stringify(summary, null, 2));
  await writeFile(path.join(outDir, "all-results.json"), JSON.stringify(allResults, null, 2));

  const md = [
    `# Smoke disciplinas — ${runId}`,
    "",
    `- **URL:** ${BASE_URL}`,
    `- **Total:** ${allResults.length} | **OK:** ${passed} | **FAIL:** ${failed} | **Taxa:** ${summary.passRate}`,
    `- **Frontend com issues:** ${summary.frontendIssues}`,
    "",
    "## Por disciplina",
    "",
    "| Disciplina | OK | FAIL | média ms |",
    "|------------|-----|------|----------|",
    ...summary.byDiscipline.map((d) => `| ${d.id} | ${d.passed} | ${d.failed} | ${d.avgMs} |`),
    "",
    "## Falhas",
    "",
    ...allResults
      .filter((r) => !r.ok)
      .map((r) => `- **${r.disciplineId} Q${r.index}:** ${r.question.slice(0, 80)}… — ${r.error || "resposta curta"}`),
    "",
  ].join("\n");
  await writeFile(path.join(outDir, "REPORT.md"), md);

  // snapshot server terminal if exists
  const termLog = "/home/gaab/.cursor/projects/home-gaab-Documentos-gitHub-KernelBot/terminals/372308.txt";
  if (existsSync(termLog)) {
    const tail = (await readFile(termLog, "utf8")).split("\n").slice(-500).join("\n");
    await writeFile(path.join(outDir, "server-log-tail.txt"), tail);
  }

  await log(`\nConcluído: ${passed}/${allResults.length} OK → ${outDir}`);
  process.exit(failed > 0 ? 1 : 0);
}

main().catch(async (e) => {
  console.error(e);
  process.exit(2);
});
