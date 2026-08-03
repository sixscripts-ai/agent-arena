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

export default function App() {
  return (
    <Router>
      <SiteHeader />
      <main className="mx-auto max-w-[1360px] px-6 py-8">
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
          <Route path="*" element={<div className="p-8 text-center">404 — Not found</div>} />
        </Routes>
      </main>
    </Router>
  );
}
