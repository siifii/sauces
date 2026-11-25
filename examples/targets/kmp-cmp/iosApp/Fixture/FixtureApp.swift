import ComposeFixture
import SwiftUI

@main
struct FixtureApp: App {
    var body: some Scene {
        WindowGroup {
            SharedContent().onAppear(perform: FixtureCapture.markReady)
        }
    }
}

struct SharedContent: UIViewControllerRepresentable {
    func makeUIViewController(context: Context) -> UIViewController {
        let arguments = ProcessInfo.processInfo.arguments
        let state = arguments.contains("--fixture-error") ? "error"
            : arguments.contains("--fixture-loading") ? "loading" : "default"
        return MainViewControllerKt.makeFixtureViewController(
            state: state,
            rtl: arguments.contains("--fixture-rtl")
        )
    }

    func updateUIViewController(_ controller: UIViewController, context: Context) {}
}
