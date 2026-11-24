from contextlib import asynccontextmanager
from math import ceil

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from .core.config import CORS_ORIGINS, ENVIRONMENT
from .database import Base, SessionLocal, engine, get_db
from .models import Category, Comment, Ticket, TicketHistory, User
from .schemas import (
    CategoryCreate,
    CategoryOut,
    CommentCreate,
    CommentOut,
    DashboardSummary,
    HistoryOut,
    LoginInput,
    TicketAssign,
    TicketCreate,
    TicketOut,
    TicketPage,
    TicketUpdate,
    TokenOut,
    UserActiveUpdate,
    UserCreate,
    UserOut,
)
from .security import (
    burn_password_check,
    create_access_token,
    get_current_user,
    hash_password,
    login_limiter,
    require_roles,
    verify_password,
)

DEFAULT_CATEGORIES = (
    ("Hardware", "Computadores, periféricos e equipamentos."),
    ("Software", "Programas, aplicativos e sistemas."),
    ("Rede e internet", "Conectividade, Wi-Fi e acesso à rede."),
    ("Acesso e contas", "Senhas, permissões e contas de usuário."),
    ("E-mail", "Problemas com e-mail e comunicação."),
    ("Outros", "Solicitações que não se encaixam nas demais categorias."),
)


def ensure_default_categories(db: Session) -> None:
    """Cria categorias iniciais sem duplicar as que já existem."""
    existing = {name.casefold() for (name,) in db.query(Category.name).all()}
    for name, description in DEFAULT_CATEGORIES:
        if name.casefold() not in existing:
            db.add(Category(name=name, description=description))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all é conveniência apenas no desenvolvimento local.
    if ENVIRONMENT == "development":
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            ensure_default_categories(db)
    yield


app = FastAPI(
    title="HelpDesk API",
    version="1.3.0",
    description="API para gerenciamento de chamados de suporte.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def log_change(
    db: Session,
    ticket: Ticket,
    actor: User,
    field: str,
    old_value: object | None,
    new_value: object | None,
) -> None:
    db.add(
        TicketHistory(
            ticket_id=ticket.id,
            changed_by=actor.id,
            field=field,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
        )
    )


