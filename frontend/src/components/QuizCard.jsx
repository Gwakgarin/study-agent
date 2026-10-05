import { useState } from "react";

const LABELS = ["A", "B", "C", "D", "E", "F"];

export default function QuizCard({ quiz, onAnswer }) {
  const [pending, setPending] = useState(null);
  const [error, setError] = useState(null);
  const answered = quiz.answered;

  async function pick(index) {
    if (answered || pending !== null) return;
    setPending(index);
    setError(null);
    try {
      await onAnswer(quiz.id, index);
    } catch (err) {
      setError(err.message || "채점하지 못했어요. 다시 눌러주세요.");
    } finally {
      setPending(null);
    }
  }

  function stateOf(index) {
    if (!answered) return pending === index ? "pending" : "";
    if (index === answered.answer_index) return "right";
    if (index === answered.choice) return "wrong";
    return "dim";
  }

  return (
    <div className="quiz-card">
      <div className="quiz-head">
        <span className="quiz-badge">퀴즈</span>
        {quiz.topic && <span className="quiz-topic">{quiz.topic}</span>}
      </div>
      <p className="quiz-question">{quiz.question}</p>
      <div className="quiz-choices" role="group" aria-label="보기">
        {quiz.choices.map((choice, i) => (
          <button
            key={i}
            type="button"
            className={`quiz-choice ${stateOf(i)}`}
            onClick={() => pick(i)}
            disabled={Boolean(answered) || pending !== null}
            aria-pressed={answered ? answered.choice === i : undefined}
          >
            <span className="quiz-label">{LABELS[i] ?? i + 1}</span>
            <span>{choice}</span>
          </button>
        ))}
      </div>
      {error && <div className="quiz-error">{error}</div>}
      {answered && (
        <div className={`quiz-result ${answered.correct ? "right" : "wrong"}`} role="status">
          <strong>{answered.correct ? "정답이에요!" : `아쉬워요. 정답은 ${LABELS[answered.answer_index]}예요.`}</strong>
          {answered.explanation && <p>{answered.explanation}</p>}
          {!answered.correct && <p className="quiz-note">이 주제는 약점 목록에 올라가고 복습 일정이 잡혀요.</p>}
        </div>
      )}
    </div>
  );
}
