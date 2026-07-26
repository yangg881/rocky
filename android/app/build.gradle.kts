import java.io.FileInputStream
import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Load release signing material from android/keystore.properties (never committed)
// or ZHIDAY_KEYSTORE* environment variables. We deliberately do NOT fall back to
// the public debug keystore for release builds (P0-4).
val keystorePropsFile = rootProject.file("keystore.properties")
val keystoreProps = Properties().apply {
    if (keystorePropsFile.exists()) FileInputStream(keystorePropsFile).use { load(it) }
}
val releaseStoreFile = keystoreProps.getProperty("storeFile") ?: System.getenv("ZHIDAY_KEYSTORE")
val releaseStorePassword = keystoreProps.getProperty("storePassword") ?: System.getenv("ZHIDAY_KEYSTORE_PASSWORD")
val releaseKeyAlias = keystoreProps.getProperty("keyAlias") ?: System.getenv("ZHIDAY_KEY_ALIAS")
val releaseKeyPassword = keystoreProps.getProperty("keyPassword") ?: System.getenv("ZHIDAY_KEY_PASSWORD")
val hasReleaseSigning = !releaseStoreFile.isNullOrBlank() && !releaseStorePassword.isNullOrBlank() &&
    !releaseKeyAlias.isNullOrBlank() && !releaseKeyPassword.isNullOrBlank()

android {
    namespace = "com.zhiday.resume"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.zhiday.resume"
        minSdk = 26
        targetSdk = 35
        versionCode = 34
        versionName = "1.8.19"
        // P0-6: HTTPS domain is the primary channel; the plaintext IP is only a
        // fallback used when domain resolution fails (see network_security_config).
        buildConfigField("String", "API_BASE_URL", "\"https://zhidajob.top/api/\"")
        buildConfigField("String", "API_FALLBACK_URL", "\"http://115.120.206.64/api/\"")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                // Resolve relative to android/ (rootProject), matching keystore.properties location
                storeFile = rootProject.file(releaseStoreFile!!)
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"))
            if (hasReleaseSigning) {
                signingConfig = signingConfigs.getByName("release")
            }
            // No silent fallback to the debug keystore. Release stays unsigned
            // until real signing material is supplied; a real build is blocked below.
        }
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.15"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

}

// Block any real release assembly when signing material is missing, so we never
// ship an unsigned or debug-signed release APK (P0-4).
gradle.taskGraph.whenReady {
    if (!hasReleaseSigning && allTasks.any { it.name.contains("Release") }) {
        throw GradleException(
            "Release signing is not configured. Create android/keystore.properties " +
                "(storeFile/storePassword/keyAlias/keyPassword — never commit it) or set the " +
                "ZHIDAY_KEYSTORE / ZHIDAY_KEYSTORE_PASSWORD / ZHIDAY_KEY_ALIAS / ZHIDAY_KEY_PASSWORD env vars."
        )
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.navigation:navigation-compose:2.8.5")
    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
