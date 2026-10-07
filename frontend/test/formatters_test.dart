import 'package:flutter_test/flutter_test.dart';
import 'package:origen_cafe/shared/formatters.dart';

void main() {
  group('formatCop', () {
    test('agrega separador de miles con punto', () {
      expect(formatCop(0), r'$0');
      expect(formatCop(950), r'$950');
      expect(formatCop(8500), r'$8.500');
      expect(formatCop(1234567), r'$1.234.567');
    });

    test('redondea los decimales a pesos enteros', () {
      expect(formatCop(8500.4), r'$8.500');
      expect(formatCop(8500.6), r'$8.501');
    });

    test('mantiene el signo en negativos', () {
      expect(formatCop(-12500), r'-$12.500');
    });
  });
}
