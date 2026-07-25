# MatchRecruiter — Documento de Visão de Negócio

> **Contratar por lacuna, não por semelhança.**
> Plataforma de recrutamento e seleção gamificada que usa IA para encontrar o candidato que melhor **complementa** o time existente.

| Campo | Valor |
|---|---|
| Versão do documento | 1.0 |
| Data | 25/07/2026 |
| Público | Investidores, stakeholders e time fundador |
| Status | Pré-desenvolvimento — visão para validação |

**Nota sobre o nome:** o repositório está grafado como "MacthRecruiter". Assume-se que se trata de erro de digitação e adota-se **MatchRecruiter** neste documento. Decisão de naming definitivo pendente (ver §12).

**Nota sobre dados:** todo número de mercado citado está marcado com sua origem. Onde não há fonte verificada, o item aparece como **[PREMISSA]** e precisa ser validado antes de ir para um deck de investimento. Nenhum dado foi inventado para preencher lacuna.

---

## 1. Sumário Executivo

**O problema.** Processos seletivos hoje otimizam a variável errada. Recrutadores buscam o "melhor currículo" — um ótimo local isolado — quando o que determina performance é o desempenho do **time**. O resultado é a homogeneização: times criativos contratam mais criativos, times analíticos contratam mais analíticos, e a lacuna comportamental que trava a entrega nunca é preenchida. Simultaneamente, o funil é caro: triagem manual de centenas de currículos, sinal comportamental capturado tarde (só na entrevista) e de forma não estruturada, e um custo alto de erro de contratação.

**A solução.** MatchRecruiter inverte a lógica do matching. Antes de abrir a vaga, a empresa aplica um diagnóstico comportamental **no time que já existe**. O sistema mapeia forças e lacunas em um framework de ~10 soft skills e gera automaticamente o perfil-alvo do candidato — onde as competências **ausentes no time** viram os critérios de maior peso da vaga. A partir daí, um funil de 7 etapas combina análise de evidências reais (currículo + GitHub + LinkedIn), score de compatibilidade com corte automático, um game de soft skills no estilo Duolingo que ranqueia candidatos, micro-resumos gerados por IA para decisão rápida do recrutador, e análise de entrevista por IA que realimenta o ranking final.

**Por que agora.** Convergência de três fatores: (a) LLMs tornaram viável extrair sinal estruturado de fontes não estruturadas (currículo, repositórios, transcrição de entrevista) a custo marginal baixo; (b) a pressão regulatória (LGPD Art. 20, EU AI Act, NYC Local Law 144) está eliminando as caixas-pretas de recrutamento e favorecendo quem nasce auditável; (c) escassez estrutural de talento técnico no Brasil torna o custo do erro de contratação cada vez menos tolerável.

**Diferencial defensável.** Nenhum player relevante no Brasil faz matching **time-cêntrico**. Gupy, Sólides e Taqe fazem matching candidato↔vaga. Pymetrics/Harver, no exterior, fazem matching por games neurocientíficos mas contra um perfil de alto desempenho **individual**. O ativo proprietário do MatchRecruiter é o **grafo de composição de times**: quanto mais diagnósticos e mais outcomes pós-contratação a base acumula, melhor o modelo prevê qual lacuna, quando preenchida, gera ganho real de performance. Esse é um efeito de dados que concorrente não copia com feature.

**Modelo de negócio.** Recomendação: **SaaS por assinatura com wedge de produto (PLG)** — o Diagnóstico de Time gratuito/barato como porta de entrada, monetização no módulo de vagas. Alternativas avaliadas: pay-per-vaga e success fee (§7).

**Pedido / próximo passo.** MVP enxuto validando a hipótese central — *o perfil-alvo gerado por lacuna produz contratações mensuravelmente melhores do que o perfil-alvo tradicional* — com 5 a 10 empresas-piloto e medição de retenção e performance a 6 meses.

---

## 2. O Problema

### 2.1 A dor estrutural: o recrutamento otimiza o indivíduo, não o time

O processo seletivo padrão avalia cada candidato contra uma *job description* estática, geralmente redigida a partir de: (i) a descrição de quem saiu da vaga, ou (ii) o "perfil ideal" imaginado pelo gestor. Nenhuma das duas fontes olha para a **composição atual do time**.

Consequências diretas:

| Sintoma | Mecanismo | Efeito no negócio |
|---|---|---|
| **Homogeneização do time** | Gestores tendem a aprovar candidatos parecidos consigo (afinidade cognitiva/similaridade) | Times com pontos cegos coletivos; redundância de força e persistência de lacuna |
| **"Bom currículo, má contratação"** | Hard skill é filtrada com rigor; soft skill é avaliada tarde e por impressão | Rotatividade precoce e retrabalho de contratação |
| **Job description genérica** | Requisitos copiados, sem ponderação por necessidade real | Funil ruidoso, alto volume de candidatos irrelevantes |
| **Sinal comportamental tardio** | Só aparece na entrevista, sem estrutura e sem comparabilidade entre candidatos | Decisão baseada em memória e simpatia; difícil de auditar |

### 2.2 A dor operacional: o funil é caro e lento

- **Triagem manual não escala.** Vagas de tecnologia com alta atratividade recebem volume de candidaturas incompatível com análise humana individual. O recrutador é forçado a heurísticas rasas (palavra-chave, nome de empresa anterior, faculdade) — que são justamente as mais enviesadas.
- **Entrevistas não estruturadas têm baixo poder preditivo.** A literatura de psicologia organizacional é consistente: entrevistas **estruturadas** preveem desempenho substancialmente melhor que entrevistas livres. A prática de mercado, porém, continua majoritariamente livre. *(Consenso da literatura de seleção de pessoal — Schmidt & Hunter e revisões posteriores. Referência exata a levantar antes de uso público.)*
- **Custo de erro de contratação.** É recorrentemente citado no mercado de RH que uma contratação equivocada custa de vários múltiplos do salário mensal do cargo, somando rescisão, tempo de rampa perdido, nova busca e impacto na produtividade do time. **[PREMISSA — a citar apenas com fonte primária verificada. Números que circulam em blogs de RH variam de 3x a 15x e não devem ir para deck sem checagem.]**

### 2.3 Contexto de mercado brasileiro

| Item | Situação | Fonte / status |
|---|---|---|
| Escassez de talento em TI no Brasil | Demanda projetada de profissionais de tecnologia significativamente superior à formação anual | Brasscom publica estudos recorrentes sobre esse gap — **verificar edição e números atuais antes de citar** |
| Alta rotatividade | Brasil historicamente apresenta taxa de rotatividade elevada frente a economias comparáveis | Base: dados de CAGED/Novo CAGED — **[PREMISSA: obter recorte por setor de tecnologia]** |
| Adoção de ATS com IA | Mercado brasileiro já educado — Gupy tornou "IA no recrutamento" categoria conhecida por RHs | Observação de mercado; sem dado quantitativo |
| Pressão regulatória | LGPD Art. 20 garante revisão de decisões automatizadas; EU AI Act classifica sistemas de recrutamento como **alto risco**; NYC Local Law 144 exige auditoria anual de viés em ferramentas automatizadas de decisão de emprego | Legislação pública verificável |

**Leitura estratégica:** o mercado já aceita IA no recrutamento (a categoria foi educada). O que ninguém resolveu é *qual pergunta a IA deveria estar respondendo*. Hoje ela responde "quem é o melhor candidato?". Deveria responder "**de quem este time precisa?**".

---

## 3. Solução e Proposta de Valor Única

### 3.1 A tese em uma frase

