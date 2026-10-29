/**
 * Universal formatting utility for Hearsay percentages and telemetry metrics.
 * Strictly guarantees percentages are mathematically bounded between 0.0% and 100.0%.
 * Prevents double-multiplication bugs (e.g. 3333.0%, 5000.0%, 10000.0%).
 */

export function formatPercentage(val: number | string | undefined | null): string {
  if (val === undefined || val === null || val === '') return '0.0%';
  let num = Number(val);
  if (isNaN(num)) return '0.0%';

  // If fractional representation (0.0 < num <= 1.0), scale to 0-100%
  if (num > 0 && num <= 1.0) {
    num = num * 100;
  }

  // Mathematically bound strictly between 0 and 100
  const clamped = Math.min(100, Math.max(0, num));
  return `${clamped.toFixed(1)}%`;
}

export function clampPercentage(val: number | string | undefined | null): number {
  if (val === undefined || val === null || val === '') return 0;
  let num = Number(val);
  if (isNaN(num)) return 0;
  if (num > 0 && num <= 1.0) {
    num = num * 100;
  }
  return Math.min(100, Math.max(0, num));
}
