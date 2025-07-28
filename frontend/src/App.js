import React, { useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import LandingPage from "./components/LandingPage";
import MapPage from "./components/MapPage";
import CommunePage from "./components/CommunePage";
import WeatherAnimationDemo from "./components/WeatherAnimationDemo";
import VigilancePreview from "./components/VigilancePreview";
import { Toaster } from "./components/ui/toaster";
import { useVigilanceTheme } from "./hooks/useVigilanceTheme";

function App() {
  const { theme, loading, error } = useVigilanceTheme();

  useEffect(() => {
    // Appliquer les styles de vigilance au body
    if (theme && !loading && !error) {
      document.body.className = `vigilance-${theme.level}`;
      
      // Mettre à jour les variables CSS globales
      const root = document.documentElement;
      root.style.setProperty('--vigilance-primary', theme.primary_color);
      root.style.setProperty('--vigilance-level', theme.level);
      
      // Ajouter une classe CSS pour les transitions
      root.classList.add('vigilance-theme-active');
    }
  }, [theme, loading, error]);

  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/commune/:slug" element={<CommunePage />} />
          <Route path="/demo" element={<WeatherAnimationDemo />} />
          <Route path="/vigilance" element={<VigilancePreview />} />
        </Routes>
        <Toaster />
      </BrowserRouter>
    </div>
  );
}

export default App;