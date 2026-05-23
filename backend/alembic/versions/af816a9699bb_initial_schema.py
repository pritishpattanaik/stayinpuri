"""initial schema

Revision ID: af816a9699bb
Revises:
Create Date: 2026-05-24 00:00:33.941406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af816a9699bb'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Create properties table
    op.create_table(
        'properties',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('bedrooms', sa.Integer(), nullable=True),
        sa.Column('price_per_night', sa.Float(), nullable=True),
        sa.Column('amenities', sa.String(length=255), nullable=True),
        sa.Column('image_url', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # Create services table
    op.create_table(
        'services',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('price_unit', sa.String(length=50), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('image_url', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # Create bookings table
    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('booking_ref', sa.String(length=20), nullable=False),
        sa.Column('service_type', sa.String(length=50), nullable=False),
        sa.Column('property_slug', sa.String(length=50), nullable=True),
        sa.Column('guest_name', sa.String(length=100), nullable=False),
        sa.Column('guest_email', sa.String(length=100), nullable=True),
        sa.Column('guest_phone', sa.String(length=20), nullable=False),
        sa.Column('num_guests', sa.Integer(), nullable=True),
        sa.Column('checkin_date', sa.Date(), nullable=True),
        sa.Column('checkout_date', sa.Date(), nullable=True),
        sa.Column('special_requests', sa.Text(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_ref')
    )

    # Create ical_bookings table
    op.create_table(
        'ical_bookings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uid', sa.String(length=255), nullable=False),
        sa.Column('property_name', sa.String(length=100), nullable=False),
        sa.Column('platform', sa.String(length=50), nullable=False),
        sa.Column('summary', sa.String(length=255), nullable=True),
        sa.Column('dtstart', sa.String(length=20), nullable=False),
        sa.Column('dtend', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('hash', sa.String(length=64), nullable=True),
        sa.Column('first_seen', sa.String(length=50), nullable=True),
        sa.Column('last_seen', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uid')
    )


def downgrade() -> None:
    op.drop_table('ical_bookings')
    op.drop_table('bookings')
    op.drop_table('services')
    op.drop_table('properties')
