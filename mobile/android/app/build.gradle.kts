import java.util.Properties

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// Google Services plugin for Firebase - only apply if config file exists
// 添加 google-services.json 到 app/ 目录后启用
val googleServicesJson = file("google-services.json")
if (googleServicesJson.exists()) {
    apply(plugin = "com.google.gms.google-services")
} else {
    logger.warn("google-services.json not found. Firebase features will be disabled.")
}

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
val hasReleaseSigning = keystorePropertiesFile.exists()
if (hasReleaseSigning) {
    keystorePropertiesFile.inputStream().use { keystoreProperties.load(it) }
} else {
    logger.warn("Release signing config not found: ${keystorePropertiesFile.path}")
}

val applicationIdValue =
    (project.findProperty("APPLICATION_ID") as String?) ?: "com.example.sparkle"

val sanitizeGeneratedPluginRegistrant by tasks.registering {
    doLast {
        val registrantFile =
            file("src/main/java/io/flutter/plugins/GeneratedPluginRegistrant.java")
        if (!registrantFile.exists()) {
            return@doLast
        }

        val originalContent = registrantFile.readText()
        val sanitizedContent =
            originalContent.replace(
                Regex(
                    """\s*try \{\s*flutterEngine\.getPlugins\(\)\.add\(new dev\.flutter\.plugins\.integration_test\.IntegrationTestPlugin\(\)\);\s*\} catch \(Exception e\) \{\s*Log\.e\(TAG, "Error registering plugin integration_test, dev\.flutter\.plugins\.integration_test\.IntegrationTestPlugin", e\);\s*\}\s*""",
                    setOf(RegexOption.MULTILINE, RegexOption.DOT_MATCHES_ALL)
                ),
                "\n"
            )

        if (sanitizedContent != originalContent) {
            registrantFile.writeText(sanitizedContent)
            logger.lifecycle("Sanitized GeneratedPluginRegistrant.java for release build")
        }
    }
}

tasks.matching { it.name.matches(Regex("generate.*PluginRegistrant")) }.configureEach {
    finalizedBy(sanitizeGeneratedPluginRegistrant)
}

tasks.matching { it.name == "compileReleaseJavaWithJavac" }.configureEach {
    dependsOn(sanitizeGeneratedPluginRegistrant)
}

android {
    namespace = applicationIdValue
    compileSdk = 36  // Updated to support newer Android libraries (required by plugins)
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
        isCoreLibraryDesugaringEnabled = true
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        applicationId = applicationIdValue
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = flutter.minSdkVersion  // Minimum supported Android version
        targetSdk = 34  // Target Android 14
        versionCode = flutter.versionCode
        versionName = flutter.versionName

        // JPush configuration
        manifestPlaceholders["JPUSH_PKGNAME"] = applicationIdValue
        manifestPlaceholders["JPUSH_APPKEY"] = "YOUR_JPUSH_APPKEY"  // Replace with actual JPush AppKey
        manifestPlaceholders["JPUSH_CHANNEL"] = "developer-default"
    }

    signingConfigs {
        create("release") {
            if (hasReleaseSigning) {
                keyAlias = keystoreProperties["keyAlias"] as String?
                keyPassword = keystoreProperties["keyPassword"] as String?
                storeFile = keystoreProperties["storeFile"]?.let { file(it as String) }
                storePassword = keystoreProperties["storePassword"] as String?
            }
        }
    }

    buildTypes {
        release {
            signingConfig = if (hasReleaseSigning) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }

            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
}

flutter {
    source = "../.."
}

dependencies {
    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")
}
