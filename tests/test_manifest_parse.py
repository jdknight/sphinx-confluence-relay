# SPDX-License-Identifier: BSD-2-Clause
# Copyright jdknight

from sphinx_confluence_relay.manifest import BadRequestException
from sphinx_confluence_relay.manifest import parse_manifest
from tests import DATA_FOLDER
from tests import ScrAppTestCase
from unittest.mock import patch
import json


# maximum entries patch key
ME_KEY = 'sphinx_confluence_relay.manifest.MAX_ENTRIES'


def parse(name: str) -> dict:
    manifest = DATA_FOLDER / 'test-manifests' / name
    data = json.loads(manifest.read_text())
    return parse_manifest(data)


class TestManifestParse(ScrAppTestCase):
    def test_manifest_parse_attachment_entry_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-entry-bad.json')

    def test_manifest_parse_attachment_entry_empty(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-entry-empty.json')

    def test_manifest_parse_attachment_value_data_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-data-bad.json')

    def test_manifest_parse_attachment_value_data_empty(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-data-empty.json')

    def test_manifest_parse_attachment_value_data_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-data-missing.json')

    def test_manifest_parse_attachment_value_id_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-id-bad.json')

    def test_manifest_parse_attachment_value_id_empty(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-id-empty.json')

    def test_manifest_parse_attachment_value_id_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-id-missing.json')

    def test_manifest_parse_attachment_value_mimetype_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-mimetype-bad.json')

    def test_manifest_parse_attachment_value_mimetype_empty(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-mimetype-empty.json')

    def test_manifest_parse_attachment_value_mimetype_invalid(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-mimetype-invalid.json')

    def test_manifest_parse_attachment_value_mimetype_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-mimetype-missing.json')

    def test_manifest_parse_attachment_value_page_id_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-page-id-bad.json')

    def test_manifest_parse_attachment_value_page_id_noref(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachment-value-page-id-noref.json')

    def test_manifest_parse_attachments_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('attachments-bad.json')

    def test_manifest_parse_attachments_empty(self) -> None:
        data = parse('attachments-empty.json')
        self.assertFalse(data['attachments'])

    def test_manifest_parse_includes_data_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('includes-data-bad.json')

    def test_manifest_parse_order_swap(self) -> None:
        data = parse('order-swap.json')
        self.assertTrue(data['pages'][0]['isRoot'])

    def test_manifest_parse_orphan(self) -> None:
        data = parse('orphan.json')
        self.assertEqual(len(data['pages']), 2)

    def test_manifest_parse_includes_data_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('includes-data-missing.json')

    def test_manifest_parse_page_entry_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-entry-bad.json')

    def test_manifest_parse_page_entry_empty(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-entry-empty.json')

    def test_manifest_parse_page_value_data_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-data-bad.json')

    def test_manifest_parse_page_value_data_empty(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-data-empty.json')

    def test_manifest_parse_page_value_data_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-data-missing.json')

    def test_manifest_parse_page_value_id_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-id-bad.json')

    def test_manifest_parse_page_value_id_conflict(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-id-conflict.json')

    def test_manifest_parse_page_value_id_empty(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-id-empty.json')

    def test_manifest_parse_page_value_id_selfref(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-id-selfref.json')

    def test_manifest_parse_page_value_parent_id_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-parent-id-bad.json')

    def test_manifest_parse_page_value_parent_id_noref(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-parent-id-noref.json')

    def test_manifest_parse_page_value_title_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-title-bad.json')

    def test_manifest_parse_page_value_title_empty(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-title-empty.json')

    def test_manifest_parse_page_value_title_long(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-title-long.json')

    def test_manifest_parse_page_value_title_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-title-missing.json')

    def test_manifest_parse_page_value_title_whitespace(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('page-value-title-whitespace.json')

    def test_manifest_parse_pages_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('pages-bad.json')

    def test_manifest_parse_pages_empty(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('pages-empty.json')

    def test_manifest_parse_pages_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('pages-missing.json')

    def test_manifest_parse_root_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('root-bad.json')

    def test_manifest_parse_root_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('root-missing.json')

    def test_manifest_parse_root_multiple(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('root-multiple.json')

    def test_manifest_parse_spec_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('spec-bad.json')

    def test_manifest_parse_spec_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('spec-missing.json')

    def test_manifest_parse_spec_negative(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('spec-negative.json')

    def test_manifest_parse_type_bad(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('type-bad.json')

    def test_manifest_parse_type_missing(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('type-missing.json')

    def test_manifest_parse_type_unknown(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('type-unknown.json')

    @patch(ME_KEY, 2)
    def test_manifest_parse_too_many_attachments(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('too-many-attachments.json')

    @patch(ME_KEY, 1)
    def test_manifest_parse_too_many_pages(self) -> None:
        with self.assertRaises(BadRequestException):
            parse('too-many-pages.json')
