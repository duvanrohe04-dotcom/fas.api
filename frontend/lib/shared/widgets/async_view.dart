import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

Widget _errorBody(Object error, VoidCallback? onRetry) => Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(error.toString(), textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              OutlinedButton(onPressed: onRetry, child: const Text('Reintentar')),
            ],
          ],
        ),
      ),
    );

/// Renderiza los tres estados de un `AsyncValue` con reintento.
class AsyncView<T> extends StatelessWidget {
  const AsyncView({
    super.key,
    required this.value,
    required this.builder,
    this.onRetry,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => value.when(
        data: builder,
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _errorBody(error, onRetry),
      );
}

/// Igual que [AsyncView] pero para usar dentro de un `CustomScrollView`.
class AsyncSliver<T> extends StatelessWidget {
  const AsyncSliver({
    super.key,
    required this.value,
    required this.builder,
    this.onRetry,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) builder;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => value.when(
        data: builder,
        loading: () => const SliverFillRemaining(
          hasScrollBody: false,
          child: Center(child: CircularProgressIndicator()),
        ),
        error: (error, _) => SliverFillRemaining(
          hasScrollBody: false,
          child: _errorBody(error, onRetry),
        ),
      );
}
