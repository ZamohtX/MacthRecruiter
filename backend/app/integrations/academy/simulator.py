"""Orquestra o encontro alunos do Academy ↔ vaga do MatchRecruiter.

Fluxo, ponta a ponta, sobre alunos vindos da API (ou do roster sintético):

    1. importa cada aluno como usuário do MatchRecruiter;
    2. sorteia parte deles para formar o time e o restante vira candidato;
    3. todos respondem o mesmo diagnóstico comportamental (SJT);
    4. abre-se uma vaga sobre o time;
    5. cada candidato é ranqueado pelo **fit complementar** — quem mais cobre as
       lacunas do time e deixa o radar de competências mais regular fica no topo.

O passo 3 é o "realizar os testes neles": as respostas de cada pessoa são
sintetizadas de forma **determinística** a partir do seu id, então dois alunos
diferentes produzem perfis diferentes e o mesmo aluno produz sempre o mesmo
perfil — a demo e os testes ficam reproduzíveis.

Este módulo não fala HTTP: recebe uma lista de `AcademyAluno` já carregada. Quem
decide entre API real e roster sintético é a camada de cima (script/endpoint).
"""

import hashlib
import random
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.big_five import TRAITS
from app.integrations.academy.schemas import AcademyAluno
from app.models.questionnaire import Question, Questionnaire
from app.models.user import User, UserRole
from app.repositories.job_repository import JobRepository
from app.repositories.questionnaire_repository import AnswerInput, QuestionnaireRepository
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.services.fit_engine import team_profile_dispersion
from app.services.soft_skills_service import SoftSkillsService

# Domínio de e-mail sintético dos usuários importados. A API não expõe e-mail
# real (contato é intermediado pela coordenação), então derivamos um estável do
# id para servir de chave única sem inventar dado de contato.
_ACADEMY_EMAIL_DOMAIN = "academy.oxetech.local"


def _stable_unit(*parts: object) -> float:
    """Float determinístico em [0, 1) a partir dos argumentos.

    `hash()` do Python é randomizado por processo (PYTHONHASHSEED); sha256 dá o
    mesmo número em toda execução, que é o que torna o perfil reproduzível.
    """
    digest = hashlib.sha256(":".join(str(p) for p in parts).encode()).hexdigest()
    return int(digest[:8], 16) / 0x100000000


def derive_trait_preference(aluno: AcademyAluno) -> dict[str, float]:
    """Tendência de traços Big Five do aluno, derivada de id + tecnologias.

    Não é uma medida de verdade sobre a pessoa — é um perfil sintético estável
    que dá ao SJT um respondente com preferências próprias, para que o pool de
    candidatos tenha a diversidade que o motor de fit precisa para diferenciar.
    """
    tech_key = "|".join(sorted(aluno.techs)) or "sem-stack"
    return {trait: _stable_unit(aluno.id, tech_key, index) for index, trait in enumerate(TRAITS)}


def answers_for_preference(
    questions: list[Question], preference: dict[str, float], seed: int, spread: float = 0.35
) -> list[AnswerInput]:
    """Escolhe, em cada cenário, a conduta mais alinhada à preferência de traços.

    Mesma lógica do respondente simulado dos testes (`conftest.choose_options`):
    um pequeno favorecimento rotativo entre os fatores evita que a pessoa escolha
    o mesmo traço nas 20 situações — consistência que ninguém real tem.
    """
    inputs: list[AnswerInput] = []
    for index, question in enumerate(questions):
        boosted = TRAITS[index % len(TRAITS)]

        def affinity(option, boosted=boosted):
            return sum(
                (preference.get(trait, 0.0) + (spread if trait == boosted else 0.0)) * weight
                for trait, weight in option.loadings_map().items()
            )

        best = max(question.options, key=affinity)
        # Tempo por cenário plausível e determinístico (8–15 s) — dá insumo real
        # ao cronômetro/gamificação sem depender de relógio.
        elapsed_ms = 8000 + int(_stable_unit(seed, "elapsed", index) * 7000)
        inputs.append(AnswerInput(question_id=question.id, selected_option_id=best.id, elapsed_ms=elapsed_ms))
    return inputs


@dataclass
class RankedCandidate:
    aluno_id: int
    name: str
    techs: list[str]
    fit_score: float
    supplementary_fit_index: float
    verdict: str
    gaps_filled: list[str]
    gaps_missed: list[str]
    dispersion_after: float
    candidate_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class SimulationResult:
    source: str  # "academy_api" | "synthetic"
    team_name: str
    job_title: str
    team_members: list[str]
    team_scores: dict[str, float]
    dispersion_before: float
    respondent_count: int
    ranked: list[RankedCandidate]

    @property
    def best(self) -> RankedCandidate | None:
        return self.ranked[0] if self.ranked else None


