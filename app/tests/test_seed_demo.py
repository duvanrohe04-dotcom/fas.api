from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Product, Table
from app.scripts import init_db
from app.scripts.seed_demo import MENU, TABLES, seed_demo_data


def _count(session: Session, model: type) -> int:
    return session.execute(select(func.count()).select_from(model)).scalar_one()


def test_carga_menu_y_mesas_en_una_base_vacia(session: Session):
    assert seed_demo_data(session) is True

    assert _count(session, Category) == len(MENU)
    assert _count(session, Product) == sum(len(p) for _, p in MENU)
    assert _count(session, Table) == len(TABLES)
    producto = session.execute(select(Product).limit(1)).scalar_one()
    assert producto.image_url and producto.price > 0 and producto.stock > 0


def test_repetirlo_no_duplica_ni_pisa_cambios(session: Session):
    seed_demo_data(session)
    cafe = session.execute(select(Product).where(Product.name == "Latte")).scalar_one()
    cafe.price = 12345
    session.commit()

    assert seed_demo_data(session) is False

    assert _count(session, Product) == sum(len(p) for _, p in MENU)
    session.refresh(cafe)
    assert cafe.price == 12345


def test_no_carga_nada_si_ya_hay_datos(session: Session):
    session.add(Category(name="Mi categoría"))
    session.commit()

    assert seed_demo_data(session) is False
    assert _count(session, Product) == 0


def test_load_demo_data_respeta_la_variable_de_entorno(session: Session, monkeypatch):
    monkeypatch.setattr(init_db, "SessionLocal", lambda: session)

    monkeypatch.delenv("SEED_DEMO_DATA", raising=False)
    init_db.load_demo_data()
    assert _count(session, Product) == 0

    monkeypatch.setenv("SEED_DEMO_DATA", "true")
    init_db.load_demo_data()
    assert _count(session, Product) > 0
