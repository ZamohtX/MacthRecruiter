"""Camada latente Big Five e o banco de itens em formato SJT.

**Duas camadas, não duas alternativas.** Big Five é o *modelo de traço* — o que se
mede. SJT (Situational Judgment Test) é o *formato do item* — como se mede. Aqui
os dois se combinam: cada item apresenta uma situação de trabalho com alternativas
plausíveis, e cada alternativa carrega peso nos cinco fatores.

```
resposta SJT  →  5 fatores Big Five  →  10 soft skills observáveis  →  fit
  (o que a       (camada latente,       (camada de competência,        (produto)
   pessoa        com literatura)         legível para o gestor)
   escolhe)
```

Por que SJT em vez de escala Likert de autoavaliação:

* **Mais difícil de gamear.** Em "Sou uma pessoa organizada — 1 a 5" a resposta
  socialmente desejável é óbvia. Aqui todas as alternativas são condutas
  profissionais legítimas; não existe opção obviamente correta a marcar.
* **Mede julgamento aplicado**, não autoimagem.
* **Não coleta traço de personalidade declarado**, o que reduz a exposição a dado
  sensível sob LGPD frente a um inventário de personalidade tradicional.

⚠️ **Limitação de método (importante).** O formato de escolha forçada produz
medidas parcialmente *ipsativas*: escolher uma alternativa implica não escolher as
outras, então os escores de traço de uma pessoa são em parte relativos entre si.
Isso é conhecido por complicar comparação entre pessoas — que é justamente o que
este produto faz (candidato × média do time). Duas mitigações aplicadas:

1. As cargas são **graduadas e sobrepostas** (uma alternativa pode carregar 1.0 no
   fator primário e 0.4 num secundário), então a soma dos fatores não é constante
   entre respondentes — a medida é parcialmente ipsativa, não puramente.
2. A normalização é feita **por fator, contra o mínimo e o máximo teoricamente
   obteníveis naquele instrumento** (ver `app/services/scoring.py`), e não contra
   o total do respondente.

Isso reduz o problema; não o elimina. Validação empírica continua pendente —
ver `docs/visao-de-negocio.md` §10.3.
"""

from dataclasses import dataclass, field


class Trait:
    """Os cinco fatores. Todos orientados de forma que **maior = mais do traço**."""

    ABERTURA = "Abertura à Experiência"
    CONSCIENCIOSIDADE = "Conscienciosidade"
    EXTROVERSAO = "Extroversão"
    AMABILIDADE = "Amabilidade"
    # Polo positivo de Neuroticismo. Usar o polo positivo evita um fator em que
    # "nota alta" significa "pior", o que inverteria a leitura de lacuna do time.
    ESTABILIDADE = "Estabilidade Emocional"


TRAITS: tuple[str, ...] = (
    Trait.ABERTURA,
    Trait.CONSCIENCIOSIDADE,
    Trait.EXTROVERSAO,
    Trait.AMABILIDADE,
    Trait.ESTABILIDADE,
)

TRAIT_DESCRIPTIONS: dict[str, str] = {
    Trait.ABERTURA: "Interesse por ideias novas, tolerância à ambiguidade e disposição a explorar alternativas.",
    Trait.CONSCIENCIOSIDADE: "Organização, persistência, cuidado com detalhe e cumprimento de compromisso.",
    Trait.EXTROVERSAO: "Iniciativa social, assertividade e disposição a ocupar espaço na interação.",
    Trait.AMABILIDADE: "Cooperação, consideração pelo outro e disposição a preservar a relação.",
    Trait.ESTABILIDADE: "Regulação emocional sob pressão e recuperação após contrariedade.",
}


