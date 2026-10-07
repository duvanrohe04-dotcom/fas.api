import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../auth/auth_controller.dart';
import 'orders_tab.dart';
import 'products_tab.dart';
import 'tables_tab.dart';

/// Panel interno (/admin): pedidos y, solo para administradores, productos.
class AdminPage extends ConsumerWidget {
  const AdminPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).valueOrNull;
    final isAdmin = user?.isAdmin ?? false;
    final tabs = <(String, IconData, Widget)>[
      ('Pedidos', Icons.receipt_long, const OrdersTab()),
      ('Mesas', Icons.table_restaurant, const TablesTab()),
      if (isAdmin) ('Productos', Icons.local_cafe, const ProductsTab()),
    ];

    return DefaultTabController(
      length: tabs.length,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Administración',
              style: TextStyle(fontWeight: FontWeight.w800)),
          actions: [
            TextButton.icon(
              onPressed: () => context.go('/'),
              icon: const Icon(Icons.storefront_outlined),
              label: const Text('Ver tienda'),
            ),
            IconButton(
              tooltip: 'Cerrar sesión',
              onPressed: () => ref.read(authControllerProvider.notifier).logout(),
              icon: const Icon(Icons.logout),
            ),
          ],
          bottom: tabs.length < 2
              ? null
              : TabBar(
                  indicatorColor: AppColors.terracotta,
                  labelColor: AppColors.terracotta,
                  tabs: [for (final t in tabs) Tab(icon: Icon(t.$2), text: t.$1)],
                ),
        ),
        body: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: TabBarView(children: [for (final t in tabs) t.$3]),
          ),
        ),
      ),
    );
  }
}
