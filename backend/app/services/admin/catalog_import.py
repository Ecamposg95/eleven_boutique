"""Catalog import. The source spreadsheets hold prices, costs, stock, barcodes and sale history.

Those values must never reach the database, so the reader is an allow-list: `_read_rows` yields
only the contract's columns and reduces Descripcion to photo references on the spot. Nothing
downstream ever sees another column. The uploaded bytes are never written anywhere.
"""

import csv
import io
import re
import uuid
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from openpyxl import load_workbook
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.errors import ApiError
from app.models import (
    IMPORT_COMPLETED,
    IMPORT_EXPIRED,
    IMPORT_PREVIEW,
    KIND_CLASSIFICATION,
    STATUS_DRAFT,
    AdminUser,
    Brand,
    BrandAlias,
    Category,
    ImportRun,
    Product,
    ProductVariant,
)
from app.models.base import utcnow
from app.schemas import admin as schemas
from app.services.admin import audit
from app.services.admin.common import unique_slug
from app.services.admin.images import sanitize_filename
from app.services.text import normalize

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_ROWS = 20_000
PREVIEW_TTL = timedelta(minutes=30)
SAMPLE_SIZE = 10

# Zip bomb limits, checked against the archive's directory before anything is decompressed.
# zipfile refuses to read past an entry's declared size, so these numbers can be trusted.
MAX_ZIP_ENTRIES = 1_000
MAX_UNCOMPRESSED_BYTES = 200 * 1024 * 1024
MAX_RATIO = 150
RATIO_APPLIES_ABOVE = 10 * 1024 * 1024

MAX_SKU = 100
MAX_NAME = 300
MAX_CATEGORY = 200
MAX_COLOR = 100
MAX_SIZE = 50
MAX_BRAND = 200

# Normalized header -> internal field. No other column is ever read.
COLUMNS = {
    "sku": "sku",
    "nombre": "name",
    "departamento": "department",
    "marca": "brand",
    "color": "color",
    "talla": "size",
    "descripcion": "description",
}
REQUIRED_COLUMNS = ("sku", "nombre", "departamento", "marca")
TEMPLATE_HEADER = ("SKU", "Nombre", "Departamento", "Marca", "Color", "Talla", "Descripcion")
_TEXT_FIELDS = ("sku", "name", "department", "brand", "color", "size")
PREFERRED_SHEET = "plantilla"
NO_BRAND = "sin marca"

_PHOTO_REF = re.compile(r"\bFoto( mujer)? (\d+(?:\+\d+)*)(?![\d])", re.IGNORECASE)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_FORMULA_ERROR = "La celda contiene una fórmula; no se evalúa ni se importa"


def extract_photo_refs(description: str | None) -> list[str]:
    """Only what matches the reference pattern survives: "Foto 12+13" -> Foto 12, Foto 13."""
    if not description or description.startswith("="):
        return []
    refs: list[str] = []
    for found in _PHOTO_REF.finditer(description):
        prefix = "Foto mujer" if found.group(1) else "Foto"
        refs.extend(f"{prefix} {number}" for number in found.group(2).split("+"))
    return list(dict.fromkeys(refs))


def _cell_text(value: Any) -> str | None:
    """Cells are data. Numbers become text and whole floats lose the spreadsheet's `.0`."""
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = _CONTROL.sub(" ", str(value)).strip()
    return text or None


# --- Reading ---------------------------------------------------------------------------


def _bad_file(message: str) -> ApiError:
    return ApiError(422, "invalid_file", message)


def _map_header(header: Iterable[Any]) -> dict[str, int]:
    """Field -> column index, for allow-listed columns only."""
    positions: dict[str, int] = {}
    for index, title in enumerate(header):
        field_name = COLUMNS.get(normalize(str(title))) if title is not None else None
        if field_name and field_name not in positions:
            positions[field_name] = index
    missing = [c for c in REQUIRED_COLUMNS if COLUMNS[c] not in positions]
    if missing:
        raise ApiError(
            422, "invalid_template", f"Faltan columnas obligatorias: {', '.join(missing)}"
        )
    return positions


