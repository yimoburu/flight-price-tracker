import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { TrackedSearchesPage } from './pages/TrackedSearchesPage';
import { NavBar } from './components/NavBar';

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/tracked" element={<TrackedSearchesPage />} />
      </Routes>
    </BrowserRouter>
  );
}
