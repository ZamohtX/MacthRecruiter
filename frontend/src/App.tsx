import { Navigate, Route, Routes, useLocation } from "react-router";
import type { ReactNode } from "react";

import { useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { Spinner } from "./components/ui";
import { ApplyPage, CandidateHome, InvitePage, MyAssessmentPage } from "./pages/AssessmentPages";
import { ImpactPage } from "./pages/ImpactPage";
import { JobDetailPage, JobsPage } from "./pages/JobDetailPage";
import { LoginPage } from "./pages/LoginPage";
import { TeamDetailPage } from "./pages/TeamDetailPage";
import { TeamsPage } from "./pages/TeamsPage";

/** Recrutador vê a lista de times; os demais, uma entrada direta ao teste. */
function Home() {
  const { user } = useAuth();
  return user?.role === "RECRUITER" ? <TeamsPage /> : <CandidateHome />;
}

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Spinner label="Verificando sessão…" />;
  if (!user) {
    // Preserva o destino para voltar a ele depois do login.
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      {/* Links de entrada de convidado e candidato ficam fora do layout
          autenticado: quem chega por eles ainda não tem sessão. */}
      <Route path="/convite/:inviteToken" element={<InvitePage />} />

      <Route element={<Layout />}>
        <Route path="/vaga/:jobId" element={<ApplyPage />} />

        <Route
          path="/"
          element={
            <RequireAuth>
              <Home />
            </RequireAuth>
          }
        />
        <Route
          path="/times/:teamId"
          element={
            <RequireAuth>
              <TeamDetailPage />
            </RequireAuth>
          }
        />
        <Route
          path="/vagas"
          element={
            <RequireAuth>
              <JobsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/vagas/:jobId"
          element={
            <RequireAuth>
              <JobDetailPage />
            </RequireAuth>
          }
        />
        <Route
          path="/vagas/:jobId/candidatos/:candidateId"
          element={
            <RequireAuth>
              <ImpactPage />
            </RequireAuth>
          }
        />
        <Route
          path="/meu-teste"
          element={
            <RequireAuth>
              <MyAssessmentPage />
            </RequireAuth>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
