plugins {
    id("com.android.application") version "8.11.2"
    kotlin("multiplatform") version "2.2.20"
    id("org.jetbrains.compose") version "1.9.3"
    id("org.jetbrains.kotlin.plugin.compose") version "2.2.20"
}

kotlin {
    jvmToolchain(17)
    androidTarget()
    listOf(iosArm64(), iosSimulatorArm64()).forEach { target ->
        target.binaries.framework {
            baseName = "ComposeFixture"
            isStatic = true
        }
    }
    sourceSets {
        commonMain.dependencies {
            implementation(compose.material3)
        }
        androidMain.dependencies {
            implementation("androidx.activity:activity-compose:1.10.1")
        }
    }
}

android {
    namespace = "dev.sauces.fixture"
    compileSdk = 35
    defaultConfig {
        applicationId = "dev.sauces.kmpfixture"
        minSdk = 24
        targetSdk = 35
    }
}
