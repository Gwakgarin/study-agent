import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Logo from "../components/Logo.jsx";
import { useUser } from "../components/RequireAuth.jsx";
import { AuthRequiredError, createProject, createSampleProject, fetchProjects, logout } from "../api.js";

function ProjectCard({ project }) {
  const practised = project.attempts > 0;
  return (
    <Link to={`/app/${project.id}`} className="project-card">
      <div className="project-card-top">
        <div className="project-card-name">{project.name}</div>
        {project.due > 0 && <span className="due-badge">복습 {project.due}</span>}
      </div>
      <dl className="project-stats">
        <div>
          <dt>노트</dt>
          <dd>{project.notes}개</dd>
        </div>
        <div>
          <dt>푼 문제</dt>
          <dd>{project.attempts}개</dd>
        </div>
        <div>
          <dt>정답률</dt>
          <dd>{practised ? `${Math.round(project.accuracy * 100)}%` : "-"}</dd>
        </div>
      </dl>
      {practised && (
        <div className="accuracy-track" aria-hidden="true">
          <div className="accuracy-fill" style={{ width: `${project.accuracy * 100}%` }} />
        </div>
      )}
    </Link>
  );
}

export default function Projects() {
  const navigate = useNavigate();
  const user = useUser();
  const [projects, setProjects] = useState(null);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [preparingSample, setPreparingSample] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchProjects()
      .then(setProjects)
      .catch(() => setProjects([]));
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || creating) return;
    setCreating(true);
    setError(null);
    try {
      const project = await createProject(trimmed);
      navigate(`/app/${project.id}`);
    } catch (err) {
      if (err instanceof AuthRequiredError) {
        navigate("/login", { replace: true });
        return;
      }
      setError("프로젝트를 만들지 못했어요. 서버가 켜져 있는지 확인해주세요.");
    } finally {
      setCreating(false);
    }
  }

  async function handleSample() {
    setPreparingSample(true);
    setError(null);
    try {
      const project = await createSampleProject();
      navigate(`/app/${project.id}`);
    } catch (err) {
      if (err instanceof AuthRequiredError) {
        navigate("/login", { replace: true });
        return;
      }
      setError(err.message || "샘플 과목을 만들지 못했어요.");
    } finally {
      setPreparingSample(false);
    }
  }

  async function handleLogout() {
    await logout().catch(() => {});
    navigate("/login", { replace: true });
  }

  return (
    <div className="projects-page">
      <nav className="navbar">
        <Link to="/">
          <Logo size={28} />
        </Link>
        <div className="nav-user">
          <span>{user.username}</span>
          <button type="button" onClick={handleLogout}>
            로그아웃
          </button>
        </div>
      </nav>

      <div className="projects-content">
        <h1>어떤 과목을 공부할까요?</h1>
        <p className="projects-sub">
          과목마다 노트와 약점 기록이 따로 관리돼요. 새 과목을 만들거나 이어서 공부할 과목을 골라주세요.
        </p>

        <form className="project-create" onSubmit={handleCreate}>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="예: 생물학, 알고리즘, 토익..."
            disabled={creating}
          />
          <button type="submit" className="btn-primary" disabled={creating || !name.trim()}>
            {creating ? "만드는 중..." : "새 과목 만들기"}
          </button>
        </form>
        {error && <div className="error-banner">{error}</div>}

        {projects === null ? null : projects.length === 0 ? (
          <div className="sample-cta">
            <div>
              <div className="sample-title">처음이라면 샘플 과목으로 먼저 체험해보세요</div>
              <p>SQLD 개념 노트 6개가 미리 들어 있어요. 질문하고, 퀴즈를 풀고, 약점이 쌓이는 흐름을 바로 볼 수 있어요.</p>
            </div>
            <button type="button" className="btn-primary" onClick={handleSample} disabled={preparingSample}>
              {preparingSample ? "준비하는 중..." : "샘플 과목 열기"}
            </button>
          </div>
        ) : (
          <div className="project-grid">
            {projects.map((p) => (
              <ProjectCard project={p} key={p.id} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
