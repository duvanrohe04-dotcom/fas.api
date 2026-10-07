import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../menu/menu_models.dart';
import '../orders/order_models.dart';
import '../orders/order_status.dart';

class CartLine {
  const CartLine({required this.product, required this.quantity});

  final Product product;
  final int quantity;

  double get subtotal => product.price * quantity;
}

class CartController extends Notifier<Map<int, CartLine>> {
  @override
  Map<int, CartLine> build() => const {};

  int quantityOf(int productId) => state[productId]?.quantity ?? 0;

  void add(Product product) => setQuantity(product, quantityOf(product.id) + 1);

  void remove(Product product) => setQuantity(product, quantityOf(product.id) - 1);

  /// Fija la cantidad respetando el stock. Cantidad 0 quita la línea.
  void setQuantity(Product product, int quantity) {
    final next = {...state};
    if (quantity <= 0) {
      next.remove(product.id);
    } else {
      next[product.id] = CartLine(
        product: product,
        quantity: quantity.clamp(1, product.stock),
      );
    }
    state = next;
  }

  void clear() => state = const {};
}

final cartProvider =
    NotifierProvider<CartController, Map<int, CartLine>>(CartController.new);

final cartCountProvider = Provider<int>(
  (ref) => ref.watch(cartProvider).values.fold(0, (sum, l) => sum + l.quantity),
);

final cartTotalProvider = Provider<double>(
  (ref) => ref.watch(cartProvider).values.fold(0.0, (sum, l) => sum + l.subtotal),
);

/// Operaciones públicas (sin sesión) del cliente.
class OrderRepository {
  OrderRepository(this._dio);

  final Dio _dio;

  Future<TrackedOrder> createPublic(
    Iterable<CartLine> lines, {
    required OrderType type,
    int? tableId,
    String? customerName,
    String? notes,
  }) async {
    try {
      final res = await _dio.post<Map<String, dynamic>>(
        '/orders/public',
        data: {
          'order_type': type.api,
          'table_id': type == OrderType.table ? tableId : null,
          'customer_name': customerName,
          'notes': notes,
          'items': [
            for (final l in lines) {'product_id': l.product.id, 'quantity': l.quantity},
          ],
        },
      );
      return TrackedOrder.fromJson(res.data!);
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<TrackedOrder> track(String code) async {
    try {
      final res = await _dio.get<Map<String, dynamic>>('/orders/track/$code');
      return TrackedOrder.fromJson(res.data!);
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<List<TableInfo>> tables() async {
    try {
      final res = await _dio.get<List<dynamic>>('/tables/public');
      return [
        for (final t in res.data!) TableInfo.fromJson(t as Map<String, dynamic>),
      ];
    } catch (e) {
      throw ApiException.from(e);
    }
  }
}

final orderRepositoryProvider = Provider<OrderRepository>(
  (ref) => OrderRepository(ref.watch(dioProvider)),
);

final publicTablesProvider = FutureProvider<List<TableInfo>>(
  (ref) => ref.watch(orderRepositoryProvider).tables(),
);
