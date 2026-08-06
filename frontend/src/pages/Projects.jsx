import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Logo from "../components/Logo.jsx";
import { createProject, fetchProjects } from "../api.js";

export default function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState(null);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
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
    } catch {
      setError("프로젝트를 만들지 못했어요. 서버가 켜져 있는지 확인해주세요.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="projects-page">
      <nav className="navbar">
        <Link to="/">
          <Logo size={28} />
        </Link>
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
          <div className="empty-state projects-empty">
            아직 만든 과목이 없어요. 위에서 첫 과목을 만들어보세요.
          </div>
        ) : (
          <div className="project-grid">
            {projects.map((p) => (
              <Link to={`/app/${p.id}`} className="project-card" key={p.id}>
                <div className="project-card-name">{p.name}</div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