def _read_rows(rows: Iterator[tuple]) -> Iterator[dict[str, Any]]:
    """The allow-list. Whole rows go out of scope here; only selected cells are yielded."""
    try:
        header = next(rows)
    except StopIteration:
        raise _bad_file("El archivo está vacío") from None
    positions = _map_header(header)

    def cell(raw: tuple, name: str) -> Any:
        index = positions.get(name)
        return raw[index] if index is not None and index < len(raw) else None

    yielded = 0
    for number, raw in enumerate(rows, start=2):
        values = {name: _cell_text(cell(raw, name)) for name in _TEXT_FIELDS}
        # A formula's text is dropped right here, so not even the staged preview holds it.
        formula = [name for name, value in values.items() if value and value.startswith("=")]
        for name in formula:
            values[name] = None
        description = cell(raw, "description")
        refs = extract_photo_refs(description if isinstance(description, str) else None)
        if not any(values.values()) and not formula:
            continue  # Spreadsheets often carry formatted empty rows; they count for nothing.
        yielded += 1
        if yielded > MAX_ROWS:
            raise ApiError(422, "too_many_rows", f"El archivo supera las {MAX_ROWS} filas")
        yield {"row": number, **values, "refs": refs, "formula": bool(formula)}


def _check_zip(data: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
    except zipfile.BadZipFile as error:
        raise _bad_file("El archivo .xlsx no es válido") from error
    bomb = _bad_file("El archivo .xlsx excede los límites de descompresión")
    if len(entries) > MAX_ZIP_ENTRIES:
        raise bomb
    if sum(entry.file_size for entry in entries) > MAX_UNCOMPRESSED_BYTES:
        raise bomb
    for entry in entries:
        if entry.file_size > RATIO_APPLIES_ABOVE and (
            entry.file_size / max(entry.compress_size, 1) > MAX_RATIO
        ):
            raise bomb


def _parse_xlsx(data: bytes) -> list[dict[str, Any]]:
    _check_zip(data)
    try:
        # read_only streams rows. data_only=False keeps a formula as its literal text: openpyxl
        # never evaluates it, and a cached result (possibly a price) is never picked up.
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=False, keep_links=False)
    except Exception as error:  # openpyxl raises many types on malformed archives.
        raise _bad_file("El archivo .xlsx no es válido") from error
    try:
        names = {name.casefold(): name for name in workbook.sheetnames}
        sheet = workbook[names.get(PREFERRED_SHEET, workbook.sheetnames[0])]
        return list(_read_rows(sheet.iter_rows(values_only=True)))
    except ApiError:
        raise
    except Exception as error:
        raise _bad_file("No se pudo leer el archivo .xlsx") from error
    finally:
        workbook.close()


