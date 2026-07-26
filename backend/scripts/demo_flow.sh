#!/usr/bin/env bash
# Demonstração ponta a ponta do MVP contra uma API já em execução.
#
# Monta um time de "exploradores" (privilegiam Abertura, evitam a conduta
# cooperativa), aplica o diagnóstico SJT, abre a vaga e compara dois candidatos:
# um que cobre as lacunas e outro que responde exatamente como o time.
#
# Uso:  ./scripts/demo_flow.sh [base_url]
# Requer a API no ar com o seed aplicado e GOOGLE_CLIENT_ID=mock_google_client_id.

set -euo pipefail

BASE="${1:-http://localhost:8000}"
API="$BASE/api/v1"

jqp() { python3 -c "import sys,json;d=json.load(sys.stdin);print($1)"; }

login() { # $1 = sufixo do token mock, $2... = pares extras de JSON
  local suffix="$1"; shift
  local extra="${1:-}"
  curl -s -X POST "$API/auth/google" -H 'content-type: application/json' \
    -d "{\"id_token\":\"mock_google_token_$suffix\"${extra:+,$extra}}"
}

# Responde os 20 cenários escolhendo, em cada um, a conduta mais alinhada à
# tendência de traço informada. As cargas não vêm da API — a simulação usa a
# mesma chave de correção do servidor, embutida aqui só para a demo.
answer() { # $1 = token, $2 = questionnaire_id, $3 = json {traço: peso}
  local token="$1" qid="$2" pref="$3"
  local body
  body=$(curl -s "$API/questionnaires/$qid" -H "Authorization: Bearer $token" \
    | PREF="$pref" python3 -c "
import sys, os, json
sys.path.insert(0, '.')
from app.core.big_five import SJT_SCENARIOS, TRAITS

qs = json.load(sys.stdin)['questions']
pref = json.loads(os.environ['PREF'])
loads = {o.text: o.loadings for sc in SJT_SCENARIOS for o in sc.options}

answers = []
for i, q in enumerate(qs):
    boosted = TRAITS[i % len(TRAITS)]
    def affinity(opt):
        L = loads.get(opt['text'], {})
        return sum((pref.get(t, 0.0) + (0.35 if t == boosted else 0.0)) * w for t, w in L.items())
    best = max(q['options'], key=affinity)
    answers.append({'question_id': q['id'], 'selected_option_id': best['id']})
print(json.dumps({'answers': answers}))")
  curl -s -X POST "$API/questionnaires/$qid/answers" \
    -H "Authorization: Bearer $token" -H 'content-type: application/json' -d "$body" \
    | jqp "'  respondeu %s/%s cenarios' % (d['progress']['answered_questions'], d['progress']['total_questions'])"
}

echo "==> 0. Health"
curl -s "$BASE/health" | jqp "d['status']"

echo
echo "==> 1. Recrutador entra e cria o time"
BOSS=$(login demoboss | jqp "d['access_token']")
TEAM=$(curl -s -X POST "$API/teams" -H "Authorization: Bearer $BOSS" \
  -H 'content-type: application/json' -d '{"name":"Squad Explorador"}' | jqp "d['id']")
echo "  team_id=$TEAM"

QID=$(curl -s "$API/questionnaires/default" -H "Authorization: Bearer $BOSS" | jqp "d['id']")
echo "  questionario padrao=$QID"

INVITE=$(curl -s -X POST "$API/teams/$TEAM/invites" -H "Authorization: Bearer $BOSS" | jqp "d['invite_token']")

echo
echo "==> 2. Diagnostico: 4 integrantes respondem o SJT (perfil explorador)"
# Privilegiam Abertura; quase nunca escolhem a conduta cooperativa.
TEAM_PREF='{"Abertura à Experiência":1.4,"Conscienciosidade":0.5,"Extroversão":0.2,"Amabilidade":0.1,"Estabilidade Emocional":0.2}'
answer "$BOSS" "$QID" "$TEAM_PREF"
for m in demom1 demom2 demom3; do
  TK=$(login "$m" "\"invite_token\":\"$INVITE\"" | jqp "d['access_token']")
  answer "$TK" "$QID" "$TEAM_PREF"
done

echo
echo "==> 3. Perfil do time: fatores Big Five e competencias derivadas"
curl -s "$API/teams/$TEAM/soft-skills-profile" -H "Authorization: Bearer $BOSS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('  respondentes=%s/%s  baixa_confianca=%s' % (d['respondent_count'], d['member_count'], d['low_confidence']))
print('  Big Five:', ' | '.join('%s=%.1f' % (k.split()[0], v) for k, v in d['trait_scores'].items()))
top = sorted(d['dimension_scores'].items(), key=lambda kv: -kv[1])
print('  competencia mais alta: %s (%.2f)' % top[0])
print('  competencia mais baixa: %s (%.2f)' % top[-1])
"

echo
echo "==> 4. Perfil-alvo por lacuna (Etapa 2)"
curl -s "$API/teams/$TEAM/gap-analysis" -H "Authorization: Bearer $BOSS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('  prioridades:', ', '.join(d['priority_dimensions']))
print('  forcas:', ', '.join(d['strengths']))
for dim in d['dimensions'][:3]:
    print('  peso %-28s %.3f  (%s)' % (dim['dimension'], dim['weight'], dim['status']))
"

echo
echo "==> 5. Vaga aberta (usa o mesmo instrumento do diagnostico)"
JOB=$(curl -s -X POST "$API/jobs" -H "Authorization: Bearer $BOSS" -H 'content-type: application/json' \
  -d "{\"title\":\"Dev Backend Pleno\",\"team_id\":\"$TEAM\"}" | jqp "d['id']")
echo "  job_id=$JOB"

echo
echo "==> 6. Dois candidatos respondem o mesmo SJT"
# A: privilegia as condutas cooperativas que o time evita.
CAND_A='{"Amabilidade":1.4,"Extroversão":1.0,"Estabilidade Emocional":0.8,"Conscienciosidade":0.4,"Abertura à Experiência":0.1}'
# B: responde exatamente como o time — o "encaixe cultural perfeito".
CAND_B="$TEAM_PREF"

A=$(login democomplementar "\"job_id\":\"$JOB\"")
A_TOKEN=$(echo "$A" | jqp "d['access_token']")
echo "  A (cobre as lacunas):"; answer "$A_TOKEN" "$QID" "$CAND_A"

B=$(login demoespelho "\"job_id\":\"$JOB\"")
B_TOKEN=$(echo "$B" | jqp "d['access_token']")
echo "  B (espelho do time):"; answer "$B_TOKEN" "$QID" "$CAND_B"

echo
echo "==> 7. Painel do recrutador: ranking por fit complementar"
curl -s "$API/jobs/$JOB/candidates" -H "Authorization: Bearer $BOSS" | python3 -c "
import sys, json
for i, c in enumerate(json.load(sys.stdin), 1):
    print('  %d. %-22s fit_complementar=%5.1f  indice_suplementar=%5.1f  %s'
          % (i, c['candidate_name'], c['fit_score'], c['supplementary_fit_index'], c['verdict']))
    print('     lacunas cobertas: %s' % (', '.join(c['gaps_filled']) or 'nenhuma'))
"

echo
echo "==> 8. Simulacao pos-contratacao do melhor colocado"
BEST=$(curl -s "$API/jobs/$JOB/candidates?limit=1" -H "Authorization: Bearer $BOSS" | jqp "d[0]['candidate_id']")
curl -s -X POST "$API/jobs/$JOB/candidates/$BEST/impact-analysis" -H "Authorization: Bearer $BOSS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
s = d['simulation']
print('  time: %d -> %d pessoas | veredito: %s' % (s['current_team_size'], s['new_team_size'], d['verdict']))
for dim, delta in sorted(s['score_deltas'].items(), key=lambda kv: -kv[1])[:4]:
    print('  %-28s %.2f -> %.2f  (%+.2f)' % (dim, s['current_team_scores'].get(dim, 0), s['simulated_team_scores'][dim], delta))
for i in d['insights']:
    if i['contribution'] != 'NEUTRAL':
        print('  *', i['explanation'])
"

echo
echo "==> 9. Contratacao: o candidato entra no time e passa a compor o diagnostico"
curl -s -X POST "$API/jobs/$JOB/candidates/$BEST/hire" -H "Authorization: Bearer $BOSS" | jqp "'  status=%s' % d['status']"
curl -s "$API/teams/$TEAM/soft-skills-profile" -H "Authorization: Bearer $BOSS" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('  time agora tem %d pessoas' % d['member_count'])
print('  Colaboração: %.2f' % d['dimension_scores']['Colaboração'])
"
echo
echo "Fluxo completo executado."
