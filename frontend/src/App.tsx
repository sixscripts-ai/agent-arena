import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import SiteHeader from "@/components/SiteHeader";
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import Providers from "@/pages/Providers";
import NewBattle from "@/pages/NewBattle";
import LiveBattle from "@/pages/LiveBattle";
import Leaderboard from "@/pages/Leaderboard";
import History from "@/pages/History";
import DesignOptions from "@/pages/DesignOptions";
import DesignMockup from "@/pages/DesignMockup";
import { useEffect } from "react";
import { subscribeSystemTheme } from "@/lib/theme";

export default function App() {
  useEffect(() => {
    return subscribeSystemTheme();
  }, []);

  return (
    <Router>
      <SiteHeader />
      <main className="relative mx-auto max-w-[1440px] px-5 py-7 md:px-8 md:py-10">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/providers" element={<Providers />} />
          <Route path="/battles/new" element={<NewBattle />} />
          <Route path="/battles/:id" element={<LiveBattle />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/history" element={<History />} />
          <Route path="/design" element={<DesignOptions />} />
          <Route path="/design/battle" element={<DesignMockup />} />
          <Route path="*" element={<div className="card p-10 text-center text-[13px] text-muted">404 — Not found</div>} />
        </Routes>
      </main>
    </Router>
  );
}
