import { useEffect, useMemo, useRef, useState } from "react";
import { appRoutes } from "../../app/routing/routes";
import { useCommandCenter } from "../../hooks/useCommandCenter";
import "./commandCenter.css";

export function CommandCenter() {
  const { isCommandCenterOpen, setCommandCenterOpen } = useCommandCenter();
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const close = () => setCommandCenterOpen(false);

  useEffect(() => {
    if (isCommandCenterOpen) {
      setQuery("");
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [isCommandCenterOpen]);

  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return [];
    }

    return appRoutes
      .filter(
        (route) =>
          route.label.toLowerCase().includes(normalized) ||
          route.path.toLowerCase().includes(normalized)
      )
      .slice(0, 8);
  }, [query]);

  if (!isCommandCenterOpen) {
    return null;
  }

  return (
    <div className="command-center" role="dialog" aria-modal="true" aria-label="Command center">
      <button
        className="command-center__backdrop"
        type="button"
        aria-label="Close command center"
        onClick={close}
      />
      <div className="command-center__panel">
        <input
          ref={inputRef}
          className="command-center__input"
          type="text"
          placeholder="Search pages, batteries, machines..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              close();
            }
          }}
        />
        <div className="command-center__results">
          {results.length > 0 ? (
            results.map((result) => (
              <div key={result.path} className="command-center__result">
                <span>{result.label}</span>
                <span className="command-center__hint">{result.path}</span>
              </div>
            ))
          ) : (
            <p className="command-center__hint">
              {query
                ? "No matches yet. Full search arrives in a later phase."
                : "Type to search. Results are placeholders in Phase 2.5."}
            </p>
          )}
        </div>
        <footer className="command-center__footer">
          <span>Esc to close</span>
          <span>Search results are placeholders</span>
        </footer>
      </div>
    </div>
  );
}
