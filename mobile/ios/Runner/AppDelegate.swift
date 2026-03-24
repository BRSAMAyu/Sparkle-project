import Flutter
import UIKit
import FirebaseCore
import FirebaseMessaging
import AVFAudio

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    do {
      try AVAudioSession.sharedInstance().setCategory(
        .playback,
        mode: .default,
        options: [.mixWithOthers],
      )
      try AVAudioSession.sharedInstance().setActive(true)
    } catch {
      print("Failed to configure AVAudioSession: \\(error)")
    }

    // Initialize Firebase only if GoogleService-Info.plist exists
    if let googleServicePath = Bundle.main.path(forResource: "GoogleService-Info", ofType: "plist") {
      if FirebaseApp.app() == nil {
        FirebaseApp.configure()
      }
      // Configure Firebase Messaging delegate
      Messaging.messaging().delegate = self
    } else {
      print("GoogleService-Info.plist not found, skipping Firebase initialization")
    }

    // Initialize JPush
    // Read configuration from Info.plist
    let jpushAppKey = Bundle.main.infoDictionary?["JPushAppKey"] as? String ?? ""
    let jpushChannel = Bundle.main.infoDictionary?["JPushChannel"] as? String ?? "developer-default"

    // Initialize JPush with launch options
    // Note: For production, set apsForProduction to true
    let isProduction = false  // Set to true for App Store builds
    JPUSHService.setup(withOption: launchOptions, appKey: jpushAppKey, channel: jpushChannel, apsForProduction: isProduction)

    // Request notification permissions
    UNUserNotificationCenter.current().delegate = self
    let authOptions: UNAuthorizationOptions = [.alert, .badge, .sound]
    UNUserNotificationCenter.current().requestAuthorization(
      options: authOptions,
      completionHandler: { _, _ in }
    )

    application.registerForRemoteNotifications()

    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
  }

  // Handle APNs token registration
  override func application(
    _ application: UIApplication,
    didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
  ) {
    // Register with Firebase (only if configured)
    if FirebaseApp.app() != nil {
      Messaging.messaging().apnsToken = deviceToken
    }

    // Register with JPush
    JPUSHService.registerDeviceToken(deviceToken)

    super.application(application, didRegisterForRemoteNotificationsWithDeviceToken: deviceToken)
  }

  // Handle APNs token failure
  override func application(
    _ application: UIApplication,
    didFailToRegisterForRemoteNotificationsWithError error: Error
  ) {
    print("Failed to register for remote notifications: \(error)")
    super.application(application, didFailToRegisterForRemoteNotificationsWithError: error)
  }

  // Handle remote notification (iOS 10+)
  override func userNotificationCenter(
    _ center: UNUserNotificationCenter,
    willPresent notification: UNNotification,
    withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void
  ) {
    // Forward to JPush
    let userInfo = notification.request.content.userInfo
    JPUSHService.handleRemoteNotification(userInfo)

    // Show notification even when app is in foreground
    completionHandler([.banner, .badge, .sound])
  }

  // Handle notification tap (iOS 10+)
  override func userNotificationCenter(
    _ center: UNUserNotificationCenter,
    didReceive response: UNNotificationResponse,
    withCompletionHandler completionHandler: @escaping () -> Void
  ) {
    // Forward to JPush
    let userInfo = response.notification.request.content.userInfo
    JPUSHService.handleRemoteNotification(userInfo)

    completionHandler()
  }
}

// MARK: - MessagingDelegate
extension AppDelegate: MessagingDelegate {
  func messaging(
    _ messaging: Messaging,
    didReceiveRegistrationToken fcmToken: String?
  ) {
    // Send token to Flutter side via MethodChannel or let FCM plugin handle it
    print("Firebase registration token: \(String(describing: fcmToken))")
  }
}
