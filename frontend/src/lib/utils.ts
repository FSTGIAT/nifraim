// Tiny shadcn-style cn() — joins truthy class names with spaces.
// We don't pull clsx/tailwind-merge because the project isn't on Tailwind;
// downstream components ship their own scoped CSS instead.
export function cn(...inputs: Array<string | false | null | undefined>): string {
  return inputs.filter(Boolean).join(' ')
}
