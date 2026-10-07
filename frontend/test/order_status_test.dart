import 'package:flutter_test/flutter_test.dart';
import 'package:origen_cafe/features/orders/order_status.dart';

void main() {
  group('OrderStatus', () {
    test('interpreta los valores de la API', () {
      expect(OrderStatus.parse('pendiente'), OrderStatus.pending);
      expect(OrderStatus.parse('listo'), OrderStatus.ready);
      expect(OrderStatus.parse('cancelado'), OrderStatus.cancelled);
      expect(OrderStatus.parse('desconocido'), OrderStatus.pending);
    });

    test('el flujo avanza paso a paso hasta entregar', () {
      expect(OrderStatus.pending.next?.$1, OrderStatus.preparing);
      expect(OrderStatus.preparing.next?.$1, OrderStatus.ready);
      expect(OrderStatus.ready.next?.$1, OrderStatus.delivered);
      expect(OrderStatus.delivered.next, isNull);
      expect(OrderStatus.cancelled.next, isNull);
    });

    test('solo se cancela antes de estar listo', () {
      expect(OrderStatus.pending.canCancel, isTrue);
      expect(OrderStatus.preparing.canCancel, isTrue);
      expect(OrderStatus.ready.canCancel, isFalse);
      expect(OrderStatus.delivered.canCancel, isFalse);
    });

    test('entregado y cancelado son estados finales', () {
      expect(OrderStatus.delivered.isFinal, isTrue);
      expect(OrderStatus.cancelled.isFinal, isTrue);
      expect(OrderStatus.preparing.isFinal, isFalse);
    });

    test('el mensaje del cliente depende de mesa o para llevar', () {
      final atTable =
          OrderStatus.ready.customerMessage(atTable: true, tableNumber: 3);
      final takeaway = OrderStatus.ready.customerMessage(atTable: false);

      expect(atTable, contains('mesa (3)'));
      expect(takeaway, contains('mostrador'));
    });
  });

  group('OrderType', () {
    test('usa para llevar cuando el valor es nulo o desconocido', () {
      expect(OrderType.parse('mesa'), OrderType.table);
      expect(OrderType.parse(null), OrderType.takeaway);
      expect(OrderType.parse('x'), OrderType.takeaway);
    });
  });
}
