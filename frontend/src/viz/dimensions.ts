/**
 * Ordem canônica das 10 soft skills — espelha `backend/app/core/soft_skills.py`
 * (`DIMENSIONS`). Os escores vêm da API como um dicionário sem ordem garantida;
 * fixar a sequência aqui é o que faz o polígono do radar ter a MESMA forma em
 * toda tela (sem isto, ImpactPage ordenava alfabético e o mesmo perfil desenharia
 * shapes diferentes em telas diferentes).
 */
export const DIMENSIONS = [
  "Comunicação",
  "Colaboração",
  "Disciplina e Organização",
  "Criatividade e Inovação",
  "Pensamento Analítico",
  "Adaptabilidade",
  "Liderança e Influência",
  "Proatividade e Autonomia",
  "Resiliência sob Pressão",
  "Aprendizado Contínuo",
] as const;

/**
 * Rótulo curto para o eixo do radar. O nome completo continua na tabela-gêmea e
 * no tooltip; ao redor do círculo, nomes longos se sobrepõem — a versão curta
 * mantém o eixo legível sem perder a identidade da dimensão.
 */
export const DIMENSION_SHORT: Record<string, string> = {
  "Comunicação": "Comunicação",
  "Colaboração": "Colaboração",
  "Disciplina e Organização": "Disciplina",
  "Criatividade e Inovação": "Criatividade",
  "Pensamento Analítico": "Analítico",
  "Adaptabilidade": "Adaptabilidade",
  "Liderança e Influência": "Liderança",
  "Proatividade e Autonomia": "Proatividade",
  "Resiliência sob Pressão": "Resiliência",
  "Aprendizado Contínuo": "Aprendizado",
};
