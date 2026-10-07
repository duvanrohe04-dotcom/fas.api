import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/storage/token_store.dart';

class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
  });

  final int id;
  final String email;
  final String fullName;
  final String role;

  bool get isAdmin => role == 'admin';

  /// Roles con acceso al panel /admin.
  bool get canUseAdminPanel => role == 'admin' || role == 'cajero';

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as int,
        email: json['email'] as String,
        fullName: json['full_name'] as String,
        role: json['role'] as String,
      );
}

class AuthRepository {
  AuthRepository(this._dio);

  final Dio _dio;

  Future<({String token, AppUser user})> login(String email, String password) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>(
        '/auth/login',
        data: {'email': email, 'password': password},
      );
      final data = res.data!;
      return (
        token: data['access_token'] as String,
        user: AppUser.fromJson(data['user'] as Map<String, dynamic>),
      );
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<AppUser> me() async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/auth/me');
      return AppUser.fromJson(res.data!);
    } catch (e) {
      throw ApiException.from(e);
    }
  }
}

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(ref.watch(dioProvider)),
);

/// Estado de sesión: `null` = sin sesión. Restaura la sesión desde el token guardado.
class AuthController extends AsyncNotifier<AppUser?> {
  @override
  Future<AppUser?> build() async {
    final store = ref.read(tokenStoreProvider);
    if (store.read() == null) return null;
    try {
      return await ref.read(authRepositoryProvider).me();
    } on ApiException {
      await store.clear();
      return null;
    }
  }

  Future<void> login(String email, String password) async {
    state = const AsyncLoading();
    state = await AsyncValue.guard(() async {
      final result = await ref.read(authRepositoryProvider).login(email, password);
      await ref.read(tokenStoreProvider).save(result.token);
      return result.user;
    });
  }

  Future<void> logout() async {
    await ref.read(tokenStoreProvider).clear();
    state = const AsyncData(null);
  }
}

final authControllerProvider =
    AsyncNotifierProvider<AuthController, AppUser?>(AuthController.new);
