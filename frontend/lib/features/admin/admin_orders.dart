import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import '../orders/order_models.dart';
import '../orders/order_status.dart';

class OrderLine {
  const OrderLine({required this.productId, required this.quantity, required this.subtotal});

  final int productId;
  final int quantity;
  final double subtotal;
}

class AdminOrder {
  const AdminOrder({
    required this.id,
    required this.status,
    required this.type,
    required this.tableNumber,
    required this.customerName,
    required this.notes,
    required this.createdAt,
    required this.isPaid,
    required this.total,
    required this.lines,
  });

  final int id;
  final OrderStatus status;
  final OrderType type;
  final int? tableNumber;
  final String? customerName;
  final String? notes;
  final DateTime? createdAt;
  final bool isPaid;
  final double total;
  final List<OrderLine> lines;

  /// Lo que el personal necesita ver primero: a dónde va el pedido.
  String get destination =>
      type == OrderType.table ? 'Mesa ${tableNumber ?? '-'}' : 'Para llevar';

  factory AdminOrder.fromJson(Map<String, dynamic> json) => AdminOrder(
        id: json['id'] as int,
        status: OrderStatus.parse(json['status'] as String),
        type: OrderType.parse(json['order_type'] as String?),
        tableNumber: json['table_number'] as int?,
        customerName: json['customer_name'] as String?,
        notes: json['notes'] as String?,
        createdAt: json['created_at'] == null
            ? null
            : DateTime.tryParse(_asUtc(json['created_at'] as String))?.toLocal(),
        isPaid: json['is_paid'] as bool,
        total: (json['total_amount'] as num).toDouble(),
        lines: [
          for (final i in json['items'] as List<dynamic>)
            OrderLine(
              productId: (i as Map<String, dynamic>)['product_id'] as int,
              quantity: i['quantity'] as int,
              subtotal: (i['subtotal'] as num).toDouble(),
            ),
        ],
      );

  /// La API puede devolver fechas UTC sin sufijo de zona.
  static String _asUtc(String value) =>
      value.endsWith('Z') || value.contains('+') ? value : '${value}Z';
}

class OrdersSummary {
  const OrdersSummary({
    required this.pending,
    required this.active,
    required this.ordersToday,
    required this.salesToday,
    required this.awaitingPayment,
  });

  final int pending;
  final int active;
  final int ordersToday;
  final double salesToday;
  final int awaitingPayment;

  factory OrdersSummary.fromJson(Map<String, dynamic> json) => OrdersSummary(
        pending: json['pending'] as int,
        active: json['active'] as int,
        ordersToday: json['orders_today'] as int,
        salesToday: (json['sales_today'] as num).toDouble(),
        awaitingPayment: json['awaiting_payment'] as int,
      );
}

enum PaymentMethod {
  cash('efectivo', 'Efectivo'),
  card('tarjeta', 'Tarjeta'),
  transfer('transferencia', 'Transferencia');

  const PaymentMethod(this.api, this.label);

  final String api;
  final String label;
}

class AdminOrderRepository {
  AdminOrderRepository(this._dio);

  final Dio _dio;

  Future<T> _guard<T>(Future<T> Function() call) async {
    try {
      return await call();
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<List<AdminOrder>> list(OrderStatus status) => _guard(() async {
        final res = await _dio.get<Map<String, dynamic>>(
          '/orders',
          queryParameters: {'status': status.api, 'page': 1, 'size': 50},
        );
        return [
          for (final e in res.data!['items'] as List<dynamic>)
            AdminOrder.fromJson(e as Map<String, dynamic>),
        ];
      });

  Future<void> setStatus(int orderId, OrderStatus status) => _guard(
        () => _dio.patch<void>('/orders/$orderId/status', data: {'status': status.api}),
      );

  Future<void> pay(int orderId, PaymentMethod method, double amount) => _guard(
        () => _dio.post<void>(
          '/orders/$orderId/pay',
          data: {'method': method.api, 'amount': amount},
        ),
      );

  Future<OrdersSummary> summary() => _guard(() async {
        final res = await _dio.get<Map<String, dynamic>>('/orders/summary');
        return OrdersSummary.fromJson(res.data!);
      });

  Future<List<TableInfo>> tables() => _guard(() async {
        final res = await _dio.get<Map<String, dynamic>>(
          '/tables',
          queryParameters: {'page': 1, 'size': 100},
        );
        return [
          for (final t in res.data!['items'] as List<dynamic>)
            TableInfo.fromJson(t as Map<String, dynamic>),
        ];
      });

  Future<void> createTable(int number, int capacity) => _guard(
        () => _dio.post<void>('/tables', data: {'number': number, 'capacity': capacity}),
      );

  Future<void> setTableOccupied(int tableId, bool occupied) => _guard(
        () => _dio.patch<void>(
          '/tables/$tableId/status',
          queryParameters: {'status': occupied ? 'ocupada' : 'disponible'},
        ),
      );
}

final adminOrderRepositoryProvider = Provider<AdminOrderRepository>(
  (ref) => AdminOrderRepository(ref.watch(dioProvider)),
);

final orderFilterProvider = StateProvider<OrderStatus>((ref) => OrderStatus.pending);

/// Se refresca solo cada 15 s mientras la pestaña está abierta.
final adminOrdersProvider = StreamProvider.autoDispose<List<AdminOrder>>((ref) async* {
  final status = ref.watch(orderFilterProvider);
  final repo = ref.watch(adminOrderRepositoryProvider);
  while (true) {
    yield await repo.list(status);
    await Future<void>.delayed(const Duration(seconds: 15));
  }
});

final adminSummaryProvider = StreamProvider.autoDispose<OrdersSummary>((ref) async* {
  final repo = ref.watch(adminOrderRepositoryProvider);
  while (true) {
    yield await repo.summary();
    await Future<void>.delayed(const Duration(seconds: 15));
  }
});

final adminTablesProvider = FutureProvider.autoDispose<List<TableInfo>>(
  (ref) => ref.watch(adminOrderRepositoryProvider).tables(),
);
