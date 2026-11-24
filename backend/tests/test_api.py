from app.models import Category, User
from app.security import hash_password


def create_account(client, name, email):
    response = client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": "SenhaForte123"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(client, email):
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "SenhaForte123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_ticket(client, headers, category_id, title="Computador não liga"):
    return client.post(
        "/tickets/",
        headers=headers,
        json={
            "title": title,
            "description": "O computador da estação não liga desde hoje.",
            "priority": "high",
            "category_id": category_id,
        },
    )


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_login_and_me(client):
    created = create_account(client, "Pessoa", "pessoa@example.com")
    assert created["role"] == "user"
    headers = auth(client, "pessoa@example.com")
    assert client.get("/auth/me", headers=headers).json()["email"] == "pessoa@example.com"


def test_duplicate_email_is_case_insensitive(client):
    create_account(client, "Pessoa", "pessoa@example.com")
    response = client.post(
        "/auth/register",
        json={"name": "Outra Pessoa", "email": "PESSOA@example.com", "password": "SenhaForte123"},
    )
    assert response.status_code == 409


def test_bad_password_and_inactive_user(client, db_session):
    create_account(client, "Pessoa", "pessoa@example.com")
    bad = client.post("/auth/login", json={"email": "pessoa@example.com", "password": "errada"})
    assert bad.status_code == 401
    user = db_session.query(User).filter_by(email="pessoa@example.com").one()
    user.is_active = False
    db_session.commit()
    inactive = client.post(
        "/auth/login", json={"email": "pessoa@example.com", "password": "SenhaForte123"}
    )
    assert inactive.status_code == 401


def test_auth_required(client):
    assert client.get("/tickets/").status_code == 401
    assert client.get("/dashboard/summary").status_code == 401


def test_user_cannot_list_users_or_see_other_ticket(client, db_session):
    create_account(client, "Pessoa A", "a@example.com")
    headers_a = auth(client, "a@example.com")
    category = Category(name="Hardware")
    db_session.add(category)
    db_session.commit()
    created = create_ticket(client, headers_a, category.id)
    assert created.status_code == 201, created.text

    create_account(client, "Pessoa B", "b@example.com")
    headers_b = auth(client, "b@example.com")
    assert client.get("/users/", headers=headers_b).status_code == 403
    ticket_id = created.json()["id"]
    assert client.get(f"/tickets/{ticket_id}", headers=headers_b).status_code == 403
    assert client.get("/tickets/", headers=headers_b).json()["total"] == 0


def test_ticket_comments_and_history(client, db_session):
    create_account(client, "Solicitante", "user@example.com")
    headers = auth(client, "user@example.com")
    category = Category(name="Rede")
    db_session.add(category)
    db_session.commit()
    ticket = create_ticket(client, headers, category.id)
    assert ticket.status_code == 201, ticket.text
    ticket_id = ticket.json()["id"]

    comment = client.post(
        f"/tickets/{ticket_id}/comments",
        headers=headers,
        json={"content": "Já reiniciei o equipamento."},
    )
    assert comment.status_code == 201, comment.text
    assert len(client.get(f"/tickets/{ticket_id}/comments", headers=headers).json()) == 1
    history = client.get(f"/tickets/{ticket_id}/history", headers=headers).json()
    assert any(item["field"] == "comment_added" for item in history)


