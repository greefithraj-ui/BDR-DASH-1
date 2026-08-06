function pad(value: number, width = 2): string {
  return String(value).padStart(width, "0");
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function formatDate(iso: string): string {
  return formatDateTime(iso).slice(0, 10);
}

export function formatTime(iso: string): string {
  return formatDateTime(iso).slice(11);
}

export function toDisplayCount(value: number): string {
  return value.toLocaleString("en-US");
}
