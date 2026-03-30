import { Link } from 'react-router-dom';

export function NavBar() {
  return (
    <nav>
      <Link to="/">Search</Link>
      <Link to="/tracked">My Tracked Searches</Link>
    </nav>
  );
}
