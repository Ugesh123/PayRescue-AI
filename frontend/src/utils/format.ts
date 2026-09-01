export function formatCurrency(amountInPaise: number, currency: string = "INR"): string {
  const amount = amountInPaise / 100;
  return new Intl.NumberFormat("en-IN", { style: "currency", currency }).format(amount);
}

export function formatDateTime(isoString: string): string {
  return new Date(isoString).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function titleCase(value: string): string {
  return value
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
