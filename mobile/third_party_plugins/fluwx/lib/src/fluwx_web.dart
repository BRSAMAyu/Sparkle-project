/*
 * Copyright (c) 2023.  OpenFlutter Project
 *
 *   Licensed to the Apache Software Foundation (ASF) under one or more contributor
 * license agreements.  See the NOTICE file distributed with this work for
 * additional information regarding copyright ownership. The ASF licenses this
 * file to you under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

// In order to *not* need this ignore, consider extracting the "web" version
// of your plugin as a separate package, instead of inlining it in the same
// package as the core of your plugin.
// ignore: avoid_web_libraries_in_flutter
import 'dart:async';

import 'package:flutter_web_plugins/flutter_web_plugins.dart';

import 'foundation/arguments.dart';
import 'method_channel/fluwx_platform_interface.dart';
import 'response/wechat_response.dart';

/// A web implementation of the FluwxPlatform of the Fluwx plugin.
///
/// N-3（web-round2）根因修复：本类此前注册为 web 平台实现却**没有重写任何
/// 平台方法**，而 `Fluwx()` 构造函数第一时间监听
/// `FluwxPlatform.instance.responseEventHandler` —— 命中基类
/// `throw UnimplementedError('responseEventHandler has not been implemented.')`。
/// 首个访问 `SocialAuthService` 单例的页面（升级账户页 build 中的
/// `isWeChatAvailable`）在 build 期当场红屏（2/2 复现，事件留档
/// `UnimplementedError: respon…`）。
///
/// Web 端没有微信 SDK 运行时，这里给出**优雅降级**语义：
/// - `responseEventHandler` 恒定空广播流（订阅安全、永不发射）；
/// - `registerApi` 返回 false（上层 `initWeChat` 据此保持不可用态）；
/// - 其余能力（分享/支付/授权/打开）一律返回 false，由上层布尔检查与
///   既有的 UnsupportedError 提示路径自然降级，不再抛平台级异常。
class FluwxWeb extends FluwxPlatform {
  /// Constructs a FluwxWeb
  FluwxWeb();

  static void registerWith(Registrar registrar) {
    FluwxPlatform.instance = FluwxWeb();
  }

  final StreamController<WeChatResponse> _responseController =
      StreamController<WeChatResponse>.broadcast();

  @override
  Stream<WeChatResponse> get responseEventHandler => _responseController.stream;

  @override
  Future<bool> get isWeChatInstalled async => false;

  @override
  Future<bool> get isSupportOpenBusinessView async => false;

  @override
  Future<bool> registerApi({
    required String appId,
    bool doOnIOS = true,
    bool doOnAndroid = true,
    String? universalLink,
  }) async =>
      false;

  @override
  Future<String?> getExtMsg() async => null;

  @override
  Future<bool> open(OpenType target) async => false;

  @override
  Future<bool> share(WeChatShareModel what) async => false;

  @override
  Future<bool> sendAuth({
    required String scope,
    String state = 'state',
    bool nonAutomatic = false,
  }) async =>
      false;

  @override
  Future<bool> authByPhoneLogin({
    required String scope,
    String state = 'state',
  }) async =>
      false;

  @override
  Future<bool> authByQRCode({
    required String appId,
    required String scope,
    required String nonceStr,
    required String timestamp,
    required String signature,
    String? schemeData,
  }) async =>
      false;

  @override
  Future<bool> stopAuthByQRCode() async => false;

  @override
  Future<bool> pay(PayType which) async => false;

  @override
  Future<bool> autoDeduct(AutoDeduct data) async => false;

  @override
  Future<bool> authBy(AuthType which) async => false;

  @override
  Future<void> attemptToResumeMsgFromWx() async {}

  @override
  Future<void> selfCheck() async {}
}
