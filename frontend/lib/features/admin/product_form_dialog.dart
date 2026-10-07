import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../../shared/widgets/product_image.dart';
import '../menu/menu_models.dart';
import '../menu/menu_repository.dart';

Future<void> showProductForm(BuildContext context, {Product? product}) =>
    showDialog<void>(
      context: context,
      builder: (_) => _ProductForm(product: product),
    );

class _ProductForm extends ConsumerStatefulWidget {
  const _ProductForm({this.product});

  final Product? product;

  @override
  ConsumerState<_ProductForm> createState() => _ProductFormState();
}

class _ProductFormState extends ConsumerState<_ProductForm> {
  final _formKey = GlobalKey<FormState>();
  late final _name = TextEditingController(text: widget.product?.name);
  late final _description = TextEditingController(text: widget.product?.description);
  late final _price = TextEditingController(
    text: widget.product == null ? '' : widget.product!.price.round().toString(),
  );
  late final _stock = TextEditingController(text: '${widget.product?.stock ?? 0}');
  late final _image = TextEditingController(text: widget.product?.imageUrl);
  late int? _categoryId = widget.product?.categoryId;
  late bool _active = widget.product?.isActive ?? true;
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    for (final c in [_name, _description, _price, _stock, _image]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref.read(menuRepositoryProvider).save(
            id: widget.product?.id,
            name: _name.text.trim(),
            description: _description.text.trim().isEmpty ? null : _description.text.trim(),
            price: double.parse(_price.text.trim()),
            stock: int.parse(_stock.text.trim()),
            categoryId: _categoryId!,
            imageUrl: _image.text.trim().isEmpty ? null : _image.text.trim(),
            isActive: _active,
          );
      ref.invalidate(productsProvider);
      if (mounted) Navigator.of(context).pop();
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  String? _required(String? v) => (v == null || v.trim().isEmpty) ? 'Obligatorio' : null;

  @override
  Widget build(BuildContext context) {
    final categories = ref.watch(categoriesProvider).valueOrNull ?? const <Category>[];

    return AlertDialog(
      title: Text(widget.product == null ? 'Nuevo producto' : 'Editar producto'),
      content: SizedBox(
        width: 440,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ValueListenableBuilder(
                  valueListenable: _image,
                  builder: (_, value, __) => SizedBox(
                    height: 140,
                    width: double.infinity,
                    child: ProductImage(url: value.text.trim()),
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _image,
                  decoration: const InputDecoration(hintText: 'Enlace de la imagen (URL)'),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _name,
                  decoration: const InputDecoration(hintText: 'Nombre'),
                  validator: _required,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _description,
                  decoration: const InputDecoration(hintText: 'Descripción (opcional)'),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextFormField(
                        controller: _price,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(hintText: 'Precio (COP)'),
                        validator: (v) {
                          final n = double.tryParse(v ?? '');
                          return (n == null || n <= 0) ? 'Precio inválido' : null;
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextFormField(
                        controller: _stock,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(hintText: 'Stock'),
                        validator: (v) {
                          final n = int.tryParse(v ?? '');
                          return (n == null || n < 0) ? 'Stock inválido' : null;
                        },
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  initialValue: _categoryId,
                  decoration: const InputDecoration(hintText: 'Categoría'),
                  items: [
                    for (final c in categories)
                      DropdownMenuItem(value: c.id, child: Text(c.name)),
                  ],
                  onChanged: (v) => setState(() => _categoryId = v),
                  validator: (v) => v == null ? 'Elige una categoría' : null,
                ),
                if (widget.product != null)
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Visible para clientes'),
                    value: _active,
                    onChanged: (v) => setState(() => _active = v),
                  ),
                if (_error != null) ...[
                  const SizedBox(height: 8),
                  Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                ],
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          style: FilledButton.styleFrom(minimumSize: const Size(120, 44)),
          onPressed: _saving ? null : _save,
          child: const Text('Guardar'),
        ),
      ],
    );
  }
}
