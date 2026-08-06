type PromptSuggestionsProps = {
  label?: string;
  onPick: (prompt: string) => void;
  prompts: string[];
};

export function PromptSuggestions({ label = "Suggested prompts", onPick, prompts }: PromptSuggestionsProps) {
  if (prompts.length === 0) {
    return null;
  }

  return (
    <div className="ai__suggestions" aria-label={label}>
      <p className="ai__kicker">{label}</p>
      <div className="ai__suggestions-list">
        {prompts.map((prompt) => (
          <button key={prompt} className="ai__suggestion-chip" type="button" onClick={() => onPick(prompt)}>
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
