/// Estados del pedido tal como los devuelve la API.
enum OrderStatus {
  pending('pendiente', 'Nuevo'),
  preparing('preparando', 'En preparación'),
  ready('listo', 'Listo'),
  delivered('entregado', 'Entregado'),
  cancelled('cancelado', 'Cancelado');

  const OrderStatus(this.api, this.label);

  final String api;
  final String label;

  static OrderStatus parse(String value) =>
      values.firstWhere((s) => s.api == value, orElse: () => pending);

  /// Nombre del estado desde el punto de vista del cliente.
  String get customerLabel => switch (this) {
        pending => 'Recibido',
        preparing => 'Preparando',
        ready => 'Listo',
        delivered => 'Entregado',
        cancelled => 'Cancelado',
      };

  bool get isFinal => this == delivered || this == cancelled;

  bool get canCancel => this == pending || this == preparing;

  /// Siguiente paso del flujo y el texto del botón que lo ejecuta.
  (OrderStatus, String)? get next => switch (this) {
        pending => (preparing, 'Preparar'),
        preparing => (ready, 'Marcar listo'),
        ready => (delivered, 'Entregar'),
        _ => null,
      };

  /// Posición en la línea de tiempo del cliente (0..3); -1 si se canceló.
  int get step => switch (this) {
        pending => 0,
        preparing => 1,
        ready => 2,
        delivered => 3,
        cancelled => -1,
      };

  /// Mensaje para el cliente según cómo pidió ("mesa" o "llevar").
  String customerMessage({required bool atTable, int? tableNumber}) =>
      switch (this) {
        pending => 'Recibimos tu pedido. Enseguida lo empezamos.',
        preparing => 'Estamos preparando tu pedido.',
        ready => atTable
            ? '¡Listo! Ya te lo llevamos a tu mesa${tableNumber == null ? '' : ' ($tableNumber)'}.'
            : '¡Listo! Pasa por el mostrador a recogerlo.',
        delivered => '¡Buen provecho!',
        cancelled => 'Tu pedido fue cancelado. Si fue un error, avísanos.',
      };
}

/// Cómo se sirve el pedido.
enum OrderType {
  table('mesa', 'En mesa'),
  takeaway('llevar', 'Para llevar');

  const OrderType(this.api, this.label);

  final String api;
  final String label;

  static OrderType parse(String? value) =>
      values.firstWhere((t) => t.api == value, orElse: () => takeaway);
}
