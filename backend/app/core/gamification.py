"""Camada de jogo do instrumento: níveis, ritmo e estimativa de duração.

A Etapa 5 do produto pede uma experiência gamificada — progressão por níveis,
feedback imediato, sequência e barra de conclusão. Este módulo define a parte
que é **do instrumento** (como os cenários se agrupam e quanto tempo o teste
deve levar); a parte que é de interface fica no frontend.

⚠️ **O que a gamificação daqui não faz, de propósito: dizer se a escolha foi
boa.** Todas as condutas de um cenário são profissionalmente defensáveis, e as
cargas nos fatores nunca chegam ao cliente (ver `app/schemas/questionnaire.py`).
Um "acertou!" estilo quiz exigiria uma alternativa correta — que é exatamente o
que o formato SJT existe para não ter, porque reintroduziria a resposta
socialmente desejável. Então o reforço é sempre de **progresso e ritmo**, nunca
de conteúdo: quantos cenários faltam, qual nível fechou, há quanto tempo a
pessoa está respondendo.

Os níveis também têm função de método, não só de engajamento: eles criam pontos
de parada explícitos. Quem cansa no cenário 12 fecha a aba num limite marcado e
volta — em vez de abandonar no meio de um bloco.
"""

from dataclasses import dataclass

# Cenários por nível. Cinco é curto o bastante para o primeiro nível terminar
# antes do cansaço aparecer e longo o bastante para não picotar o teste em
# comemorações a cada duas telas.
LEVEL_SIZE = 5

# **[PREMISSA]** O documento de visão fixa a duração-alvo em 10–15 min e manda
# validar com dado real (§Etapa 5). 35 s por cenário coloca os 20 itens em ~12
# min, dentro da faixa. Assim que `assessment_answers.elapsed_ms` acumular
# volume, este número deve ser trocado pela mediana observada — é para isso que
# o tempo por resposta é gravado.
ESTIMATED_SECONDS_PER_SCENARIO = 35


@dataclass(frozen=True)
class LevelSpec:
    """Rótulo de um nível.

    Os títulos descrevem o **tipo de situação**, nunca o traço que os itens
    medem. "Zona cinzenta" é seguro; "Nível da disciplina" entregaria a chave de
    correção do bloco inteiro e faria a pessoa responder pelo rótulo.
    """

    title: str
    subtitle: str


LEVEL_SPECS: tuple[LevelSpec, ...] = (
    LevelSpec(
        title="Quando algo aperta",
        subtitle="Prazo curto, sistema fora do ar e conversa difícil.",
    ),
    LevelSpec(
        title="Com outras pessoas",
        subtitle="Colegas, liderança e um problema que não é bem o seu.",
    ),
    LevelSpec(
        title="O trabalho de todo dia",
        subtitle="Processo, estimativa, rotina e quem acabou de chegar.",
    ),
    LevelSpec(
        title="Zona cinzenta",
        subtitle="Decisão sem dono, erro próprio e demanda além da conta.",
    ),
)


@dataclass(frozen=True)
class Level:
    """Um bloco de cenários já posicionado dentro de um instrumento concreto."""

    index: int
    title: str
    subtitle: str
    first_position: int
    question_count: int

    @property
    def last_position(self) -> int:
        return self.first_position + self.question_count - 1


def _spec_for(index: int) -> LevelSpec:
    """Rótulo do nível, com fallback para instrumentos maiores que os rótulos.

    O banco de itens é pequeno hoje (20 cenários) e a rotação prevista em §10.4
    do documento de visão vai aumentá-lo. Sem o fallback, o 5º bloco quebraria a
    montagem do questionário inteiro por falta de um título.
    """
    if index < len(LEVEL_SPECS):
        return LEVEL_SPECS[index]
    return LevelSpec(title=f"Rodada {index + 1}", subtitle="Mais cenários do mesmo instrumento.")


def level_index_for(ordinal: int) -> int:
    """Nível de um cenário pela sua ordem de exibição (0-based)."""
    return max(0, ordinal) // LEVEL_SIZE


def level_count(total_questions: int) -> int:
    return -(-max(0, total_questions) // LEVEL_SIZE)  # divisão para cima


def build_levels(total_questions: int) -> tuple[Level, ...]:
    """Divide um instrumento de `total_questions` itens em níveis.

    O último nível pode ficar menor que `LEVEL_SIZE` — um instrumento de 22
    cenários termina em um bloco de 2, e isso é preferível a esconder itens.
    """
    levels: list[Level] = []
    for index in range(level_count(total_questions)):
        first = index * LEVEL_SIZE
        spec = _spec_for(index)
        levels.append(
            Level(
                index=index,
                title=spec.title,
                subtitle=spec.subtitle,
                first_position=first,
                question_count=min(LEVEL_SIZE, total_questions - first),
            )
        )
    return tuple(levels)


def estimated_seconds(question_count: int) -> int:
    """Tempo estimado para responder `question_count` cenários."""
    return max(0, question_count) * ESTIMATED_SECONDS_PER_SCENARIO
