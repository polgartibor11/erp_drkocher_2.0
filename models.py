from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from config import DB_PATHS

Base = declarative_base()
engine = create_engine(f"sqlite:///{DB_PATHS['order']}", echo=False)
SessionLocal = sessionmaker(bind=engine)

class Product(Base):
    __tablename__ = 'products'
    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String,  nullable=False, index=True)
    qty  = Column(Integer, default=0)
    orders = relationship('Order', back_populates='product', cascade='all, delete')

class Order(Base):
    __tablename__ = 'orders'
    id         = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'))
    amount     = Column(Integer, nullable=False)
    product    = relationship('Product', back_populates='orders')
