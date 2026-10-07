import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../config/env.dart';
import '../storage/token_store.dart';

/// Error de dominio con mensaje apto para mostrar al usuario.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  bool get isUnauthorized => statusCode == 401;

  factory ApiException.from(Object error) {
    if (error is DioException) {
      final data = error.response?.data;
      final detail = data is Map ? data['detail'] : null;
      return ApiException(
        detail is String ? detail : 'No se pudo conectar con el servidor',
        statusCode: error.response?.statusCode,
      );
    }
    return ApiException('Ocurrió un error inesperado');
  }

  @override
  String toString() => message;
}

final dioProvider = Provider<Dio>((ref) {
  final store = ref.watch(tokenStoreProvider);
  final dio = Dio(
    BaseOptions(
      baseUrl: Env.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 15),
    ),
  );

  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        final token = store.read();
        if (token != null) options.headers['Authorization'] = 'Bearer $token';
        handler.next(options);
      },
    ),
  );
  return dio;
});
