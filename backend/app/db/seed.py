"""Popula o banco com o instrumento padrão de diagnóstico comportamental.

Idempotente: pode rodar em toda subida da aplicação. Cenários, alternativas e
cargas nos fatores são sincronizados a partir de `app/core/big_five.py`, que é a
fonte de verdade do instrumento.

Uso:
    python -m app.db.seed
    make seed
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.big_five import (
    DEFAULT_QUESTIONNAIRE_DESCRIPTION,
    DEFAULT_QUESTIONNAIRE_TITLE,
    SJT_SCENARIOS,
)
from app.db.session import AsyncSessionLocal
from app.models.questionnaire import (
    OptionTraitLoading,
    Question,
    Questionnaire,
    QuestionOption,
)

logger = logging.getLogger(__name__)


async def seed_default_questionnaire(db: AsyncSession) -> Questionnaire:
    """Cria (ou atualiza) o instrumento SJT padrão ancorado em Big Five."""
    result = await db.execute(
        select(Questionnaire)
        .options(selectinload(Questionnaire.questions).selectinload(Question.options))
        .where(Questionnaire.is_default.is_(True))
    )
    questionnaire = result.scalars().first()

    if questionnaire is None:
        questionnaire = Questionnaire(
            title=DEFAULT_QUESTIONNAIRE_TITLE,
            description=DEFAULT_QUESTIONNAIRE_DESCRIPTION,
            is_default=True,
        )
        db.add(questionnaire)
        await db.flush()
        logger.info("Questionário padrão criado: %s", questionnaire.id)
        existing_by_text: dict[str, Question] = {}
    else:
        questionnaire.title = DEFAULT_QUESTIONNAIRE_TITLE
        questionnaire.description = DEFAULT_QUESTIONNAIRE_DESCRIPTION
        existing_by_text = {q.text: q for q in questionnaire.questions}

    created = 0
    for position, scenario in enumerate(SJT_SCENARIOS):
        question = existing_by_text.get(scenario.text)

        if question is None:
            question = Question(
                questionnaire_id=questionnaire.id,
                context=scenario.context,
                text=scenario.text,
                position=position,
            )
            db.add(question)
            await db.flush()
            created += 1
        else:
            question.context = scenario.context
            question.position = position

        await _sync_options(db, question, scenario)

    await db.commit()

    if created:
        logger.info("Seed: %d cenários adicionados ao instrumento padrão.", created)

    # Recarrega com itens, alternativas e cargas materializados: quem chama o
    # seed usa essas relações logo em seguida, e lazy loading em sessão async
    # estoura.
    reloaded = await db.execute(
        select(Questionnaire)
        .options(
            selectinload(Questionnaire.questions).selectinload(Question.options).selectinload(QuestionOption.loadings)
        )
        .where(Questionnaire.id == questionnaire.id)
    )
    return reloaded.scalar_one()


async def _sync_options(db: AsyncSession, question: Question, scenario) -> None:
    """Sincroniza alternativas e cargas de um cenário.

    A chave de correção pode mudar durante a calibração do instrumento, então o
    seed atualiza as cargas de alternativas já existentes em vez de só inserir.
    """
    result = await db.execute(select(QuestionOption).where(QuestionOption.question_id == question.id))
    existing = {option.text: option for option in result.scalars().all()}

    # Cargas carregadas por consulta direta em vez de por `option.loadings`:
    # a relação de uma alternativa recém-inserida dispararia lazy load, que não
    # funciona em sessão async.
    loadings_result = await db.execute(
        select(OptionTraitLoading).where(
            OptionTraitLoading.option_id.in_([o.id for o in existing.values()] or [question.id])
        )
    )
    by_option: dict[object, dict[str, OptionTraitLoading]] = {}
    for loading in loadings_result.scalars().all():
        by_option.setdefault(loading.option_id, {})[loading.trait] = loading

    for position, spec in enumerate(scenario.options):
        option = existing.get(spec.text)
        if option is None:
            option = QuestionOption(question_id=question.id, text=spec.text, position=position)
            db.add(option)
            await db.flush()
        else:
            option.position = position

        current = dict(by_option.get(option.id, {}))
        for trait, weight in spec.loadings.items():
            loading = current.pop(trait, None)
            if loading is None:
                db.add(OptionTraitLoading(option_id=option.id, trait=trait, weight=weight))
            else:
                loading.weight = weight

        # Cargas que saíram da definição do item não podem sobreviver no banco.
        for orphan in current.values():
            await db.delete(orphan)


async def run_seed() -> None:
    async with AsyncSessionLocal() as session:
        questionnaire = await seed_default_questionnaire(session)
        total_options = sum(len(s.options) for s in SJT_SCENARIOS)
        print(f"Instrumento padrão pronto: {questionnaire.id} — {questionnaire.title}")
        print(f"Cenários: {len(SJT_SCENARIOS)} | Alternativas: {total_options}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_seed())
