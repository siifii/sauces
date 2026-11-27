"""SDK-backed fixture checks, opt in with pytest -m mobile."""
import hashlib
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from pathlib import Path

from PIL import Image
import pytest

from conftest import REPO

pytestmark = pytest.mark.mobile


def run(project, *argv, timeout=600):
    result = subprocess.run(argv, cwd=project, capture_output=True, timeout=timeout)
    output = result.stdout + result.stderr
    assert result.returncode == 0, output.decode(errors="replace")
    return result.stdout


@pytest.fixture
def copy_app(tmp_path):
    def copy(name):
        return shutil.copytree(
            REPO / "examples" / "targets" / name, tmp_path / name,
            ignore=shutil.ignore_patterns("build", ".gradle", ".kotlin", "node_modules", "dist", ".expo",
                                          "DerivedData", "local.properties", "xcuserdata"),
        )

    return copy


@pytest.fixture(params=["existing", "starter"])
def native_app(copy_app, tmp_path, request):
    def create(platform, fixture_id):
        if request.param == "existing":
            return copy_app(platform), fixture_id
        run(tmp_path, sys.executable, "-I", str(REPO / "scripts/scaffold_native.py"), platform,
            "--name", f"Parity {platform}", "--org", "dev.sauces")
        folder = {"android-compose": "android", "ios-swiftui": "ios", "kmp-cmp": "kmp"}[platform]
        return tmp_path / folder, "dev.sauces.parity" + platform.replace("-", "")

    return create


@pytest.mark.parametrize("name,app_id", [
    ("android-compose", "dev.sauces.fixture"),
    ("kmp-cmp", "dev.sauces.kmpfixture"),
])
def test_compose_build_and_optional_device_capture(native_app, tmp_path, name, app_id):
    app, app_id = native_app(name, app_id)
    run(app, "./gradlew", "--no-daemon", "assembleDebug")
    if name == "kmp-cmp" and shutil.which("xcodebuild"):
        run(app, "./gradlew", "--no-daemon", "compileKotlinIosSimulatorArm64")

    serial = os.environ.get("SAUCES_ANDROID_SERIAL")
    if not serial:
        return

    apk, = app.glob("build/outputs/apk/debug/*.apk")
    adb = ("adb", "-s", serial)
    run(app, *adb, "install", "-r", str(apk))
    for state in ("default", "error", "loading"):
        for direction in ("ltr", "rtl"):
            run(app, *adb, "shell", "am", "force-stop", app_id)
            output = run(app, *adb, "shell", "am", "start", "-W", "-n",
                         f"{app_id}/dev.sauces.fixture.MainActivity",
                         "--es", "fixtureState", state, "--ez", "fixtureRtl",
                         str(direction == "rtl").lower())
            assert b"Status: ok" in output, output
            wait_for_android_screen(app, adb, app_id, state, direction)
            path = tmp_path / f"{name}--{state}--{direction}.png"
            path.write_bytes(run(app, *adb, "exec-out", "screencap", "-p"))
            check_png(path)


def wait_for_android_screen(app, adb, app_id, state, direction):
    button = "متابعة" if direction == "rtl" else "Continue"
    error = "تحقق من البريد الإلكتروني" if direction == "rtl" else "Check your email"
    path = f"/data/local/tmp/sauces-{app_id}-{state}-{direction}.xml"
    for _ in range(5):
        output = run(app, *adb, "shell", "uiautomator", "dump", path, timeout=20)
        if path.encode() not in output:
            continue
        tree = ET.fromstring(run(app, *adb, "exec-out", "cat", path))
        nodes = [node.attrib for node in tree.iter("node") if node.get("package") == app_id]
        texts = {node.get("text", "").casefold() for node in nodes}
        loading = any(node.get("class") == "android.widget.ProgressBar" for node in nodes)
        if (button.casefold() in texts and (error.casefold() in texts) == (state == "error")
                and loading == (state == "loading")):
            return
    pytest.fail(f"{app_id} did not show the {state} screen in {direction}")


def check_png(path):
    with Image.open(path) as image:
        assert image.format == "PNG" and min(image.size) > 0
        image.verify()


