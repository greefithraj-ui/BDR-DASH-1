const API_FAILURE_PATTERN = /status (\d+)/;

export function describeApiError(error: unknown): string {
  if (error instanceof TypeError) {
    return "Unable to reach API";
  }

  const message = error instanceof Error ? error.message : "";
  const match = message.match(API_FAILURE_PATTERN);
  const status = match ? Number(match[1]) : null;

  if (status === 500) {
    return "Database unavailable";
  }

  if (status === 502 || status === 503 || status === 504) {
    return "Collector unavailable";
  }

  return "Unable to load data";
}
