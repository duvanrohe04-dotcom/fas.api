import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/formatters.dart';
import '../../shared/widgets/async_view.dart';
import '../../shared/widgets/product_image.dart';
import '../menu/menu_models.dart';
import '../menu/menu_repository.dart';
import 'product_form_dialog.dart';

class ProductsTab extends ConsumerWidget {
  const ProductsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final products = ref.watch(productsProvider);

    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.espresso,
        foregroundColor: Colors.white,
        onPressed: () => showProductForm(context),
        icon: const Icon(Icons.add),
        label: const Text('Nuevo producto'),
      ),
      body: AsyncView(
        value: products,
        onRetry: () => ref.invalidate(productsProvider),
        builder: (list) {
          if (list.isEmpty) return const Center(child: Text('Aún no hay productos'));
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
            itemCount: list.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, i) => _ProductRow(product: list[i]),
          );
        },
      ),
    );
  }
}

class _ProductRow extends ConsumerWidget {
  const _ProductRow({required this.product});

  final Product product;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    return InkWell(
      borderRadius: BorderRadius.circular(AppRadius.card),
      onTap: () => showProductForm(context, product: product),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(AppRadius.card),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            ProductImage(url: product.imageUrl, size: 64),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(product.name,
                      style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
                  Text('${formatCop(product.price)} · Stock: ${product.stock}',
                      style: theme.textTheme.bodySmall?.copyWith(color: AppColors.textMuted)),
                ],
              ),
            ),
            Tooltip(
              message: product.isActive ? 'Visible para clientes' : 'Oculto',
              child: Switch(
                value: product.isActive,
                onChanged: (v) async {
                  final messenger = ScaffoldMessenger.of(context);
                  try {
                    await ref.read(menuRepositoryProvider).setActive(product.id, v);
                    ref.invalidate(productsProvider);
                  } on ApiException catch (e) {
                    messenger.showSnackBar(SnackBar(content: Text(e.message)));
                  }
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
