import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/storage/token_store.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formatters.dart';
import '../cart/cart_controller.dart';
import '../orders/order_models.dart';

/// Código del pedido que el cliente está siguiendo (persiste al recargar).
class TrackedCode extends Notifier<String?> {
  static const _key = 'tracking_code';

  @override
  String? build() => ref.read(sharedPreferencesProvider).getString(_key);

  Future<void> set(String code) async {
    state = code;
    await ref.read(sharedPreferencesProvider).setString(_key, code);
  }

  Future<void> clear() async {
    state = null;
    await ref.read(sharedPreferencesProvider).remove(_key);
  }
}

final trackedCodeProvider =
    NotifierProvider<TrackedCode, String?>(TrackedCode.new);

/// Consulta el pedido cada 8 s hasta que termina (entregado o cancelado).
final trackedOrderProvider = StreamProvider.autoDispose<TrackedOrder?>((ref) async* {
  final code = ref.watch(trackedCodeProvider);
  if (code == null) {
    yield null;
    return;
  }
  final repo = ref.watch(orderRepositoryProvider);
  while (true) {
    try {
      final order = await repo.track(code);
      yield order;
      if (order.status.isFinal) return;
    } on ApiException catch (e) {
      if (e.statusCode == 404) {
        await ref.read(trackedCodeProvider.notifier).clear();
        yield null;
        return;
      }
      // Fallo de red momentáneo: se reintenta en el siguiente ciclo.
    }
    await Future<void>.delayed(const Duration(seconds: 8));
  }
});

/// Línea de tiempo con el estado del pedido.
class TrackingPanel extends StatelessWidget {
  const TrackingPanel({super.key, required this.order});

  final TrackedOrder order;

  static const _steps = ['Recibido', 'Preparando', 'Listo', 'Entregado'];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final step = order.status.step;
    final where = order.atTable
        ? 'Mesa ${order.tableNumber ?? '-'}'
        : 'Para llevar';

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text('Pedido #${order.id}',
            style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
        const SizedBox(height: 4),
        Text('$where · ${formatCop(order.total)}',
            style: theme.textTheme.bodyMedium?.copyWith(color: AppColors.textMuted)),
        const SizedBox(height: 20),
        if (step >= 0)
          Row(
            children: [
              for (var i = 0; i < _steps.length; i++)
                Expanded(
                  child: Column(
                    children: [
                      Container(
                        height: 6,
                        margin: EdgeInsets.only(right: i == _steps.length - 1 ? 0 : 4),
                        decoration: BoxDecoration(
                          color: i <= step ? AppColors.terracotta : AppColors.border,
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(_steps[i],
                          style: theme.textTheme.labelSmall?.copyWith(
                            fontWeight: i == step ? FontWeight.w800 : FontWeight.w500,
                            color: i <= step ? AppColors.textPrimary : AppColors.textMuted,
                          )),
                    ],
                  ),
                ),
            ],
          ),
        const SizedBox(height: 16),
        Text(
          order.status.customerMessage(
            atTable: order.atTable,
            tableNumber: order.tableNumber,
          ),
          textAlign: TextAlign.center,
          style: theme.textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.w600),
        ),
      ],
    );
  }
}

Future<void> showTrackingSheet(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      constraints: const BoxConstraints(maxWidth: 560),
      backgroundColor: AppColors.background,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => const _TrackingSheet(),
    );

class _TrackingSheet extends ConsumerWidget {
  const _TrackingSheet();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final order = ref.watch(trackedOrderProvider).valueOrNull;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (order == null)
              const Text('No tienes pedidos en curso')
            else
              TrackingPanel(order: order),
            const SizedBox(height: 20),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cerrar'),
            ),
          ],
        ),
      ),
    );
  }
}

/// Franja superior con el estado del pedido en curso.
class TrackingBanner extends ConsumerWidget {
  const TrackingBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final order = ref.watch(trackedOrderProvider).valueOrNull;
    if (order == null) return const SizedBox.shrink();

    final done = order.status.isFinal;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Material(
        color: done ? AppColors.success : AppColors.terracottaSoft,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => showTrackingSheet(context),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                Icon(done ? Icons.check_circle : Icons.receipt_long, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Pedido #${order.id} · ${order.status.customerLabel}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                if (done)
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    tooltip: 'Ocultar',
                    onPressed: () => ref.read(trackedCodeProvider.notifier).clear(),
                    icon: const Icon(Icons.close),
                  )
                else
                  const Text('Ver', style: TextStyle(fontWeight: FontWeight.w700)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