> Contratação de alta performance não é a soma de indivíduos de alta performance — é a **composição** certa. MatchRecruiter é a primeira plataforma que trata a vaga como uma **função da lacuna do time**, e não como um retrato do candidato ideal.

### 3.2 Proposta de valor por stakeholder

| Stakeholder | Valor entregue | Dor que substitui |
|---|---|---|
| **RH / Recrutador** | Perfil-alvo gerado automaticamente, funil pré-triado, micro-resumo por candidato antes de abrir currículo | Horas de triagem manual; briefing vago do gestor |
| **Gestor da área** | Evidência objetiva de qual competência falta no seu time; ranking comparável entre finalistas | "Achismo" na definição de vaga; entrevistas incomparáveis entre si |
| **Candidato** | Processo curto, gamificado e transparente; avaliação por competência, não por pedigree de currículo | Candidatura em buraco negro; eliminação por filtro de palavra-chave |
| **C-level / board** | Times balanceados por design, com métrica de composição rastreável ao longo do tempo | Gestão de pessoas sem instrumentação |

### 3.3 Os quatro pilares do produto

1. **Diagnóstico antes da vaga.** Nenhum concorrente relevante exige o mapeamento do time como pré-condição da abertura de vaga. Isso é fricção — e é exatamente onde nasce a defensabilidade.
2. **Evidência sobre declaração.** Currículo é auto-relato. GitHub é comportamento observado (frequência, colaboração, revisão de código, consistência). Cruzar as três fontes (CV + GitHub + LinkedIn) detecta inconsistência e ancora o score em evidência.
3. **Gamificação como instrumento de medida, não como enfeite.** O game estilo Duolingo não existe para "engajar" — existe porque situações-problema aplicadas medem soft skill melhor que autoavaliação em escala Likert, e porque geram um ranking comparável entre candidatos.
4. **Loop fechado com a entrevista.** A análise de IA da entrevista **realimenta o score**, o que transforma cada processo em dado de treino para o modelo de matching.

---

## 4. Público-Alvo e Personas

### 4.1 Segmentação de mercado

| Segmento | Perfil | Fit com o produto | Prioridade |
|---|---|---|---|
| **ICP inicial** | Empresas de tecnologia, 50–500 funcionários, com time de RH estruturado e squads formados | Alto — times pequenos e definidos, lacunas visíveis, cultura receptiva a produto | **1ª** |
| Scale-ups / startups Série A+ | 20–200 pessoas, contratando rápido | Alto volume, mas RH pequeno e pouco processo | 2ª |
| Consultorias de RH e RPO | Recrutam para terceiros | Canal de distribuição potencial (revenda) | 2ª |
| Grandes corporações | 1.000+ funcionários | Ticket alto, mas ciclo de venda longo, compliance pesado, integração com SAP/Workday | 3ª |
| PMEs não-tech | <50 pessoas | Baixa maturidade de RH; exigência de GitHub inviabiliza | Fora de escopo inicial |

**[PREMISSA]** O ICP inicial é de empresas de tecnologia porque o fluxo exige GitHub obrigatório. Isso limita o TAM e precisa ser validado: ou a exigência de GitHub vira opcional/por-tipo-de-vaga, ou o produto assume nicho tech (ver §12, Decisão 2).

### 4.2 Personas

---

**Persona 1 — Camila, Analista de R&S Sênior (usuária primária)**

| | |
|---|---|
| **Contexto** | RH de scale-up de tecnologia, ~180 funcionários. Conduz 8–15 processos simultâneos. |
| **Objetivo** | Fechar vagas rápido, sem entregar candidato que o gestor rejeita na primeira entrevista. |
| **Dores** | Recebe 300+ currículos por vaga; briefing do gestor é vago ("quero alguém proativo"); é cobrada por time-to-hire mas culpada por quality-of-hire. |
| **O que a faz adotar** | Redução drástica do tempo de triagem + argumento objetivo para defender a shortlist perante o gestor. |
| **O que a faz rejeitar** | Ferramenta que a substitui em vez de instrumentar; qualquer decisão automática que ela não consiga explicar ao candidato ou ao jurídico. |
| **Métrica pessoal** | Time-to-hire, taxa de aprovação da shortlist pelo gestor. |

---

**Persona 2 — Rodrigo, Tech Lead / Gestor da Área (comprador de valor)**

| | |
|---|---|
| **Contexto** | Lidera squad de 7 pessoas. Perdeu 2 devs no último ano. |
| **Objetivo** | Contratar alguém que resolva o gargalo real do squad — não mais um sênior que faz o que o time já faz bem. |
| **Dores** | Sabe intuitivamente que "falta organização no time", mas não sabe traduzir isso em requisito de vaga. Entrevista mal e sabe disso. |
| **O que o faz adotar** | O diagnóstico do time entrega um insight que ele não tinha — esse é o momento "aha" do produto. |
| **O que o faz rejeitar** | Diagnóstico que soa como horóscopo corporativo; se o resultado do teste não bater com o que ele observa no dia a dia, perde credibilidade instantaneamente. |
| **Métrica pessoal** | Velocity do squad, retenção do time. |

---

**Persona 3 — Lucas, Candidato Desenvolvedor (usuário de volume)**

| | |
|---|---|
| **Contexto** | Dev pleno, 4 anos de experiência, candidatando-se a 10–20 vagas simultaneamente. |
| **Objetivo** | Ser avaliado pelo que sabe fazer, não pelo nome da empresa no currículo. |
| **Dores** | Processos longos com 5 etapas e sem feedback; testes técnicos de 6 horas não remunerados. |
| **O que o faz completar o funil** | Game curto (< 15 min), com feedback e senso de progresso; transparência sobre quais competências estão sendo avaliadas. |
| **O que o faz abandonar** | Obrigatoriedade de GitHub ativo se ele trabalha só com código privado; qualquer etapa que pareça teste de personalidade invasivo; tempo total > 45 min. |
| **Risco associado** | Candidato é o lado não-pagante — mas é quem determina a qualidade do dado. Abandono alto destrói o produto. |

---

## 5. Como Funciona — As 7 Etapas

```
[1] Diagnóstico    →  [2] Perfil-alvo   →  [3] Captação e      →  [4] Score e
    do Time            por Lacuna           Análise de CV         Pré-triagem
                                            (CV+GitHub+LinkedIn)   (corte automático)
                                                     ↓
[7] Entrevista     ←  [6] Micro-resumo   ←  [5] Game de
    + Análise IA       para Recrutador       Soft Skills
        ↓                                    (ranking)
        └──── realimenta o ranking final ────┘
```

---

### Etapa 1 — Diagnóstico do Time

**O quê:** a empresa aplica um instrumento comportamental nos membros atuais do time da área com vaga aberta.

| Item | Definição |
|---|---|
| **Instrumento** | Questionário situacional sobre framework de ~10 soft skills |
| **Respondentes** | Membros atuais do time (+ opcionalmente o gestor, avaliando o time) |
| **Output** | Mapa de forças e lacunas: perfil agregado do time por competência |
| **Tempo estimado** | **[PREMISSA]** 10–15 min por respondente |

**Framework de ~10 soft skills — proposta inicial:**

| # | Competência | Observável em |
|---|---|---|
| 1 | Comunicação | Clareza escrita, documentação, alinhamento |
| 2 | Colaboração / trabalho em time | Code review, pair, resolução de conflito |
| 3 | Disciplina e organização | Cumprimento de prazo, consistência de entrega |
| 4 | Criatividade e inovação | Proposição de alternativas, exploração |
| 5 | Resolução de problemas / pensamento analítico | Decomposição, uso de dado |
| 6 | Adaptabilidade | Resposta a mudança de escopo/prioridade |
| 7 | Liderança e influência | Condução sem autoridade formal, mentoria |
| 8 | Proatividade / autonomia | Iniciativa sem direcionamento |
| 9 | Resiliência sob pressão | Comportamento em incidente/prazo crítico |
| 10 | Aprendizado contínuo | Aquisição de novas competências |

