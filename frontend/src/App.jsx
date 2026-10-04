import { BrowserRouter, Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import Projects from "./pages/Projects.jsx";
import ChatApp from "./pages/ChatApp.jsx";
import Login from "./pages/Login.jsx";
import RequireAuth from "./components/RequireAuth.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/app" element={<RequireAuth><Projects /></RequireAuth>} />
        <Route path="/app/:projectId" element={<RequireAuth><ChatApp /></RequireAuth>} />
      </Routes>
    </BrowserRouter>
  );
}
