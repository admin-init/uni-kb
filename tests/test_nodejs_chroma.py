from __future__ import annotations

import tempfile

from uni_kb.parsers.nodejs.route import NodejsRouteParser
from uni_kb.parsers.nodejs.service import NodejsServiceParser
from uni_kb.parsers.nodejs.model import NodejsModelParser
from uni_kb.parsers.nodejs.middleware import NodejsMiddlewareParser
from uni_kb.store.chroma_indexes import ChromaIndexes


class TestNodejsChromaIndexing:
    def test_route_parser_indexes_to_collection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexes = ChromaIndexes(tmpdir)
            parser = NodejsRouteParser()

            source = """
const express = require('express');
const router = express.Router();

router.get('/api/users', (req, res) => {
  res.json({ users: [] });
});

router.post('/api/users', (req, res) => {
  res.json({ created: true });
});
"""
            result = parser.parse("routes.js", source)
            indexes.index_code(result, source, language="nodejs")

            count = indexes.count("code_nodejs_route")
            assert count > 0

    def test_service_parser_indexes_to_collection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexes = ChromaIndexes(tmpdir)
            parser = NodejsServiceParser()

            source = """
@Injectable()
export class UserService {
  async findAll() {
    return [];
  }
}
"""
            result = parser.parse("user.service.ts", source)
            indexes.index_code(result, source, language="nodejs")

            count = indexes.count("code_nodejs_service")
            assert count > 0

    def test_model_parser_indexes_to_collection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexes = ChromaIndexes(tmpdir)
            parser = NodejsModelParser()

            source = """
@Entity()
export class User {
  @PrimaryGeneratedColumn()
  id: number;

  @Column()
  name: string;
}
"""
            result = parser.parse("user.entity.ts", source)
            indexes.index_code(result, source, language="nodejs")

            count = indexes.count("code_nodejs_model")
            assert count > 0

    def test_middleware_parser_indexes_to_collection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            indexes = ChromaIndexes(tmpdir)
            parser = NodejsMiddlewareParser()

            source = """
@UseGuards(AuthGuard)
@Injectable()
export class JwtGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    return true;
  }
}
"""
            result = parser.parse("jwt.guard.ts", source)
            indexes.index_code(result, source, language="nodejs")

            count = indexes.count("code_nodejs_middleware")
            assert count > 0
