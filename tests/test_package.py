"""Regression tests for packaging and publication boundaries; standard library only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile


PROJECT = Path(__file__).resolve().parents[1]


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='fitness-package-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'project'
        shutil.copytree(PROJECT, self.root, ignore=shutil.ignore_patterns('dist', '.git', '__pycache__', '.DS_Store'))
        spec = importlib.util.spec_from_file_location('fitness_package_under_test', PROJECT / 'scripts' / 'package.py')
        self.package = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.package)
        self.package.ROOT = self.root
        self.package.SKILL = self.root / 'skills' / 'fitness-companion'

    def test_public_tree_and_release_contacts(self):
        files, version, links = self.package.validate()
        self.package.validate_release(files)
        self.assertTrue(version)
        self.assertGreater(links, 0)

    def test_unapproved_private_file_is_rejected(self):
        (self.root / 'private-notes.md').write_text('Private fixture, not a real record.', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unapproved release file'):
            self.package.validate()

    def test_outside_symlink_is_rejected(self):
        external = self.base / 'external.md'
        external.write_text('External fixture.', encoding='utf-8')
        (self.package.SKILL / 'references' / 'external.md').symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'Symlink is not allowed'):
            self.package.validate()

    def test_arbitrary_media_and_invalid_icon_are_rejected(self):
        extra = self.package.SKILL / 'assets' / 'extra.png'
        extra.write_bytes(b'Unapproved image fixture')
        with self.assertRaisesRegex(ValueError, 'Unapproved release file'):
            self.package.validate()
        extra.unlink()
        icon = self.package.SKILL / 'assets' / 'fitness-companion-icon-v1.png'
        icon.write_bytes(b'Invalid PNG fixture')
        with self.assertRaisesRegex(ValueError, 'Invalid icon PNG'):
            self.package.validate()

    def test_contact_placeholders_block_release(self):
        closing = self.package.SKILL / 'references' / 'plan-closing.md'
        closing.write_text(closing.read_text(encoding='utf-8').replace(self.package.CONTACT_EMAIL, '[你的邮箱地址]'), encoding='utf-8')
        files, _, _ = self.package.validate()
        with self.assertRaisesRegex(ValueError, 'Unfilled public contact placeholder'):
            self.package.validate_release(files)

    def test_skill_archive_hashes_and_scope(self):
        files, version, _ = self.package.validate()
        skill_files = [p for p in files if p.is_relative_to(self.package.SKILL)]
        archive = self.base / 'skill.zip'
        self.package.build_archive(archive, skill_files, self.package.SKILL, version, 'skill')
        with zipfile.ZipFile(archive) as z:
            manifest = json.loads(z.read('fitness-companion/MANIFEST.json'))
            expected = {p.relative_to(self.package.SKILL).as_posix() for p in skill_files}
            self.assertEqual(set(manifest['sha256']), expected)
            self.assertNotIn('README.md', expected)
            for name, digest in manifest['sha256'].items():
                self.assertEqual(hashlib.sha256(z.read('fitness-companion/' + name)).hexdigest(), digest)
            self.assertTrue(all(name.startswith('fitness-companion/') and '..' not in Path(name).parts for name in z.namelist()))

    def test_repository_archive_round_trip(self):
        files, version, _ = self.package.validate()
        archive = self.base / 'repository.zip'
        self.package.build_archive(archive, files, self.root, version, 'repository')
        with zipfile.ZipFile(archive) as z:
            expected = {'fitness-companion/' + p.relative_to(self.root).as_posix() for p in files}
            self.assertEqual(set(z.namelist()), expected)
            self.assertIn('fitness-companion/.github/workflows/validate.yml', expected)
            self.assertIn('fitness-companion/CONTRIBUTING.md', expected)
            z.extractall(self.base / 'extracted')
        self.package.ROOT = self.base / 'extracted' / 'fitness-companion'
        self.package.SKILL = self.package.ROOT / 'skills' / 'fitness-companion'
        unpacked_files, _, _ = self.package.validate()
        self.package.validate_release(unpacked_files)

    def test_author_text_changes_only_for_confirmed_contacts(self):
        text = (self.package.SKILL / 'references' / 'plan-closing.md').read_text(encoding='utf-8')
        body = text.split('## 结尾文案\n', 1)[1]
        body = body.replace('[RuneYang123/fitness-companion](' + self.package.REPOSITORY_URL + ')', '`[可在此填入你的 GitHub 仓库链接]`')
        body = body.replace('[' + self.package.CONTACT_EMAIL + '](mailto:' + self.package.CONTACT_EMAIL + ')', '`[你的邮箱地址]`')
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), '5ff596804449cc22cdb74cca4bf5e2889b10d4001f2347dfe25c42e7af369fae')


if __name__ == '__main__':
    unittest.main()
