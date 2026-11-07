# Copyright (c) 2026-present RopeOps contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Helpers for proving that one workspace (tenant) can never see another's data.

Every RopeOps module PR that adds a model or an endpoint MUST ship a test built
from these helpers (see docs/TENANT_ISOLATION_TESTING.md).

Model: two fully separate tenants, A and B. Each has an admin, a member and a
guest, plus one project. Tests create "secret" rows in tenant A, then act as
every tenant-B user (and an anonymous caller) and assert that nothing about A
is reachable or leaks into responses.
"""

import json
from dataclasses import dataclass, field
from typing import Iterable
from uuid import uuid4

from rest_framework.test import APIClient

from plane.db.models import Project, ProjectMember, User, Workspace, WorkspaceMember

ADMIN, MEMBER, GUEST = 20, 15, 5
ROLES = {"admin": ADMIN, "member": MEMBER, "guest": GUEST}

# A cross-tenant request must be refused or hidden, never served.
DENIED_STATUSES = (401, 403, 404)


@dataclass
class Tenant:
    workspace: Workspace
    project: Project
    users: dict = field(default_factory=dict)  # role name -> User

    @property
    def slug(self) -> str:
        return self.workspace.slug

    def client_for(self, role: str) -> APIClient:
        client = APIClient()
        client.force_authenticate(user=self.users[role])
        return client


@dataclass
class TwoTenants:
    a: Tenant
    b: Tenant

    def attackers(self, victim: Tenant) -> Iterable[tuple[str, APIClient]]:
        """Every authenticated role of the *other* tenant, plus an anonymous client."""
        other = self.b if victim is self.a else self.a
        for role in ROLES:
            yield f"{other.slug}:{role}", other.client_for(role)
        yield "anonymous", APIClient()


def _user(label: str) -> User:
    uid = uuid4().hex[:10]
    user = User.objects.create(
        email=f"{label}-{uid}@example.test",
        username=f"{label}_{uid}",
        first_name=label,
        last_name="Tester",
    )
    user.set_password(uuid4().hex)
    user.save()
    return user


def build_tenant(name: str) -> Tenant:
    """Create a workspace with admin/member/guest users and one project."""
    users = {role: _user(f"{name}-{role}") for role in ROLES}
    workspace = Workspace.objects.create(
        name=f"Tenant {name}", slug=f"tenant-{name}-{uuid4().hex[:6]}", owner=users["admin"]
    )
    for role, user in users.items():
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=ROLES[role])
    project = Project.objects.create(
        name=f"Project {name}",
        identifier=name.upper()[:3] + uuid4().hex[:3].upper(),
        workspace=workspace,
        created_by=users["admin"],
    )
    for role, user in users.items():
        ProjectMember.objects.create(project=project, workspace=workspace, member=user, role=ROLES[role])
    return Tenant(workspace=workspace, project=project, users=users)


def _call(client: APIClient, method: str, url: str, data=None):
    return getattr(client, method.lower())(url, data=data, format="json")


def _body_text(response) -> str:
    if getattr(response, "data", None) is not None:
        try:
            return json.dumps(response.data, default=str)
        except TypeError:
            return str(response.data)
    return response.content.decode(errors="ignore")


def assert_cross_tenant_denied(
    tenants: TwoTenants,
    victim: Tenant,
    method: str,
    url: str,
    *,
    data=None,
    secrets: Iterable[str] = (),
) -> None:
    """Every user of the other tenant (and anonymous) must get 401/403/404 on url.

    secrets are strings (ids, names) that must never appear in any response body.
    """
    for who, client in tenants.attackers(victim):
        response = _call(client, method, url, data)
        assert response.status_code in DENIED_STATUSES, (
            f"{who} got {response.status_code} on {method} {url}; expected one of {DENIED_STATUSES}"
        )
        text = _body_text(response)
        for secret in secrets:
            assert str(secret) not in text, f"{who}: {method} {url} leaked {secret!r}"


def assert_list_scoped(
    tenants: TwoTenants,
    owner: Tenant,
    own_url: str,
    other_url: str,
    *,
    secret_ids: Iterable[str],
    expected_ids: Iterable[str] = (),
    role: str = "admin",
) -> None:
    """List endpoints must show only the caller's own tenant data.

    own_url is the list URL for owner's workspace, other_url the equivalent URL
    for the other tenant. Called as owner's role user:
      * own_url returns 200 and contains every id in expected_ids;
      * neither response contains any id in secret_ids (rows belonging to the other tenant);
      * other_url (the other tenant's workspace) is denied.
    """
    client = owner.client_for(role)
    own = client.get(own_url)
    assert own.status_code == 200, f"{own_url} -> {own.status_code}"
    text = _body_text(own)
    for wanted in expected_ids:
        assert str(wanted) in text, f"own row {wanted!r} missing from {own_url}"
    for secret in secret_ids:
        assert str(secret) not in text, f"{own_url} leaked other-tenant id {secret!r}"
    other = client.get(other_url)
    assert other.status_code in DENIED_STATUSES, f"{other_url} -> {other.status_code}"
    for secret in secret_ids:
        assert str(secret) not in _body_text(other)
