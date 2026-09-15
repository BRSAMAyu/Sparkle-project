# 国内网络镜像配置指南

本文档说明如何配置国内镜像以加速依赖下载。

## 快速开始

```bash
cd /path/to/Sparkle-project
bash scripts/setup_china_mirrors.sh
```

执行后重启终端即可。

## 手动配置

### Python (pip)

创建或编辑 `~/.pip/pip.conf`:

```ini
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
```

**备选镜像:**
- 清华: https://pypi.tuna.tsinghua.edu.cn/simple
- 中科大: https://mirrors.ustc.edu.cn/pypi/web/simple
- 豆瓣: https://pypi.douban.com/simple

**使用方法:**
```bash
# 使用镜像安装
pip install -r backend/requirements.txt

# 或使用 uv
uv pip install -r backend/requirements.txt
```

### Flutter/Dart

添加到 `~/.zshrc` 或 `~/.bashrc`:

```bash
export PUB_HOSTED_URL="https://pub.flutter-io.cn"
export FLUTTER_STORAGE_BASE_URL="https://storage.flutter-io.cn"
```

**备选镜像:**
- 清华: https://mirrors.tuna.tsinghua.edu.cn/dart-pub
- 上海交大: https://mirror.sjtu.edu.cn/dart-pub
- 阿里云: https://mirrors.aliyun.com/dart-pub

**使用方法:**
```bash
# 运行配置脚本
bash scripts/setup_flutter_mirrors.sh

# 重启终端后
cd mobile && flutter pub get
```

### iOS CocoaPods

Podfile 已配置使用 CDN 源，无需额外配置。

如果 CDN 失败，可切换到清华镜像：

```ruby
# 在 Podfile 中修改 source
source 'https://mirrors.tuna.tsinghua.edu.cn/git/CocoaPods/Specs.git'
```

**使用方法:**
```bash
cd mobile/ios
pod install
```

### Android Gradle

已配置阿里云镜像，无需额外操作。

**配置位置:**
- Maven 仓库: `mobile/android/build.gradle.kts`
- Gradle 分发包: `mobile/android/gradle/wrapper/gradle-wrapper.properties`

**使用方法:**
```bash
cd mobile/android
./gradlew build
```

## 镜像源汇总

| 类型 | 推荐镜像 | 备选镜像 |
|------|----------|----------|
| Python | 阿里云 | 清华、中科大 |
| Flutter/Dart | flutter-io.cn | 清华、上海交大 |
| CocoaPods | cdn.cocoapods.org | 清华 Specs |
| Gradle/Maven | 阿里云 | 华为云 |

## 无法镜像的服务

以下服务需要直接访问 Google 服务器，建议首次构建时使用 VPN：

- **Firebase SDK** - 推送、分析
- **Google Sign-In** - 谷歌登录
- **部分 Google Play Services 组件**

**解决方案:**
1. 首次构建时开启 VPN
2. 依赖会被缓存到本地
3. 后续构建无需 VPN

## 故障排除

### pip 安装失败

```bash
# 临时使用镜像
pip install -r backend/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 或清除缓存重试
pip cache purge
pip install -r backend/requirements.txt
```

### Flutter pub get 失败

```bash
# 检查环境变量
echo $PUB_HOSTED_URL
echo $FLUTTER_STORAGE_BASE_URL

# 清除缓存
flutter pub cache clean
flutter pub get
```

### CocoaPods CDN 失败

```bash
# 使用清华镜像
cd mobile/ios
# 编辑 Podfile，将 source 改为清华镜像
pod install --repo-update
```

### Gradle 下载失败

```bash
# 手动下载 Gradle
# 放到 ~/.gradle/wrapper/dists/ 目录下
```

## Makefile 快捷命令

```bash
# 安装 Python 依赖（使用镜像）
make pip-install-china

# 配置 Flutter 镜像并安装依赖
make mobile-setup-china
```
