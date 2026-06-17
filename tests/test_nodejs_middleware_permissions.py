from __future__ import annotations

from uni_kb.parsers.nodejs.middleware import NodejsMiddlewareParser


class TestNodejsMiddlewarePermissions:
    def test_permissions_in_annotations(self):
        parser = NodejsMiddlewareParser()

        source = """
@UseGuards(AuthGuard)
@Injectable()
export class RoleGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const role = 'admin';
    return role === 'admin';
  }
}
"""
        result = parser.parse("role.guard.ts", source)
        assert len(result.classes) == 1
        cls = result.classes[0]

        assert "NestGuard" in cls.annotations
        perm_annotations = [a for a in cls.annotations if a.startswith("perm:")]
        assert len(perm_annotations) > 0
