"""Carga un menú y unas mesas de ejemplo en una base de datos vacía.

Es seguro repetirlo: solo inserta datos si NO existe ninguna categoría, producto
ni mesa. Nunca modifica ni borra lo que ya hay, así que los cambios hechos desde
el panel de administración sobreviven a los redespliegues.

Se activa al arrancar con `SEED_DEMO_DATA=true` (ver `init_db`).
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Product, Table

logger = logging.getLogger("seed_demo")

_PHOTO = "https://images.unsplash.com/{id}?w=600&q=70&auto=format&fit=crop"

#: (categoría, [(nombre, descripción, precio COP, foto)])
MENU: list[tuple[str, list[tuple[str, str, int, str]]]] = [
    (
        "Café caliente",
        [
            (
                "Tinto de la casa",
                "Café de origen colombiano, filtrado al momento",
                3500,
                "photo-1509042239860-f550ce710b93",
            ),
            (
                "Cappuccino",
                "Espresso con leche vaporizada y espuma cremosa",
                8500,
                "photo-1485808191679-5f86510681a2",
            ),
            (
                "Latte",
                "Suave, con leche texturizada y arte latte",
                9000,
                "photo-1572442388796-11668a67e53d",
            ),
            (
                "Americano",
                "Espresso largo, intenso y limpio",
                5500,
                "photo-1514432324607-a09d9b4aefdd",
            ),
        ],
    ),
    (
        "Café frío",
        [
            (
                "Cold Brew",
                "Macerado en frío por 18 horas",
                10500,
                "photo-1461023058943-07fcbe16d735",
            ),
            (
                "Capuchino frío",
                "Espresso, leche fría y hielo",
                9500,
                "photo-1495474472287-4d71bcdd2085",
            ),
        ],
    ),
    (
        "Panadería",
        [
            (
                "Croissant de mantequilla",
                "Hojaldrado, horneado cada mañana",
                6500,
                "photo-1555507036-ab1f4038808a",
            ),
            (
                "Pan de bono",
                "Tradicional colombiano, calientico",
                3000,
                "photo-1509440159596-0249088772ff",
            ),
        ],
    ),
]

#: Número de mesa -> puestos.
TABLES: dict[int, int] = {1: 2, 2: 2, 3: 2, 4: 2, 5: 4, 6: 4}

DEFAULT_STOCK = 50


def _is_empty(session: Session) -> bool:
    """Indica si no hay categorías, productos ni mesas."""
    return all(
        session.execute(select(func.count()).select_from(model)).scalar_one() == 0
        for model in (Category, Product, Table)
    )


def seed_demo_data(session: Session) -> bool:
    """Inserta el menú y las mesas de ejemplo. Devuelve `True` si cargó datos."""
    if not _is_empty(session):
        logger.info("Ya hay menú o mesas: no se cargan datos de ejemplo.")
        return False

    for category_name, products in MENU:
        category = Category(name=category_name)
        session.add(category)
        session.flush()
        for name, description, price, photo in products:
            session.add(
                Product(
                    name=name,
                    description=description,
                    price=price,
                    image_url=_PHOTO.format(id=photo),
                    stock=DEFAULT_STOCK,
                    category_id=category.id,
                )
            )

    for number, capacity in TABLES.items():
        session.add(Table(number=number, capacity=capacity))

    session.commit()
    logger.info("Datos de ejemplo cargados (menú y mesas).")
    return True