@pytest.mark.skipif(not shutil.which("xcodebuild"), reason="Xcode required")
@pytest.mark.parametrize("name,project,app_id", [
    ("ios-swiftui", "Fixture.xcodeproj", "dev.sauces.swiftfixture"),
    ("kmp-cmp", "iosApp/Fixture.xcodeproj", "dev.sauces.kmpfixture"),
])
def test_ios_simulator_build_and_optional_capture(native_app, tmp_path, name, project, app_id):
    app, app_id = native_app(name, app_id)
    if name == "kmp-cmp" and os.uname().machine != "arm64":
        pytest.skip("the KMP fixture uses the Apple silicon simulator target")
    products = tmp_path / "Products"
    arch = ("ARCHS=arm64",) if name == "kmp-cmp" else ()
    run(app, "xcodebuild", "-quiet", "-project", project, "-target", "Fixture",
        "-sdk", "iphonesimulator", f"SYMROOT={products}", f"OBJROOT={tmp_path / 'Intermediates'}",
        *arch, "CODE_SIGNING_ALLOWED=NO", "build")
    bundle = products / "Debug-iphonesimulator/Fixture.app"
    assert (bundle / "Fixture").is_file()
    with (bundle / "Info.plist").open("rb") as info_file:
        info = plistlib.load(info_file)
    assert "UILaunchScreen" in info
    if name == "kmp-cmp":
        assert info.get("CADisableMinimumFrameDurationOnPhone") is True

    device = os.environ.get("SAUCES_IOS_SIMULATOR")
    if not device:
        return
    run(app, "xcrun", "simctl", "install", device, str(bundle))
    container = run(app, "xcrun", "simctl", "get_app_container", device, app_id, "data")
    marker = Path(container.decode().strip()) / "Library/Caches/sauces-fixture-ready"
    for state in ("default", "error", "loading"):
        for direction in ("ltr", "rtl"):
            marker.unlink(missing_ok=True)
            args = ["--fixture-capture", f"--fixture-{state}"]
            if direction == "rtl":
                args.append("--fixture-rtl")
            run(app, "xcrun", "simctl", "launch", "--terminate-running-process", device, app_id, *args)
            for _ in range(40):
                if marker.is_file():
                    break
                time.sleep(0.25)
            else:
                pytest.fail(f"{app_id} did not report readiness for {state} in {direction}")
            path = tmp_path / f"{name}--{state}--{direction}.png"
            run(app, "xcrun", "simctl", "io", device, "screenshot", str(path))
            check_png(path)


@pytest.mark.skipif(not shutil.which("npm"), reason="Node and npm required")
def test_expo_typecheck_and_mobile_bundles(copy_app, tmp_path):
    app = copy_app("react-native")
    run(app, "npm", "ci", "--no-audit", "--no-fund")
    run(app, "npm", "run", "typecheck")
    run(app, "npm", "run", "bundle:mobile")
    assert (app / "dist/_expo/static/js/android").is_dir()
    assert (app / "dist/_expo/static/js/ios").is_dir()

    serial = os.environ.get("SAUCES_ANDROID_SERIAL")
    if serial:
        capture_expo_android(app, tmp_path, serial)


def capture_expo_android(app, output, serial):
    # Test the Expo host with its own bundled JS so Expo Go and Metro aren't required.
    run(app, "env", "CI=1", "EXPO_NO_TELEMETRY=1", "./node_modules/.bin/expo",
        "prebuild", "--platform", "android", "--no-install")
    android = app / "android"
    gradle = android / "app/build.gradle"
    suffix = ".capture" + hashlib.sha256(str(output).encode()).hexdigest()[:8]
    gradle.write_text(gradle.read_text().replace(
        'bundleCommand = "export:embed"', 'bundleCommand = "export:embed"\n    debuggableVariants = []'
    ).replace("buildTypes {\n        debug {", f'buildTypes {{\n        debug {{\n            applicationIdSuffix "{suffix}"'))
    application = android / "app/src/main/java/dev/sauces/rnfixture/MainApplication.kt"
    application.write_text(application.read_text().replace(
        "context = applicationContext,", "context = applicationContext,\n      useDevSupport = false,"))
    debug_manifest = android / "app/src/debug/AndroidManifest.xml"
    debug_manifest.write_text(debug_manifest.read_text().replace(
        "</manifest>", '    <uses-permission android:name="android.permission.ACCESS_LOCAL_NETWORK" '
        'tools:node="remove"/>\n</manifest>'))

    adb = ("adb", "-s", serial)
    abi = run(app, *adb, "shell", "getprop", "ro.product.cpu.abi").decode().strip()
    run(android, "./gradlew", "--no-daemon", f"-PreactNativeArchitectures={abi}", "assembleDebug")
    apk, = android.glob("app/build/outputs/apk/debug/*.apk")
    run(app, *adb, "install", "-r", str(apk))
    app_id = "dev.sauces.rnfixture" + suffix
    for state in ("default", "error", "loading"):
        for direction in ("ltr", "rtl"):
            run(app, *adb, "shell", "am", "force-stop", app_id)
            uri = f"sauces-fixture://screen?state={state}&rtl={int(direction == 'rtl')}"
            launch = run(app, *adb, "shell", "am", "start", "-W", "-a",
                         "android.intent.action.VIEW", "-d", shlex.quote(uri), "-p", app_id)
            assert b"Status: ok" in launch, launch
            wait_for_android_screen(app, adb, app_id, state, direction)
            path = output / f"react-native-expo--{state}--{direction}.png"
            path.write_bytes(run(app, *adb, "exec-out", "screencap", "-p"))
            check_png(path)


@pytest.mark.skipif(not shutil.which("npm"), reason="Node and npm required")
def test_bare_react_native_template_creates_both_hosts(tmp_path):
    run(tmp_path, "npm", "exec", "--yes", "--package=@react-native-community/cli@21.0.0",
        "--", "rnc-cli", "init", "ParityBare", "--version", "0.88.1", "--directory",
        "react-native-app", "--package-name", "dev.sauces.paritybare",
        "--skip-install", "--skip-git-init")
    project = tmp_path / "react-native-app"
    android = (project / "android/app/build.gradle").read_text()
    ios = (project / "ios/ParityBare.xcodeproj/project.pbxproj").read_text()
    assert 'applicationId "dev.sauces.paritybare"' in android
    assert 'PRODUCT_BUNDLE_IDENTIFIER = "dev.sauces.paritybare";' in ios
    assert not (project / ".git").exists()