def escape_like(term: str) -> str:
    """Escapa curingas do LIKE para que a busca trate % e _ como texto comum."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def can_view(ticket: Ticket, user: User) -> bool:
    return user.role in ("admin", "technician") or ticket.creator_id == user.id


def get_ticket(db: Session, ticket_id: int, user: User) -> Ticket:
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
            joinedload(Ticket.category),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado.")
    if not can_view(ticket, user):
        raise HTTPException(status_code=403, detail="Você não tem acesso a este chamado.")
    return ticket


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserOut, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)) -> User:
    email = str(data.email).strip().lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

    user = User(
        name=data.name,
        email=email,
        password_hash=hash_password(data.password),
        role="user",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.") from None
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenOut)
def login(request: Request, data: LoginInput, db: Session = Depends(get_db)) -> dict[str, str]:
    email = str(data.email).strip().lower()
    client_ip = request.client.host if request.client else "desconhecido"
    limiter_key = f"{client_ip}|{email}"
    wait = login_limiter.retry_after(limiter_key)
    if wait:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Aguarde alguns minutos e tente novamente.",
            headers={"Retry-After": str(wait)},
        )
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None:
        burn_password_check(data.password)
        password_ok = False
    else:
        password_ok = verify_password(data.password, user.password_hash)
    if user is None or not password_ok or not user.is_active:
        login_limiter.register_failure(limiter_key)
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    login_limiter.reset(limiter_key)
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@app.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@app.get("/users/", response_model=list[UserOut])
def users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> list[User]:
    return db.query(User).order_by(User.name).all()


def ensure_another_active_admin(db: Session, target: User) -> None:
    """Impede que a operação deixe o sistema sem nenhum administrador ativo."""
    if target.role == "admin" and target.is_active:
        remaining_admins = (
            db.query(User)
            .filter(User.role == "admin", User.is_active.is_(True), User.id != target.id)
            .count()
        )
        if remaining_admins == 0:
            raise HTTPException(
                status_code=409, detail="O sistema precisa manter pelo menos um administrador ativo."
            )


@app.patch("/users/{user_id}/role", response_model=UserOut)
def set_role(
    user_id: int,
    role: str = Query(..., pattern="^(user|technician|admin)$"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if target.id == admin.id and role != "admin":
        raise HTTPException(status_code=400, detail="Você não pode remover sua própria função de administrador.")
    if role != "admin":
        ensure_another_active_admin(db, target)
    target.role = role
    db.commit()
    db.refresh(target)
    return target


@app.patch("/users/{user_id}/active", response_model=UserOut)
def set_active(
    user_id: int,
    data: UserActiveUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if target.id == admin.id and not data.is_active:
        raise HTTPException(status_code=400, detail="Você não pode desativar a própria conta.")
    if not data.is_active:
        ensure_another_active_admin(db, target)
    target.is_active = data.is_active
    db.commit()
    db.refresh(target)
    return target


@app.get("/categories/", response_model=list[CategoryOut])
def categories(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Category]:
    return db.query(Category).order_by(Category.name).all()


@app.post("/categories/", response_model=CategoryOut, status_code=201)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> Category:
    name = data.name.strip()
    if db.query(Category).filter(func.lower(Category.name) == name.lower()).first():
        raise HTTPException(status_code=409, detail="Categoria já existe.")
    category = Category(name=name, description=data.description.strip() if data.description else None)
    db.add(category)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Categoria já existe.") from None
    db.refresh(category)
    return category


@app.get("/tickets/", response_model=TicketPage)
def list_tickets(
    search: str | None = Query(default=None, max_length=120),
    status: str | None = Query(default=None, pattern="^(open|in_progress|waiting|completed)$"),
    priority: str | None = Query(default=None, pattern="^(low|medium|high|urgent)$"),
    category_id: int | None = Query(default=None, gt=0),
    assignee_id: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    query = db.query(Ticket).options(
        joinedload(Ticket.creator),
        joinedload(Ticket.assignee),
        joinedload(Ticket.category),
    )
    if user.role == "user":
        query = query.filter(Ticket.creator_id == user.id)
    if search and search.strip():
        term = f"%{escape_like(search.strip())}%"
        query = query.filter(
            or_(Ticket.title.ilike(term, escape="\\"), Ticket.description.ilike(term, escape="\\"))
        )
    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if category_id:
        query = query.filter(Ticket.category_id == category_id)
    if assignee_id:
        query = query.filter(Ticket.assignee_id == assignee_id)

    total = query.count()
    items = (
        query.order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size) if total else 0,
    }


@app.post("/tickets/", response_model=TicketOut, status_code=201)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Ticket:
    if db.get(Category, data.category_id) is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")
    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        creator_id=user.id,
        category_id=data.category_id,
        status="open",
    )
    db.add(ticket)
    db.flush()
    log_change(db, ticket, user, "created", None, "open")
    db.commit()
    return get_ticket(db, ticket.id, user)


@app.get("/tickets/{ticket_id}", response_model=TicketOut)
def ticket_detail(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Ticket:
    return get_ticket(db, ticket_id, user)


@app.patch("/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Ticket:
    ticket = get_ticket(db, ticket_id, user)
    if user.role == "user":
        raise HTTPException(status_code=403, detail="Solicitantes não podem editar chamados.")
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Informe ao menos um campo para atualizar.")
    if user.role == "technician":
        if ticket.assignee_id != user.id:
            raise HTTPException(status_code=403, detail="Você só pode atualizar chamados atribuídos a você.")
        if ticket.status == "completed":
            raise HTTPException(status_code=409, detail="Chamados concluídos não podem ser alterados por técnicos.")
        if set(changes) - {"status"}:
            raise HTTPException(status_code=403, detail="Técnicos só podem alterar o status.")
    # Técnicos podem concluir somente chamados atribuídos a eles (validado acima).
    # Solicitantes já são bloqueados antes desta etapa; o gerente/admin mantém o controle total.
    if changes.get("status") == "completed" and user.role not in ("admin", "technician"):
        raise HTTPException(status_code=403, detail="Você não tem permissão para concluir chamados.")
    if "status" in changes and changes["status"] != ticket.status:
        allowed_transitions = {
            "open": {"in_progress", "waiting", "completed"},
            "in_progress": {"open", "waiting", "completed"},
            "waiting": {"open", "in_progress", "completed"},
            "completed": set(),
        }
        if user.role != "admin" and changes["status"] not in allowed_transitions[ticket.status]:
            raise HTTPException(status_code=409, detail="Transição de status não permitida para técnico.")

    for field, new_value in changes.items():
        old_value = getattr(ticket, field)
        if old_value != new_value:
            setattr(ticket, field, new_value)
            log_change(db, ticket, user, field, old_value, new_value)
    db.commit()
    return get_ticket(db, ticket.id, user)


@app.patch("/tickets/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    ticket_id: int,
    data: TicketAssign,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
) -> Ticket:
    ticket = get_ticket(db, ticket_id, admin)
    if ticket.status == "completed":
        raise HTTPException(status_code=409, detail="Não é possível atribuir um chamado concluído.")
    person = None
    if data.assignee_id is not None:
        person = db.get(User, data.assignee_id)
        if person is None or not person.is_active or person.role != "technician":
            raise HTTPException(status_code=422, detail="O responsável precisa ser um técnico ativo.")
    if ticket.assignee_id != data.assignee_id:
        old_name = ticket.assignee.name if ticket.assignee else None
        new_name = person.name if data.assignee_id is not None else None
        ticket.assignee_id = data.assignee_id
        log_change(db, ticket, admin, "assignee", old_name, new_name)
        db.commit()
    return get_ticket(db, ticket.id, admin)


@app.post("/tickets/{ticket_id}/claim", response_model=TicketOut)
def claim_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    tech: User = Depends(require_roles("technician")),
) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Chamado não encontrado.")
    result = db.execute(
        update(Ticket)
        .where(
            Ticket.id == ticket_id,
            Ticket.assignee_id.is_(None),
            Ticket.status != "completed",
        )
        .values(assignee_id=tech.id)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Este chamado já foi atribuído ou está concluído.",
        )
    log_change(db, ticket, tech, "assignee", None, tech.name)
    db.commit()
    return get_ticket(db, ticket_id, tech)


@app.get("/tickets/{ticket_id}/history", response_model=list[HistoryOut])
def ticket_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TicketHistory]:
    get_ticket(db, ticket_id, user)
    return (
        db.query(TicketHistory)
        .options(joinedload(TicketHistory.actor))
        .filter(TicketHistory.ticket_id == ticket_id)
        .order_by(TicketHistory.changed_at.desc(), TicketHistory.id.desc())
        .all()
    )


@app.get("/tickets/{ticket_id}/comments", response_model=list[CommentOut])
def comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Comment]:
    get_ticket(db, ticket_id, user)
    return (
        db.query(Comment)
        .options(joinedload(Comment.author))
        .filter(Comment.ticket_id == ticket_id)
        .order_by(Comment.created_at.asc(), Comment.id.asc())
        .all()
    )


@app.post("/tickets/{ticket_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    ticket_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Comment:
    ticket = get_ticket(db, ticket_id, user)
    if ticket.status == "completed" and user.role != "admin":
        raise HTTPException(status_code=409, detail="Não é possível comentar em chamado concluído.")
    comment = Comment(content=data.content, ticket_id=ticket.id, author_id=user.id)
    db.add(comment)
    db.flush()
    log_change(db, ticket, user, "comment_added", None, f"Comentário #{comment.id}")
    db.commit()
    db.refresh(comment)
    return comment


@app.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    query = db.query(Ticket)
    if user.role == "user":
        query = query.filter(Ticket.creator_id == user.id)
    statuses = {key: 0 for key in ("open", "in_progress", "waiting", "completed")}
    priorities = {key: 0 for key in ("low", "medium", "high", "urgent")}
    for key, count in query.with_entities(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status):
        statuses[key] = count
    for key, count in query.with_entities(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority):
        priorities[key] = count
    return {"total": sum(statuses.values()), "by_status": statuses, "by_priority": priorities}
