# Copyright (c) 2026-present RopeOps contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Static guard: every model in a RopeOps app must be tenant-scoped.

RopeOps apps are Django apps whose label starts with "ropeops_". Each concrete model
needs a "workspace" foreign key (inherit plane.db.models.WorkspaceBaseModel) unless it is
listed in EXEMPT with a written reason reviewed by the CTO.
"""

import pytest
from django.apps import apps
from django.db import models

# "app_label.ModelName": "reason"
EXEMPT: dict[str, str] = {}


def _ropeops_models():
    for config in apps.get_app_configs():
        if config.label.startswith("ropeops_"):
            yield from config.get_models()


@pytest.mark.parametrize("model", list(_ropeops_models()) or [None], ids=lambda m: m._meta.label if m else "none-yet")
def test_model_has_workspace_fk(model):
    if model is None:
        pytest.skip("no ropeops_* apps installed yet")
    if model._meta.label in EXEMPT:
        return
    field = model._meta.get_field("workspace")
    assert isinstance(field, models.ForeignKey), f"{model._meta.label}.workspace must be a ForeignKey"
    assert field.remote_field.model._meta.label == "db.Workspace"
    assert not field.null, f"{model._meta.label}.workspace must not be nullable"
