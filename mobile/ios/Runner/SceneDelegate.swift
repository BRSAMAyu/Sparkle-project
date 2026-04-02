import Flutter
import UIKit
import app_links

final class SceneDelegate: FlutterSceneDelegate {
  override func scene(
    _ scene: UIScene,
    willConnectTo session: UISceneSession,
    options connectionOptions: UIScene.ConnectionOptions
  ) {
    if let url = connectionOptions.urlContexts.first?.url {
      AppLinks.shared.handleLink(url: url)
    } else if let userActivity = connectionOptions.userActivities.first,
              let url = userActivity.webpageURL {
      AppLinks.shared.handleLink(url: url)
    }

    super.scene(scene, willConnectTo: session, options: connectionOptions)
  }

  override func scene(
    _ scene: UIScene,
    openURLContexts URLContexts: Set<UIOpenURLContext>
  ) {
    URLContexts.forEach { context in
      AppLinks.shared.handleLink(url: context.url)
    }
    super.scene(scene, openURLContexts: URLContexts)
  }

  override func scene(
    _ scene: UIScene,
    continue userActivity: NSUserActivity
  ) {
    if let url = userActivity.webpageURL {
      AppLinks.shared.handleLink(url: url)
    }
    super.scene(scene, continue: userActivity)
  }
}
