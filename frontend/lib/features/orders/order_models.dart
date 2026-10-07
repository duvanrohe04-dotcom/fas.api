import 'order_status.dart';

class TableInfo {
  const TableInfo({
    required this.id,
    required this.number,
    required this.capacity,
    required this.occupied,
  });

  final int id;
  final int number;
  final int capacity;
  final bool occupied;

  factory TableInfo.fromJson(Map<String, dynamic> json) => TableInfo(
        id: json['id'] as int,
        number: json['number'] as int,
        capacity: json['capacity'] as int,
        occupied: json['status'] == 'ocupada',
      );
}

/// Pedido visto por el cliente (respuesta de crear o de seguir un pedido).
class TrackedOrder {
  const TrackedOrder({
    required this.id,
    required this.status,
    required this.type,
    required this.tableNumber,
    required this.customerName,
    required this.total,
    this.code,
  });

  final int id;
  final OrderStatus status;
  final OrderType type;
  final int? tableNumber;
  final String? customerName;
  final double total;

  /// Código de seguimiento; solo viene al crear el pedido.
  final String? code;

  bool get atTable => type == OrderType.table;

  factory TrackedOrder.fromJson(Map<String, dynamic> json) => TrackedOrder(
        id: json['id'] as int,
        status: OrderStatus.parse(json['status'] as String),
        type: OrderType.parse(json['order_type'] as String?),
        tableNumber: json['table_number'] as int?,
        customerName: json['customer_name'] as String?,
        total: (json['total_amount'] as num).toDouble(),
        code: json['tracking_code'] as String?,
      );
}
