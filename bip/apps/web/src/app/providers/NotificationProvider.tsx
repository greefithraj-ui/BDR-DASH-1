import type { ReactNode } from "react";
import { useNotificationStore } from "../../state/notificationStore";

type NotificationProviderProps = {
  children: ReactNode;
};

export function NotificationProvider({ children }: NotificationProviderProps) {
  const notifications = useNotificationStore((state) => state.notifications);

  return (
    <>
      {children}
      <div aria-live="polite" className="notification-region">
        {notifications.map((notification) => (
          <div key={notification.id} className="notification-shell">
            {notification.title}
          </div>
        ))}
      </div>
    </>
  );
}
