# Fluxo do MVP — passo a passo executável

Este documento percorre o fluxo completo do MatchRecruiter com chamadas HTTP reais.
A saída mostrada foi capturada de uma execução de verdade contra a API.

Para rodar tudo automaticamente:

```bash
cd backend
make bootstrap                          # containers + migrações + seed
./scripts/demo_flow.sh                  # executa os 9 passos abaixo
```

O cenário montado é o caso central do produto: um time de **exploradores** — forte em
Criatividade e Análise, fraco em Colaboração e Comunicação — e dois candidatos. Um cobre as
lacunas; o outro responde o teste exatamente como o time.

O instrumento é um **teste de julgamento situacional (SJT) ancorado em Big Five**: 20 situações
de trabalho, 4 condutas possíveis em cada, todas profissionalmente defensáveis. A escolha
pontua nos cinco fatores, e as 10 soft skills são derivadas deles.

Em desenvolvimento (`GOOGLE_CLIENT_ID=mock_google_client_id`), qualquer token no formato
`mock_google_token_<sufixo>` cria e loga um usuário determinístico. Isso torna o fluxo
reproduzível sem depender do Google.

---

## 1. Recrutador entra e cria o time

```bash
BOSS=$(curl -s -X POST localhost:8000/api/v1/auth/google \
  -H 'content-type: application/json' \
  -d '{"id_token":"mock_google_token_boss"}' | jq -r .access_token)

curl -s -X POST localhost:8000/api/v1/teams \
  -H "Authorization: Bearer $BOSS" -H 'content-type: application/json' \
  -d '{"name":"Squad Explorador"}'
```

Quem cria o time vira **responsável, não integrante**. O recrutador não responde o diagnóstico e
não entra na média: incluí-lo contaminaria o perfil com alguém que não convive com o problema que
a vaga vai resolver. Todo respondente entra pelo link de convite — inclusive o gestor do squad,
quando é ele quem abre a vaga.

Um usuário sem `invite_token` e sem `job_id` é criado como `RECRUITER`.

## 2. Link de convite para os integrantes

```bash
curl -s -X POST "localhost:8000/api/v1/teams/$TEAM/invites" \
  -H "Authorization: Bearer $BOSS"
```

```json
{ "invite_token": "…", "invite_url": "/teams/…/invites?token=…", "expires_at": "2026-08-25T…" }
```

O convite expira (padrão 30 dias, configurável via `expires_in_days`). Só o dono do time gera
convites — qualquer outra pessoa recebe **403**.

## 3. Cada integrante responde o diagnóstico

O integrante entra com o `invite_token`, o que já o vincula ao time como `MEMBER`:

```bash
curl -s -X POST localhost:8000/api/v1/auth/google \
  -H 'content-type: application/json' \
  -d "{\"id_token\":\"mock_google_token_m1\",\"invite_token\":\"$INVITE\"}"
```

Busca o instrumento e vê os cenários:

```bash
curl -s localhost:8000/api/v1/questionnaires/default -H "Authorization: Bearer $TOKEN"
```

```jsonc
{
  "format": "SJT",
  "traits": ["Abertura à Experiência", "Conscienciosidade", "Extroversão", "Amabilidade", "Estabilidade Emocional"],
  "derived_dimensions": ["Comunicação", "Colaboração", …],
  "questions": [
    {
      "context": "Prazo e dívida técnica",
      "text": "Faltam dois dias para a entrega e você percebe que a solução que construiu vai gerar retrabalho para o time em algumas semanas. O que você faz?",
      "options": [
        { "id": "…", "text": "Entrego no prazo e registro a dívida com um plano concreto para a próxima sprint." },
        { "id": "…", "text": "Levo a decisão para o time: prefiro que a escolha do trade-off seja coletiva." },
        { "id": "…", "text": "Proponho uma abordagem diferente que evita a dívida, mesmo mudando o plano agora." },
        { "id": "…", "text": "Absorvo o trabalho extra e resolvo os dois lados sem transformar isso em assunto." }
      ]
    }
  ]
}
```

**As quatro condutas são todas defensáveis.** Não há opção obviamente certa a marcar — a
diferença entre elas é de ênfase de traço, não de qualidade. E **as cargas nos fatores nunca
aparecem na resposta**: se o candidato visse que uma alternativa pontua Conscienciosidade,
escolheria pelo rótulo, que é a desejabilidade social que o formato existe para evitar.

Envia as escolhas:

```bash
curl -s -X POST "localhost:8000/api/v1/questionnaires/$QID/answers" \
  -H "Authorization: Bearer $TOKEN" -H 'content-type: application/json' \
  -d '{"answers":[{"question_id":"…","selected_option_id":"…"}, …]}'
```

```jsonc
{
  "message": "Respostas registradas com sucesso.",
  "saved_answers": 20,
  "progress": {
    "answered_questions": 20, "total_questions": 20, "is_complete": true,
    "missing_question_ids": [],
    "trait_scores": { "Abertura à Experiência": 5.0, "Amabilidade": 1.0, … },
    "dimension_scores": { "Criatividade e Inovação": 4.04, "Colaboração": 1.24, … }
  }
}
```

