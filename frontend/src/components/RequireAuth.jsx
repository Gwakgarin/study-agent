import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { fetchMe } from "../api.js";

const UserContext = createContext(null);

export function useUser() {
  return useContext(UserContext);
}

export default function RequireAuth({ children }) {
  const location = useLocation();
  const [state, setState] = useState({ status: "loading", user: null });

  useEffect(() => {
    fetchMe()
      .then((user) => setState({ status: "in", user }))
      .catch(() => setState({ status: "out", user: null }));
  }, []);

  if (state.status === "loading") return null;
  if (state.status === "out") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <UserContext.Provider value={state.user}>{children}</UserContext.Provider>;
}
