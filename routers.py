from fastapi import APIRouter, Depends,HTTPException,status,Query,Response,Request,Form, BackgroundTasks
from sqlalchemy.orm import Session
from database import engine,SessionLocal
import models,schemas
from sqlalchemy import desc 
from auth import create_token, verify_token
from fastapi.security import OAuth2PasswordRequestForm
from otp_config import generate_and_save_otp, send_otp_email
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.templating import Jinja2Templates
import math


# 2. Templates Config
templates = Jinja2Templates(directory="templates")

router = APIRouter()

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# home router
@router.get("/", response_class=HTMLResponse)
def home(request: Request,
         page: int = Query(1, ge=1),      
         limit: int = Query(6, ge=1),     
         search: str = Query(None),      
         db: Session = Depends(get_db)):
    

    query = db.query(models.Blog).order_by(desc(models.Blog.id))
    
   
    search_clean = search.strip() if search else None
    if search_clean:
        query = query.filter(models.Blog.title.ilike(f"%{search_clean}%"))
    
    # 3. Total match entries ka count nikaalein
    total_blogs = query.count()
    
    # 4. Total pages calculate karein (Math ceiling function handles division rounding)
    total_pages = math.ceil(total_blogs / limit) if total_blogs > 0 else 1
    
    # 5. Offset calculation parameters setup karein
    start = (page - 1) * limit
    blogs = query.offset(start).limit(limit).all()

    # 6. HTML template ko data inject karein
    return templates.TemplateResponse(
        request=request,
        name="blog/index.html",
        context={
            "blogs": blogs,
            "current_page": page,
            "total_pages": total_pages,
            "search_query": search_clean  # Input me text barkarar rakhne ke liye
        }
    )

     


#login router
@router.get("/auth/login", response_class=HTMLResponse)
def login_page(request:Request):
    return templates.TemplateResponse(
        request=request,
        name="blog/login.html",    
    )

# login user
@router.post("/auth/login")
def login_user(background_tasks: BackgroundTasks, 
               username: str = Form(...),
               password: str = Form(...),
               db:Session = Depends(get_db),
               ):
    
    username = username.strip().lower()
    password = password.strip()

    user = db.query(models.User).filter(models.User.email == username).first()
    
    if not user or  user.password != password:
        response = RedirectResponse(url="/auth/login", 
            status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Invalid Email or Password",
            httponly=False,
            path="/"
        )
        return response
    
    # check is user no verified 
    if not user.is_verified:
        response = RedirectResponse(url="/auth/verify-otp", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="pending_email_verification", 
            value=user.email,
            httponly=True, 
            max_age=300,
            path="/"
        )
        response.set_cookie(
            key="flash_error",
            value="Please verify your email address to continue.",
            httponly=False,
            path="/"
        )

        otp_code = generate_and_save_otp(user_id=user.id, db=db)

        send_otp_email(
            background_tasks=background_tasks,
            username=user.username,
            email=user.email,
            otp_code=otp_code
        )


        return response

    token_data = {"user":user.email}
    access_token = create_token(data=token_data)
    
    redirect_to_profile = RedirectResponse(
        url="/profile",
        status_code=status.HTTP_303_SEE_OTHER)
    
    redirect_to_profile.set_cookie(
        key="flash_success",
        value="You have Login Successfully",
        httponly=False,
        path="/"
    )

    redirect_to_profile.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False, # Its Change to True when Production it is working only HTTPS
        samesite="lax",
        path='/'
    )

    redirect_to_profile.set_cookie(
        key="token_type",
        value="bearer",
        httponly=True,
        secure=False, # Its Change to True when Production it is working only HTTPS
        samesite="lax",
        path="/"

    )

    return redirect_to_profile

# profile router
@router.get("/profile", response_class=HTMLResponse)
def profile_page(request:Request, db:Session = Depends(get_db)):
    
    try:
        token_data = verify_token(request)
       
        
        user_email = token_data.get("user")
        user = db.query(models.User).filter(models.User.email == user_email).first()

        if not user:
            return RedirectResponse(url="/auth/login/", status_code=status.HTTP_303_SEE_OTHER)
        
        return templates.TemplateResponse(
        request=request,
        name="blog/profile.html",
        context={
            "user":user
        }

    )
  
    except Exception:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    
# Signup router
@router.get('/auth/signup', response_class=HTMLResponse)
def signup_page(request:Request):
    return templates.TemplateResponse(
        request=request,
        name="blog/signup.html",
        
    )