# ---------------------------------------------------------------------------
# Ponte Big Five → 10 soft skills
# ---------------------------------------------------------------------------
# Cada soft skill é uma combinação ponderada de fatores. Os pesos somam 1.0 por
# competência, de modo que uma soft skill derivada cai na mesma escala 1–5 dos
# fatores — e todos os limiares de `soft_skills.py` continuam válidos.
#
# Os pesos são uma proposta de produto informada pelo padrão da literatura
# (Conscienciosidade como preditor mais consistente de desempenho; Abertura
# ligada a criatividade e aprendizado; Amabilidade a trabalho em equipe).
# **Não são coeficientes empíricos** — precisam ser recalibrados contra dados de
# desempenho reais. Ver §10.3 do documento de visão.
SOFT_SKILL_LOADINGS: dict[str, dict[str, float]] = {
    "Comunicação": {Trait.EXTROVERSAO: 0.45, Trait.AMABILIDADE: 0.35, Trait.ABERTURA: 0.20},
    "Colaboração": {Trait.AMABILIDADE: 0.55, Trait.EXTROVERSAO: 0.25, Trait.ESTABILIDADE: 0.20},
    "Disciplina e Organização": {Trait.CONSCIENCIOSIDADE: 0.80, Trait.ESTABILIDADE: 0.20},
    "Criatividade e Inovação": {Trait.ABERTURA: 0.75, Trait.EXTROVERSAO: 0.25},
    "Pensamento Analítico": {Trait.ABERTURA: 0.45, Trait.CONSCIENCIOSIDADE: 0.55},
    "Adaptabilidade": {Trait.ABERTURA: 0.50, Trait.ESTABILIDADE: 0.50},
    "Liderança e Influência": {Trait.EXTROVERSAO: 0.45, Trait.ESTABILIDADE: 0.30, Trait.CONSCIENCIOSIDADE: 0.25},
    "Proatividade e Autonomia": {Trait.CONSCIENCIOSIDADE: 0.40, Trait.EXTROVERSAO: 0.35, Trait.ABERTURA: 0.25},
    "Resiliência sob Pressão": {Trait.ESTABILIDADE: 0.75, Trait.CONSCIENCIOSIDADE: 0.25},
    "Aprendizado Contínuo": {Trait.ABERTURA: 0.60, Trait.CONSCIENCIOSIDADE: 0.40},
}


@dataclass(frozen=True)
class SJTOption:
    """Uma alternativa de resposta e suas cargas nos fatores.

    `loadings` mapeia fator → carga em [0.0, 1.0]. Toda alternativa é uma conduta
    profissional defensável: a diferença entre elas é de *ênfase de traço*, não de
    qualidade. Alternativa obviamente melhor destrói a medida.
    """

    text: str
    loadings: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SJTScenario:
    context: str
    text: str
    options: tuple[SJTOption, ...]


_O, _C, _E, _A, _N = (
    Trait.ABERTURA,
    Trait.CONSCIENCIOSIDADE,
    Trait.EXTROVERSAO,
    Trait.AMABILIDADE,
    Trait.ESTABILIDADE,
)