**⚠️ Ponto crítico de validade:** este framework é uma proposta de produto, **não um instrumento psicometricamente validado**. Antes de qualquer uso comercial, precisa de: definição operacional de cada construto, ancoragem em modelo com evidência (Big Five/HEXACO como camada latente é o caminho mais defensável), teste de consistência interna e análise fatorial. Ver §10.3.

**Lógica de agregação — decisão em aberto:** o "perfil do time" é a **média** das competências, o **máximo** (basta um membro forte para a competência estar coberta), ou uma medida de **cobertura ponderada por senioridade/papel**? A escolha muda completamente o output. **[PREMISSA para o MVP: cobertura — uma competência é considerada "presente" se ao menos N membros a pontuam acima de um limiar; abaixo disso é lacuna.]**

---

### Etapa 2 — Perfil-Alvo por Lacuna

**O quê:** o sistema converte as lacunas identificadas em critérios ponderados da vaga.

**Mecânica proposta:**

```
peso_da_competência_i = f(déficit_no_time_i, criticidade_para_a_função_i)
```

| Componente | Origem | Observação |
|---|---|---|
| `déficit_no_time` | Etapa 1 | Quanto mais ausente, maior o peso |
| `criticidade_para_a_função` | Biblioteca de arquétipos de cargo + ajuste do gestor | Impede absurdos (ex.: priorizar "criatividade" acima de "analítico" numa vaga de SRE só porque o time é analítico) |

**Guarda-corpos obrigatórios:**
- ✅ **Piso de competência mínima por função.** Nenhuma competência crítica ao cargo pode ser zerada só porque o time já a tem. Contratar alguém sem comunicação porque "o time já comunica bem" é uma falha de design, não uma feature.
- ✅ **Override humano.** O gestor revisa e ajusta os pesos gerados. O sistema propõe; a pessoa decide. Isso também é exigência prática de LGPD Art. 20.
- ✅ **Explicabilidade.** Cada peso vem com a justificativa: *"Disciplina recebeu peso 0,25 porque 5 de 7 membros pontuaram abaixo do limiar."*

---

### Etapa 3 — Captação e Análise de Currículo

**Entradas obrigatórias:** currículo + perfil GitHub + perfil LinkedIn.

| Fonte | O que a IA extrai | Confiabilidade do sinal |
|---|---|---|
| **Currículo** | Experiências, stack, progressão de carreira, formação | Baixa — auto-relato, não verificado |
| **GitHub** | Frequência e consistência de commits, colaboração (PRs, issues, code review), qualidade de documentação, linguagens reais, contribuição a projetos de terceiros | **Alta** — comportamento observado |
| **LinkedIn** | Trajetória, recomendações, permanência média por empresa, coerência de narrativa | Média |
| **Cruzamento** | Consistência entre as três fontes (ex.: "5 anos de Go" no CV vs. zero Go no GitHub) | Sinal de integridade |

**🚨 Risco técnico-jurídico crítico — LinkedIn.** Os Termos de Uso do LinkedIn proíbem coleta automatizada (scraping) de perfis, e a plataforma bloqueia ativamente esse acesso. **Não existe API pública que devolva o perfil completo de terceiros.** Caminhos viáveis:

| Opção | Viabilidade | Custo |
|---|---|---|
| Candidato faz upload do PDF exportado do próprio perfil | ✅ Legal e viável | Fricção no candidato |
| "Sign in with LinkedIn" (OpenID Connect) | ⚠️ Retorna dados muito limitados (nome, e-mail, foto) | Baixo sinal |
| Scraping / dados de terceiros | ❌ Violação de ToS, risco jurídico e de bloqueio | Inaceitável |

**Recomendação:** MVP usa **upload do PDF exportado pelo candidato**. O GitHub, ao contrário, tem API pública robusta e é a fonte de sinal mais forte e mais barata do produto.

**🚨 Risco de viés por exigência de GitHub.** Exigir GitHub ativo penaliza sistematicamente: profissionais que só trabalham com código proprietário, pessoas com menos tempo livre para open source (correlacionado a responsabilidades de cuidado, majoritariamente assumidas por mulheres, e a jornadas duplas), e candidatos em transição de carreira. **Tratar GitHub como sinal positivo quando presente, nunca como critério eliminatório.** Ver §10.1.

---

### Etapa 4 — Score e Pré-Triagem Automática

| Item | Definição |
|---|---|
| **O quê** | Score de compatibilidade candidato ↔ perfil-alvo (0–100) |
| **Componentes** | Hard skills (aderência técnica) + evidência de comportamento (GitHub) + consistência entre fontes + experiência ponderada |
| **Corte** | Threshold configurável pelo recrutador; abaixo dele, eliminação automática |

**Salvaguardas não-negociáveis:**

- 🔒 **Threshold com piso auditável.** Recrutador configura, mas o sistema registra o valor usado e alerta se o corte elimina proporção anormal do funil.
- 🔒 **Nenhuma eliminação silenciosa e irreversível.** Candidatos abaixo do corte vão para uma "zona de revisão" acessível, não para o lixo. Isso é exigência prática do direito de revisão da LGPD.
- 🔒 **Monitoramento de impacto adverso.** Taxa de aprovação por grupo demográfico monitorada continuamente (ver §10.1).
- 🔒 **Score explicável.** Cada candidato eliminado tem registro de por qual dimensão foi cortado.

---

### Etapa 5 — Game de Soft Skills

**O quê:** experiência gamificada estilo Duolingo, com desafios específicos das soft skills priorizadas na Etapa 2.

| Dimensão | Definição proposta |
|---|---|
| **Formato** | Situational Judgment Test (SJT) gamificado — cenários realistas com escolhas de ação, não autoavaliação |
| **Duração-alvo** | **[PREMISSA]** 10–15 min. Acima de 20 min o abandono cresce. Validar com dado real. |
| **Mecânicas** | Progressão por níveis, feedback imediato, streaks, barra de conclusão |
| **Output** | Pontuação por competência + ranking comparável entre candidatos da mesma vaga |
| **Adaptatividade (V2)** | Dificuldade ajustada ao desempenho, reduzindo tempo e aumentando precisão |

**Por que SJT e não questionário de personalidade:** SJTs medem julgamento aplicado em contexto, são mais difíceis de "responder o que o recrutador quer ouvir", e não coletam traço de personalidade — o que **reduz materialmente a exposição a dado sensível sob LGPD** e a percepção de invasividade pelo candidato.

**Risco de gaming** — tratado em §10.4.

---

### Etapa 6 — Micro-Resumo para o Recrutador

**O quê:** antes de abrir o currículo completo, o recrutador vê um cartão de síntese gerado por IA.

**Estrutura proposta do cartão:**

```
┌──────────────────────────────────────────────────────┐
│ [Nome]                          Score: 87  •  #3/42  │
│──────────────────────────────────────────────────────│
│ SÍNTESE                                              │
│ Dev backend, 5 anos, forte em sistemas distribuídos. │
│                                                      │
│ ADERÊNCIA À LACUNA DO TIME                           │
│ ●●●● Disciplina  (lacuna nº1 do time)                │
│ ●●●○ Comunicação (lacuna nº2 do time)                │
│ ●●○○ Criatividade (time já forte — peso baixo)       │
│                                                      │
│ DESTAQUES                                            │
│ + Consistência de commits em 3 anos de histórico     │
│ + Documentação exemplar em projeto próprio           │
│ − Sem experiência prévia em liderança técnica        │
│                                                      │
│ ⚠ Ponto de atenção: stack do CV não confirmada       │
│   no GitHub (Kotlin declarado, não observado)        │
└──────────────────────────────────────────────────────┘
```

