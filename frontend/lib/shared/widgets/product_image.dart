import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

/// Imagen de producto con marcador cuando no hay URL o falla la carga.
class ProductImage extends StatelessWidget {
  const ProductImage({super.key, required this.url, this.size, this.radius = 14});

  final String? url;

  /// Lado fijo (cuadrado). Si es `null` ocupa todo el espacio disponible.
  final double? size;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final placeholder = Container(
      color: AppColors.surfaceMuted,
      alignment: Alignment.center,
      child: const Icon(Icons.local_cafe, color: AppColors.terracotta),
    );

    final image = (url == null || url!.isEmpty)
        ? placeholder
        : Image.network(
            url!,
            fit: BoxFit.cover,
            loadingBuilder: (_, child, progress) =>
                progress == null ? child : placeholder,
            errorBuilder: (_, __, ___) => placeholder,
          );

    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: SizedBox(width: size, height: size, child: image),
    );
  }
}