@router.post('/auth/signup')
def singup_user(response:Response,
                background_tasks: BackgroundTasks,
                name:str = Form(...),
                username:str = Form(...),
                email:str = Form(...),
                password:str = Form(...),
                bio:str = Form(...),
                db:Session = Depends(get_db)
                ):
    
    name = name.strip().lower()
    username = username .strip().lower()
    email = email.strip().lower()
    password = password.strip() 
    bio = bio.strip()
    
    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        if existing_user.is_verified:
            response = RedirectResponse(url="/auth/signup", status_code=status.HTTP_303_SEE_OTHER)
            response.set_cookie(
                key="flash_error",
                value="Email Already Exits",
                httponly=False,
                path='/'
            )
            return response
        
        else:
            db.query(models.OTPStorage).filter(models.OTPStorage.user_id == existing_user.id).delete()
            db.delete(existing_user)
            db.commit()
    
    existing_username = db.query(models.User).filter(models.User.username == username).first()
    if existing_username and existing_username.is_verified:
        response = RedirectResponse(url="/auth/signup", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Username Already Taken",
            httponly=False,
            path='/'
        )
        return response
    
    user = models.User(
        name=name,
        username=username,
        email=email,
        password=password,
        bio=bio,
        is_verified = False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    otp_code = generate_and_save_otp(user_id=user.id, db=db)

    send_otp_email(
        background_tasks=background_tasks,
        username=user.username,
        email=user.email,
        otp_code=otp_code
    )

    response = RedirectResponse(url=f"/auth/verify-otp", status_code=status.HTTP_303_SEE_OTHER)
    
    response.set_cookie(
        key="pending_email_verification", 
        value=user.email,
        httponly=False, 
        max_age=300,
        path="/"
    )

    response.set_cookie(
        key="flash_success", 
        value="OTP sent successfully! Please check your email inbox.", 
        httponly=False, 
        path="/"
    )

    return response

# verify_ otp
@router.get('/auth/verify-otp', response_class=HTMLResponse)
def verify_otp_page(request:Request):
    email = request.cookies.get("pending_email_verification")

    if not email:
        response = RedirectResponse(url="/auth/signup", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error", 
            value="Session invalid. Please start registration again.", 
            httponly=False, 
            path="/"
        )
        return response

    return templates.TemplateResponse(
        request=request,
        name="blog/verify_otp.html",  
        context={"email": email}     
    )

@router.post("/auth/verify-otp")
def verify_user_otp(request:Request, db:Session = Depends(get_db), otp:str = Form(...)):

    otp = otp.strip()

    email = request.cookies.get("pending_email_verification")

    if not email or not otp:
        response = RedirectResponse(url="/auth/signup", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error", 
            value="Session invalid. Please start registration again.", 
            httponly=False, 
            path="/"
        )
        return response
    
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        response = RedirectResponse(url="/auth/signup", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="flash_error", value="User profile not found.", httponly=False, path="/")
        return response
    
    otp_storage = db.query(models.OTPStorage).filter(models.OTPStorage.user_id == user.id ).first()

    if not otp_storage:
        response = RedirectResponse(url="/auth/verify-otp", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="flash_error", value="No active OTP found. Please request a new one.", httponly=False, path="/")
        return response

    if otp == otp_storage.otp_code:
        user.is_verified = True        
        db.delete(otp_storage)
        db.commit()
        response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_success", 
            value="You are Registerd Successfully", 
            httponly=False, 
            path="/"
        )
        response.delete_cookie(key="pending_email_verification", path="/")

        return response
    
    else:
        response = RedirectResponse(url="/auth/verify-otp", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error", 
            value="Invalid OTP. Please try again.",  
            httponly=False, 
            path="/"
        )
        return response
    
    