**Envio parcial é aceito** — o teste pode ser respondido em etapas, e `missing_question_ids` diz
o que falta. **Reenviar troca** a escolha em vez de acumular respostas.

Duas validações protegem o perfil: cenário que não pertence ao instrumento informado e
alternativa que não pertence ao cenário são ambos rejeitados com **400** — aplicariam cargas
erradas.

## 4. Perfil do time

```bash
curl -s "localhost:8000/api/v1/teams/$TEAM/soft-skills-profile" -H "Authorization: Bearer $BOSS"
```

```
respondentes=4/4  baixa_confianca=False

Big Five:  Abertura=5.0 | Conscienciosidade=2.3 | Estabilidade=2.0 | Extroversão=1.1 | Amabilidade=1.0
competencia mais alta:  Criatividade e Inovação (4.04)
competencia mais baixa: Colaboração (1.24)
```

A resposta traz as **duas camadas**: `trait_scores` (os cinco fatores medidos) e
`dimension_scores` (as competências derivadas). Os fatores dizem que tipo de gente é o time; as
competências são o que entra na lacuna e no fit.

O perfil do time é a **média das pessoas**, não das respostas agrupadas. Com escolha forçada os
dois números divergem: somar as escolhas de N pessoas e normalizar uma vez só infla todos os
fatores para o topo da escala.

`respondent_count` é o campo que separa **"time equilibrado"** de **"ninguém respondeu ainda"** —
sem ele um time vazio pareceria um time com perfil neutro. Com menos de 4 respondentes a resposta
sai com `low_confidence: true` e uma `confidence_note` explicando a margem de erro.

Para saber **quem** falta responder:

```bash
curl -s "localhost:8000/api/v1/teams/$TEAM/diagnostic-status" -H "Authorization: Bearer $BOSS"
```

Retorna pessoa a pessoa (`answered_questions`, `assessment_completed`) e um
`ready_for_job_opening` indicando se o diagnóstico já é maduro o bastante.

## 5. Perfil-alvo por lacuna — a Etapa 2 do produto

```bash
curl -s "localhost:8000/api/v1/teams/$TEAM/gap-analysis" -H "Authorization: Bearer $BOSS"
```

```
prioridades: Colaboração, Liderança e Influência, Comunicação, Resiliência sob Pressão
forcas: Adaptabilidade, Aprendizado Contínuo, Criatividade e Inovação, Pensamento Analítico

peso Colaboração                  0.330  (GAP)
peso Liderança e Influência       0.225  (GAP)
peso Comunicação                  0.186  (GAP)
peso Criatividade e Inovação      0.000  (STRENGTH)
```

As dimensões em que o time fica **abaixo do próprio centro** viram os critérios de maior peso da
vaga. Cada peso vem com justificativa rastreável:

> *"Média do time em Colaboração é 1.2, abaixo do nível médio do próprio time (2.7). 4 de 4
> respondentes pontuam abaixo desse nível."*

**Lacuna e força são relativas ao perfil do time, não notas absolutas.** Com um instrumento
normativo e de escolha forçada, um corte fixo não funciona: a média de um time diverso regride
ao centro por construção, e um limiar absoluto classificaria toda dimensão de todo time
equilibrado como lacuna.

O `target_profile` aplica o guarda-corpo de **piso mínimo por competência**: as lacunas recebem
como alvo o ponto em que deixariam de ser lacuna neste time, e as demais mantêm o piso absoluto
de 2.0 — nenhuma competência é zerada só porque o time já a tem.

## 6. Vaga aberta

```bash
curl -s -X POST localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $BOSS" -H 'content-type: application/json' \
  -d "{\"title\":\"Dev Backend Pleno\",\"team_id\":\"$TEAM\"}"
```

Sem `questionnaire_id`, a vaga usa o **instrumento padrão** — o mesmo que o time respondeu.
É o que torna os dois perfis comparáveis dimensão a dimensão.

Abrir vaga para um time de outra pessoa retorna **403**.

## 7. Candidatos respondem o mesmo teste

```bash
curl -s -X POST localhost:8000/api/v1/auth/google \
  -H 'content-type: application/json' \
  -d "{\"id_token\":\"mock_google_token_ana\",\"job_id\":\"$JOB\"}"

curl -s "localhost:8000/api/v1/jobs/$JOB/questionnaire" -H "Authorization: Bearer $CAND"

curl -s -X POST "localhost:8000/api/v1/jobs/$JOB/answers" \
  -H "Authorization: Bearer $CAND" -H 'content-type: application/json' \
  -d '{"answers":[{"question_id":"…","selected_option_id":"…"}, …]}'
```

`job_id` no login já cria a candidatura. A candidatura só passa a `SOFT_SKILLS_COMPLETED` quando
**todos** os cenários forem respondidos — antes disso o perfil está incompleto e não deveria ser
comparado com o do time.

## 8. Painel do recrutador — o ranking