**Princípio de design:** o micro-resumo deve **acelerar a decisão sem substituí-la**. Precisa expor os pontos negativos com o mesmo destaque que os positivos — um resumo só elogioso vira ruído e destrói a confiança do recrutador. Cada afirmação do resumo deve ser rastreável até a fonte (link para o commit, para a linha do CV).

**Risco de alucinação:** o resumo é gerado por LLM. Toda afirmação factual precisa ser ancorada em campo extraído, não gerada livremente. Arquitetura recomendada: extração estruturada → redação a partir apenas dos campos extraídos.

---

### Etapa 7 — Entrevista com Análise por IA

| Item | Definição |
|---|---|
| **O quê** | Recrutador seleciona finalistas e conduz a entrevista. IA (Gemini) gera resumo + análise qualitativa. |
| **Entrada** | Transcrição da entrevista (áudio → texto) |
| **Saída** | Resumo estruturado + avaliação por competência priorizada + evidências citadas |
| **Loop** | A análise realimenta o score e produz o ranking final |
| **Apoio ao recrutador** | Roteiro de perguntas estruturadas gerado a partir das lacunas priorizadas — aumenta validade preditiva e comparabilidade |

**Salvaguardas obrigatórias:**
- 🔒 **Consentimento explícito e específico** do candidato para gravação e processamento por IA. Sem consentimento, sem análise — e isso não pode prejudicar o candidato no processo.
- 🔒 **Nenhuma análise de vídeo/expressão facial/tom de voz.** Análise de micro-expressões e prosódia carece de base científica sólida para predição de desempenho e é o tipo exato de prática que atrai autuação regulatória. **Apenas conteúdo verbal transcrito.**
- 🔒 **A IA nunca decide.** Ela sumariza e evidencia; o recrutador decide. O ranking final é sugestão, não veredito.
- ⚠️ **Risco de viés linguístico:** transcrição automática tem desempenho desigual entre sotaques regionais e registros de fala. Um candidato do interior do Nordeste pode ser transcrito com mais erro que um do eixo Rio–São Paulo, contaminando a análise. Requer teste explícito de acurácia de transcrição por variedade linguística.

---

## 6. Diferenciais Competitivos e Análise de Concorrentes

### 6.1 Mapa competitivo

| Player | Categoria | O que faz | Onde o MatchRecruiter difere |
|---|---|---|---|
| **Gupy** | ATS + IA (BR, líder) | Triagem por IA, matching candidato↔vaga, banco de talentos, forte marca junto a RHs | Gupy otimiza o candidato contra a vaga. Não modela o time existente. |
| **Sólides** | Gestão de pessoas + perfil comportamental (BR) | Profiler (base DISC), forte em PMEs, R&S + gestão | Sólides tem o dado comportamental do time, mas o usa para gestão — não para gerar perfil-alvo por lacuna nem para ranquear candidatos por complementaridade. **Concorrente mais próximo no Brasil.** |
| **Taqe** | R&S com gamificação (BR) | Matching + testes gamificados, foco em alto volume/operacional | Gamificação sim, mas matching individual e público-alvo distinto (operacional vs. tech). |
| **Revelo / Coodesh** | Marketplace de talento tech (BR) | Curadoria + matching de devs | São marketplaces de oferta; não instrumentam o time do cliente. |
| **Pymetrics (Harver)** | Games neurocientíficos (EUA) | Games que medem traços cognitivos/emocionais; benchmarking contra top performers da empresa | **Análogo internacional mais próximo.** Mas o alvo é o perfil do *alto desempenho individual*, não a lacuna do time. Pymetrics contrata por semelhança com o melhor; MatchRecruiter contrata por complemento ao conjunto. |
| **HackerRank / Codility** | Avaliação técnica | Testes de código | Hard skill apenas. Complementares, não concorrentes. |
| **Plum, Traitify, Predictive Index, Hogan** | Psicometria para seleção | Avaliação de traços validada | Instrumento, não fluxo. Potenciais **parceiros de validação científica** (ver §12, Decisão 3). |
| **Belbin Team Roles** | Framework de papéis de time | Modelo consagrado de complementaridade de papéis em equipes | Precedente conceitual que **legitima a tese** de complementaridade. É metodologia offline, não produto. |

### 6.2 Onde está o fosso (moat)

| Camada | Defensabilidade | Prazo |
|---|---|---|
| Fluxo de 7 etapas | **Baixa** — copiável em 6–12 meses por qualquer ATS estabelecido | — |
| Game de soft skills | **Média** — o conteúdo dos SJTs e sua calibração são ativo real, mas replicável | 12–18 meses |
| **Grafo de composição de times + outcomes** | **Alta** — exige base de diagnósticos e de resultados pós-contratação que só se acumula com o tempo | 24 meses+ |
| Marca de "recrutamento auditável" | **Média-alta** — se nascer com trilha de auditoria e relatório de impacto adverso, vira requisito de compliance que concorrente precisa retrofitar | 18 meses+ |

**Verdade desconfortável:** o fluxo em si não é defensável. Gupy pode construí-lo. A defesa real é **velocidade de acúmulo de dado de outcome** — quantas contratações o sistema consegue rastrear até performance e retenção a 6/12 meses. Isso deve ser prioridade de produto desde o dia 1, não uma feature de V3.

### 6.3 Riscos competitivos

- **Incumbente com distribuição.** Gupy tem os RHs. Se validarmos a tese e ela for boa, o caminho mais provável é cópia rápida ou aquisição.
- **Categoria estreita.** "Matching por lacuna de time" pode ser feature, não empresa. Mitigação: expandir para gestão contínua de composição de time (ver Roadmap V3), transformando um evento pontual (contratação) em uso recorrente.

---

## 7. Modelo de Negócio e Monetização

### Opção A — SaaS por assinatura com wedge PLG **(recomendada)**

O Diagnóstico de Time é o produto de entrada — barato ou gratuito, alto valor percebido, gera o "aha moment" e captura o dado proprietário. A monetização acontece no módulo de vagas.

| Plano | Alvo | Inclui | Preço **[PREMISSA — validar com pesquisa de disposição a pagar]** |
|---|---|---|---|
| **Diagnóstico** (freemium) | Qualquer empresa | Diagnóstico de até 2 times, mapa de lacunas, sem vagas | R$ 0 |
| **Starter** | 20–80 func. | 3 vagas ativas, game, micro-resumos | R$ 490–990/mês |
| **Growth** | 80–300 func. | 10 vagas ativas, análise de entrevista, integrações | R$ 1.900–3.500/mês |
| **Enterprise** | 300+ | Vagas ilimitadas, SSO, relatório de auditoria de viés, SLA | Sob consulta |

| Prós | Contras |
|---|---|
| Receita previsível (MRR), múltiplo de valuation mais alto | Freemium tem custo de infraestrutura e de IA sem receita |
| O wedge gratuito acelera acúmulo do ativo de dados | Conversão freemium→pago é incerta e pode ser lenta |
| Alinha com hábito de compra de RH (orçamento anual de ferramenta) | Exige uso recorrente para justificar assinatura — empresa que contrata 2x/ano churna |

---

### Opção B — Pay-per-vaga (crédito por processo)

Empresa compra créditos; cada vaga aberta consome um crédito. Diagnóstico incluso.

