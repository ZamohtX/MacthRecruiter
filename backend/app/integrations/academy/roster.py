"""Pool de talentos sintético — usado quando a API do Academy não devolve alunos.

Por que existe: a API é real e o token autentica (o `/ping` responde), mas o
programa pode estar entre turmas, com nenhum aluno marcado como disponível. Foi
exatamente o que observamos em 26/07/2026 — `stats` e `alunos` vieram zerados.
Sem um fallback, a demonstração de "montar time e ranquear candidatos" não teria
dado nenhum para percorrer.

O roster é **determinístico** (sem aleatoriedade): os mesmos alunos, com os
mesmos ids, saem em toda execução — o que torna a demo e os testes reproduzíveis.
Os registros seguem o mesmo schema `AcademyAluno` da API real, então o restante
do pipeline não sabe (nem precisa saber) se a origem foi a rede ou este arquivo.
"""

from app.integrations.academy.schemas import AcademyAluno

# Nomes e stacks plausíveis de egressos do Academy. A ordem é fixa de propósito.
_SEED_ALUNOS: tuple[tuple[str, tuple[str, ...], str, str], ...] = (
    ("Ana Beatriz Cavalcante", ("Python", "Django", "PostgreSQL"), "Remoto", "Noite"),
    ("Carlos Henrique Tenório", ("React", "TypeScript", "Node.js"), "Presencial", "Manhã"),
    ("Mariana Lopes Vasconcelos", ("Flutter", "Dart", "Firebase"), "Remoto", "Tarde"),
    ("João Pedro Malta", ("Java", "Spring", "MySQL"), "Híbrido", "Noite"),
    ("Larissa Ferreira Acioli", ("Python", "FastAPI", "Docker"), "Remoto", "Manhã"),
    ("Rafael Gomes Buarque", ("Go", "Kubernetes", "gRPC"), "Presencial", "Tarde"),
    ("Beatriz Santos Wanderley", ("React", "Next.js", "Tailwind"), "Remoto", "Noite"),
    ("Lucas Almeida Correia", ("Node.js", "Express", "MongoDB"), "Híbrido", "Manhã"),
    ("Gabriela Nunes Peixoto", ("Data Science", "Python", "Pandas"), "Remoto", "Tarde"),
    ("Matheus Rocha Sarmento", ("C#", ".NET", "Azure"), "Presencial", "Noite"),
    ("Isabela Duarte Melo", ("UX", "Figma", "React"), "Remoto", "Manhã"),
    ("Pedro Lucas Barros", ("PHP", "Laravel", "MySQL"), "Híbrido", "Tarde"),
    ("Camila Souza Lira", ("Python", "Machine Learning", "TensorFlow"), "Remoto", "Noite"),
    ("Vinícius Torres Amorim", ("Vue.js", "JavaScript", "Nuxt"), "Presencial", "Manhã"),
    ("Amanda Ribeiro Calheiros", ("Android", "Kotlin", "Jetpack"), "Remoto", "Tarde"),
    ("Thiago Mendonça Farias", ("DevOps", "Terraform", "AWS"), "Híbrido", "Noite"),
    ("Letícia Barbosa Goulart", ("QA", "Cypress", "Selenium"), "Remoto", "Manhã"),
    ("Bruno Cavalcanti Leão", ("Rust", "WebAssembly", "Actix"), "Presencial", "Tarde"),
    ("Sofia Andrade Pontes", ("React Native", "TypeScript", "Expo"), "Remoto", "Noite"),
    ("Daniel Oliveira Ramalho", ("Python", "Airflow", "Spark"), "Híbrido", "Manhã"),
    ("Juliana Costa Meireles", ("Angular", "RxJS", "NgRx"), "Remoto", "Tarde"),
    ("Felipe Nogueira Tavares", ("Elixir", "Phoenix", "PostgreSQL"), "Presencial", "Noite"),
    ("Natália Freitas Sampaio", ("Data Engineering", "SQL", "dbt"), "Remoto", "Manhã"),
    ("Guilherme Aragão Pires", ("Swift", "iOS", "SwiftUI"), "Híbrido", "Tarde"),
)

# Base de id acima da faixa real observada, para deixar óbvio no log que o
# registro é sintético e nunca colidir com um id vindo da API.
_SYNTHETIC_ID_BASE = 900_000


def synthetic_talent_pool(size: int | None = None) -> list[AcademyAluno]:
    """Devolve alunos sintéticos determinísticos (todos marcados `disponivel`)."""
    rows = _SEED_ALUNOS if size is None else _SEED_ALUNOS[: max(0, size)]
    return [
        AcademyAluno(
            id=_SYNTHETIC_ID_BASE + index,
            nome=nome,
            techs=list(techs),
            modalidade=modalidade,
            turno=turno,
            disponivel=True,
        )
        for index, (nome, techs, modalidade, turno) in enumerate(rows)
    ]
