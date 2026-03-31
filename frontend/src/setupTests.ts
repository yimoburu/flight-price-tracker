import '@testing-library/jest-dom';

// ResizeObserver is not available in jsdom; mock it for Recharts' ResponsiveContainer
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