# resend otp
@router.post('/auth/resend-otp')
def resend_otp(request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):

    email = request.cookies.get("pending_email_verification")
    
    if not email:
        response = RedirectResponse(url="/auth/signup", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error", 
            value="Session expired. Please sign up again.", 
            httponly=False, 
            path="/"
        )
        return response

   
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        response = RedirectResponse(url="/auth/signup", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(key="flash_error", value="User profile not found.", httponly=False, path="/")
        return response

   
    db.query(models.OTPStorage).filter(models.OTPStorage.user_id == user.id).delete()
    db.commit()

    # 4. Naya OTP generate aur save karo
    otp_code = generate_and_save_otp(user_id=user.id, db=db)

    # 5. Background task se naya email bhejo
    send_otp_email(
        background_tasks=background_tasks,
        username=user.username,
        email=user.email,
        otp_code=otp_code
    )

    
    response = RedirectResponse(url="/auth/verify-otp", status_code=status.HTTP_303_SEE_OTHER)
    
   
    response.set_cookie(
        key="pending_email_verification", 
        value=user.email,
        httponly=True, 
        max_age=300, # cookie max age  300 second(5 min)
        path="/"
    )
    
    response.set_cookie(
        key="flash_success", 
        value="A new OTP has been sent to your email!", 
        httponly=False, 
        path="/"
    )
    return response


# forgot password
@router.get('/auth/forgot-password', response_class=HTMLResponse)
def forgot_password_page(request:Request):

    return templates.TemplateResponse(
        request=request,
        name="blog/forget_password.html",
        context={}

    )

@router.post('/auth/forgot-password')
def forgot_password_user(
    request:Request, 
    background_tasks: BackgroundTasks,
    email:str = Form(...),
    password:str = Form(...),
    
    db:Session = Depends(get_db)):

    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        response = RedirectResponse(url = "/auth/forgot-password", status_code = status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Invalid Email",
            httponly = False,
            path="/"
        )
        return response
    
    if not user.is_verified:
        response = RedirectResponse(url="/auth/verify-otp", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="pending_email_verification", 
            value=user.email,
            httponly=True, 
            max_age=300,
            path="/"
        )
        response.set_cookie(
            key="flash_error",
            value="Please verify your email address to continue.",
            httponly=False,
            path="/"
        )

        otp_code = generate_and_save_otp(user_id=user.id, db=db)

        send_otp_email(
            background_tasks=background_tasks,
            username=user.username,
            email=user.email,
            otp_code=otp_code
        )
        return response
    

    user.email = email
    user.password = password
    
    otp_code = generate_and_save_otp(user_id=user.id, db=db)

    send_otp_email(
        background_tasks=background_tasks,
        username=user.username,
        email=user.email,
        otp_code=otp_code
    )

    response = RedirectResponse(url = "/auth/verify-otp", status_code = status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key= "flash_success",
        value = "otp send successfully",
        httponly = False,
        path = "/"

    )
    response.set_cookie(
        key="pending_email_verification", 
        value=user.email,
        httponly=True, 
        max_age=300, # cookie max age  300 second(5 min)
        path="/"
    )
    return response
    



# logout route
@router.get('/auth/logout')
def logout():

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="flash_success",
        value="You Have Logout Successfully",
        httponly=False,
        path="/")
    
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="token_type", path="/")

    return response
   
    

# create blog
@router.get("/blog/create", response_class=HTMLResponse)
def create_blog_page(request:Request):

    token_data = verify_token(request)
    
    
    if not token_data:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Please Login First",
            httponly=False,
            path="/"
        )
        return response 

    return templates.TemplateResponse(
        request=request,
        name="blog/create_blog.html"
    )

@router.post("/blog/create")
def create_blog_user(
    request:Request,
    title:str = Form(...),
    content:str = Form(...),
    tag:str = Form(...),
    db:Session = Depends(get_db)):  
        
        title = title.strip()
        content = content.strip()
        tag = tag.strip()
        
        try:
            token_data = verify_token(request)
            user_email = token_data.get("user")

            user = db.query(models.User).filter(models.User.email == user_email).first()
            if not user:
                response = RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
                response.set_cookie(
                    key="flash_error",
                    value="Plase Login First",
                    httponly=False,
                    path="/"
                )
                return response
            new_blog=models.Blog(
                title=title,
                content=content,
                tag=tag,
                user_id = user.id
            )
            db.add(new_blog)
            db.commit()
            db.refresh(new_blog)

            response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
            response.set_cookie(
                key="flash_success",
                value="Your Blog Posted Successfully",
                httponly=False,
                path="/"
            )
            return response
        
        except Exception as e:
            print(f"ye errro hai yaarrr{e}")
            response = RedirectResponse(url="/blog/create", status_code=status.HTTP_303_SEE_OTHER)

        response.set_cookie(key="flash_error", value="Failed to publish blog. Try again.", httponly=False, path="/")
        return response

    

#read blog by id
@router.get("/blog/{id}", response_class=HTMLResponse)
def blog_by_id(request:Request, id:int, db:Session = Depends(get_db)):
    blog = db.query(models.Blog).filter(models.Blog.id == id).first()

    if not blog:
        response = RedirectResponse(url='/', status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Sorry Blog not Found",
            httponly=False,
            path="/"
        )
        return response

    return templates.TemplateResponse(
        request=request,
        name="blog/read_blog.html",
        context={
            "blog":blog
        }

    )

# contact us router 
@router.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="blog/contact_us.html"
    )

