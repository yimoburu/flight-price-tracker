import { Link, useLocation } from 'react-router-dom';
import { Plane } from 'lucide-react';

export function NavBar() {
  const location = useLocation();

  const activeClass = 'text-sky-600 font-medium border-b-2 border-sky-600 pb-0.5';
  const inactiveClass = 'text-neutral-600 hover:text-sky-600 transition-colors';

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-14 bg-white border-b border-neutral-200 shadow-sm">
      <div className="max-w-5xl mx-auto px-4 h-full flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Plane className="h-5 w-5 text-sky-600" />
          <span className="font-bold text-sky-600 text-lg">FlightTracker</span>
        </div>
        <div className="flex items-center gap-6">
          <Link
            to="/"
            className={location.pathname === '/' ? activeClass : inactiveClass}
          >
            Search
          </Link>
          <Link
            to="/tracked"
            className={location.pathname === '/tracked' ? activeClass : inactiveClass}
          >
            My Tracked Searches
          </Link>
        </div>
      </div>
    </nav>
  );
}
