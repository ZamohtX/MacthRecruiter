"""Camada de competências observáveis e limiares do diagnóstico.

As 10 soft skills daqui **não são medidas diretamente**: são derivadas dos cinco
fatores Big Five, que por sua vez vêm das escolhas do respondente no teste
situacional (SJT). A cadeia completa é:

    resposta SJT → fatores Big Five → soft skills → lacuna / fit

* Formato dos itens e cargas dos fatores: `app/core/big_five.py`
* Aritmética da conversão: `app/services/scoring.py`

Este módulo guarda os nomes das competências e os limiares usados pelo
diagnóstico do time e pelo motor de fit — não duplicar essas constantes.

⚠️ O framework é uma proposta de produto e **não** um instrumento
psicometricamente validado. Ver `docs/visao-de-negocio.md` §10.3.
"""

# Escala em que os fatores e as competências derivadas são expressos.
SCALE_MIN = 1.0
SCALE_MAX = 5.0

# Ponto médio da escala. Com o instrumento SJT ancorado no acaso, 3.0 significa
# "escolhe as condutas deste fator na frequência que o acaso produziria".
SCALE_MIDPOINT = 3.0

# Quantos desvios-padrão do próprio perfil do time uma dimensão precisa estar
# afastada do centro para virar LACUNA ou FORÇA. Meio desvio é a convenção usual
# de "diferença perceptível"; é uma calibração a validar com dado real, não um
# valor derivado.
RELATIVE_BAND = 0.5

# Abaixo desta dispersão o perfil do time é considerado uniforme: forte (ou
# fraco) na mesma medida em tudo, sem nada a priorizar por complementaridade.
MIN_MEANINGFUL_SPREAD = 0.15

# Piso mínimo absoluto para o candidato em qualquer dimensão — bem abaixo do
# nível de acaso. Contratar alguém abaixo disso numa competência que o time
# também não tem deixa o buraco aberto; é o guarda-corpo de "piso de competência
# mínima por função". Ao contrário da classificação de lacuna, este limiar é
# absoluto de propósito: mede ausência da competência, não posição relativa.
MIN_CANDIDATE_FLOOR = 2.0

# Nº mínimo de respondentes para o diagnóstico do time ser estatisticamente
# apresentável. Abaixo disso o resultado sai marcado como baixa confiança.
MIN_RESPONDENTS_FOR_CONFIDENCE = 4


class Dimension:
    """Nomes canônicos das dimensões. Usados como chave em todos os dicts."""

    COMUNICACAO = "Comunicação"
    COLABORACAO = "Colaboração"
    DISCIPLINA = "Disciplina e Organização"
    CRIATIVIDADE = "Criatividade e Inovação"
    ANALITICO = "Pensamento Analítico"
    ADAPTABILIDADE = "Adaptabilidade"
    LIDERANCA = "Liderança e Influência"
    PROATIVIDADE = "Proatividade e Autonomia"
    RESILIENCIA = "Resiliência sob Pressão"
    APRENDIZADO = "Aprendizado Contínuo"


DIMENSIONS: tuple[str, ...] = (
    Dimension.COMUNICACAO,
    Dimension.COLABORACAO,
    Dimension.DISCIPLINA,
    Dimension.CRIATIVIDADE,
    Dimension.ANALITICO,
    Dimension.ADAPTABILIDADE,
    Dimension.LIDERANCA,
    Dimension.PROATIVIDADE,
    Dimension.RESILIENCIA,
    Dimension.APRENDIZADO,
)

DIMENSION_DESCRIPTIONS: dict[str, str] = {
    Dimension.COMUNICACAO: "Clareza escrita e verbal, documentação e alinhamento com outras pessoas.",
    Dimension.COLABORACAO: "Trabalho em conjunto, code review, pareamento e resolução de conflito.",
    Dimension.DISCIPLINA: "Cumprimento de prazo, consistência de entrega e organização do próprio trabalho.",
    Dimension.CRIATIVIDADE: "Proposição de alternativas, exploração de caminhos não óbvios.",
    Dimension.ANALITICO: "Decomposição de problemas, uso de dado e rigor na tomada de decisão.",
    Dimension.ADAPTABILIDADE: "Resposta a mudança de escopo, prioridade ou contexto.",
    Dimension.LIDERANCA: "Condução sem autoridade formal, mentoria e influência sobre decisões.",
    Dimension.PROATIVIDADE: "Iniciativa sem direcionamento explícito e autonomia de execução.",
    Dimension.RESILIENCIA: "Comportamento em incidente, prazo crítico e situação de pressão.",
    Dimension.APRENDIZADO: "Aquisição deliberada de novas competências e absorção de feedback.",
}

# `DIMENSIONS` fixa a ordem de exibição das competências. As competências em si
# são as chaves de `big_five.SOFT_SKILL_LOADINGS` — a consistência entre as duas
# listas é garantida por teste, para que adicionar uma competência sem definir
# suas cargas nos fatores quebre o build em vez de sair silenciosamente com nota
# ausente no diagnóstico.
