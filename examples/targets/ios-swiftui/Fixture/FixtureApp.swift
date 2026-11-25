import SwiftUI

@main
struct FixtureApp: App {
    var body: some Scene {
        WindowGroup {
            let arguments = ProcessInfo.processInfo.arguments
            let rtl = arguments.contains("--fixture-rtl")
            let state = arguments.contains("--fixture-error") ? "error"
                : arguments.contains("--fixture-loading") ? "loading" : "default"
            HomeView(state: state)
                .environment(\.locale, Locale(identifier: rtl ? "ar" : "en"))
                .environment(\.layoutDirection, rtl ? .rightToLeft : .leftToRight)
                .onAppear(perform: FixtureCapture.markReady)
        }
    }
}

struct HomeView: View {
    let state: String
    @State private var email = ""

    var body: some View {
        VStack {
            AppTextField(label: "Email", value: $email)
            AppButton(label: "Continue", action: {})
            if state == "error" {
                Text("Check your email")
            } else if state == "loading" {
                ProgressView()
            }
        }
        .padding()
    }
}

struct AppButton: View {
    let label: LocalizedStringKey
    let action: () -> Void

    var body: some View {
        Button(label, action: action).buttonStyle(.borderedProminent)
    }
}

struct AppTextField: View {
    let label: LocalizedStringKey
    @Binding var value: String

    var body: some View {
        TextField(label, text: $value).textFieldStyle(.roundedBorder)
    }
}
