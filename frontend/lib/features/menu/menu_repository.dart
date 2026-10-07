import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_client.dart';
import 'menu_models.dart';

class MenuRepository {
  MenuRepository(this._dio);

  final Dio _dio;

  Future<List<T>> _fetchAll<T>(
    String path,
    T Function(Map<String, dynamic>) fromJson,
  ) async {
    try {
      final res = await _dio.get<Map<String, dynamic>>(
        path,
        queryParameters: {'page': 1, 'size': 100},
      );
      final items = res.data!['items'] as List<dynamic>;
      return items.map((e) => fromJson(e as Map<String, dynamic>)).toList();
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<List<Category>> categories() => _fetchAll('/categories', Category.fromJson);

  Future<List<Product>> products() => _fetchAll('/products', Product.fromJson);

  /// Crea (sin [id]) o actualiza un producto. Solo administradores.
  Future<void> save({
    int? id,
    required String name,
    required String? description,
    required double price,
    required int stock,
    required int categoryId,
    required String? imageUrl,
    required bool isActive,
  }) async {
    final body = {
      'name': name,
      'description': description,
      'price': price,
      'stock': stock,
      'category_id': categoryId,
      'image_url': imageUrl,
    };
    try {
      if (id == null) {
        await _dio.post<void>('/products', data: body);
      } else {
        await _dio.patch<void>('/products/$id', data: {...body, 'is_active': isActive});
      }
    } catch (e) {
      throw ApiException.from(e);
    }
  }

  Future<void> setActive(int id, bool active) async {
    try {
      await _dio.patch<void>('/products/$id', data: {'is_active': active});
    } catch (e) {
      throw ApiException.from(e);
    }
  }
}

final menuRepositoryProvider = Provider<MenuRepository>(
  (ref) => MenuRepository(ref.watch(dioProvider)),
);

final categoriesProvider = FutureProvider<List<Category>>(
  (ref) => ref.watch(menuRepositoryProvider).categories(),
);

/// Todos los productos (incluye inactivos; el cliente filtra).
final productsProvider = FutureProvider<List<Product>>(
  (ref) => ref.watch(menuRepositoryProvider).products(),
);

/// Categoría seleccionada en el menú del cliente (`null` = todas).
final selectedCategoryProvider = StateProvider<int?>((ref) => null);

final customerProductsProvider = Provider<AsyncValue<List<Product>>>((ref) {
  final selected = ref.watch(selectedCategoryProvider);
  return ref.watch(productsProvider).whenData(
        (all) => all
            .where((p) => p.isActive && (selected == null || p.categoryId == selected))
            .toList(),
      );
});
