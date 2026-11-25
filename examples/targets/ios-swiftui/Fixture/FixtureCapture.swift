import Foundation

enum FixtureCapture {
    static func markReady() {
        guard ProcessInfo.processInfo.arguments.contains("--fixture-capture") else { return }
        let directory = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        let marker = directory.appendingPathComponent("sauces-fixture-ready")
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            try? Data("ready".utf8).write(to: marker, options: .atomic)
        }
    }
}
