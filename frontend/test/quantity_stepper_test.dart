import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:origen_cafe/shared/widgets/quantity_stepper.dart';

void main() {
  testWidgets('muestra la cantidad y avisa al sumar o restar', (tester) async {
    var plus = 0;
    var minus = 0;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: QuantityStepper(
            quantity: 3,
            onMinus: () => minus++,
            onPlus: () => plus++,
          ),
        ),
      ),
    );

    expect(find.text('3'), findsOneWidget);

    await tester.tap(find.byTooltip('Agregar uno'));
    await tester.tap(find.byTooltip('Quitar uno'));

    expect(plus, 1);
    expect(minus, 1);
  });

  testWidgets('deshabilita sumar cuando no hay más stock', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: QuantityStepper(quantity: 2, onMinus: () {}, onPlus: null),
        ),
      ),
    );

    final plusButton = tester.widget<IconButton>(
      find.widgetWithIcon(IconButton, Icons.add_circle_outline),
    );
    expect(plusButton.onPressed, isNull);
  });
}
