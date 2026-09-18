import "@testing-library/jest-dom/vitest";

globalThis.IntersectionObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

globalThis.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

globalThis.matchMedia = () => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} });
HTMLElement.prototype.scrollIntoView = () => {};