def test_technician_can_complete_assigned_ticket_and_admin_keeps_access(client, db_session):
    create_account(client, "Solicitante", "user@example.com")
    user_headers = auth(client, "user@example.com")
    category = Category(name="Software")
    db_session.add(category)
    db_session.commit()
    ticket = create_ticket(client, user_headers, category.id).json()

    technician = User(
        name="Técnico", email="tech@example.com", password_hash=hash_password("SenhaForte123"), role="technician"
    )
    admin = User(
        name="Admin", email="admin@example.com", password_hash=hash_password("SenhaForte123"), role="admin"
    )
    db_session.add_all([technician, admin])
    db_session.commit()
    tech_headers = auth(client, "tech@example.com")
    admin_headers = auth(client, "admin@example.com")

    claimed = client.post(f"/tickets/{ticket['id']}/claim", headers=tech_headers)
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["assignee_id"] == technician.id
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=tech_headers, json={"status": "in_progress"}
    ).status_code == 200
    completed = client.patch(
        f"/tickets/{ticket['id']}", headers=tech_headers, json={"status": "completed"}
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"
    # Depois de concluído, o técnico não pode reabrir nem editar o chamado.
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=tech_headers, json={"status": "in_progress"}
    ).status_code == 409
    # O administrador continua podendo acessar o chamado concluído.
    admin_view = client.get(f"/tickets/{ticket['id']}", headers=admin_headers)
    assert admin_view.status_code == 200
    assert admin_view.json()["status"] == "completed"
    blocked_comment = client.post(
        f"/tickets/{ticket['id']}/comments",
        headers=user_headers,
        json={"content": "Mais uma observação."},
    )
    assert blocked_comment.status_code == 409


