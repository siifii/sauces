import subprocess

import pytest

from conftest import REPO


@pytest.mark.parametrize("platform,folder,configuration", [
    ("android-compose", "android", "build.gradle.kts"),
    ("ios-swiftui", "ios", "Fixture.xcodeproj/project.pbxproj"),
    ("kmp-cmp", "kmp", "build.gradle.kts"),
])
def test_native_starter_sets_app_identifier_and_refuses_overwrite(tmp_path, platform, folder, configuration):
    command = ["python3", "-I", str(REPO / "scripts/scaffold_native.py"), platform,
               "--name", "Parity Demo", "--org", "org.example"]
    result = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    app = tmp_path / folder
    config = (app / configuration).read_text()
    assert "org.example.paritydemo" in config
    assert not (app / "build").exists()
    if platform == "kmp-cmp":
        assert "org.example.paritydemo" in (app / "iosApp/Fixture.xcodeproj/project.pbxproj").read_text()
    result = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode != 0 and "exists" in result.stderr
    assert (app / configuration).read_text() == config
