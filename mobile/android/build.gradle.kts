allprojects {
    repositories {
        // 国内镜像优先 (Aliyun mirrors for China network)
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/central") }
        maven { url = uri("https://maven.aliyun.com/repository/public") }
        maven { url = uri("https://maven.aliyun.com/repository/gradle-plugin") }
        // 原始仓库作为备用
        google()
        mavenCentral()
        // Huawei repository for JPush dependencies
        maven { url = uri("https://developer.huawei.com/repo/") }
    }
}

// Add Google Services plugin classpath
buildscript {
    repositories {
        // 国内镜像优先
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/central") }
        maven { url = uri("https://maven.aliyun.com/repository/public") }
        maven { url = uri("https://maven.aliyun.com/repository/gradle-plugin") }
        // 原始仓库作为备用
        google()
        mavenCentral()
    }
    dependencies {
        classpath("com.google.gms:google-services:4.4.2")
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    buildscript {
        configurations.configureEach {
            resolutionStrategy.eachDependency {
                if (requested.group == "com.android.tools.build" && requested.name == "gradle") {
                    useVersion("8.11.1")
                    because("All Android subprojects need to use the same AGP version under Gradle 8.14 / JDK 17")
                }
                if (requested.group == "org.jetbrains.kotlin" && requested.name == "kotlin-gradle-plugin") {
                    useVersion("2.2.20")
                    because("Keep legacy plugin subprojects on the same Kotlin Gradle plugin as the app")
                }
            }
        }
    }

    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}

subprojects {
    val project = this
    fun configureNamespace() {
        if (project.plugins.hasPlugin("com.android.library") || project.plugins.hasPlugin("com.android.application")) {
            val android = project.extensions.findByName("android") as? com.android.build.gradle.BaseExtension
            if (android != null && android.namespace == null) {
                android.namespace = "com.sparkle." + project.name.replace("-", ".").replace(":", ".")
            }
        }
    }

    if (project.state.executed) {
        configureNamespace()
    } else {
        project.afterEvaluate {
            configureNamespace()
        }
    }

    // Keep problematic plugins on the same Android toolchain level as the app.
    project.plugins.withId("com.android.library") {
        if (project.name == "isar_flutter_libs" ||
            project.name == "jpush_flutter" ||
            project.name == "file_picker" ||
            project.name == "fluwx" ||
            project.name == "flutter_local_notifications"
        ) {
            val android = project.extensions.findByName("android") as? com.android.build.gradle.BaseExtension
            android?.compileSdkVersion(36)
        }
    }

    if (project.name == "fluwx") {
        project.tasks.matching { task ->
            task.name == "preBuild" || (task.name.startsWith("compile") && task.name.endsWith("Kotlin"))
        }.configureEach {
            dependsOn("generateFluwxHelperFile")
        }
    }

    project.tasks.whenTaskAdded {
        if (name == "processDebugManifest" || name == "processReleaseManifest") {
            (this as? com.android.build.gradle.tasks.ProcessLibraryManifest)?.let { task ->
                task.doFirst {
                    val manifestFile = task.mainManifest.get().asFile
                    if (manifestFile.exists()) {
                        val content = manifestFile.readText()
                        if (content.contains("package=")) {
                            val updatedContent = content.replace(Regex("package=\"[^\"]*\""), "")
                            manifestFile.writeText(updatedContent)
                        }
                    }
                }
            }
        }
    }
}

gradle.projectsEvaluated {
    allprojects {
        tasks.withType<JavaCompile>().configureEach {
            sourceCompatibility = "17"
            targetCompatibility = "17"
        }
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            compilerOptions {
                jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
            }
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
