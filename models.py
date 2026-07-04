from sqlalchemy import Column, Integer, String,ForeignKey, Text,Boolean, DateTime
from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from database import Base

#Blog Table
class Blog(Base):
    __tablename__ = "blogs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    tag = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    author = relationship("User", back_populates="blogs")

    def __str__(self):
        return self.title
    

# user table
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)

    #profile details
    name = Column(String, nullable=False)
    bio = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    blogs = relationship("Blog", back_populates="author",  cascade="all, delete-orphan")

    is_verified = Column(Boolean, default=False)

    def __str__(self):
        return self.email
        

#Contact Us Table

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, index=True, nullable=False)
    subject = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    def __str__(self):
        return f"{self.name} - {self.subject}"



class OTPStorage(Base):
    __tablename__ = "otp_storage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    otp_code = Column(String(6))
    created_at = Column(DateTime, default=datetime.now(timezone.utc)) 


from sqlalchemy import Column, Integer, String

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # Isme hashed password save hoga

    def __str__(self):
        return self.username
