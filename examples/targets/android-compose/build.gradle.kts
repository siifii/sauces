plugins {
    id("com.android.application") version "8.11.2"
    kotlin("android") version "2.2.20"
    id("org.jetbrains.kotlin.plugin.compose") version "2.2.20"
}

kotlin { jvmToolchain(17) }

dependencies {
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.compose.material3:material3:1.3.2")
}

android {
    namespace = "dev.sauces.fixture"
    compileSdk = 35
    defaultConfig {
        applicationId = "dev.sauces.fixture"
        minSdk = 24
        targetSdk = 35
    }
}
