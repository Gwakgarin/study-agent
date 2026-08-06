import { BrowserRouter, Routes, Route } from "react-router-dom";
import Landing from "./pages/Landing.jsx";
import Projects from "./pages/Projects.jsx";
import ChatApp from "./pages/ChatApp.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/app" element={<Projects />} />
        <Route path="/app/:projectId" element={<ChatApp />} />
      </Routes>
    </BrowserRouter>
  );
}
