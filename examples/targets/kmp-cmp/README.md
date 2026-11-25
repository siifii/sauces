Run `./gradlew assembleDebug` with Gradle 8.14, JDK 17 and Android SDK 35.
On Apple silicon, build the iOS host with `xcodebuild -project iosApp/Fixture.xcodeproj -scheme Fixture -destination generic/platform=iOS\ Simulator ARCHS=arm64 CODE_SIGNING_ALLOWED=NO build`. The scheme builds and links the shared Compose framework through Gradle.
