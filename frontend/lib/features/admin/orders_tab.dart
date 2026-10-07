import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formatters.dart';
import '../../shared/widgets/async_view.dart';
import '../../shared/widgets/product_image.dart';
import '../menu/menu_models.dart';
import '../menu/menu_repository.dart';
import '../orders/order_status.dart';
import 'admin_orders.dart';

String _ago(DateTime? time) {
  if (time == null) return '';
  final minutes = DateTime.now().difference(time).inMinutes;
  if (minutes < 1) return 'ahora';
  if (minutes < 60) return 'hace $minutes min';
  final hours = minutes ~/ 60;
  return hours < 24 ? 'hace $hours h' : 'hace ${hours ~/ 24} d';
}

class OrdersTab extends ConsumerWidget {
  const OrdersTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(orderFilterProvider);
    final orders = ref.watch(adminOrdersProvider);
    final products = ref.watch(productsProvider).valueOrNull ?? const <Product>[];
    final byId = {for (final p in products) p.id: p};

    // Aviso cuando entra un pedido nuevo.
    ref.listen(adminSummaryProvider, (previous, next) {
      final before = previous?.valueOrNull?.pending;
      final now = next.valueOrNull?.pending;
      if (before != null && now != null && now > before) {
        ref.invalidate(adminOrdersProvider);
        ScaffoldMessenger.of(context)
          ..hideCurrentSnackBar()
          ..showSnackBar(
            const SnackBar(content: Text('Llegó un pedido nuevo')),
          );
      }
    });

    return Column(
      children: [
        const _SummaryStrip(),
        SizedBox(
          height: 56,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            children: [
              for (final s in OrderStatus.values.where((s) => s != OrderStatus.cancelled))
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(s.label),
                    selected: filter == s,
                    showCheckmark: false,
                    shape: const StadiumBorder(),
                    selectedColor: AppColors.espresso,
                    labelStyle: TextStyle(
                      color: filter == s ? Colors.white : null,
                      fontWeight: FontWeight.w600,
                    ),
                    onSelected: (_) => ref.read(orderFilterProvider.notifier).state = s,
                  ),
                ),
            ],
          ),
        ),
        Expanded(
          child: AsyncView(
            value: orders,
            onRetry: () => ref.invalidate(adminOrdersProvider),
            builder: (list) {
              if (list.isEmpty) {
                return Center(child: Text('No hay pedidos "${filter.label.toLowerCase()}"'));
              }
              return ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: list.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (_, i) => _OrderCard(order: list[i], products: byId),
              );
            },
          ),
        ),
      ],
    );
  }
}

class _SummaryStrip extends ConsumerWidget {
  const _SummaryStrip();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(adminSummaryProvider).valueOrNull;
    if (s == null) return const SizedBox(height: 8);

    Widget stat(String label, String value, {bool highlight = false}) => Expanded(
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 4),
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
            decoration: BoxDecoration(
              color: highlight ? AppColors.terracottaSoft : AppColors.surfaceMuted,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              children: [
                Text(value,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                const SizedBox(height: 2),
                Text(label,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 11, color: AppColors.textMuted)),
              ],
            ),
          ),
        );

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
      child: Row(
        children: [
          stat('Activos', '${s.active}', highlight: s.pending > 0),
          stat('Pedidos hoy', '${s.ordersToday}'),
          stat('Ventas hoy', formatCop(s.salesToday)),
          stat('Por cobrar', '${s.awaitingPayment}', highlight: s.awaitingPayment > 0),
        ],
      ),
    );
  }
}

class _OrderCard extends ConsumerWidget {
  const _OrderCard({required this.order, required this.products});

  final AdminOrder order;
  final Map<int, Product> products;

  void _refresh(WidgetRef ref) {
    ref.invalidate(adminOrdersProvider);
    ref.invalidate(adminSummaryProvider);
  }

  Future<void> _change(BuildContext context, WidgetRef ref, OrderStatus status) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(adminOrderRepositoryProvider).setStatus(order.id, status);
      _refresh(ref);
      ref.invalidate(productsProvider); // cancelar devuelve stock
      ref.invalidate(adminTablesProvider);
    } on ApiException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _charge(BuildContext context, WidgetRef ref) async {
    final method = await showDialog<PaymentMethod>(
      context: context,
      builder: (_) => SimpleDialog(
        title: Text('Cobrar ${formatCop(order.total)}'),
        children: [
          for (final m in PaymentMethod.values)
            SimpleDialogOption(
              onPressed: () => Navigator.of(context).pop(m),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Text(m.label, style: const TextStyle(fontSize: 16)),
              ),
            ),
        ],
      ),
    );
    if (method == null || !context.mounted) return;

    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(adminOrderRepositoryProvider).pay(order.id, method, order.total);
      _refresh(ref);
      messenger.showSnackBar(
        SnackBar(content: Text('Pedido #${order.id} cobrado (${method.label})')),
      );
    } on ApiException catch (e) {
      messenger.showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final next = order.status.next;
    final needsPayment = order.status == OrderStatus.delivered && !order.isPaid;
    final isTable = order.type == OrderType.table;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: isTable ? AppColors.terracotta : AppColors.espresso,
                  borderRadius: BorderRadius.circular(AppRadius.pill),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(isTable ? Icons.table_restaurant : Icons.shopping_bag,
                        size: 16, color: Colors.white),
                    const SizedBox(width: 6),
                    Text(order.destination,
                        style: const TextStyle(
                            color: Colors.white, fontWeight: FontWeight.w800)),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  '#${order.id}${order.customerName == null ? '' : ' · ${order.customerName}'}',
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
              Text(_ago(order.createdAt),
                  style: theme.textTheme.bodySmall?.copyWith(color: AppColors.textMuted)),
            ],
          ),
          const SizedBox(height: 12),
          for (final line in order.lines)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  ProductImage(url: products[line.productId]?.imageUrl, size: 56),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(products[line.productId]?.name ?? 'Producto ${line.productId}',
                        style: const TextStyle(fontWeight: FontWeight.w600)),
                  ),
                  Text('x${line.quantity}',
                      style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800)),
                ],
              ),
            ),
          if (order.notes != null)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(top: 2, bottom: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF4D6),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.sticky_note_2_outlined, size: 18),
                  const SizedBox(width: 8),
                  Expanded(child: Text(order.notes!)),
                ],
              ),
            ),
          Row(
            children: [
              Text(formatCop(order.total),
                  style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
              if (order.isPaid) ...[
                const SizedBox(width: 8),
                const Chip(
                  label: Text('Pagado'),
                  visualDensity: VisualDensity.compact,
                  backgroundColor: AppColors.success,
                  side: BorderSide.none,
                ),
              ],
              const Spacer(),
              if (order.status.canCancel)
                TextButton(
                  onPressed: () => _change(context, ref, OrderStatus.cancelled),
                  child: const Text('Cancelar'),
                ),
              if (next != null)
                FilledButton(
                  style: FilledButton.styleFrom(minimumSize: const Size(140, 44)),
                  onPressed: () => _change(context, ref, next.$1),
                  child: Text(next.$2),
                ),
              if (needsPayment)
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(140, 44),
                    backgroundColor: AppColors.terracotta,
                  ),
                  onPressed: () => _charge(context, ref),
                  icon: const Icon(Icons.payments_outlined, size: 18),
                  label: const Text('Cobrar'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