| Prós | Contras |
|---|---|
| Alinhado ao valor entregue; sem fricção de compromisso anual | Receita irregular e difícil de projetar |
| Funciona para quem contrata esporadicamente (amplia TAM) | Desincentiva o uso contínuo do diagnóstico (o ativo de dados cresce mais devagar) |
| Ciclo de venda curto | Múltiplo de valuation inferior ao de SaaS puro |

**Preço de referência [PREMISSA]:** R$ 300–800 por vaga, com desconto por pacote.

---

### Opção C — Success fee (% do salário na contratação efetivada)

Cobrança apenas quando a contratação acontece, ao estilo de agências de recrutamento.

| Prós | Contras |
|---|---|
| Zero fricção de venda — risco todo do fornecedor | Fluxo de caixa ruim: recebe meses depois do custo incorrido |
| Ticket alto por contratação | Difícil atribuir o fechamento à plataforma (empresa pode fechar por fora) |
| Comunica confiança extrema no produto | Mercado precifica como agência (serviço), não como software — **destrói o múltiplo de valuation** |

**Referência de mercado:** agências cobram tipicamente entre 10% e 25% do salário anual. **[PREMISSA — confirmar prática atual no mercado brasileiro de tecnologia.]**

---

### Recomendação

**Opção A como modelo principal, com Opção B como porta de entrada para contas que não querem assinar.**

Racional: (1) SaaS é o modelo que o mercado de RH já compra e que investidores premiam; (2) o freemium de diagnóstico é o único mecanismo que faz o ativo de dados crescer mais rápido que a concorrência consegue copiar o fluxo; (3) success fee reposiciona a empresa como agência — é o caminho de maior receita no ano 1 e de menor valuation no ano 3.

**Vetores de expansão de receita (V2+):** módulo de gestão contínua de composição de time (recorrência real, independente de contratação), relatório de auditoria de viés como add-on de compliance, e API/integração com ATS existentes.

---

## 8. Métricas de Sucesso

### 8.1 A métrica-norte

> **Quality of Hire ajustada por lacuna:** a proporção de contratações feitas via MatchRecruiter que, aos 6 meses, apresentam (a) permanência na empresa e (b) avaliação de desempenho do gestor igual ou superior a "atende plenamente" — comparada ao baseline histórico do mesmo cliente.

É a única métrica que prova a tese. Tudo mais é intermediário.

### 8.2 KPIs de produto

| Categoria | KPI | Meta inicial **[PREMISSA]** |
|---|---|---|
| **Ativação** | % de empresas cadastradas que completam o Diagnóstico de Time | > 60% |
| | % de times com ≥70% dos membros respondendo o diagnóstico | > 80% |
| **Funil do candidato** | Taxa de conclusão do game | > 75% |
| | Tempo mediano de conclusão do game | < 15 min |
| | Drop-off por etapa (funil completo) | < 25% por etapa |
| | % de candidatos com GitHub + LinkedIn válidos | > 70% |
| **Qualidade do modelo** | Correlação entre score final e avaliação de desempenho aos 6 meses | Estatisticamente significativa |
| | % de finalistas cujo ranking o recrutador mantém sem reordenar | > 60% |
| | Taxa de override do perfil-alvo gerado pelo gestor | < 40% (acima disso, o gerador está errado) |
| **Confiança** | Taxa de alucinação detectada em micro-resumos (auditoria amostral) | < 2% |
| | NPS do candidato | > 40 |
| | NPS do recrutador | > 50 |
| **Equidade** | Impacto adverso (taxa de aprovação do grupo minoritário / grupo majoritário) | ≥ 0,80 em todas as etapas automáticas |

### 8.3 KPIs de negócio

| Categoria | KPI | Referência |
|---|---|---|
| Receita | MRR, ARR, ARPA | — |
| Crescimento | Novos clientes/mês, taxa de conversão freemium→pago | **[PREMISSA]** > 5% |
| Retenção | Churn logo mensal, Net Revenue Retention | Churn < 3%/mês; NRR > 100% |
| Eficiência | CAC, payback de CAC, LTV/CAC | LTV/CAC > 3; payback < 12 meses |
| Uso | Vagas ativas por cliente/mês, candidatos processados/mês | — |
| Venda | Ciclo médio de venda | — |

### 8.4 KPIs de impacto no cliente (argumento comercial)

| KPI | Como medir |
|---|---|
| Redução de time-to-hire | Antes vs. depois, mesmo cliente |
| Horas de triagem economizadas | Volume triado automaticamente × tempo médio por currículo |
| Retenção a 12 meses das contratações via plataforma | Comparado ao baseline do cliente |
| Diversidade do funil | Composição demográfica em cada etapa vs. topo de funil |

---

## 9. Roadmap

### Fase 0 — Hackathon / Protótipo (agora)

**Objetivo:** provar que o fluxo é compreensível e que o insight do diagnóstico gera reação.

- [ ] Diagnóstico de time com framework de 10 competências (versão não validada, explicitamente rotulada como tal)
- [ ] Geração de perfil-alvo por lacuna com pesos visíveis
- [ ] Upload de CV + integração com API do GitHub
- [ ] Score de compatibilidade (regras + LLM)
- [ ] Game de soft skills — 1 competência completa como vertical slice, demais mockadas
- [ ] Micro-resumo gerado por IA
- [ ] Demo de análise de entrevista com transcrição de exemplo

---

### Fase 1 — MVP (0–4 meses pós-hackathon)

**Hipótese a validar:** *empresas percebem valor no perfil-alvo gerado por lacuna e completam o funil.*

| Escopo | Detalhe |
|---|---|
| ✅ Diagnóstico | Framework revisado com apoio de psicometrista; consistência interna medida |
| ✅ Perfil-alvo | Com piso mínimo por função e override do gestor |
| ✅ Captação | CV (upload) + GitHub (API oficial) + LinkedIn (**PDF exportado pelo candidato**) |
| ✅ Score e corte | Threshold configurável + zona de revisão (sem eliminação irreversível) |
| ✅ Game | 4–5 competências, formato SJT, < 15 min |
| ✅ Micro-resumo | Com ancoragem obrigatória em campo extraído |
| ✅ Entrevista | Upload de transcrição → resumo + análise (sem gravação nativa ainda) |
| ✅ **Base de compliance** | Consentimento granular, trilha de auditoria de toda decisão automática, política de retenção, canal de revisão humana |
| ✅ **Instrumentação de outcome** | Follow-up estruturado com o cliente aos 3 e 6 meses de cada contratação — **inegociável, é o ativo** |
| ❌ Fora | Integrações com ATS, mobile app, análise de vídeo, adaptatividade do game |

**Meta:** 5–10 empresas-piloto, 20+ vagas processadas, primeira leitura de correlação score × desempenho.

---

### Fase 2 — V2 (4–12 meses)

| Tema | Entregas |
|---|---|
| **Precisão** | Game adaptativo; recalibração do score com dados reais de outcome; detecção de resposta socialmente desejável |
| **Escala do funil** | Gravação e transcrição nativas de entrevista; roteiro estruturado de perguntas gerado por lacuna |
| **Integração** | API pública; integração com ATS incumbentes (posicionamento como camada de inteligência, não como substituto) |
| **Compliance como produto** | Relatório de auditoria de viés exportável pelo cliente; painel de impacto adverso por etapa |
| **Experiência do candidato** | Feedback automático ao candidato reprovado (diferencial real de employer branding para o cliente) |
| **Banco de talentos** | Candidato reprovado em uma vaga é reaproveitado em outra com perfil-alvo compatível |

---

### Fase 3 — Visão de longo prazo (12–36 meses)

**Da contratação para a arquitetura contínua de times.**

