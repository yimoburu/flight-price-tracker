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
});
