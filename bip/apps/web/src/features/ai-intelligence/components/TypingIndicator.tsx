type TypingIndicatorProps = {
  label?: string;
};

export function TypingIndicator({ label = "Analyzing context…" }: TypingIndicatorProps) {
  return (
    <div className="ai__typing" aria-label={label}>
      <span className="ai__typing-dots" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <span className="ai__typing-label">{label}</span>
    </div>
  );
}
