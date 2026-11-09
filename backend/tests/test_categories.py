from sqlalchemy import func, select

from app.models import Category
from app.services.base_seed import seed_categories

EXPECTED = {
    "Ropa": ["Camisetas", "Camisas", "Sudaderas", "Pantalones", "Vestidos", "Chamarras"],
    "Calzado": ["Sneakers", "Botas", "Sandalias", "Zapatos"],
    "Bolsos": ["Bolsas", "Mochilas", "Clutches", "Carteras"],
    "Accesorios": ["Cinturones", "Gorras", "Lentes", "Pañuelos"],
    "Joyería": ["Anillos", "Pulseras", "Collares"],
    "Relojería": ["Relojes"],
    "Equipaje": ["Maletas", "Artículos de viaje"],
    "Otros": ["Artículos especiales", "Coleccionables"],
}


def test_seed_tree_is_idempotent(db):
    seed_categories(db)
    db.commit()
    total = db.scalar(select(func.count()).select_from(Category))
    assert total == len(EXPECTED) + sum(len(children) for children in EXPECTED.values())
    seed_categories(db)
    db.commit()
    assert db.scalar(select(func.count()).select_from(Category)) == total


def test_endpoint_returns_the_tree_in_order(db, public_client):
    seed_categories(db)
    db.commit()
    items = public_client.get("/api/v1/categories").json()["items"]
    assert items[0] == {"slug": "ropa", "name": "Ropa", "parent_slug": None}
    assert items[1] == {"slug": "camisetas", "name": "Camisetas", "parent_slug": "ropa"}
    by_name = {item["name"]: item for item in items}
    for parent, children in EXPECTED.items():
        assert by_name[parent]["parent_slug"] is None
        for child in children:
            assert by_name[child]["parent_slug"] == by_name[parent]["slug"]
