import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/async_view.dart';
import '../auth/auth_controller.dart';
import '../orders/order_models.dart';
import 'admin_orders.dart';

/// Estado de las mesas: libres u ocupadas, con opción de cambiarlo a mano.
class TablesTab extends ConsumerWidget {
  const TablesTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tables = ref.watch(adminTablesProvider);
    final isAdmin = ref.watch(authControllerProvider).valueOrNull?.isAdmin ?? false;

    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: isAdmin
          ? FloatingActionButton.extended(
              backgroundColor: AppColors.espresso,
              foregroundColor: Colors.white,
              onPressed: () => _createTable(context, ref),
              icon: const Icon(Icons.add),
              label: const Text('Nueva mesa'),
            )
          : null,
      body: AsyncView(
        value: tables,
        onRetry: () => ref.invalidate(adminTablesProvider),
        builder: (list) {
          if (list.isEmpty) return const Center(child: Text('Aún no hay mesas'));
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(adminTablesProvider),
            child: GridView.builder(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
              gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: 200,
                mainAxisSpacing: 12,
                crossAxisSpacing: 12,
                childAspectRatio: 1.1,
              ),
              itemCount: list.length,
              itemBuilder: (_, i) => _TableCard(table: list[i]),
            ),
          );
        },
      ),
    );
  }

  Future<void> _createTable(BuildContext context, WidgetRef ref) async {
    final number = TextEditingController();
    final capacity = TextEditingController(text: '4');
    final created = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Nueva mesa'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: number,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(hintText: 'Número de mesa'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: capacity,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(hintText: 'Puestos'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancelar')),
          FilledButton(
            style: FilledButton.styleFrom(minimumSize: const Size(120, 44)),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Crear'),
          ),
        ],
      ),
    );
    final n = int.tryParse(number.text.trim());
    final c = int.tryParse(capacity.text.trim());
    number.dispose();
    capacity.dispose();
    if (created != true || n == null || c == null || !context.mounted) return;

    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(adminOrderRepositoryProvider).createTable(n, c);
      ref.invalidate(adminTablesProvider);
    } on ApiException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.message)));
    }
  }
}

class _TableCard extends ConsumerWidget {
  const _TableCard({required this.table});

  final TableInfo table;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final occupied = table.occupied;

    return InkWell(
      borderRadius: BorderRadius.circular(AppRadius.card),
      onTap: () async {
        final messenger = ScaffoldMessenger.of(context);
        try {
          await ref
              .read(adminOrderRepositoryProvider)
              .setTableOccupied(table.id, !occupied);
          ref.invalidate(adminTablesProvider);
        } on ApiException catch (e) {
          messenger.showSnackBar(SnackBar(content: Text(e.message)));
        }
      },
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: occupied ? AppColors.terracottaSoft : AppColors.success,
          borderRadius: BorderRadius.circular(AppRadius.card),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Mesa ${table.number}',
                style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 4),
            Text('${table.capacity} puestos', style: theme.textTheme.bodySmall),
            const SizedBox(height: 8),
            Text(occupied ? 'Ocupada' : 'Libre',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }
}
