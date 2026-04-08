import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { TrackedSearchesPage } from './pages/TrackedSearchesPage';
import { NavBar } from './components/NavBar';

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-sky-50 font-sans">
        <NavBar />
        <main className="max-w-5xl mx-auto px-4 py-8 pt-20">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/tracked" element={<TrackedSearchesPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
