import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { fetchMe, startGuest } from "../api.js";
import SaveProgress from "./SaveProgress.jsx";

const UserContext = createContext(null);

export function useUser() {
  return useContext(UserContext).user;
}

// Lets any screen open the "save progress" dialog, e.g. when a guest tries to upload.
export function useSaveProgress() {
  return useContext(UserContext).openSave;
}

export default function RequireAuth({ children }) {
  const location = useLocation();
  const [state, setState] = useState({ status: "loading", user: null, notice: null });
  const [saveOpen, setSaveOpen] = useState(false);

  useEffect(() => {
    // No login yet: start as a guest so the app can be tried without signing up.
    fetchMe()
      .catch(() => startGuest())
      .then((user) => setState({ status: "in", user }))
      // e.g. this address already started today's share of guests: explain on the login page.
      .catch((err) => setState({ status: "out", user: null, notice: err.status === 429 ? err.message : null }));
  }, []);

  if (state.status === "loading") return null;
  if (state.status === "out") {
    return <Navigate to="/login" replace state={{ from: location.pathname, notice: state.notice }} />;
  }

  const value = { user: state.user, openSave: () => setSaveOpen(true) };
  return (
    <UserContext.Provider value={value}>
      {state.user.is_guest && <GuestBar onSave={value.openSave} />}
      {children}
      {saveOpen && (
        <SaveProgress
          onClose={() => setSaveOpen(false)}
          onSaved={(user) => {
            setState({ status: "in", user });
            setSaveOpen(false);
          }}
        />
      )}
    </UserContext.Provider>
  );
}

function GuestBar({ onSave }) {
  return (
    <div className="guest-bar" role="status">
      <span>게스트로 둘러보는 중이에요. 기록을 저장하면 다른 기기에서도 이어서 복습할 수 있어요.</span>
      <button type="button" onClick={onSave}>
        기록 저장하기
      </button>
    </div>
  );
}
