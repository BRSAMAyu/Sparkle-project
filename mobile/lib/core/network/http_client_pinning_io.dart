import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:dio/io.dart';

void configureDioForPinning(Dio dio, String? sha256Pin) {
  if (sha256Pin == null || sha256Pin.isEmpty) {
    return;
  }

  dio.httpClientAdapter = IOHttpClientAdapter(
    createHttpClient: () {
      final context = SecurityContext();
      final client = HttpClient(context: context);
      client.badCertificateCallback = (cert, host, port) {
        final actual = sha256.convert(cert.der).toString();
        return actual.toLowerCase() == sha256Pin.toLowerCase();
      };
      return client;
    },
  );
}
