"""Seeds that hold no invented content: the category tree and the real site settings row."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.data.categories import CATEGORY_TREE
from app.models import Category, SiteSettings
from app.services.text import slugify


def seed_categories(db: Session) -> int:
    """Returns how many categories were created."""
    created = 0
    order = 0

    def ensure(name: str, parent: Category | None) -> Category:
        nonlocal created, order
        order += 1
        slug = slugify(name)
        category = db.scalar(select(Category).where(Category.slug == slug))
        if category is None:
            category = Category(
                name=name,
                slug=slug,
                parent_id=parent.id if parent else None,
                display_order=order,
            )
            db.add(category)
            db.flush()
            created += 1
        return category

    for parent_name, children in CATEGORY_TREE:
        parent = ensure(parent_name, None)
        for child_name in children:
            ensure(child_name, parent)
    return created


def seed_site_settings(db: Session, settings: Settings) -> SiteSettings:
    """Creates the real row and fills the number from WHATSAPP_NUMBER only if none is stored."""
    row = db.scalar(select(SiteSettings).where(SiteSettings.is_demo.is_(False)))
    if row is None:
        row = SiteSettings(is_demo=False)
        db.add(row)
    if not row.whatsapp_number and settings.whatsapp_number.strip():
        row.whatsapp_number = settings.whatsapp_number.strip()
    db.flush()
    return row
