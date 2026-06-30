/* =============================================================
   Aulas fictícias do Kernel — uma por placa do globo.
   ============================================================= */

export const LESSONS = [
  { title: "Bloco 01 — Introdução ao Python", discipline: "Python" },
  { title: "Bloco 02 — Estruturas de Controle", discipline: "Python" },
  { title: "Bloco 03 — Funções", discipline: "Python" },
  { title: "Bloco 04 — Listas e Tuplas", discipline: "Python" },
  { title: "Bloco 05 — Dicionários", discipline: "Python" },
  { title: "Bloco 06 — Arquivos e Exceções", discipline: "Python" },
  { title: "Bloco 07 — Módulos e Pacotes", discipline: "Python" },
  { title: "Try/Except na Prática", discipline: "Python" },
  { title: "Compreensões e Iteradores", discipline: "Python" },
  { title: "Modelo Entidade-Relacionamento", discipline: "Banco de Dados" },
  { title: "Normalização até 3FN", discipline: "Banco de Dados" },
  { title: "Chaves Primárias e Estrangeiras", discipline: "Banco de Dados" },
  { title: "Índices e Performance", discipline: "Banco de Dados" },
  { title: "Transações e ACID", discipline: "Banco de Dados" },
  { title: "Diagramas ER Avançados", discipline: "Banco de Dados" },
  { title: "SELECT e Projeção", discipline: "SQL" },
  { title: "JOINs Internos e Externos", discipline: "SQL" },
  { title: "GROUP BY e HAVING", discipline: "SQL" },
  { title: "Subconsultas Correlacionadas", discipline: "SQL" },
  { title: "Agregações Analíticas", discipline: "SQL" },
  { title: "Views e CTEs", discipline: "SQL" },
  { title: "Fundamentos de Visualização", discipline: "Visualização" },
  { title: "Gráficos de Barras e Linhas", discipline: "Visualização" },
  { title: "Dashboards com Matplotlib", discipline: "Visualização" },
  { title: "Storytelling com Dados", discipline: "Visualização" },
  { title: "Visualização SQL no Notebook", discipline: "Visualização" },
  { title: "Planejamento de Carreira", discipline: "Carreira" },
  { title: "Portfólio Técnico", discipline: "Carreira" },
  { title: "Entrevistas e Soft Skills", discipline: "Carreira" },
  { title: "Networking Profissional", discipline: "Carreira" },
  { title: "Trilhas de Especialização", discipline: "Carreira" },
  { title: "Fundamentos de PPD", discipline: "PPD" },
  { title: "Projeto Integrador — Escopo", discipline: "PPD" },
  { title: "Entrega e Apresentação", discipline: "PPD" },
  { title: "Trabalho em Equipe", discipline: "PPD" },
  { title: "Método Científico Aplicado", discipline: "Metodologia" },
  { title: "Revisão Bibliográfica", discipline: "Metodologia" },
  { title: "Documentação de Projeto", discipline: "Metodologia" },
  { title: "Pesquisa com Fontes Confiáveis", discipline: "Metodologia" },
  { title: "Requisitos Funcionais", discipline: "Engenharia de Software" },
  { title: "Arquitetura em Camadas", discipline: "Engenharia de Software" },
  { title: "Testes Unitários", discipline: "Engenharia de Software" },
  { title: "Padrões de Projeto", discipline: "Engenharia de Software" },
  { title: "APIs REST Introdução", discipline: "Engenharia de Software" },
  { title: "O que é Inteligência Artificial", discipline: "Fluência IA" },
  { title: "Machine Learning vs Deep Learning", discipline: "Fluência IA" },
  { title: "Prompts e Contexto", discipline: "Fluência IA" },
  { title: "Ética e Viés em IA", discipline: "Fluência IA" },
  { title: "Ferramentas de Produtividade com IA", discipline: "Fluência IA" },
  { title: "Pandas — DataFrames", discipline: "Python" },
  { title: "Window Functions", discipline: "SQL" },
  { title: "Heatmaps e Correlação", discipline: "Visualização" },
  { title: "Currículo e LinkedIn", discipline: "Carreira" },
  { title: "UML e Casos de Uso", discipline: "Engenharia de Software" },
  { title: "Modelagem Dimensional", discipline: "Banco de Dados" },
  { title: "Mini-projeto — Kickoff", discipline: "PPD" },
];

/**
 * Distribui aulas pelas placas evitando disciplinas iguais em vizinhas.
 * @param {Array<{ lat: number, lon: number, lesson?: object }>} faces
 * @param {number} latCount
 * @param {number} lonCount
 */
export function assignLessonsToFaces(faces, latCount, lonCount) {
  const grid = Array.from({ length: latCount }, () => Array(lonCount).fill(null));

  let cursor = 0;

  for (let i = 0; i < latCount; i++) {
    for (let j = 0; j < lonCount; j++) {
      const neighborDiscs = new Set();
      if (i > 0 && grid[i - 1][j]) neighborDiscs.add(grid[i - 1][j].discipline);
      if (j > 0 && grid[i][j - 1]) neighborDiscs.add(grid[i][j - 1].discipline);
      if (i > 0 && j > 0 && grid[i - 1][j - 1]) neighborDiscs.add(grid[i - 1][j - 1].discipline);
      if (i > 0 && j < lonCount - 1 && grid[i - 1][j + 1]) {
        neighborDiscs.add(grid[i - 1][j + 1].discipline);
      }

      let picked = null;
      for (let k = 0; k < LESSONS.length; k++) {
        const candidate = LESSONS[(cursor + k) % LESSONS.length];
        if (!neighborDiscs.has(candidate.discipline)) {
          picked = candidate;
          cursor = (cursor + k + 1) % LESSONS.length;
          break;
        }
      }
      if (!picked) {
        picked = LESSONS[cursor % LESSONS.length];
        cursor = (cursor + 1) % LESSONS.length;
      }

      grid[i][j] = picked;
      const face = faces.find((f) => f.lat === i && f.lon === j);
      if (face) face.lesson = picked;
    }
  }
}
