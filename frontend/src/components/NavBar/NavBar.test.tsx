import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { NavBar } from './index';

describe('NavBar', () => {
  it('renders a link with text "Search" that points to "/"', () => {
    render(<MemoryRouter><NavBar /></MemoryRouter>);
    const link = screen.getByRole('link', { name: 'Search' });
    expect(link).toHaveAttribute('href', '/');
  });

  it('renders a link with text "My Tracked Searches" that points to "/tracked"', () => {
    render(<MemoryRouter><NavBar /></MemoryRouter>);
    const link = screen.getByRole('link', { name: 'My Tracked Searches' });
    expect(link).toHaveAttribute('href', '/tracked');
  });

  it('renders the "FlightTracker" brand text', () => {
    render(<MemoryRouter><NavBar /></MemoryRouter>);
    expect(screen.getByText('FlightTracker')).toBeInTheDocument();
  });

  it('nav element has fixed positioning class', () => {
    render(<MemoryRouter><NavBar /></MemoryRouter>);
    const nav = screen.getByRole('navigation');
    expect(nav.className).toContain('fixed');
  });

  it('Search link is highlighted (active class) on the "/" route', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <NavBar />
      </MemoryRouter>
    );
    const searchLink = screen.getByRole('link', { name: 'Search' });
    expect(searchLink.className).toContain('border-b-2');
    expect(searchLink.className).toContain('border-sky-600');
  });

  it('Search link is NOT highlighted on the "/tracked" route', () => {
    render(
      <MemoryRouter initialEntries={['/tracked']}>
        <NavBar />
      </MemoryRouter>
    );
    const searchLink = screen.getByRole('link', { name: 'Search' });
    expect(searchLink.className).not.toContain('border-b-2');
  });

  it('"My Tracked Searches" link is highlighted on the "/tracked" route', () => {
    render(
      <MemoryRouter initialEntries={['/tracked']}>
        <NavBar />
      </MemoryRouter>
    );
    const trackedLink = screen.getByRole('link', { name: 'My Tracked Searches' });
    expect(trackedLink.className).toContain('border-b-2');
    expect(trackedLink.className).toContain('border-sky-600');
  });

  it('"My Tracked Searches" link is NOT highlighted on the "/" route', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <NavBar />
      </MemoryRouter>
    );
    const trackedLink = screen.getByRole('link', { name: 'My Tracked Searches' });
    expect(trackedLink.className).not.toContain('border-b-2');
  });
});
