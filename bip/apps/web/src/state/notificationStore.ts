import { create } from "zustand";

export type Notification = {
  id: string;
  title: string;
  variant: "info" | "success" | "warning" | "error";
};

type NotificationState = {
  notifications: Notification[];
  pushNotification: (notification: Notification) => void;
  dismissNotification: (id: string) => void;
};

export const useNotificationStore = create<NotificationState>((set) => ({
  notifications: [],
  pushNotification: (notification) =>
    set((state) => ({ notifications: [...state.notifications, notification] })),
  dismissNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((notification) => notification.id !== id)
    }))
}));
