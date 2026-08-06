import type { ReactNode } from "react";
import { cn } from "../../../lib/cn";

type ChatSidebarProps = {
  children: ReactNode;
  onClose: () => void;
  open: boolean;
};

export function ChatSidebar({ children, onClose, open }: ChatSidebarProps) {
  return (
    <>
      <aside className={cn("ai__sidebar", open && "ai__sidebar--open")} aria-label="Conversations sidebar">
        <button className="ai__sidebar-close" type="button" onClick={onClose}>
          Close
        </button>
        {children}
      </aside>
      {open ? <div className="ai__backdrop" onClick={onClose} aria-hidden="true" /> : null}
    </>
  );
}
