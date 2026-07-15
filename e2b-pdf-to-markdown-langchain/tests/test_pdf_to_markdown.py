"""Tests for the template-build and conversion phase boundary."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

import pdf_to_markdown_agent
import build_template


class ConvertPdfTest(unittest.TestCase):
    def test_uses_provided_template_without_building_a_new_one(self) -> None:
        """The agent phase creates a sandbox from the persisted template ID."""
        with tempfile.NamedTemporaryFile(suffix=".pdf") as pdf_file:
            sandbox = MagicMock()
            sandbox.sandbox_id = "sandbox-123"
            sandbox.commands.run.return_value.exit_code = 0
            sandbox.commands.run.return_value.stdout = "converted 1 pages"
            sandbox.files.read.return_value = "# Converted\n"

            with patch.dict(os.environ, {"E2B_API_KEY": "test-key"}, clear=True), patch.object(
                pdf_to_markdown_agent, "load_environment"
            ), patch.object(
                pdf_to_markdown_agent.Sandbox, "create", return_value=sandbox
            ) as sandbox_create:
                markdown = pdf_to_markdown_agent.convert_pdf(
                    pdf_file.name, template_id="document-template-123"
                )

        self.assertEqual(markdown, "# Converted\n")
        self.assertEqual(sandbox_create.call_args.kwargs["template"], "document-template-123")


class BuildTemplateTest(unittest.TestCase):
    def test_builds_template_from_the_published_image(self) -> None:
        """The template stage returns the ID later used by the agent stage."""
        self.assertEqual(Path(build_template.__file__).resolve().parent, PROJECT_DIR)
        template_definition = object()
        build = MagicMock(template_id="document-template-123")

        with patch.dict(
            os.environ,
            {"E2B_API_KEY": "test-key", "E2B_TEMPLATE_IMAGE": "registry.example/image:1"},
            clear=True,
        ), patch.object(build_template, "Template") as template:
            template.return_value.from_image.return_value = template_definition
            template.build.return_value = build

            template_id = build_template.build_document_template()

        self.assertEqual(template_id, "document-template-123")
        template.return_value.from_image.assert_called_once_with("registry.example/image:1")
        template.build.assert_called_once()


if __name__ == "__main__":
    unittest.main()
