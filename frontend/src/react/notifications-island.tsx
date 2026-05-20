/**
 * Bridge module — re-exports SplashedPushNotifications so the Vue host can
 * dynamically import a single chunk instead of pulling in the .tsx by name.
 * Mirrors the shape of frontend/src/remotion/index.ts.
 */
export {
  SplashedPushNotifications,
  type SplashedPushNotificationsHandle,
  type SplashedPushNotificationsProps,
  type NotificationType,
} from './splashed-push-notifications'
