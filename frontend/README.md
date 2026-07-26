# MatchRecruiter — Frontend

Interface React do MatchRecruiter: aplica o teste situacional, mostra o diagnóstico do time e
ranqueia candidatos por **fit complementar**.

## Stack

| Peça | Escolha | Por quê |
| :--- | :--- | :--- |
| Build | **Vite 6** | Dev server rápido e proxy embutido para o backend |
| UI | **React 19 + TypeScript** | Tipos espelhando os schemas do backend acusam quebra de contrato no build |
| Dados | **TanStack Query 5** | Cache, revalidação e estados de carregamento/erro sem código repetido |
| Rotas | **React Router 8** | Rotas aninhadas com layout compartilhado |
| Estilo | **Tailwind CSS 4** | Configuração em CSS, sem arquivo de config JS |

## Como rodar

O backend precisa estar no ar. **Em outro terminal**, a partir da raiz do repositório:

```bash
cd backend && make dev-local     # sem Docker, SQLite
# ou: cd backend && make bootstrap   # com Docker + PostgreSQL
```

Depois, neste terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev          # http://localhost:5173
```

Em desenvolvimento o Vite faz proxy de `/api` para `http://localhost:8000` — o navegador vê tudo
na mesma origem, então **não há CORS nem preflight**. Aponte para outro backend com `BACKEND_URL`.

| Script | O que faz |
| :--- | :--- |
| `npm run dev` | Servidor de desenvolvimento com proxy |
| `npm run build` | Typecheck + build de produção em `dist/` |
| `npm run typecheck` | Só a verificação de tipos |
| `npm run lint` | ESLint — regras de hooks, que o typecheck não vê |
| `node scripts/e2e-demo.mjs` | Percorre o fluxo inteiro no navegador e captura as telas |

### Sobre o aviso de `install-scripts` do esbuild

O npm desta máquina bloqueia scripts de pós-instalação, e o esbuild imprime um aviso. **Pode
ignorar**: o binário vem pronto no pacote de plataforma (`@esbuild/linux-x64`), não é o
`postinstall` que o baixa. `npx esbuild --version` confirma.

### Login sem credenciais do Google

Com `VITE_GOOGLE_CLIENT_ID` vazio, a tela de login entra em **modo de demonstração** e usa os
tokens simulados do backend (`GOOGLE_CLIENT_ID=mock_google_client_id`). Basta digitar um
identificador: o mesmo texto sempre entra na mesma conta, o que permite simular recrutador, time e
candidatos em abas diferentes.

Com um client ID configurado, a mesma tela carrega o Google Identity Services e usa o botão real.

## Telas

| Rota | Quem usa | O que faz |
| :--- | :--- | :--- |
| `/login` | todos | Google real ou modo demo; preserva convite/vaga na query |
| `/` | recrutador | Lista e cria times |
| `/times/:id` | recrutador | Diagnóstico do time, perfil-alvo por lacuna, convite, abrir vaga |
| `/vagas` · `/vagas/:id` | recrutador | Vagas e ranking de candidatos |
| `/vagas/:id/candidatos/:id` | recrutador | Simulação pós-contratação e decisão |
| `/meu-teste` | integrante do time | Responde o teste situacional (o recrutador não vê este link) |
| `/convite/:token` | convidado | Entra no time e vai ao teste |
| `/vaga/:id` | candidato | Candidata-se e responde o teste |

A navegação segue o papel: candidato não vê links de administração que dariam 403, e o recrutador
não vê "Meu teste" — ele administra o diagnóstico sem responder a ele.

## Decisões de interface

**O teste é respondido um cenário por vez**, com salvamento a cada escolha. Fechar a aba no
cenário 15 não perde nada — as respostas já enviadas são carregadas de volta e o teste retoma de
onde parou.

**As cargas dos fatores nunca chegam ao navegador.** A API entrega apenas o texto das alternativas.
Se o respondente visse que uma opção pontua Conscienciosidade, escolheria pelo rótulo — que é
exatamente a desejabilidade social que o formato SJT existe para evitar.

**Ganho e custo aparecem com o mesmo destaque.** A simulação mostra as dimensões que caem tão
claramente quanto as que sobem. Um resumo só elogioso destruiria a confiança do recrutador.

## Visualização de dados

Os gráficos seguem um método fixo; nada aqui é escolha de gosto.

**Formas.** Magnitude por dimensão → barras horizontais de série única. Time × candidato → barras
agrupadas de duas séries com legenda. Antes → depois → **dumbbell**, que é a forma certa para o
mesmo valor em dois momentos. Um número isolado → *stat tile*, nunca um gráfico de uma barra.

**Cores.** Paleta de referência validada com o script de checagem em light e dark: banda de
luminosidade, piso de croma, separação sob daltonismo, piso de visão normal e contraste — todos
passam nos dois modos. As duas séries são os slots categóricos 1 (azul) e 2 (laranja). O modo
escuro tem passos próprios da mesma rampa, não é uma inversão automática.

**Cor de status nunca carrega significado sozinha.** Lacuna, força e veredito vêm sempre com ícone
e rótulo em texto.

**Toda visualização tem tabela gêmea.** O botão "Ver tabela" mostra os mesmos números — o tooltip
enriquece, nunca é o único caminho para o valor.

### A escala é normativa

Os gráficos crescem do piso real da escala (1.0) e marcam **3.0** com um tique mais forte: é o
nível de acaso. Sem essa referência, 4.2 seria lido como "domina a competência", quando significa
"escolhe estas condutas bem mais que o acaso". A legenda diz isso em todo gráfico de perfil.

Uma nota no piso da escala desenha um toco de 3px em vez de sumir — número na tela sem marca que o
represente é pior que uma barra mínima.

## Verificação

`scripts/e2e-demo.mjs` monta um cenário completo pela API (time de exploradores, quatro
diagnósticos, uma vaga, um candidato complementar e um espelho do time), percorre as telas num
Chromium headless, captura tudo em claro e escuro e **falha se houver erro de console**.

```bash
node scripts/e2e-demo.mjs           # capturas em screenshots/
```

Ele lê a chave de correção direto de `backend/app/core/big_five.py` para simular respondentes com
tendências de traço coerentes — a API não expõe essa chave, e é assim de propósito.

## Limitações conhecidas

- **Sem testes automatizados de componente.** A verificação hoje é o percurso end-to-end acima,
  que cobre integração e regressão visual, mas não casos de borda de cada componente.
- **Sem paginação no ranking.** Uma vaga com centenas de candidatos renderiza a lista inteira.
- **Sem feedback ao candidato reprovado** — previsto na V2 do documento de visão.
- **`localStorage` para o token.** Simples e suficiente para o MVP; um cookie `HttpOnly` é o
  caminho para produção.