def _parse_csv(data: bytes) -> list[dict[str, Any]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("cp1252", errors="replace")
    first_line = text.split("\n", 1)[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    try:
        return list(_read_rows(tuple(row) for row in reader))
    except csv.Error as error:
        raise _bad_file("No se pudo leer el archivo .csv") from error


def parse_file(filename: str | None, data: bytes) -> list[dict[str, Any]]:
    if len(data) > MAX_FILE_BYTES:
        raise ApiError(413, "file_too_large", "El archivo supera los 20 MB")
    name = (filename or "").casefold()
    is_zip = data[:4] == b"PK\x03\x04"
    if name.endswith(".xlsx"):
        if not is_zip:
            raise _bad_file("El archivo no es un .xlsx válido")
        return _parse_xlsx(data)
    if name.endswith(".csv"):
        if is_zip or b"\x00" in data[:4096]:
            raise _bad_file("El archivo no es un .csv válido")
        return _parse_csv(data)
    raise _bad_file("Solo se aceptan archivos .xlsx o .csv")


# --- Planning: shared by preview and commit, always against the current database -------


@dataclass
class Group:
    base_sku: str
    brand: Brand
    name: str
    department: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)
    existing_id: uuid.UUID | None = None


@dataclass
class Plan:
    row_count: int
    groups: list[Group]
    errors: list[dict[str, Any]]
    categories: dict[str, Category]
    new_categories: list[str]

    @property
    def variant_count(self) -> int:
        return sum(len(group.rows) for group in self.groups)


def base_sku(sku: str, size: str | None) -> str:
    """Removes a final `-{Talla}`, ignoring case and stray spaces. Any other ending is kept."""
    if not size:
        return sku
    found = re.fullmatch(rf"(.*\S)\s*-\s*{re.escape(size)}", sku, flags=re.IGNORECASE)
    return found.group(1) if found else sku


def _brand_index(db: Session) -> tuple[dict[str, set[uuid.UUID]], dict[uuid.UUID, Brand]]:
    brands = {brand.id: brand for brand in db.scalars(select(Brand))}
    index: dict[str, set[uuid.UUID]] = {}
    for brand in brands.values():
        index.setdefault(normalize(brand.name), set()).add(brand.id)
    for alias, brand_id in db.execute(select(BrandAlias.alias, BrandAlias.brand_id)):
        index.setdefault(normalize(alias), set()).add(brand_id)
    return index, brands


def _row_problem(row: dict[str, Any]) -> str | None:
    if row["formula"]:
        return _FORMULA_ERROR
    if not row["sku"]:
        return "SKU vacío"
    if not row["name"]:
        return "Nombre vacío"
    if not row["department"]:
        return "Departamento vacío"
    limits = (
        ("sku", MAX_SKU, "SKU"),
        ("name", MAX_NAME, "Nombre"),
        ("department", MAX_CATEGORY, "Departamento"),
        ("brand", MAX_BRAND, "Marca"),
        ("color", MAX_COLOR, "Color"),
        ("size", MAX_SIZE, "Talla"),
    )
    for name, limit, label in limits:
        if row[name] and len(row[name]) > limit:
            return f"{label} demasiado largo"
    return None


def build_plan(db: Session, rows: list[dict[str, Any]]) -> Plan:
    brand_index, brands = _brand_index(db)
    no_brand = next(
        (
            brand
            for brand in brands.values()
            if brand.kind == KIND_CLASSIFICATION and normalize(brand.name) == NO_BRAND
        ),
        None,
    )
    categories = {normalize(item.name): item for item in db.scalars(select(Category))}
    variant_owner = dict(db.execute(select(ProductVariant.sku, ProductVariant.product_id)).all())
    product_by_sku = dict(db.execute(select(Product.sku, Product.id)).all())

    errors: list[dict[str, Any]] = []
    groups: dict[str, Group] = {}
    seen_skus: set[str] = set()
    new_categories: dict[str, str] = {}

    def fail(row: dict[str, Any], message: str) -> None:
        errors.append({"row": row["row"], "sku": row["sku"], "message": message})

    for row in rows:
        problem = _row_problem(row)
        if problem:
            fail(row, problem)
            continue
        if row["sku"] in seen_skus:
            fail(row, "SKU repetido en el archivo")
            continue
        seen_skus.add(row["sku"])

        label = normalize(row["brand"] or "")
        if not row["brand"] or label == NO_BRAND:
            brand = no_brand
            if brand is None:
                fail(row, "No existe la clasificación Sin marca")
                continue
        else:
            owners = brand_index.get(label, set())
            if len(owners) != 1:
                reason = "Marca ambigua" if owners else "Marca desconocida"
                fail(row, f"{reason}: {row['brand']}")
                continue
            brand = brands[next(iter(owners))]

        base = base_sku(row["sku"], row["size"])
        group = groups.get(base)
        if group is not None and group.brand.id != brand.id:
            fail(row, "SKU base repetido con otra marca")
            continue
        if group is None:
            group = Group(base, brand, row["name"], row["department"])
            group.existing_id = product_by_sku.get(base)
            groups[base] = group
            key = normalize(row["department"])
            if key not in categories:
                new_categories.setdefault(key, row["department"])

        owner = variant_owner.get(row["sku"])
        if owner is not None and owner != group.existing_id:
            fail(row, "El SKU ya es variante de otra pieza")
            continue
        group.rows.append(row)
        for ref in row["refs"]:
            if ref not in group.refs:
                group.refs.append(ref)

    live_groups = [group for group in groups.values() if group.rows]
    used = {normalize(group.department) for group in live_groups}
    return Plan(
        row_count=len(rows),
        groups=live_groups,
        errors=errors,
        categories=categories,
        new_categories=[name for key, name in new_categories.items() if key in used],
    )


# --- Preview ---------------------------------------------------------------------------


def purge_expired(db: Session) -> None:
    """Runs on every import call: there is no background worker to do it on a schedule."""
    expired = db.scalars(
        select(ImportRun).where(ImportRun.status == IMPORT_PREVIEW, ImportRun.expires_at <= utcnow())
    )
    for run in expired:
        run.status = IMPORT_EXPIRED
        run.payload = None


def _preview_out(run: ImportRun, plan: Plan) -> schemas.ImportPreview:
    conflicts = sum(1 for group in plan.groups if group.existing_id is not None)
    return schemas.ImportPreview(
        preview_id=run.id,
        rows=plan.row_count,
        products=len(plan.groups),
        variants=plan.variant_count,
        new_products=len(plan.groups) - conflicts,
        conflicts=conflicts,
        new_categories=plan.new_categories,
        errors=[schemas.ImportRowError(**error) for error in plan.errors],
        sample=[
            schemas.ImportSample(
                sku=group.base_sku,
                name=group.name,
                brand=group.brand.name,
                category=group.department,
                variants=len(group.rows),
            )
            for group in plan.groups[:SAMPLE_SIZE]
        ],
    )


def create_preview(
    db: Session, filename: str | None, data: bytes, user: AdminUser
) -> schemas.ImportPreview:
    """Touches no catalog table. The only row written is the staging entry in import_runs."""
    rows = parse_file(filename, data)
    plan = build_plan(db, rows)
    purge_expired(db)
    run = ImportRun(
        status=IMPORT_PREVIEW,
        filename=sanitize_filename(filename),
        created_by_id=user.id,
        expires_at=utcnow() + PREVIEW_TTL,
        payload={"rows": rows},
    )
    db.add(run)
    db.commit()
    return _preview_out(run, plan)


# --- Commit ----------------------------------------------------------------------------


def _ensure_categories(db: Session, plan: Plan) -> None:
    if not plan.new_categories:
        return
    taken = set(db.scalars(select(Category.slug)))
    order = db.scalar(select(func.max(Category.display_order))) or 0
    for name in plan.new_categories:
        order += 1
        category = Category(
            name=name,
            slug=unique_slug(name, taken, fallback="categoria"),
            parent_id=None,
            display_order=order,
        )
        db.add(category)
        plan.categories[normalize(name)] = category
    db.flush()


def _group_slug_text(group: Group) -> str:
    if group.brand.kind == KIND_CLASSIFICATION:
        return group.name
    return f"{group.brand.name} {group.name}"


def _update_existing(product: Product, group: Group, category: Category) -> bool:
    """Name, brand, category and variants. Status, photos and editorial fields stay untouched."""
    changed = False
    for attribute, value in (
        ("name", group.name),
        ("brand_id", group.brand.id),
        ("category_id", category.id),
    ):
        if getattr(product, attribute) != value:
            setattr(product, attribute, value)
            changed = True
    if group.refs and product.photo_refs != group.refs:
        product.photo_refs = group.refs
        changed = True
    variants = {variant.sku: variant for variant in product.variants}
    for row in group.rows:
        variant = variants.get(row["sku"])
        if variant is None:
            product.variants.append(
                ProductVariant(sku=row["sku"], color=row["color"], size=row["size"])
            )
            changed = True
        elif (variant.color, variant.size) != (row["color"], row["size"]):
            variant.color, variant.size = row["color"], row["size"]
            changed = True
    return changed


def commit_import(
    db: Session, preview_id: uuid.UUID, update_existing: bool, user: AdminUser
) -> schemas.ImportResult:
    purge_expired(db)
    db.flush()
    run = db.get(ImportRun, preview_id)
    if run is None:
        raise ApiError(404, "not_found", "Vista previa no encontrada")
    if run.status == IMPORT_EXPIRED:
        db.commit()
        raise ApiError(410, "preview_expired", "La vista previa expiró; vuelve a subir el archivo")
    if run.status != IMPORT_PREVIEW:
        raise ApiError(409, "preview_already_used", "Esta vista previa ya se importó")

    plan = build_plan(db, run.payload["rows"])
    _ensure_categories(db, plan)
    existing = {
        product.id: product
        for product in db.scalars(
            select(Product)
            .options(selectinload(Product.variants))
            .where(Product.id.in_([g.existing_id for g in plan.groups if g.existing_id]))
        )
    }
    taken_slugs = set(db.scalars(select(Product.slug)))
    results = [
        {"row": error["row"], "sku": error["sku"], "result": "error", "message": error["message"]}
        for error in plan.errors
    ]
    created = updated = skipped = 0

    def report(group: Group, result: str, message: str = "") -> None:
        results.extend(
            {"row": row["row"], "sku": row["sku"], "result": result, "message": message}
            for row in group.rows
        )

    for group in plan.groups:
        category = plan.categories[normalize(group.department)]
        if group.existing_id is not None:
            if not update_existing:
                skipped += 1
                report(group, "skipped", "SKU existente")
            elif _update_existing(existing[group.existing_id], group, category):
                updated += 1
                report(group, "updated")
            else:
                skipped += 1
                report(group, "unchanged", "Sin cambios")
            continue
        db.add(
            Product(
                sku=group.base_sku,
                slug=unique_slug(_group_slug_text(group), taken_slugs, fallback="pieza"),
                name=group.name,
                brand_id=group.brand.id,
                category_id=category.id,
                status=STATUS_DRAFT,
                is_demo=False,
                photo_refs=group.refs,
                variants=[
                    ProductVariant(sku=row["sku"], color=row["color"], size=row["size"])
                    for row in group.rows
                ],
            )
        )
        created += 1
        report(group, "created")

    results.sort(key=lambda item: item["row"])
    summary = {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "errors": len(plan.errors),
    }
    run.status = IMPORT_COMPLETED
    run.payload = None
    run.update_existing = update_existing
    run.completed_at = utcnow()
    run.summary = summary
    run.results = results
    audit.record(
        db,
        user,
        "import",
        "import_run",
        run.id,
        {key: [None, value] for key, value in summary.items()}
        | {"new_categories": [None, plan.new_categories]},
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ApiError(409, "import_conflict", "El catálogo cambió durante la importación") from error
    return schemas.ImportResult(import_id=run.id, **summary)


# --- CSV output ------------------------------------------------------------------------


def _csv_safe(value: Any) -> str:
    """Spreadsheets run cells that start with these as formulas when the CSV is opened."""
    text = "" if value is None else str(value)
    return f"'{text}" if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _to_csv(rows: Iterable[Iterable[Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows([_csv_safe(cell) for cell in row] for row in rows)
    return "﻿" + output.getvalue()  # BOM: Excel otherwise misreads accents.


def template_csv() -> str:
    return _to_csv([TEMPLATE_HEADER])


def report_csv(db: Session, import_id: uuid.UUID) -> str:
    run = db.get(ImportRun, import_id)
    if run is None:
        raise ApiError(404, "not_found", "Importación no encontrada")
    if run.status != IMPORT_COMPLETED:
        raise ApiError(409, "import_not_completed", "Esta importación no se ha ejecutado")
    rows = [("fila", "sku", "resultado", "mensaje")]
    rows.extend(
        (item["row"], item["sku"], item["result"], item["message"]) for item in run.results or []
    )
    return _to_csv(rows)
