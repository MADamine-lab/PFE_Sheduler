import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import LoginScreen from "./components/LoginScreen";
import AdminPage from "./pages/AdminPage";
import EtudiantPage from "./pages/EtudiantPage";
import ProfPage from "./pages/ProfPage";
import issatLogo from "./assets/ISSATSO-logo.jpg";
import api from "./auth/api";
import { useEffect } from "react";



const rolePaths = {
  admin: "/admin",
  etudiant: "/etudiant",
  prof: "/prof",
};

function LoginRoute() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [loginError, setLoginError] = useState("");

  return (
    <LoginScreen
      logoSrc={issatLogo}
      loginError={loginError}
      onSubmit={async ({ email, password }) => {
        setLoginError("");
        try {
          const me = await login(email, password);
          const role = me?.role || (me?.is_superuser ? "admin" : me?.is_staff ? "prof" : "etudiant");
          navigate(rolePaths[role] || "/", { replace: true });
        } catch (err) {
          setLoginError(err.message);
        }
      }}
      onForgotPassword={() => {}}
      onRegister={() => {}}
    />
  );
}

function PrivateRoute({ children, roles }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Chargement...</div>;
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  const role = user?.role || (user.is_superuser ? "admin" : user.is_staff ? "prof" : "etudiant");
  if (roles && !roles.includes(role)) {
    return <Navigate to="/" replace />;
  }

  return children;
}

// Définir DOMAIN_COLORS ici
export const DOMAIN_COLORS = {
  'Informatique': 'bg-blue-100 text-blue-800',
  'Electrique':   'bg-green-100 text-green-800',
  'Mecanique':    'bg-amber-100 text-amber-800',
  'Energetique':  'bg-red-100 text-red-800',
  'Genie Civil':  'bg-purple-100 text-purple-800',
};

function App() {

  useEffect(() => {
  api.get("/auth/csrf/").catch(() => {}); // ← silent fail
  }, []);

  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginRoute />} />
          <Route
            path="/admin/*"
            element={<PrivateRoute roles={["admin"]}><AdminPage /></PrivateRoute>}
          />
          <Route
            path="/etudiant"
            element={<PrivateRoute roles={["etudiant"]}><EtudiantPage /></PrivateRoute>}
          />
          <Route
            path="/prof"
            element={<PrivateRoute roles={["prof"]}><ProfPage /></PrivateRoute>}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