# 20 cenários × 4 alternativas. Cada fator aparece como alternativa em 16 itens,
# o que dá cobertura equivalente entre os cinco.
SJT_SCENARIOS: tuple[SJTScenario, ...] = (
    SJTScenario(
        context="Prazo e dívida técnica",
        text=(
            "Faltam dois dias para a entrega e você percebe que a solução que construiu vai "
            "gerar retrabalho para o time em algumas semanas. O que você faz?"
        ),
        options=(
            SJTOption(
                "Entrego no prazo e registro a dívida com um plano concreto para a próxima sprint.", {_C: 1.0, _N: 0.3}
            ),
            SJTOption(
                "Levo a decisão para o time: prefiro que a escolha do trade-off seja coletiva.", {_A: 0.9, _E: 0.4}
            ),
            SJTOption("Proponho uma abordagem diferente que evita a dívida, mesmo mudando o plano agora.", {_O: 1.0}),
            SJTOption(
                "Absorvo o trabalho extra e resolvo os dois lados sem transformar isso em assunto.", {_N: 0.9, _C: 0.4}
            ),
        ),
    ),
    SJTScenario(
        context="Discordância técnica",
        text=(
            "Numa revisão de arquitetura, uma pessoa sênior defende uma abordagem que você "
            "considera errada. A sala parece concordar com ela. Sua reação?"
        ),
        options=(
            SJTOption("Exponho minha discordância ali mesmo, com o argumento técnico na mesa.", {_E: 1.0, _N: 0.4}),
            SJTOption("Escuto até o fim e busco entender o que ela enxerga que eu talvez não veja.", {_A: 1.0}),
            SJTOption("Peço um dia para levantar dados que sustentem ou derrubem minha posição.", {_C: 0.9, _O: 0.3}),
            SJTOption("Sugiro testar as duas abordagens num recorte pequeno antes de decidir.", {_O: 1.0, _C: 0.3}),
        ),
    ),
    SJTScenario(
        context="Incidente em produção",
        text="Sexta-feira, 18h, sistema fora do ar e a causa não está clara. Qual é seu primeiro movimento?",
        options=(
            SJTOption("Sigo o runbook passo a passo, sem pular etapa mesmo com pressão.", {_C: 1.0}),
            SJTOption("Assumo a comunicação: organizo quem faz o quê e mantenho todos informados.", {_E: 1.0, _A: 0.3}),
            SJTOption("Mantenho a calma e vou eliminando hipóteses uma a uma até achar a causa.", {_N: 1.0, _C: 0.3}),
            SJTOption("Testo uma hipótese não óbvia que pode explicar o comportamento inteiro.", {_O: 1.0}),
        ),
    ),
    SJTScenario(
        context="Feedback difícil",
        text="Você recebe uma crítica dura e pública sobre um trabalho no qual se dedicou bastante. Como responde?",
        options=(
            SJTOption("Agradeço, absorvo e sigo o dia sem que aquilo trave meu trabalho.", {_N: 1.0}),
            SJTOption("Peço exemplos concretos e transformo a crítica num plano de correção.", {_C: 0.9, _O: 0.3}),
            SJTOption("Procuro a pessoa depois para entender o ponto dela sem desgastar a relação.", {_A: 1.0}),
            SJTOption("Respondo na hora, apresentando o contexto que motivou minhas escolhas.", {_E: 0.9}),
        ),
    ),
    SJTScenario(
        context="Requisito ambíguo",
        text="Você recebe uma tarefa cujo escopo está claramente mal definido e quem pediu está indisponível hoje.",
        options=(
            SJTOption(
                "Começo pela parte que é certa e sigo, ajustando conforme a informação chegar.", {_O: 0.9, _N: 0.4}
            ),
            SJTOption("Escrevo as premissas que estou assumindo e valido por escrito antes de avançar.", {_C: 1.0}),
            SJTOption("Procuro outras pessoas que já lidaram com algo parecido para calibrar.", {_E: 0.8, _A: 0.4}),
            SJTOption("Aguardo a validação e uso o tempo em outra frente já definida.", {_C: 0.5, _A: 0.5}),
        ),
    ),
    SJTScenario(
        context="Colega com dificuldade",
        text="Alguém do time está claramente travado há dias e não pediu ajuda. Você tem suas próprias entregas apertadas.",
        options=(
            SJTOption("Ofereço ajuda direto, mesmo que isso me custe tempo hoje.", {_A: 1.0}),
            SJTOption("Chamo para uma conversa e proponho parear por um período definido.", {_E: 0.8, _A: 0.5}),
            SJTOption("Reorganizo minha semana para caber as duas coisas sem furar prazo.", {_C: 0.9, _N: 0.4}),
            SJTOption("Sugiro um caminho diferente do que a pessoa está tentando.", {_O: 0.9}),
        ),
    ),
    SJTScenario(
        context="Mudança de prioridade",
        text="Na terça a liderança muda a prioridade da sprint inteira. Metade do que você fez perde valor imediato.",
        options=(
            SJTOption("Sigo em frente sem me abalar; mudança de rota faz parte do trabalho.", {_N: 1.0}),
            SJTOption("Vejo a oportunidade de explorar algo novo que a mudança abriu.", {_O: 1.0}),
            SJTOption("Reorganizo o board e replanejo as entregas antes de continuar.", {_C: 1.0}),
            SJTOption("Levo ao grupo o custo da mudança para que a decisão seja consciente.", {_E: 0.9, _A: 0.3}),
        ),
    ),
    SJTScenario(
        context="Problema fora da sua área",
        text="Você encontra uma falha séria num sistema de outro time, que ninguém parece ter notado.",
        options=(
            SJTOption("Aviso o time responsável com o máximo de detalhe que consegui levantar.", {_C: 0.9, _A: 0.4}),
            SJTOption("Procuro a pessoa certa pessoalmente e garanto que o assunto não se perca.", {_E: 1.0}),
            SJTOption("Investigo um pouco mais para entender a extensão real antes de reportar.", {_O: 0.8, _C: 0.5}),
            SJTOption("Reporto pelo canal formal e sigo meu trabalho sem me envolver além disso.", {_C: 0.6, _N: 0.5}),
        ),
    ),
    SJTScenario(
        context="Apresentação para liderança",
        text="Você precisa apresentar um resultado ruim para a diretoria na semana que vem.",
        options=(
            SJTOption("Preparo os dados com rigor e antecipo as perguntas mais difíceis.", {_C: 1.0}),
            SJTOption("Apresento com naturalidade; sei conduzir a sala mesmo com notícia ruim.", {_E: 1.0, _N: 0.4}),
            SJTOption("Foco em enquadrar o resultado com o aprendizado e o próximo passo.", {_O: 0.8, _N: 0.4}),
            SJTOption("Alinho antes com as pessoas afetadas para ninguém ser surpreendido.", {_A: 1.0}),
        ),
    ),
    SJTScenario(
        context="Tecnologia nova",
        text="O time vai adotar uma tecnologia que você nunca usou e que muda bastante o seu dia a dia.",
        options=(
            SJTOption("Mergulho por conta própria antes mesmo de ser necessário.", {_O: 1.0, _C: 0.3}),
            SJTOption("Monto um plano de estudo com marcos e sigo até dominar.", {_C: 1.0}),
            SJTOption("Aprendo junto com o time, trocando dúvidas e descobertas.", {_A: 0.8, _E: 0.5}),
            SJTOption("Não me incomoda começar sem saber; vou aprendendo no caminho.", {_N: 0.9, _O: 0.4}),
        ),
    ),
    SJTScenario(
        context="Processo que não faz sentido",
        text="Existe um ritual no time que consome tempo e que você considera pouco útil.",
        options=(
            SJTOption("Proponho um formato alternativo para experimentarmos por algumas semanas.", {_O: 1.0}),
            SJTOption("Levanto o assunto abertamente na retrospectiva.", {_E: 1.0}),
            SJTOption("Sigo o processo enquanto ele for o combinado do time.", {_C: 0.7, _A: 0.7}),
            SJTOption("Levanto dados sobre o custo real antes de propor qualquer mudança.", {_C: 0.9, _O: 0.4}),
        ),
    ),
    SJTScenario(
        context="Conflito entre duas pessoas",
        text="Duas pessoas do time estão em atrito e isso começou a travar decisões.",
        options=(
            SJTOption("Converso com cada uma separadamente para entender os dois lados.", {_A: 1.0}),
            SJTOption("Trago o assunto à mesa e conduzo a conversa até um acordo.", {_E: 1.0, _N: 0.4}),
            SJTOption("Proponho um combinado objetivo de trabalho que independa da relação.", {_C: 0.9, _O: 0.3}),
            SJTOption("Mantenho o foco na entrega e não deixo o clima afetar meu trabalho.", {_N: 0.9}),
        ),
    ),
    SJTScenario(
        context="Estimativa furada",
        text="Você percebe na metade da tarefa que a estimativa que deu era otimista demais.",
        options=(
            SJTOption("Comunico imediatamente com uma nova estimativa fundamentada.", {_C: 1.0, _A: 0.3}),
            SJTOption("Busco um caminho mais curto que entregue o essencial no prazo original.", {_O: 0.9}),
            SJTOption("Peço ajuda ao time para recuperar o atraso.", {_A: 0.8, _E: 0.5}),
            SJTOption("Não me desespero; ajusto o ritmo e sigo trabalhando com clareza.", {_N: 1.0}),
        ),
    ),
    SJTScenario(
        context="Trabalho repetitivo",
        text="Sua semana está tomada por uma tarefa repetitiva e sem desafio, mas necessária.",
        options=(
            SJTOption("Faço com o mesmo cuidado do começo ao fim.", {_C: 1.0}),
            SJTOption("Procuro uma forma de automatizar ou eliminar parte disso.", {_O: 1.0}),
            SJTOption("Divido com quem também se beneficia do resultado.", {_A: 0.8, _E: 0.4}),
            SJTOption("Tarefa monótona não me desgasta; entrego e sigo em frente.", {_N: 1.0}),
        ),
    ),
    SJTScenario(
        context="Pessoa nova no time",
        text="Chegou alguém novo e o time está no meio de um período de entrega intensa.",
        options=(
            SJTOption("Me disponibilizo para acompanhar a pessoa nas primeiras semanas.", {_A: 1.0, _E: 0.3}),
            SJTOption("Organizo um roteiro de integração para não depender de improviso.", {_C: 1.0}),
            SJTOption("Puxo a pessoa para as conversas e reuniões desde o primeiro dia.", {_E: 1.0}),
            SJTOption("Dou a ela um problema real e interessante para aprender fazendo.", {_O: 0.9}),
        ),
    ),
    SJTScenario(
        context="Decisão sem dono",
        text="Uma decisão importante está parada porque ninguém assumiu a responsabilidade de tomá-la.",
        options=(
            SJTOption("Assumo a condução e levo a decisão até o fim.", {_E: 1.0, _C: 0.4}),
            SJTOption("Organizo as opções e os trade-offs por escrito para destravar.", {_C: 1.0, _O: 0.3}),
            SJTOption("Chamo as pessoas envolvidas para construir a decisão em conjunto.", {_A: 0.9, _E: 0.4}),
            SJTOption("Proponho uma alternativa que ninguém tinha colocado na mesa.", {_O: 1.0}),
        ),
    ),
    SJTScenario(
        context="Erro próprio com impacto",
        text="Um erro seu chegou ao cliente e gerou impacto visível.",
        options=(
            SJTOption("Assumo publicamente e conduzo a correção.", {_E: 0.9, _C: 0.5}),
            SJTOption("Faço a análise de causa e mudo o processo para não repetir.", {_C: 1.0}),
            SJTOption("Reconheço, corrijo e volto a produzir no mesmo dia.", {_N: 1.0}),
            SJTOption("Me preocupo em reparar a relação com quem foi afetado.", {_A: 1.0}),
        ),
    ),
    SJTScenario(
        context="Excesso de demanda",
        text="Três pessoas diferentes te pedem coisas urgentes no mesmo dia.",
        options=(
            SJTOption("Priorizo por critério explícito e comunico o que fica para depois.", {_C: 1.0}),
            SJTOption("Negocio prazo com cada uma para não deixar ninguém sem resposta.", {_A: 0.9, _E: 0.4}),
            SJTOption("Volume alto não me tira do sério; vou resolvendo em ordem.", {_N: 1.0}),
            SJTOption("Questiono se as três coisas precisam mesmo ser feitas como pedidas.", {_O: 0.9, _E: 0.3}),
        ),
    ),
    SJTScenario(
        context="Reunião improdutiva",
        text="Você está numa reunião longa que claramente não está chegando a lugar nenhum.",
        options=(
            SJTOption("Interrompo e proponho objetivamente um encaminhamento.", {_E: 1.0}),
            SJTOption("Registro os pontos e mando um resumo com próximos passos depois.", {_C: 1.0}),
            SJTOption("Sugiro mudar o formato da conversa para destravar a discussão.", {_O: 1.0}),
            SJTOption("Deixo a conversa seguir; às vezes o grupo precisa desse tempo.", {_A: 0.9, _N: 0.4}),
        ),
    ),
    SJTScenario(
        context="Reconhecimento do trabalho",
        text="Um resultado ao qual você contribuiu bastante é apresentado sem menção à sua participação.",
        options=(
            SJTOption("Falo diretamente com a pessoa para alinhar os créditos.", {_E: 0.9, _C: 0.3}),
            SJTOption("Não me abala; o que importa é o resultado ter saído.", {_N: 1.0}),
            SJTOption("Deixo passar para não criar desgaste com quem apresentou.", {_A: 1.0}),
            SJTOption("Passo a registrar melhor minhas contribuições daqui em diante.", {_C: 1.0}),
        ),
    ),
)

DEFAULT_QUESTIONNAIRE_TITLE = "Diagnóstico Comportamental — SJT ancorado em Big Five"
DEFAULT_QUESTIONNAIRE_DESCRIPTION = (
    "Instrumento padrão do MatchRecruiter. 20 situações de trabalho, cada uma com 4 condutas "
    "possíveis — todas profissionalmente defensáveis. A escolha é pontuada nos cinco fatores "
    "Big Five (Abertura, Conscienciosidade, Extroversão, Amabilidade e Estabilidade Emocional), "
    "e as 10 soft skills são derivadas desses fatores. Aplicado tanto ao time atual quanto aos "
    "candidatos, o que coloca os dois perfis na mesma régua."
)
