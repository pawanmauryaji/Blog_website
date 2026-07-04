from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.orm import Session
from database import engine
import models
from routers import router

import os
from dotenv import load_dotenv
load_dotenv()
DEBUG=False
app = FastAPI(
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
)

app = FastAPI()

from database import engine
from models import Base

Base.metadata.create_all(bind=engine)


#app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def flash_message_middleware(request: Request, call_next):
    success_msg = request.cookies.get("flash_success")
    error_msg = request.cookies.get("flash_error")
    
    request.state.success_msg = success_msg
    request.state.error_msg = error_msg

    response = await call_next(request)
    
    if "text/html" in response.headers.get("content-type", ""):
        if success_msg: 
            response.delete_cookie(key="flash_success", path="/")
        if error_msg: 
            response.delete_cookie(key="flash_error", path="/")
        
    return response


app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECREAT_KEY"))


app.include_router(router)


#################################################
# 🔒 ADMIN SECURE CONFIGURATION SYSTEM 
#################################################

class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username_input = form.get("username")
        password_input = form.get("password")

        # Database session local context manager open karein
        db: Session = Session(bind=engine)
        try:
            # Check karein ki kya ye admin username database mein hai
            admin_user = db.query(models.AdminUser).filter(models.AdminUser.username == username_input).first()
            
            # 🛑 NOTE: Plain password verification hai, production me password hashing check lagayein!
            if admin_user and admin_user.password == password_input:
                request.session.update({"token": "admin_logged_in_token", "admin_id": admin_user.id})
                return True
        finally:
            db.close()  # Connection leak rokne ke liye session hamesha close karein

        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if token == "admin_logged_in_token":
            return True
        return False

# Admin security backend initialization string target
authentication_backend = AdminAuth(secret_key=os.getenv("SECREAT_KEY"))

# Admin Engine Instance Object Binding
admin = Admin(
    app=app,  
    engine=engine, 
    title="Blog Project Admin Panel",
    authentication_backend=authentication_backend,
    base_url = "/secureblogadmin"
)

# 5. SQLAdmin Panel Data Model Configuration Views Setup
class UserAdmin(ModelView, model=models.User):
    column_list = [models.User.id, models.User.email, models.User.is_verified]
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

class BlogAdmin(ModelView, model=models.Blog):
    column_list = [models.Blog.id, models.Blog.title]
    can_create = True
    can_edit = True
    can_delete = True

class ContactAdmin(ModelView, model=models.Contact):
    column_list = [models.Contact.id, models.Contact.name, models.Contact.email,  models.Contact.message]
    can_create = True
    can_edit = True
    can_delete = True


class AdminUserAdmin(ModelView, model=models.AdminUser):
    column_list = [models.AdminUser.id, models.AdminUser.username]
    can_create = True
    can_edit = True
    can_delete = True


admin.add_view(AdminUserAdmin)


admin.add_view(UserAdmin)
admin.add_view(BlogAdmin)
admin.add_view(ContactAdmin)
