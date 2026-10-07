class Category {
  const Category({required this.id, required this.name});

  final int id;
  final String name;

  factory Category.fromJson(Map<String, dynamic> json) =>
      Category(id: json['id'] as int, name: json['name'] as String);
}

class Product {
  const Product({
    required this.id,
    required this.name,
    required this.description,
    required this.price,
    required this.imageUrl,
    required this.categoryId,
    required this.stock,
    required this.isActive,
  });

  final int id;
  final String name;
  final String? description;
  final double price;
  final String? imageUrl;
  final int categoryId;
  final int stock;
  final bool isActive;

  bool get available => isActive && stock > 0;

  factory Product.fromJson(Map<String, dynamic> json) => Product(
        id: json['id'] as int,
        name: json['name'] as String,
        description: json['description'] as String?,
        price: (json['price'] as num).toDouble(),
        imageUrl: json['image_url'] as String?,
        categoryId: json['category_id'] as int,
        stock: json['stock'] as int,
        isActive: json['is_active'] as bool,
      );
}