| Direção | Descrição | Por que importa |
|---|---|---|
| **Monitoramento contínuo de composição** | O diagnóstico deixa de ser evento de vaga e vira acompanhamento periódico. Alerta quando a saída de alguém abre uma lacuna crítica. | Transforma uso episódico em recorrente — resolve a maior fraqueza do modelo de assinatura |
| **Simulação de time** | "O que acontece com a composição do squad se contratarmos o candidato A vs. o B?" | Feature de altíssimo valor percebido; só possível com base de dados madura |
| **Mobilidade interna** | Aplicar o matching por lacuna a movimentações internas e formação de novos squads | Amplia o TAM para dentro de grandes corporações |
| **Recomendação de desenvolvimento** | Se a lacuna do time pode ser fechada por treinamento em vez de contratação, dizer isso | Constrói confiança e abre linha de receita em L&D |
| **Benchmark setorial** | "Times de engenharia de alta performance no seu setor têm esta composição" | Produto de dado — só o líder da categoria consegue oferecer |

---

## 10. Riscos e Mitigações

### 10.1 🔴 Viés algorítmico e discriminação

**Risco (crítico — risco existencial do negócio).** Um sistema que decide quem passa em processo seletivo é, por definição, um sistema de alto risco. Vetores concretos neste produto:

| Vetor | Mecanismo de discriminação |
|---|---|
| **Exigência de GitHub** | Penaliza quem trabalha em código fechado, quem tem menos tempo livre (correlacionado a gênero e responsabilidades de cuidado), e quem vem de contexto socioeconômico com menor acesso |
| **LinkedIn como sinal** | Rede e recomendações refletem capital social preexistente — proxy de origem social |
| **LLM sobre texto livre** | Modelos de linguagem carregam associação estatística entre nome, escola, região e "qualidade" percebida |
| **Framework comportamental** | Traços como "assertividade" e "liderança" têm expressão culturalmente variável; instrumentos mal calibrados penalizam sistematicamente certos grupos |
| **Feedback loop** | Se o modelo aprende com quem foi contratado no passado, reproduz o viés histórico do cliente |
| **Transcrição de entrevista** | Acurácia desigual entre sotaques e registros de fala |

**Mitigações:**

| # | Ação | Fase |
|---|---|---|
| 1 | **Medir impacto adverso por etapa.** Taxa de aprovação por grupo (gênero, raça, idade, região), com alerta automático abaixo da regra dos 4/5 (razão ≥ 0,80) | MVP |
| 2 | **Nenhum critério eliminatório sem justificativa de relação com o cargo.** GitHub é sinal positivo, nunca critério de corte | MVP |
| 3 | **Remoção de proxies do input do modelo.** Nome, foto, idade, instituição de ensino, endereço não entram no score | MVP |
| 4 | **Revisão humana obrigatória e efetiva** em toda eliminação automática — zona de revisão, não descarte | MVP |
| 5 | **Auditoria externa independente** de viés, anual, com relatório publicável | V2 |
| 6 | **Não treinar com histórico de contratações do cliente** até haver método de correção de viés — o passado do cliente é justamente o problema | Contínuo |
| 7 | **Comitê de ética** com participação externa para decisões de design de critério | V2 |

**Realidade a aceitar:** viés não é eliminável, é gerenciável e mensurável. A postura defensável é *"medimos, publicamos e corrigimos"* — não *"nosso algoritmo é imparcial"*. A segunda afirmação é indefensável e juridicamente perigosa.

---

### 10.2 🔴 Conformidade com LGPD

**Risco (crítico).** O produto processa dados pessoais em volume e, em algumas configurações, **dados sensíveis** (Art. 5º, II: dados referentes a origem racial, convicção religiosa, opinião política, saúde, vida sexual, genéticos ou biométricos). Perfis comportamentais estão em zona cinzenta — não são explicitamente sensíveis, mas podem inferir informação sensível (ex.: traços que correlacionam com condição de saúde mental).

| Exigência | Aplicação no produto |
|---|---|
| **Base legal (Art. 7º)** | Consentimento do candidato para o processamento; legítimo interesse para dados fornecidos no processo. **Consentimento precisa ser livre, informado, específico e revogável** — e a revogação não pode ser penalizada |
| **Finalidade e minimização (Art. 6º)** | Coletar apenas o necessário para a vaga. Perguntas do game não podem derivar para saúde, religião, orientação sexual ou política |
| **Art. 20 — revisão de decisão automatizada** | **O ponto mais crítico.** O titular tem direito a solicitar revisão de decisão tomada unicamente com base em tratamento automatizado. A Etapa 4 (corte automático) é exatamente isso. Exige: canal formal de solicitação de revisão, revisão feita por pessoa, e informação clara sobre os critérios utilizados |
| **Transparência (Art. 9º)** | Aviso de privacidade específico do processo seletivo, explicando que há avaliação por IA, quais fontes são analisadas e quais critérios pesam |
| **Retenção** | Política de prazo definida (ex.: 6 ou 12 meses após o fim do processo), com descarte automático. Manutenção em banco de talentos exige consentimento adicional |
| **Direitos do titular** | Acesso, correção, portabilidade e eliminação — implementados como funcionalidade, não como e-mail de suporte |
| **Papéis** | A empresa cliente é **controladora**; MatchRecruiter é **operadora**. Contrato precisa definir isso e alocar responsabilidades |
| **Transferência internacional** | Uso de Gemini implica processamento em infraestrutura possivelmente fora do Brasil. Exige base legal para transferência internacional (Art. 33) e cláusulas contratuais adequadas |
| **DPO** | Encarregado nomeado e publicado |

**Mitigações estruturais:**
- ✅ **Privacy by design desde o MVP** — refazer depois custa mais que fazer certo agora
- ✅ **Relatório de Impacto à Proteção de Dados (RIPD)** antes do primeiro cliente pago
- ✅ **Assessoria jurídica especializada** contratada antes do go-to-market, não depois
- ✅ **Não usar dados de candidatos de um cliente para treinar modelo servido a outro cliente** sem base legal e anonimização robusta — este ponto isolado pode inviabilizar o "grafo de dados" descrito em §6.2. **Decisão crítica (§12).**

---

### 10.3 🟠 Validade científica dos testes comportamentais

**Risco (alto).** Todo o produto repousa sobre a premissa de que o diagnóstico mede algo real e estável. Se o instrumento não for válido, todo o resto — perfil-alvo, score, ranking — é ruído bem apresentado.

| Ameaça | Descrição |
|---|---|
| **Construto mal definido** | "Proatividade" e "resiliência" não são objetos naturais. Sem definição operacional, cada respondente interpreta diferente |
| **Instrumentos populares mas fracos** | DISC e MBTI são amplamente usados no mercado e têm **validade preditiva contestada** na literatura. Big Five/HEXACO têm base empírica muito mais sólida |
| **Baixa confiabilidade teste-reteste** | Se o mesmo time refaz o diagnóstico em 3 meses e o resultado muda, o produto não mede nada |
| **A premissa da complementaridade em si** | A evidência de que times comportamentalmente diversos superam times homogêneos existe, mas é **condicional e contextual** — não é lei. Diversidade pode aumentar conflito e reduzir coesão dependendo da tarefa |
| **Amostra pequena** | Time de 5–7 pessoas produz estimativa com intervalo de confiança muito largo |

**Mitigações:**

