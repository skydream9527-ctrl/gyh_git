"""三轴权限（D-10）：平台角色 × 团队/项目成员角色 × Twin 权限(L0-L5)。

有效权限取三者交集。本模块给出枚举 + 判定骨架，M1 接入真实成员/Twin 数据。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class PlatformRole(str):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    USER = "user"


class MemberRole(str):
    OWNER = "owner"      # team
    ADMIN = "admin"      # team
    MEMBER = "member"    # team / project
    NONE = "none"


class TwinLevel(IntEnum):
    L0_OBSERVE = 0
    L1_SUGGEST = 1
    L2_DELEGATE_DRAFT = 2
    L3_REQUEST_EXEC = 3
    L4_BOUNDED_AUTOPILOT = 4
    L5_SOVEREIGN = 5


# 高风险动作清单（必须用户确认）
HIGH_RISK_ACTIONS = {
    "write_local_file",
    "run_command",
    "send_message",
    "paid_call",
    "persist_memory",
    "cross_space_read",
}


@dataclass
class EffectivePerms:
    platform_role: str
    member_role: str
    twin_level: TwinLevel

    def can_view_resource(self) -> bool:
        """是否能查看某团队/项目资源：需有成员资格或平台管理员。"""
        return self.member_role != MemberRole.NONE or self.platform_role in (
            PlatformRole.SUPER_ADMIN,
            PlatformRole.ADMIN,
        )

    def can_manage_members(self) -> bool:
        return self.member_role in (MemberRole.OWNER, MemberRole.ADMIN) or (
            self.platform_role == PlatformRole.SUPER_ADMIN
        )

    def requires_approval(self, action: str) -> bool:
        """高风险动作恒需确认；其余按 Twin 等级放行。"""
        if action in HIGH_RISK_ACTIONS:
            return True
        return self.twin_level < TwinLevel.L3_REQUEST_EXEC


def effective_perms(platform_role: str, member_role: str, twin_level: int) -> EffectivePerms:
    return EffectivePerms(
        platform_role=platform_role,
        member_role=member_role,
        twin_level=TwinLevel(int(twin_level)),
    )