@router.post("/contact")
def contact_user(
    name:str = Form(...),
    email:str = Form(...),
    subject:str = Form(...),
    message:str = Form(...),
    db:Session = Depends(get_db)):

        
        contact_message = models.Contact(
            name = name.strip(),
            email = email.lower().strip(),
            subject = subject.strip(),
            message = message.strip()
        )
        db.add(contact_message)
        db.commit()
        db.refresh(contact_message)

        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

        response.set_cookie(
            key="flash_success",
            value="Thank You for Contact Us! Message Sent Successfully.",
            httponly=False,
            path="/"
        )
        return response
    

# blogs by a user
@router.get('/blogs',  response_class=HTMLResponse)
def blogs(request:Request, db:Session = Depends(get_db)):

    token_data = verify_token(request)
    
    
    if not token_data:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Please Login First",
            httponly=False,
            path="/"
        )
        return response
    
    user_email = token_data.get("user")

    user = db.query(models.User).filter(models.User.email == user_email).first()

    if not user :
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    
    user_id = user.id

    blogs_list = db.query(models.Blog).filter(models.Blog.user_id == user_id).all()

    return templates.TemplateResponse(
        request=request,
        name="blog/blogs.html",
        context={
            "blogs":blogs_list
        }
    )

# delete Blog
@router.post("/blog/delete/{id}")
def delete(id:int, request:Request, db:Session = Depends(get_db)):

    token_data = verify_token(request)
    
    if not token_data:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Please Login First",
            httponly=False,
            path="/"
        )
        return response
    
    user_email = token_data.get("user")

    user = db.query(models.User).filter(models.User.email == user_email).first()

    if not user :
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    existing_blog = db.query(models.Blog).filter(models.Blog.id == id, models.Blog.user_id == user.id ).first()

    if not existing_blog:
        response = RedirectResponse(url="/blogs", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Sorry Blog not Found",
            httponly=False,
            path="/"
        )
        return response
    
    db.delete(existing_blog)
    db.commit()

    response  = RedirectResponse(url="/blogs", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="flash_success",
        value="Blog Deleted Successfully",
        httponly=False,
        path="/"
    )

    return response



# edit blog router
@router.get('/blog/edit/{id}', response_class=HTMLResponse)
def edit_blog(id:int, request:Request, db:Session = Depends(get_db)):

    token_data = verify_token(request)
    
    if not token_data:
        response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Please Login First",
            httponly=False,
            path="/"
        )
        return response
    
    user_email = token_data.get("user")

    user = db.query(models.User).filter(models.User.email == user_email).first()

    if not user :
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    blog = db.query(models.Blog).filter(models.Blog.id == id,models.Blog.user_id == user.id ).first()

    if not blog:
        response = RedirectResponse(url="/blogs", status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            key="flash_error",
            value="Sorry Blog not Found",
            httponly="False",
            path="/"
        )

    return templates.TemplateResponse(
        request=request,
        name="blog/edit_blog.html",
        context={
            "blog":blog
        }

    )

@router.post("/blog/edit/{id}")
def edit_user_blog(
    id:int,
    request:Request,
    title:str = Form(...),
    content:str = Form(...),
    tag:str = Form(...),
    db:Session =  Depends(get_db)):
        
        title = title.strip()
        content = content.strip()
        tag = tag.strip()

        token_data = verify_token(request)
        
        if not token_data:
            response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
            response.set_cookie(
                key="flash_error",
                value="Please Login First",
                httponly=False,
                path="/"
            )
            return response
        
        user_email = token_data.get("user")

        user = db.query(models.User).filter(models.User.email == user_email).first()

        if not user :
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        
        edit_blog = db.query(models.Blog).filter(models.Blog.id == id, models.Blog.user_id == user.id ).first()

        if not edit_blog:
            return RedirectResponse(url='/blogs', status_code=status.HTTP_303_SEE_OTHER)

        edit_blog.title=title
        edit_blog.content=content
        edit_blog.tag=tag

        db.commit()

        response = RedirectResponse(url = "/blogs", status_code=status.HTTP_303_SEE_OTHER)    
        response.set_cookie(
            key="flash_success",
            value="Blog Updated Successfully",
            httponly=False,
            path="/"        
        )
        return response


    



























# privacy router
@router.get("/privacy", response_class=HTMLResponse)
def privacy_page(request:Request):

    return templates.TemplateResponse(
        request=request,
        name="blog/privacy.html",
    )

# terms router
@router.get("/terms", response_class=HTMLResponse)
def terms_page(request:Request):

    return templates.TemplateResponse(
        request=request,
        name="blog/terms.html",
    )