def test_admin_can_demote_another_admin(client, db_session):
    admin = User(
        name="Admin A", email="admin-a@example.com", password_hash=hash_password("SenhaForte123"), role="admin"
    )
    second_admin = User(
        name="Admin B", email="admin-b@example.com", password_hash=hash_password("SenhaForte123"), role="admin"
    )
    db_session.add_all([admin, second_admin])
    db_session.commit()
    headers = auth(client, "admin-a@example.com")
    response = client.patch(f"/users/{second_admin.id}/role?role=user", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "user"


def test_invalid_ticket_filters_are_rejected(client):
    create_account(client, "Pessoa", "pessoa@example.com")
    headers = auth(client, "pessoa@example.com")
    assert client.get("/tickets/?status=banana", headers=headers).status_code == 422


def test_admin_cannot_demote_own_role(client, db_session):
    admin = User(name="Admin", email="admin@example.com", password_hash=hash_password("SenhaForte123"), role="admin")
    db_session.add(admin)
    db_session.commit()
    headers = auth(client, "admin@example.com")
    blocked = client.patch(f"/users/{admin.id}/role?role=technician", headers=headers)
    assert blocked.status_code == 400  # não pode alterar o próprio perfil administrativo


def test_technician_can_complete_from_waiting(client, db_session):
    create_account(client, "Solicitante", "user@example.com")
    user_headers = auth(client, "user@example.com")
    category = Category(name="Infraestrutura")
    db_session.add(category); db_session.commit()
    ticket = create_ticket(client, user_headers, category.id).json()
    tech = User(name="Técnico", email="tech@example.com", password_hash=hash_password("SenhaForte123"), role="technician")
    db_session.add(tech); db_session.commit()
    tech_headers = auth(client, "tech@example.com")
    assert client.post(f"/tickets/{ticket['id']}/claim", headers=tech_headers).status_code == 200
    # Aberto -> aguardando -> concluído é permitido ao técnico responsável.
    assert client.patch(f"/tickets/{ticket['id']}", headers=tech_headers, json={"status":"waiting"}).status_code == 200
    completed = client.patch(f"/tickets/{ticket['id']}", headers=tech_headers, json={"status":"completed"})
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"

def test_public_registration_cannot_choose_privileged_role(client):
    response = client.post("/auth/register", json={
        "name":"Intruso", "email":"intruso@example.com", "password":"SenhaForte123", "role":"admin"
    })
    assert response.status_code == 201
    assert response.json()["role"] == "user"


def test_invalid_token_is_rejected(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer token-invalido"})
    assert response.status_code == 401


def test_default_categories_are_created_and_seed_is_idempotent(db_session):
    from app.main import ensure_default_categories

    ensure_default_categories(db_session)
    first_count = db_session.query(Category).count()
    assert first_count >= 5
    names = {category.name for category in db_session.query(Category).all()}
    assert {"Hardware", "Software", "Rede e internet", "Acesso e contas", "E-mail", "Outros"}.issubset(names)

    ensure_default_categories(db_session)
    assert db_session.query(Category).count() == first_count


def test_categories_are_available_to_authenticated_users_and_protected_for_creation(client, db_session):
    create_account(client, "Pessoa", "categoria@example.com")
    headers = auth(client, "categoria@example.com")
    category = Category(name="Impressoras", description="Impressoras e scanners")
    db_session.add(category)
    db_session.commit()

    listed = client.get("/categories/", headers=headers)
    assert listed.status_code == 200
    assert any(item["name"] == "Impressoras" for item in listed.json())

    forbidden = client.post("/categories/", headers=headers, json={"name": "Nova categoria"})
    assert forbidden.status_code == 403


def test_admin_can_create_category_and_duplicate_is_rejected(client, db_session):
    admin = User(
        name="Admin",
        email="admin-categorias@example.com",
        password_hash=hash_password("SenhaForte123"),
        role="admin",
    )
    db_session.add(admin)
    db_session.commit()
    headers = auth(client, "admin-categorias@example.com")

    created = client.post(
        "/categories/",
        headers=headers,
        json={"name": "Telefonia", "description": "Celulares e ramais"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "Telefonia"

    duplicate = client.post(
        "/categories/",
        headers=headers,
        json={"name": "telefonia", "description": "Duplicada"},
    )
    assert duplicate.status_code == 409


def test_cors_preflight_accepts_local_frontend_origin(client):
    response = client.options(
        "/auth/register",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


# ---------------------------------------------------------------------------
# Regressões e novos comportamentos da revisão v5
# ---------------------------------------------------------------------------

def make_user(db_session, name, email, role):
    user = User(name=name, email=email, password_hash=hash_password("SenhaForte123"), role=role)
    db_session.add(user)
    db_session.commit()
    return user


def make_category(db_session, name="Hardware"):
    category = Category(name=name)
    db_session.add(category)
    db_session.commit()
    return category


def test_ticket_list_never_exposes_password_hash(client, db_session):
    create_account(client, "Pessoa", "pessoa@example.com")
    headers = auth(client, "pessoa@example.com")
    category = make_category(db_session)
    assert create_ticket(client, headers, category.id).status_code == 201

    response = client.get("/tickets/", headers=headers)
    assert response.status_code == 200
    assert "password_hash" not in response.text
    assert "argon2" not in response.text
    assert response.json()["items"][0]["creator"]["email"] == "pessoa@example.com"


def test_timestamps_are_serialized_as_utc(client, db_session):
    create_account(client, "Pessoa", "pessoa@example.com")
    headers = auth(client, "pessoa@example.com")
    category = make_category(db_session)
    ticket = create_ticket(client, headers, category.id).json()
    for value in (ticket["created_at"], ticket["updated_at"]):
        assert value.endswith("Z") or value.endswith("+00:00"), value


def test_search_treats_like_wildcards_literally(client, db_session):
    create_account(client, "Pessoa", "pessoa@example.com")
    headers = auth(client, "pessoa@example.com")
    category = make_category(db_session)
    create_ticket(client, headers, category.id, title="Desconto de 50% indevido")
    create_ticket(client, headers, category.id, title="Arquivo_final não abre")
    create_ticket(client, headers, category.id, title="Computador normal")

    percent = client.get("/tickets/", params={"search": "%"}, headers=headers).json()
    assert [item["title"] for item in percent["items"]] == ["Desconto de 50% indevido"]
    underscore = client.get("/tickets/", params={"search": "_"}, headers=headers).json()
    assert [item["title"] for item in underscore["items"]] == ["Arquivo_final não abre"]
    # a busca continua sem diferenciar maiúsculas de minúsculas
    assert client.get("/tickets/", params={"search": "NORMAL"}, headers=headers).json()["total"] == 1


def test_ticket_pagination(client, db_session):
    create_account(client, "Pessoa", "pessoa@example.com")
    headers = auth(client, "pessoa@example.com")
    category = make_category(db_session)
    for index in range(3):
        assert create_ticket(client, headers, category.id, title=f"Chamado número {index}").status_code == 201

    first = client.get("/tickets/?size=2&page=1", headers=headers).json()
    second = client.get("/tickets/?size=2&page=2", headers=headers).json()
    assert (first["total"], first["pages"], len(first["items"])) == (3, 2, 2)
    assert len(second["items"]) == 1
    ids = [item["id"] for item in first["items"] + second["items"]]
    assert len(set(ids)) == 3


def test_login_is_rate_limited_after_repeated_failures(client):
    create_account(client, "Pessoa", "pessoa@example.com")
    for _ in range(5):
        wrong = client.post("/auth/login", json={"email": "pessoa@example.com", "password": "senha-errada"})
        assert wrong.status_code == 401
    blocked = client.post("/auth/login", json={"email": "pessoa@example.com", "password": "SenhaForte123"})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0
    # outro e-mail não é afetado
    create_account(client, "Outra", "outra@example.com")
    assert client.post(
        "/auth/login", json={"email": "outra@example.com", "password": "SenhaForte123"}
    ).status_code == 200


def test_successful_login_clears_failure_counter(client):
    create_account(client, "Pessoa", "pessoa@example.com")
    for _ in range(4):
        client.post("/auth/login", json={"email": "pessoa@example.com", "password": "errada"})
    assert client.post(
        "/auth/login", json={"email": "pessoa@example.com", "password": "SenhaForte123"}
    ).status_code == 200
    for _ in range(4):
        assert client.post(
            "/auth/login", json={"email": "pessoa@example.com", "password": "errada"}
        ).status_code == 401


def test_unknown_email_login_returns_same_error_as_wrong_password(client):
    create_account(client, "Pessoa", "pessoa@example.com")
    wrong = client.post("/auth/login", json={"email": "pessoa@example.com", "password": "errada"})
    unknown = client.post("/auth/login", json={"email": "ninguem@example.com", "password": "errada"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_admin_can_deactivate_and_reactivate_user(client, db_session):
    make_user(db_session, "Admin", "admin@example.com", "admin")
    target = make_user(db_session, "Pessoa", "pessoa@example.com", "user")
    admin_headers = auth(client, "admin@example.com")
    user_headers = auth(client, "pessoa@example.com")

    off = client.patch(f"/users/{target.id}/active", headers=admin_headers, json={"is_active": False})
    assert off.status_code == 200 and off.json()["is_active"] is False
    # token já emitido deixa de valer e novo login é recusado
    assert client.get("/auth/me", headers=user_headers).status_code == 401
    assert client.post(
        "/auth/login", json={"email": "pessoa@example.com", "password": "SenhaForte123"}
    ).status_code == 401

    on = client.patch(f"/users/{target.id}/active", headers=admin_headers, json={"is_active": True})
    assert on.status_code == 200 and on.json()["is_active"] is True
    assert client.get("/auth/me", headers=auth(client, "pessoa@example.com")).status_code == 200


def test_user_activation_rules(client, db_session):
    admin = make_user(db_session, "Admin", "admin@example.com", "admin")
    other = make_user(db_session, "Pessoa", "pessoa@example.com", "user")
    admin_headers = auth(client, "admin@example.com")
    user_headers = auth(client, "pessoa@example.com")

    own = client.patch(f"/users/{admin.id}/active", headers=admin_headers, json={"is_active": False})
    assert own.status_code == 400
    assert client.patch(
        f"/users/{other.id}/active", headers=user_headers, json={"is_active": False}
    ).status_code == 403
    assert client.patch("/users/9999/active", headers=admin_headers, json={"is_active": False}).status_code == 404


def test_assignment_is_logged_with_names(client, db_session):
    create_account(client, "Solicitante", "user@example.com")
    user_headers = auth(client, "user@example.com")
    category = make_category(db_session)
    ticket = create_ticket(client, user_headers, category.id).json()
    technician = make_user(db_session, "Ana Técnica", "tech@example.com", "technician")
    make_user(db_session, "Admin", "admin@example.com", "admin")
    admin_headers = auth(client, "admin@example.com")

    assigned = client.patch(
        f"/tickets/{ticket['id']}/assign", headers=admin_headers, json={"assignee_id": technician.id}
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assignee"]["name"] == "Ana Técnica"

    released = client.patch(
        f"/tickets/{ticket['id']}/assign", headers=admin_headers, json={"assignee_id": None}
    )
    assert released.status_code == 200 and released.json()["assignee"] is None

    history = client.get(f"/tickets/{ticket['id']}/history", headers=admin_headers).json()
    changes = [(item["old_value"], item["new_value"]) for item in history if item["field"] == "assignee"]
    assert (None, "Ana Técnica") in changes
    assert ("Ana Técnica", None) in changes


def test_requester_gets_403_when_editing_even_with_empty_body(client, db_session):
    create_account(client, "Solicitante", "user@example.com")
    headers = auth(client, "user@example.com")
    category = make_category(db_session)
    ticket = create_ticket(client, headers, category.id).json()
    assert client.patch(f"/tickets/{ticket['id']}", headers=headers, json={}).status_code == 403
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=headers, json={"status": "completed"}
    ).status_code == 403


def test_dashboard_counts_only_own_tickets_for_requester(client, db_session):
    create_account(client, "Pessoa A", "a@example.com")
    create_account(client, "Pessoa B", "b@example.com")
    headers_a, headers_b = auth(client, "a@example.com"), auth(client, "b@example.com")
    category = make_category(db_session)
    create_ticket(client, headers_a, category.id)
    create_ticket(client, headers_a, category.id)
    create_ticket(client, headers_b, category.id)

    summary_a = client.get("/dashboard/summary", headers=headers_a).json()
    assert summary_a["total"] == 2
    assert summary_a["by_status"]["open"] == 2
    assert summary_a["by_priority"]["high"] == 2
    assert client.get("/dashboard/summary", headers=headers_b).json()["total"] == 1


def test_second_technician_cannot_claim_or_edit_assigned_ticket(client, db_session):
    create_account(client, "Solicitante", "user@example.com")
    user_headers = auth(client, "user@example.com")
    category = make_category(db_session)
    ticket = create_ticket(client, user_headers, category.id).json()
    make_user(db_session, "Técnico 1", "t1@example.com", "technician")
    make_user(db_session, "Técnico 2", "t2@example.com", "technician")
    first, second = auth(client, "t1@example.com"), auth(client, "t2@example.com")

    assert client.post(f"/tickets/{ticket['id']}/claim", headers=first).status_code == 200
    assert client.post(f"/tickets/{ticket['id']}/claim", headers=second).status_code == 409
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=second, json={"status": "in_progress"}
    ).status_code == 403
    # técnico só altera o status, nunca outros campos
    assert client.patch(
        f"/tickets/{ticket['id']}", headers=first, json={"priority": "low"}
    ).status_code == 403


def test_admin_can_only_assign_active_technicians(client, db_session):
    create_account(client, "Solicitante", "user@example.com")
    user_headers = auth(client, "user@example.com")
    category = make_category(db_session)
    ticket = create_ticket(client, user_headers, category.id).json()
    make_user(db_session, "Admin", "admin@example.com", "admin")
    common = make_user(db_session, "Comum", "comum@example.com", "user")
    inactive = make_user(db_session, "Inativo", "inativo@example.com", "technician")
    inactive.is_active = False
    db_session.commit()
    admin_headers = auth(client, "admin@example.com")

    for person in (common, inactive):
        response = client.patch(
            f"/tickets/{ticket['id']}/assign", headers=admin_headers, json={"assignee_id": person.id}
        )
        assert response.status_code == 422


def test_ticket_requires_existing_category(client):
    create_account(client, "Solicitante", "user@example.com")
    headers = auth(client, "user@example.com")
    assert create_ticket(client, headers, 9999).status_code == 404