```bash
curl -s "localhost:8000/api/v1/jobs/$JOB/candidates" -H "Authorization: Bearer $BOSS"
```

```
1. Candidato A   fit_complementar= 64.6   indice_suplementar= 57.1   BALANCED
   lacunas cobertas: Colaboração, Comunicação
2. Candidato B   fit_complementar=  0.0   indice_suplementar=100.0   BELOW_MINIMUM
   lacunas cobertas: nenhuma
```

**É aqui que a tese do produto aparece.** O candidato B respondeu o teste **exatamente como o
time**. Um ATS tradicional o veria como "encaixe cultural perfeito" — índice suplementar 100.0.
Aqui ele é o pior colocado, porque não cobre lacuna nenhuma e deixa descobertas as competências
que o time já não tem.

- **A** cobre as duas maiores lacunas → fit complementar **64.6**.
- **B** é o espelho do time → fit complementar **0.0**.

Um candidato pode pontuar acima da média do time numa lacuna e ainda assim não a cobrir: se
ficar abaixo do nível médio do próprio time, a lacuna sobrevive à contratação e o item sai
rotulado como `PARTIAL_LIFT`. Chamar isso de "lacuna coberta" enganaria o recrutador.

Filtros: `min_fit_score`, `status`, `limit`, `sort_desc`. Quem ainda não respondeu o teste fica no
fim da lista em ambas as ordenações.

Um recrutador de outra empresa recebe **403** — perfil comportamental de candidato não vaza entre
contas.

## 9. Simulação pós-contratação

```bash
curl -s -X POST "localhost:8000/api/v1/jobs/$JOB/candidates/$CAND/impact-analysis" \
  -H "Authorization: Bearer $BOSS"
```

```
time: 4 -> 5 pessoas | veredito: BALANCED

Colaboração                  1.24 -> 1.75  (+0.51)
Comunicação                  1.86 -> 2.18  (+0.32)
Criatividade e Inovação      4.04 -> 3.55  (-0.49)
Pensamento Analítico         3.51 -> 3.04  (-0.47)

* Colaboração é lacuna do time (1.2) e o candidato pontua 3.8 — cobre a lacuna.
* Comunicação é lacuna do time (1.9) e o candidato pontua 3.5 — cobre a lacuna.
* Criatividade e Inovação é força do time (4.0), mas o candidato pontua 1.6 e puxa a média para baixo.
* Liderança e Influência é lacuna do time (1.7) e o candidato (2.2) melhora a média, mas
  continua abaixo do nível médio do time (2.7) — a lacuna segue aberta.
```

Fórmula por dimensão: `(média_atual × N + nota_candidato) / (N + 1)`.

Repare que **duas dimensões caem**. Isso é esperado e está correto: o candidato é fraco
justamente onde o time é forte — consequência direta do formato de escolha forçada, em que ser
forte numa conduta implica não privilegiar as outras. O produto mostra o custo junto com o
ganho; um resumo só elogioso destruiria a confiança do recrutador.

Toda dimensão vem com uma frase explicando o porquê (`insights[]`), e os alertas ficam em
`risk_flags[]`.

## 10. Contratação fecha o ciclo

```bash
curl -s -X POST "localhost:8000/api/v1/jobs/$JOB/candidates/$CAND/hire" -H "Authorization: Bearer $BOSS"
```

```
status=HIRED
time agora tem 5 pessoas
Colaboração: 1.75
```

A pessoa entra no time e passa a compor o diagnóstico. **A simulação vira o diagnóstico real** — o
valor previsto (1.75) e o valor observado após a contratação coincidem. Na próxima vaga daquele
time, o perfil-alvo já parte da composição atualizada.

---

## Vereditos possíveis

| Veredito | Significado |
| :--- | :--- |
| `COMPLEMENTARY` | Cobre as lacunas do time de forma decisiva |
| `BALANCED` | Contribui, mas sem fechar lacuna de forma decisiva |
| `EXCESSIVE_SUPPLEMENTARY` | Mais do mesmo: reforça forças e deixa lacunas descobertas |
| `BELOW_MINIMUM` | Deixa uma competência ausente do time como encontrou — o buraco continua aberto |
| `INSUFFICIENT_TEAM_DATA` | Ninguém do time respondeu; não há complementaridade a medir |

## Como ler os números

O instrumento é **normativo**, não absoluto: 3.0 significa "escolhe as condutas deste fator na
frequência que o acaso produziria". Uma nota 4.2 quer dizer "escolhe muito mais que o acaso",
**não** "domina a competência". Nenhum número desta API sustenta a afirmação "esta pessoa é
excelente em X".

Pelo mesmo motivo, lacuna e força são **posições dentro do perfil daquele time**, não notas que
possam ser comparadas entre empresas.

## O que este fluxo ainda não cobre

Etapas 3, 6 e 7 do fluxo descrito em `visao-de-negocio.md` — análise de CV/GitHub, micro-resumo
gerado por IA e análise de entrevista — não estão implementadas. As limitações de método
(instrumento não validado, ipsatividade, banco de 20 cenários, agregação por média) estão
listadas em `backend/README.md`.
