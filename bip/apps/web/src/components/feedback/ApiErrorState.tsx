import { EmptyState } from "../design-system";

type ApiErrorStateProps = {
  message?: string;
  onRetry?: () => void;
  className?: string;
};

export function ApiErrorState({ message = "Unable to load data", onRetry, className }: ApiErrorStateProps) {
  return (
    <EmptyState className={className}>
      <p>{message}</p>
      {onRetry ? (
        <button className="ds-button" type="button" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </EmptyState>
  );
}