class AcademyMatchSimulator:
    """Executa o fluxo completo dentro de uma sessão de banco já aberta."""

    def __init__(self, db: AsyncSession, questionnaire: Questionnaire):
        self.db = db
        self.questionnaire = questionnaire
        self.questions = list(questionnaire.questions)
        self.user_repo = UserRepository(db)
        self.team_repo = TeamRepository(db)
        self.job_repo = JobRepository(db)
        self.quest_repo = QuestionnaireRepository(db)
        self.soft = SoftSkillsService(db)

    async def _import_user(self, aluno: AcademyAluno, role: UserRole) -> User:
        email = f"aluno-{aluno.id}@{_ACADEMY_EMAIL_DOMAIN}"
        existing = await self.user_repo.get_by_email(email)
        if existing is not None:
            return existing
        return await self.user_repo.create(
            email=email, name=aluno.display_name, role=role, google_id=f"academy:{aluno.id}"
        )

    async def _take_assessment(self, user_id: UUID, aluno: AcademyAluno) -> None:
        preference = derive_trait_preference(aluno)
        await self.quest_repo.save_answers(user_id, answers_for_preference(self.questions, preference, aluno.id))

    async def run(
        self,
        alunos: list[AcademyAluno],
        *,
        team_size: int = 6,
        team_name: str = "Squad OxeTech",
        job_title: str = "Pessoa Desenvolvedora — vaga complementar",
        source: str = "academy_api",
        seed: int = 42,
    ) -> SimulationResult:
        if len(alunos) < team_size + 1:
            raise ValueError(
                f"Pool insuficiente: {len(alunos)} aluno(s) para um time de {team_size} mais ao menos 1 candidato."
            )

        pool = list(alunos)
        random.Random(seed).shuffle(pool)  # "equipe aleatória", porém reproduzível
        team_alunos = pool[:team_size]
        candidate_alunos = pool[team_size:]

        # O responsável pela vaga é de RH e não integra o time diagnosticado —
        # ver docstring de teams.create_team.
        recruiter = await self._recruiter(seed)
        team = await self.team_repo.create_team(name=team_name, owner_id=recruiter.id)

        for aluno in team_alunos:
            member = await self._import_user(aluno, UserRole.MEMBER)
            await self.team_repo.add_member(team.id, member.id)
            await self._take_assessment(member.id, aluno)

        team_profile = await self.soft.load_team_profile(team.id, self.questionnaire.id)

        job = await self.job_repo.create_job(
            title=job_title,
            team_id=team.id,
            questionnaire_id=self.questionnaire.id,
            description="Vaga gerada a partir do pool de talentos do OxeTech Academy.",
        )

        ranked: list[RankedCandidate] = []
        for aluno in candidate_alunos:
            candidate = await self._import_user(aluno, UserRole.CANDIDATE)
            await self.job_repo.create_application(job.id, candidate.id)
            await self._take_assessment(candidate.id, aluno)

            scores = await self.soft.get_user_soft_skills_profile(candidate.id, self.questionnaire.id)
            impact = self.soft.build_impact_response(
                job_id=job.id,
                candidate_id=candidate.id,
                candidate_name=aluno.display_name,
                candidate_scores=scores,
                team_profile=team_profile,
            )
            ranked.append(
                RankedCandidate(
                    aluno_id=aluno.id,
                    name=aluno.display_name,
                    techs=aluno.techs,
                    fit_score=impact.fit_score,
                    supplementary_fit_index=impact.supplementary_fit_index,
                    verdict=impact.verdict,
                    gaps_filled=impact.simulation.gaps_filled,
                    gaps_missed=impact.simulation.gaps_missed,
                    dispersion_after=team_profile_dispersion(impact.simulation.simulated_team_scores),
                    candidate_scores=scores,
                )
            )

        # Maior fit primeiro; empate desfeito pelo menor radar resultante (mais
        # regular) e depois pelo nome, para uma ordem estável.
        ranked.sort(key=lambda c: (-c.fit_score, c.dispersion_after, c.name))

        return SimulationResult(
            source=source,
            team_name=team_name,
            job_title=job_title,
            team_members=[a.display_name for a in team_alunos],
            team_scores=team_profile.dimension_scores,
            dispersion_before=team_profile_dispersion(team_profile.dimension_scores),
            respondent_count=team_profile.respondent_count,
            ranked=ranked,
        )

    async def _recruiter(self, seed: int) -> User:
        email = f"recrutador-{seed}@{_ACADEMY_EMAIL_DOMAIN}"
        existing = await self.user_repo.get_by_email(email)
        if existing is not None:
            return existing
        return await self.user_repo.create(
            email=email, name="Coordenação (RH)", role=UserRole.RECRUITER, google_id=f"academy-rh:{seed}"
        )
