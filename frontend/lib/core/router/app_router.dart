import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/admin/admin_page.dart';
import '../../features/auth/auth_controller.dart';
import '../../features/auth/login_page.dart';
import '../../features/customer/customer_page.dart';

/// `/` es la tienda pública. `/admin` exige sesión de admin o cajero.
final routerProvider = Provider<GoRouter>((ref) {
  // Notifica a GoRouter cuando cambia la sesión sin reconstruir el router.
  final refresh = ValueNotifier<int>(0);
  ref.listen(authControllerProvider, (_, __) => refresh.value++);
  ref.onDispose(refresh.dispose);

  // La app de Windows es el puesto del personal: abre directo en /admin.
  final isWindowsApp = !kIsWeb && defaultTargetPlatform == TargetPlatform.windows;

  return GoRouter(
    initialLocation: isWindowsApp ? '/admin' : '/',
    refreshListenable: refresh,
    redirect: (context, state) {
      final path = state.matchedLocation;
      if (!path.startsWith('/admin')) return null;

      final auth = ref.read(authControllerProvider);
      if (auth.isLoading && !auth.hasValue) return null; // restaurando sesión

      final allowed = auth.valueOrNull?.canUseAdminPanel ?? false;
      final atLogin = path == '/admin/login';
      if (!allowed) return atLogin ? null : '/admin/login';
      return atLogin ? '/admin' : null;
    },
    routes: [
      GoRoute(path: '/', builder: (_, __) => const CustomerPage()),
      GoRoute(path: '/admin', builder: (_, __) => const AdminPage()),
      GoRoute(
        path: '/admin/login',
        builder: (_, __) => const LoginPage(),
      ),
    ],
  );
});
