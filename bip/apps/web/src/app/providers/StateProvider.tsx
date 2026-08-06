import type { ReactNode } from "react";

type StateProviderProps = {
  children: ReactNode;
};

export function StateProvider({ children }: StateProviderProps) {
  return <>{children}</>;
}
