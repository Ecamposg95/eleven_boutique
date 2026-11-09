"""initial schema

Revision ID: 0001
Revises: 
"""

import sqlalchemy as sa
from alembic import op


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('brands',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('original_name', sa.String(length=200), nullable=False),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('kind', sa.String(length=16), server_default='brand', nullable=False),
    sa.Column('logo_url', sa.String(length=500), nullable=True),
    sa.Column('editorial_image_url', sa.String(length=500), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
    sa.Column('is_featured', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default='draft', nullable=False),
    sa.Column('validation_status', sa.String(length=16), server_default='pending', nullable=False),
    sa.Column('search_text', sa.String(length=500), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("kind IN ('brand', 'classification')", name=op.f('ck_brands_kind')),
    sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name=op.f('ck_brands_status')),
    sa.CheckConstraint("validation_status IN ('pending', 'approved')", name=op.f('ck_brands_validation_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_brands')),
    sa.UniqueConstraint('slug', name=op.f('uq_brands_slug'))
    )
    with op.batch_alter_table('brands', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_brands_search_text'), ['search_text'], unique=False)
        batch_op.create_index(batch_op.f('ix_brands_status'), ['status'], unique=False)

    op.create_table('categories',
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=True),
    sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
    sa.Column('search_text', sa.String(length=500), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], name=op.f('fk_categories_parent_id_categories'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
    sa.UniqueConstraint('slug', name=op.f('uq_categories_slug'))
    )
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_categories_parent_id'), ['parent_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_categories_search_text'), ['search_text'], unique=False)

    op.create_table('collections',
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('cover_url', sa.String(length=500), nullable=True),
    sa.Column('status', sa.String(length=16), server_default='draft', nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name=op.f('ck_collections_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_collections')),
    sa.UniqueConstraint('slug', name=op.f('uq_collections_slug'))
    )
    with op.batch_alter_table('collections', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_collections_is_demo'), ['is_demo'], unique=False)
        batch_op.create_index(batch_op.f('ix_collections_status'), ['status'], unique=False)

    op.create_table('lookbooks',
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('title', sa.String(length=300), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('cover_url', sa.String(length=500), nullable=True),
    sa.Column('status', sa.String(length=16), server_default='draft', nullable=False),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name=op.f('ck_lookbooks_status')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lookbooks')),
    sa.UniqueConstraint('slug', name=op.f('uq_lookbooks_slug'))
    )
    with op.batch_alter_table('lookbooks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_lookbooks_is_demo'), ['is_demo'], unique=False)
        batch_op.create_index(batch_op.f('ix_lookbooks_status'), ['status'], unique=False)

    op.create_table('site_settings',
    sa.Column('is_demo', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('site_name', sa.String(length=200), nullable=True),
    sa.Column('whatsapp_number', sa.String(length=40), nullable=True),
    sa.Column('hero_image_url', sa.String(length=500), nullable=True),
    sa.Column('hero_headline', sa.Text(), nullable=True),
    sa.Column('hero_subhead', sa.Text(), nullable=True),
    sa.Column('intro', sa.Text(), nullable=True),
    sa.Column('boutique_body', sa.Text(), nullable=True),
    sa.Column('contact_body', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_site_settings')),
    sa.UniqueConstraint('is_demo', name=op.f('uq_site_settings_is_demo'))
    )
    op.create_table('brand_aliases',
    sa.Column('brand_id', sa.Uuid(), nullable=False),
    sa.Column('alias', sa.String(length=200), nullable=False),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('search_text', sa.String(length=500), nullable=False),
    sa.Column('source_position', sa.Integer(), nullable=True),
    sa.Column('is_original', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], name=op.f('fk_brand_aliases_brand_id_brands'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_brand_aliases')),
    sa.UniqueConstraint('slug', name=op.f('uq_brand_aliases_slug')),
    sa.UniqueConstraint('source_position', name=op.f('uq_brand_aliases_source_position'))
    )
    with op.batch_alter_table('brand_aliases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_brand_aliases_brand_id'), ['brand_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_brand_aliases_search_text'), ['search_text'], unique=False)

    op.create_table('lookbook_blocks',
    sa.Column('lookbook_id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('position', sa.Integer(), server_default='0', nullable=False),
    sa.Column('content', sa.JSON(), nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("type IN ('text', 'image')", name=op.f('ck_lookbook_blocks_type')),
    sa.ForeignKeyConstraint(['lookbook_id'], ['lookbooks.id'], name=op.f('fk_lookbook_blocks_lookbook_id_lookbooks'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lookbook_blocks'))
    )
    with op.batch_alter_table('lookbook_blocks', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_lookbook_blocks_lookbook_id'), ['lookbook_id'], unique=False)

    op.create_table('products',
    sa.Column('sku', sa.String(length=100), nullable=False),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('name', sa.String(length=300), nullable=False),
    sa.Column('brand_id', sa.Uuid(), nullable=False),
    sa.Column('category_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=16), server_default='draft', nullable=False),
    sa.Column('is_featured', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default='0', nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('commercial_added_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_demo', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('search_text', sa.String(length=800), nullable=False),
    sa.Column('admin_description', sa.Text(), nullable=True),
    sa.Column('internal_notes', sa.Text(), nullable=True),
    sa.Column('external_inventory_id', sa.String(length=200), nullable=True),
    sa.Column('supplier_ref', sa.String(length=200), nullable=True),
    sa.Column('seo_title', sa.String(length=300), nullable=True),
    sa.Column('seo_description', sa.Text(), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'published', 'archived')", name=op.f('ck_products_status')),
    sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], name=op.f('fk_products_brand_id_brands'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_products_category_id_categories'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_products')),
    sa.UniqueConstraint('sku', name=op.f('uq_products_sku')),
    sa.UniqueConstraint('slug', name=op.f('uq_products_slug'))
    )
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_products_brand_id'), ['brand_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_products_category_id'), ['category_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_products_commercial_added_at'), ['commercial_added_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_products_is_demo'), ['is_demo'], unique=False)
        batch_op.create_index(batch_op.f('ix_products_search_text'), ['search_text'], unique=False)
        batch_op.create_index(batch_op.f('ix_products_status'), ['status'], unique=False)

    op.create_table('catalog_events',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('type', sa.String(length=64), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=True),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_catalog_events_product_id_products'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_catalog_events'))
    )
    with op.batch_alter_table('catalog_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_catalog_events_product_id'), ['product_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_catalog_events_type'), ['type'], unique=False)

    op.create_table('collection_products',
    sa.Column('collection_id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], name=op.f('fk_collection_products_collection_id_collections'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_collection_products_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('collection_id', 'product_id', name=op.f('pk_collection_products'))
    )
    op.create_table('lookbook_products',
    sa.Column('lookbook_id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('position', sa.Integer(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['lookbook_id'], ['lookbooks.id'], name=op.f('fk_lookbook_products_lookbook_id_lookbooks'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_lookbook_products_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('lookbook_id', 'product_id', name=op.f('pk_lookbook_products'))
    )
    op.create_table('product_media',
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('alt', sa.String(length=500), nullable=False),
    sa.Column('is_primary', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('position', sa.Integer(), server_default='0', nullable=False),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_media_product_id_products'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_media')),
    sa.UniqueConstraint('product_id', 'position', name=op.f('uq_product_media_product_id'))
    )
    with op.batch_alter_table('product_media', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_product_media_product_id'), ['product_id'], unique=False)



def downgrade() -> None:
    with op.batch_alter_table('product_media', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_product_media_product_id'))

    op.drop_table('product_media')
    op.drop_table('lookbook_products')
    op.drop_table('collection_products')
    with op.batch_alter_table('catalog_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_catalog_events_type'))
        batch_op.drop_index(batch_op.f('ix_catalog_events_product_id'))

    op.drop_table('catalog_events')
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_products_status'))
        batch_op.drop_index(batch_op.f('ix_products_search_text'))
        batch_op.drop_index(batch_op.f('ix_products_is_demo'))
        batch_op.drop_index(batch_op.f('ix_products_commercial_added_at'))
        batch_op.drop_index(batch_op.f('ix_products_category_id'))
        batch_op.drop_index(batch_op.f('ix_products_brand_id'))

    op.drop_table('products')
    with op.batch_alter_table('lookbook_blocks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_lookbook_blocks_lookbook_id'))

    op.drop_table('lookbook_blocks')
    with op.batch_alter_table('brand_aliases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_brand_aliases_search_text'))
        batch_op.drop_index(batch_op.f('ix_brand_aliases_brand_id'))

    op.drop_table('brand_aliases')
    op.drop_table('site_settings')
    with op.batch_alter_table('lookbooks', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_lookbooks_status'))
        batch_op.drop_index(batch_op.f('ix_lookbooks_is_demo'))

    op.drop_table('lookbooks')
    with op.batch_alter_table('collections', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_collections_status'))
        batch_op.drop_index(batch_op.f('ix_collections_is_demo'))

    op.drop_table('collections')
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_categories_search_text'))
        batch_op.drop_index(batch_op.f('ix_categories_parent_id'))

    op.drop_table('categories')
    with op.batch_alter_table('brands', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_brands_status'))
        batch_op.drop_index(batch_op.f('ix_brands_search_text'))

    op.drop_table('brands')
