import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../shared/formatters.dart';
import '../../shared/widgets/async_view.dart';
import '../../shared/widgets/product_image.dart';
import '../cart/cart_controller.dart';
import '../menu/menu_models.dart';
import '../menu/menu_repository.dart';
import '../../shared/widgets/quantity_stepper.dart';
import 'cart_dialog.dart';
import 'tracking.dart';

/// Página única del cliente: elegir productos y pedir.
class CustomerPage extends ConsumerWidget {
  const CustomerPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final products = ref.watch(customerProductsProvider);
    final count = ref.watch(cartCountProvider);
    final total = ref.watch(cartTotalProvider);

    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1100),
          child: CustomScrollView(
            slivers: [
              const SliverToBoxAdapter(child: _Header()),
              const SliverToBoxAdapter(child: TrackingBanner()),
              const SliverToBoxAdapter(child: _CategoryBar()),
              AsyncSliver<List<Product>>(
                value: products,
                onRetry: () => ref.invalidate(productsProvider),
                builder: (items) {
                  if (items.isEmpty) {
                    return const SliverFillRemaining(
                      hasScrollBody: false,
                      child: Center(child: Text('No hay productos en esta categoría')),
                    );
                  }
                  return SliverPadding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                    sliver: SliverGrid.builder(
                      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                        maxCrossAxisExtent: 260,
                        mainAxisSpacing: 16,
                        crossAxisSpacing: 16,
                        childAspectRatio: 0.72,
                      ),
                      itemCount: items.length,
                      itemBuilder: (_, i) => _ProductCard(product: items[i]),
                    ),
                  );
                },
              ),
            ],
          ),
        ),
      ),
      bottomNavigationBar: count == 0
          ? null
          : SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Center(
                  heightFactor: 1,
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 480),
                    child: FilledButton(
                      onPressed: () => showCartDialog(context),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Ver mi pedido ($count)'),
                          Text(formatCop(total)),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 24, 16, 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.coffee_rounded, color: AppColors.terracotta),
              const SizedBox(width: 8),
              Text('ORIGEN CAFÉ',
                  style: theme.textTheme.labelLarge?.copyWith(
                    color: AppColors.terracotta,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1,
                  )),
            ],
          ),
          const SizedBox(height: 12),
          Text('¿Qué se te antoja hoy?',
              style: theme.textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800)),
          Text('Elige tus productos y haz tu pedido en un momento.',
              style: theme.textTheme.bodyLarge?.copyWith(color: AppColors.textMuted)),
        ],
      ),
    );
  }
}

class _CategoryBar extends ConsumerWidget {
  const _CategoryBar();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categories = ref.watch(categoriesProvider).valueOrNull ?? const <Category>[];
    final selected = ref.watch(selectedCategoryProvider);
    if (categories.isEmpty) return const SizedBox(height: 16);

    Widget chip(String label, int? id) => Padding(
          padding: const EdgeInsets.only(right: 8),
          child: ChoiceChip(
            label: Text(label),
            selected: selected == id,
            showCheckmark: false,
            shape: const StadiumBorder(),
            selectedColor: AppColors.espresso,
            labelStyle: TextStyle(
              color: selected == id ? Colors.white : null,
              fontWeight: FontWeight.w600,
            ),
            onSelected: (_) => ref.read(selectedCategoryProvider.notifier).state = id,
          ),
        );

    return SizedBox(
      height: 64,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        children: [chip('Todo', null), for (final c in categories) chip(c.name, c.id)],
      ),
    );
  }
}

class _ProductCard extends ConsumerWidget {
  const _ProductCard({required this.product});

  final Product product;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final qty = ref.watch(cartProvider.select((c) => c[product.id]?.quantity ?? 0));
    final cart = ref.read(cartProvider.notifier);

    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(AppRadius.card),
        border: Border.all(color: AppColors.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Stack(
              fit: StackFit.expand,
              children: [
                ProductImage(url: product.imageUrl, radius: 0),
                if (!product.available)
                  Container(
                    color: Colors.black54,
                    alignment: Alignment.center,
                    child: const Text('Agotado',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
                  ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(product.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
                if (product.description != null)
                  Text(product.description!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(color: AppColors.textMuted)),
                const SizedBox(height: 8),
                // Wrap: en pantallas angostas el contador baja bajo el precio.
                Wrap(
                  alignment: WrapAlignment.spaceBetween,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text(formatCop(product.price),
                        style: theme.textTheme.titleMedium
                            ?.copyWith(fontWeight: FontWeight.w800)),
                    if (qty == 0)
                      IconButton.filled(
                        tooltip: 'Agregar',
                        style: IconButton.styleFrom(backgroundColor: AppColors.espresso),
                        onPressed: product.available ? () => cart.add(product) : null,
                        icon: const Icon(Icons.add),
                      )
                    else
                      QuantityStepper(
                        quantity: qty,
                        onMinus: () => cart.remove(product),
                        onPlus: qty < product.stock ? () => cart.add(product) : null,
                      ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