| # | Ação |
|---|---|
| 1 | **Ancorar o framework em Big Five/HEXACO** como camada latente, com as 10 soft skills como competências observáveis derivadas — troca fundamentação frágil por fundamentação com literatura |
| 2 | **Contratar psicometrista** (consultoria ou parceria acadêmica) para desenho e validação do instrumento — antes do primeiro cliente pago |
| 3 | **Medir consistência interna** (alfa de Cronbach / ômega) e **teste-reteste** já com dados de piloto |
| 4 | **Validação preditiva contínua** — correlacionar score com desempenho real aos 6/12 meses. Se a correlação não aparecer, o produto precisa mudar, não a narrativa |
| 5 | **Comunicação honesta.** Posicionar como *"apoio à decisão baseado em sinais"*, nunca como *"medição científica de personalidade"*. Overclaim é risco jurídico e reputacional |
| 6 | **Explicitar incerteza no produto** — mostrar intervalo de confiança, especialmente com times pequenos |

---

### 10.4 🟠 Gaming do sistema pelos candidatos

**Risco (alto).** Todo teste comportamental com consequência é gameável. O candidato sabe que existe uma resposta "certa" e tende a dá-la (desejabilidade social). Vetores específicos:

| Vetor | Descrição | Mitigação |
|---|---|---|
| **Desejabilidade social no game** | Escolher a alternativa que "parece" a de bom profissional | SJT com alternativas **todas plausíveis** e trade-off real (não há opção obviamente correta); escalas de escolha forçada |
| **Uso de LLM para responder** | Candidato consulta IA durante o game | Limite de tempo por item, itens contextuais gerados dinamicamente, detecção de padrão de resposta anômalo. **Aceitar que isso é mitigável, não eliminável** |
| **GitHub inflado** | Commits artificiais, repositórios forkados, "commit farming" | Analisar **qualidade e colaboração**, não volume: PRs em projetos de terceiros, code review recebido, histórico longo. Padrões artificiais são detectáveis |
| **CV/LinkedIn inflados** | Exagero de experiência | Cruzamento entre as três fontes é justamente o detector |
| **Compartilhamento de itens** | Candidatos publicam perguntas e respostas em fóruns | Banco de itens grande e rotativo; geração dinâmica de variantes; monitoramento de vazamento |
| **Indústria de "burlar o teste"** | Surgimento de cursinhos/ferramentas específicos | Efeito inevitável do sucesso. Resposta: rotação de itens + peso maior na entrevista, que é mais difícil de simular |

**Princípio de design:** nenhuma etapa isolada deve ser decisiva. A robustez vem da **triangulação** — game + evidência observada (GitHub) + entrevista humana. Um candidato pode gamear uma etapa; gamear três de forma consistente é essencialmente performar a competência.

**Contraponto honesto:** parte do gaming é indistinguível de preparação legítima. Um candidato que estudou como se comunicar melhor "gameou" ou desenvolveu a competência? A linha é borrada e o produto deve assumir isso publicamente.

---

### 10.5 🟡 Aceitação cultural por RHs tradicionais

**Risco (médio-alto — risco de go-to-market).** O produto exige que o RH mude o processo *antes* de ver valor: aplicar teste no time atual é uma etapa nova, política e potencialmente desconfortável.

| Objeção esperada | Resposta |
|---|---|
| *"Meu time vai achar que está sendo avaliado."* | Comunicação de framing: o diagnóstico avalia a **composição do time**, não o desempenho individual. Resultados individuais podem ser privados ao respondente; o gestor vê apenas o agregado. **Decisão de produto importante.** |
| *"Não posso demorar mais para abrir vaga."* | Diagnóstico é feito **uma vez por time** e reutilizado em todas as vagas daquele time. Custo único, benefício recorrente |
| *"A IA vai me substituir."* | Posicionamento: a IA elimina a triagem manual e devolve tempo para a parte humana do trabalho. O recrutador decide em todas as etapas |
| *"Como explico a eliminação automática para um candidato?"* | O produto fornece a justificativa rastreável — este é um argumento de venda, não uma fraqueza |
| *"Contratar quem é diferente do time vai gerar conflito."* | Objeção legítima. O produto deve modelar complementaridade **dentro de uma faixa de compatibilidade cultural**, não maximizar diferença |
| *"Já usamos Gupy."* | Posicionar como camada de inteligência sobre o ATS (integração na V2), não como substituição — reduz drasticamente o custo de adoção |

**Mitigações de go-to-market:**
- Começar por **early adopters** (scale-ups de tecnologia com RH orientado a dados), não por RH tradicional
- **Diagnóstico gratuito como wedge** — entrega valor antes de exigir mudança de processo
- **Estudos de caso quantificados** dos primeiros pilotos são o principal ativo de venda para o segundo círculo de clientes
- Vender ao **gestor da área** (Rodrigo) além do RH — ele sente a dor da lacuna e tem orçamento e urgência

---

### 10.6 Riscos adicionais (não solicitados, mas materiais)

| Risco | Impacto | Mitigação |
|---|---|---|
| **Dependência de LLM de terceiro (Gemini)** | Mudança de preço, de política de uso ou de comportamento do modelo afeta custo e qualidade | Camada de abstração de provedor; avaliação de qualidade automatizada a cada mudança de modelo; monitoramento de custo por candidato processado |
| **Custo unitário de IA** | Processar CV + GitHub + resumo + entrevista por candidato tem custo real. Com funil de 300 candidatos por vaga, a margem pode inverter | Modelar custo por vaga desde o MVP; usar modelos menores nas etapas de alto volume e modelos grandes só no topo do funil |
| **Termos de uso de GitHub/LinkedIn** | Bloqueio de acesso inviabiliza a Etapa 3 | Usar apenas APIs oficiais e uploads feitos pelo próprio titular |
| **Cold start** | Sem base de outcomes, o score é heurística. O produto precisa ser útil *antes* de ter dados | Fase 1 usa regras + LLM explicáveis; o valor inicial vem da economia de tempo, não da precisão preditiva |
| **Efeito de rede negativo do candidato** | Se o processo for percebido como invasivo, candidatos bons desistem e o cliente perde talento | NPS do candidato como KPI de primeira linha; tempo total do funil como restrição de design |

---

## 11. Premissas a Validar e Perguntas em Aberto

### 11.1 Premissas críticas (se falsas, o produto não existe)

| # | Premissa | Como validar | Prazo |
|---|---|---|---|
| P1 | Times com lacunas comportamentais preenchidas performam melhor que times homogêneos reforçados | Revisão de literatura + medição de outcome nos pilotos aos 6 meses | MVP |
| P2 | Um instrumento de ~10 competências, respondido em 10–15 min, mede algo estável e útil | Teste-reteste + consistência interna com psicometrista | Pré-MVP |
| P3 | Gestores aceitam aplicar teste no time existente antes de abrir vaga | 15–20 entrevistas de descoberta com gestores de tecnologia | **Imediato** |
| P4 | Candidatos completam um game de 15 min sem abandonar | Teste de funil no piloto; medir drop-off real | MVP |
| P5 | GitHub fornece sinal comportamental com poder preditivo | Correlacionar métricas de GitHub com desempenho pós-contratação | V2 |
| P6 | Empresas pagam assinatura recorrente por isso | Pesquisa de disposição a pagar + cartas de intenção antes do desenvolvimento | **Imediato** |

### 11.2 Perguntas em aberto — Produto

- Qual a **lógica de agregação** do time: média, máximo, cobertura ou variância? (Muda todo o output do diagnóstico.)
- O que acontece quando o time tem **menos de 4 pessoas**? O diagnóstico ainda é estatisticamente utilizável?
- E quando a vaga é para **formar um time novo**, sem time existente? (Fallback necessário.)
- Resultados individuais do diagnóstico são **visíveis ao gestor** ou apenas o agregado? (Impacta diretamente a adoção — §10.5.)
- Quanto o gestor pode **sobrescrever** o perfil-alvo antes de o produto perder o sentido?
- O sistema deve **recomendar não contratar** quando a lacuna é resolvível por treinamento?
- Como lidar com o candidato que **é excelente mas reforça uma força já existente**? Rejeitá-lo é defensável para o cliente?

