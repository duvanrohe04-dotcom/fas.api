import 'package:flutter/material.dart';

class QuantityStepper extends StatelessWidget {
  const QuantityStepper({
    super.key,
    required this.quantity,
    required this.onMinus,
    required this.onPlus,
  });

  final int quantity;
  final VoidCallback onMinus;
  final VoidCallback? onPlus;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          visualDensity: VisualDensity.compact,
          tooltip: 'Quitar uno',
          onPressed: onMinus,
          icon: const Icon(Icons.remove_circle_outline),
        ),
        Text('$quantity', style: const TextStyle(fontWeight: FontWeight.w700)),
        IconButton(
          visualDensity: VisualDensity.compact,
          tooltip: 'Agregar uno',
          onPressed: onPlus,
          icon: const Icon(Icons.add_circle_outline),
        ),
      ],
    );
  }
}
