# Copyright (c) 2026-present RopeOps contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""RopeOps tenant-isolation test harness. See docs/TENANT_ISOLATION_TESTING.md."""

from .isolation import (  # noqa: F401
    Tenant,
    TwoTenants,
    assert_cross_tenant_denied,
    assert_list_scoped,
    build_tenant,
)