### 11.3 Perguntas em aberto — Técnicas

- O LinkedIn é **viável em qualquer forma automatizada**, ou o produto deve assumir upload manual permanentemente?
- Qual o **custo real de IA por candidato processado** ponta a ponta? Isso fecha a margem no plano Starter?
- É possível **detectar respostas geradas por LLM** no game com precisão aceitável?
- Como versionar o modelo de score sem **invalidar comparações** entre candidatos de um mesmo processo?

### 11.4 Perguntas em aberto — Negócio e jurídico

- MatchRecruiter é **operadora ou controladora** dos dados de candidato? (Provavelmente operadora — mas o banco de talentos e o modelo agregado complicam.)
- É juridicamente possível usar dados agregados de múltiplos clientes para **treinar o modelo compartilhado**? Se não, o moat de §6.2 precisa ser repensado.
- O produto deve buscar **certificação/auditoria externa** desde cedo como diferencial de venda?
- Qual a estratégia se **Gupy lançar a mesma feature em 12 meses**?
- Vender **direto ao gestor** ou sempre via RH?

---

## 12. As 5 Decisões Mais Críticas Antes de Iniciar o Desenvolvimento

---

### 🔴 Decisão 1 — Qual é a fundamentação científica do framework comportamental?

**A escolha:** (a) framework próprio de 10 soft skills, criado internamente; (b) framework próprio **ancorado em Big Five/HEXACO** como camada latente; (c) licenciar instrumento validado de terceiro (Hogan, Plum, Predictive Index).

**Por que é a decisão nº 1:** tudo no produto — perfil-alvo, score, ranking, entrevista — deriva do diagnóstico. Se o instrumento não mede nada estável, o produto é uma interface bonita sobre ruído, e isso não aparece no hackathon: aparece no cliente número 12, quando as contratações não performam.

**Recomendação:** **(b)**. Preserva a propriedade do ativo e a flexibilidade de produto, com fundamentação defensável perante cliente, investidor e regulador. Requer contratação de psicometrista antes do primeiro cliente pago.

---

### 🔴 Decisão 2 — GitHub obrigatório significa nichar em tecnologia. Isso é aceito?

**A escolha:** (a) manter GitHub obrigatório e assumir o nicho tech; (b) tornar GitHub um sinal opcional e abrir o produto para qualquer área; (c) fontes de evidência configuráveis por tipo de vaga (GitHub para dev, portfólio para design, etc.).

**Por que é crítica:** define o TAM, o ICP, a estratégia de venda e o risco de viés (§10.1). Também determina se a proposta de valor é "recrutamento tech inteligente" ou "recrutamento inteligente" — duas empresas diferentes.

**Recomendação:** **(a) no MVP, com arquitetura preparada para (c)**. Nichar acelera a validação; a arquitetura de "fontes de evidência plugáveis" evita reescrita quando a expansão vier. **Em nenhum cenário GitHub deve ser critério eliminatório.**

---

### 🔴 Decisão 3 — Qual é o modelo de dados entre clientes, e o moat sobrevive à LGPD?

**A escolha:** (a) dados totalmente isolados por cliente — sem modelo compartilhado; (b) modelo compartilhado treinado com dados anonimizados e agregados, com base legal e consentimento explícitos; (c) modelo compartilhado apenas com dados de diagnóstico de time (não de candidato).

**Por que é crítica:** a defensabilidade descrita em §6.2 depende inteiramente disso. Se a resposta for (a), o produto é um fluxo copiável e a estratégia precisa ser outra (velocidade, distribuição ou aquisição). Decidir isso *depois* de construir significa reprojetar a arquitetura de dados inteira.

**Recomendação:** **(c) como caminho de menor risco jurídico com moat preservado** — dados de composição de time são menos sensíveis que dados de candidato, e são exatamente o ativo diferenciador. Validar com assessoria jurídica **antes** da primeira linha de código de persistência.

---

### 🟠 Decisão 4 — Substituir o ATS ou ser a camada de inteligência sobre ele?

**A escolha:** (a) ATS completo e independente, competindo de frente com Gupy; (b) camada de inteligência que se integra ao ATS existente do cliente; (c) começar independente e integrar depois.

**Por que é crítica:** define a arquitetura, o ciclo de venda, o custo de aquisição e a postura competitiva. Substituir o ATS significa vender uma troca de sistema — ciclo longo, resistência alta. Integrar significa venda incremental e adoção rápida, mas dependência de plataformas que podem virar concorrentes.

**Recomendação:** **(c)**, com a integração explicitamente planejada para a V2 e a arquitetura desenhada com API-first desde o MVP. Não construir funcionalidades genéricas de ATS (agenda, pipeline, e-mails) — construir só o que é diferenciado.

---

### 🟠 Decisão 5 — Qual modelo de monetização entra em campo no dia 1?

**A escolha:** SaaS com wedge freemium (A), pay-per-vaga (B) ou success fee (C) — ver §7.

**Por que é crítica:** determina a estratégia de produto (freemium exige que o diagnóstico seja autossuficiente em valor), a estrutura de custo de IA, o perfil de investidor que a empresa atrai e o múltiplo de valuation. Trocar de modelo depois de ter clientes é caro e desgastante.

**Recomendação:** **(A) — SaaS com diagnóstico como wedge**, com (B) disponível para contas que resistem à assinatura. Validar disposição a pagar com 15–20 entrevistas comerciais **antes** de escrever código de billing.

---

## Apêndice A — Glossário

| Termo | Definição |
|---|---|
| **ATS** | Applicant Tracking System — sistema de gestão de candidaturas |
| **Impacto adverso** | Taxa de aprovação de um grupo protegido significativamente inferior à do grupo majoritário (regra dos 4/5: razão < 0,80) |
| **SJT** | Situational Judgment Test — teste de julgamento situacional |
| **Big Five / HEXACO** | Modelos de personalidade com maior base empírica na psicologia |
| **PLG** | Product-Led Growth — crescimento conduzido pelo próprio produto |
| **Quality of Hire** | Métrica de qualidade da contratação, tipicamente medida por desempenho e retenção pós-admissão |
| **RIPD** | Relatório de Impacto à Proteção de Dados Pessoais (LGPD) |
| **NRR** | Net Revenue Retention — retenção líquida de receita |

---

## Apêndice B — Índice de premissas e dados a verificar

Antes de qualquer uso deste documento em contexto de investimento, os itens abaixo precisam de fonte primária verificada:

| # | Item | Seção |
|---|---|---|
| 1 | Custo de contratação equivocada (múltiplo do salário) | §2.2 |
| 2 | Gap de profissionais de TI no Brasil — edição e números Brasscom atuais | §2.3 |
| 3 | Taxa de rotatividade no setor de tecnologia — recorte CAGED | §2.3 |
| 4 | Validade preditiva de entrevista estruturada — referência primária | §2.2 |
| 5 | Prática de success fee no mercado brasileiro de tecnologia | §7 |
| 6 | Faixas de preço dos planos — pesquisa de disposição a pagar | §7 |
| 7 | Todas as metas numéricas de KPI | §8 |
| 8 | Evidência sobre diversidade comportamental e desempenho de times | §10.3 |

---

*Documento preparado para discussão. Todas as recomendações são explicitamente marcadas como tal e todas as lacunas de informação estão sinalizadas em vez de preenchidas com estimativa não fundamentada.*
