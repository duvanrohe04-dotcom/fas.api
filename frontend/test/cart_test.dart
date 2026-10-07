import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:origen_cafe/features/cart/cart_controller.dart';
import 'package:origen_cafe/features/menu/menu_models.dart';

Product _product(int id, {double price = 5000, int stock = 10}) => Product(
      id: id,
      name: 'Producto $id',
      description: null,
      price: price,
      imageUrl: null,
      categoryId: 1,
      stock: stock,
      isActive: true,
    );

void main() {
  late ProviderContainer container;
  late CartController cart;

  setUp(() {
    container = ProviderContainer();
    addTearDown(container.dispose);
    cart = container.read(cartProvider.notifier);
  });

  test('agrega y acumula cantidades', () {
    final p = _product(1);
    cart
      ..add(p)
      ..add(p);

    expect(container.read(cartProvider)[1]?.quantity, 2);
    expect(container.read(cartCountProvider), 2);
  });

  test('calcula el total del pedido', () {
    cart
      ..add(_product(1, price: 8500))
      ..add(_product(1, price: 8500))
      ..add(_product(2, price: 3000));

    expect(container.read(cartTotalProvider), 20000);
  });

  test('no supera el stock disponible', () {
    final p = _product(1, stock: 2);
    cart
      ..add(p)
      ..add(p)
      ..add(p);

    expect(container.read(cartProvider)[1]?.quantity, 2);
  });

  test('quitar la última unidad elimina la línea', () {
    final p = _product(1);
    cart
      ..add(p)
      ..remove(p);

    expect(container.read(cartProvider), isEmpty);
    expect(container.read(cartCountProvider), 0);
  });

  test('clear vacía el pedido', () {
    cart
      ..add(_product(1))
      ..add(_product(2))
      ..clear();

    expect(container.read(cartProvider), isEmpty);
  });
}
