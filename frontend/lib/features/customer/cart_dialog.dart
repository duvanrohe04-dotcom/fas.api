import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formatters.dart';
import '../../shared/widgets/product_image.dart';
import '../../shared/widgets/quantity_stepper.dart';
import '../cart/cart_controller.dart';
import '../menu/menu_repository.dart';
import '../orders/order_models.dart';
import '../orders/order_status.dart';
import 'tracking.dart';

Future<void> showCartDialog(BuildContext context) => showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      constraints: const BoxConstraints(maxWidth: 560),
      backgroundColor: AppColors.background,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => const _CartSheet(),
    );

class _CartSheet extends ConsumerStatefulWidget {
  const _CartSheet();

  @override
  ConsumerState<_CartSheet> createState() => _CartSheetState();
}

class _CartSheetState extends ConsumerState<_CartSheet> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _notes = TextEditingController();
  OrderType _type = OrderType.table;
  int? _tableId;
  bool _sending = false;
  bool _placed = false;
  String? _error;

  @override
  void dispose() {
    _name.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _confirm() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _sending = true;
      _error = null;
    });
    try {
      final lines = ref.read(cartProvider).values.toList();
      final order = await ref.read(orderRepositoryProvider).createPublic(
            lines,
            type: _type,
            tableId: _tableId,
            customerName: _name.text.trim(),
            notes: _notes.text.trim().isEmpty ? null : _notes.text.trim(),
          );
      await ref.read(trackedCodeProvider.notifier).set(order.code!);
      ref.read(cartProvider.notifier).clear();
      ref.invalidate(productsProvider); // el stock cambió
      if (mounted) setState(() => _placed = true);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    if (_placed) {
      final order = ref.watch(trackedOrderProvider).valueOrNull;
      return Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.check_circle, size: 56, color: Colors.green),
            const SizedBox(height: 8),
            Text('¡Pedido recibido!',
                style: theme.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800)),
            const SizedBox(height: 20),
            if (order == null)
              const CircularProgressIndicator()
            else
              TrackingPanel(order: order),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Listo'),
            ),
          ],
        ),
      );
    }

    final lines = ref.watch(cartProvider).values.toList();
    final total = ref.watch(cartTotalProvider);
    final cart = ref.read(cartProvider.notifier);
    final tables = ref.watch(publicTablesProvider).valueOrNull ?? const <TableInfo>[];

    if (lines.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(32),
        child: Text('Tu pedido está vacío', textAlign: TextAlign.center),
      );
    }

    return Padding(
      padding: EdgeInsets.fromLTRB(20, 20, 20, 16 + bottomInset),
      child: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Tu pedido',
                  style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 12),
              for (final line in lines)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: Row(
                    children: [
                      ProductImage(url: line.product.imageUrl, size: 52),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(line.product.name,
                                style: const TextStyle(fontWeight: FontWeight.w700)),
                            Text(formatCop(line.subtotal)),
                          ],
                        ),
                      ),
                      QuantityStepper(
                        quantity: line.quantity,
                        onMinus: () => cart.remove(line.product),
                        onPlus: line.quantity < line.product.stock
                            ? () => cart.add(line.product)
                            : null,
                      ),
                    ],
                  ),
                ),
              const Divider(height: 28),
              SegmentedButton<OrderType>(
                showSelectedIcon: false,
                style: SegmentedButton.styleFrom(
                  selectedBackgroundColor: AppColors.espresso,
                  selectedForegroundColor: Colors.white,
                ),
                segments: const [
                  ButtonSegment(
                    value: OrderType.table,
                    icon: Icon(Icons.table_restaurant_outlined),
                    label: Text('En mesa'),
                  ),
                  ButtonSegment(
                    value: OrderType.takeaway,
                    icon: Icon(Icons.shopping_bag_outlined),
                    label: Text('Para llevar'),
                  ),
                ],
                selected: {_type},
                onSelectionChanged: (s) => setState(() => _type = s.first),
              ),
              const SizedBox(height: 12),
              if (_type == OrderType.table) ...[
                DropdownButtonFormField<int>(
                  initialValue: _tableId,
                  decoration: const InputDecoration(hintText: '¿En qué mesa estás?'),
                  items: [
                    for (final t in tables)
                      DropdownMenuItem(
                        value: t.id,
                        child: Text('Mesa ${t.number} · ${t.capacity} puestos'),
                      ),
                  ],
                  onChanged: (v) => setState(() => _tableId = v),
                  validator: (v) => v == null ? 'Elige tu mesa' : null,
                ),
                const SizedBox(height: 12),
              ],
              TextFormField(
                controller: _name,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(hintText: '¿A nombre de quién?'),
                validator: (v) =>
                    (v == null || v.trim().isEmpty) ? 'Dinos tu nombre' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _notes,
                maxLength: 300,
                decoration: const InputDecoration(
                  hintText: 'Notas (sin azúcar, leche deslactosada…)',
                  counterText: '',
                ),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Total', style: theme.textTheme.titleMedium),
                  Text(formatCop(total),
                      style:
                          theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
                ],
              ),
              if (_error != null) ...[
                const SizedBox(height: 8),
                Text(_error!, style: const TextStyle(color: Colors.redAccent)),
              ],
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _sending ? null : _confirm,
                child: _sending
                    ? const SizedBox.square(
                        dimension: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Confirmar pedido'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
