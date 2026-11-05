"""Tests for the orchestrated-template, dependency, deprecation and requirements rules."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from conftest import edit

DEBIAN = Path("templates/ludusplusplus-debian-13/ludusplusplus-debian-13.pkr.hcl")

LUDUS_BLOCK = textwrap.dedent(
    '''
    variable "proxmox_url" {
      type = string
    }
    variable "proxmox_host" {
      type = string
    }
    variable "proxmox_username" {
      type = string
    }
    variable "proxmox_password" {
      type      = string
      sensitive = true
    }
    variable "proxmox_storage_pool" {
      type = string
    }
    variable "proxmox_storage_format" {
      type = string
    }
    variable "proxmox_skip_tls_verify" {
      type = bool
    }
    variable "proxmox_pool" {
      type = string
    }
    variable "iso_storage_pool" {
      type = string
    }
    variable "ansible_home" {
      type = string
    }
    variable "ludus_nat_interface" {
      type = string
    }
    '''
)

ORCHESTRATION_ENV = textwrap.dedent(
    '''
        environment_vars = [
          "PROXMOX_URL=${var.proxmox_url}",
          "PROXMOX_HOST=${var.proxmox_host}",
          "PROXMOX_INSECURE=${var.proxmox_skip_tls_verify}",
          "PROXMOX_POOL=${var.proxmox_pool}",
          "PROXMOX_STORAGE_POOL=${var.proxmox_storage_pool}",
          "PROXMOX_STORAGE_FORMAT=${var.proxmox_storage_format}",
          "ISO_STORAGE_POOL=${var.iso_storage_pool}",
          "LUDUS_NAT_INTERFACE=${var.ludus_nat_interface}",
          "ANSIBLE_HOME=${var.ansible_home}",
        ]
    '''
)


def add_orchestrated_template(root: Path, name: str = "ludusplusplus-orch-test-template", with_os: bool = True, env: str = ORCHESTRATION_ENV, inline: str = 'bash \\"${path.root}/scripts/import.sh\\"') -> Path:
    tdir = root / "templates" / "orch-test"
    (tdir / "scripts").mkdir(parents=True)
    (tdir / "scripts" / "import.sh").write_text("#!/usr/bin/env bash\necho import\n", encoding="utf-8")
    os_block = 'variable "os" {\n  type    = string\n  default = "l26"\n}\n' if with_os else ""
    (tdir / "orch-test.pkr.hcl").write_text(
        textwrap.dedent(
            f'''
            variable "description" {{
              type    = string
              default = "Orchestrated test template."
            }}
            variable "vm_name" {{
              type    = string
              default = "{name}"
            }}
            variable "ssh_username" {{
              type    = string
              default = "localuser"
            }}
            variable "ssh_password" {{
              type    = string
              default = "password"
            }}
            '''
        )
        + os_block
        + LUDUS_BLOCK
        + textwrap.dedent(
            f'''
            source "null" "orch" {{
              communicator = "none"
            }}

            build {{
              sources = ["source.null.orch"]
              provisioner "shell-local" {{{env}
                inline = ["{inline}"]
              }}
            }}
            '''
        ),
        encoding="utf-8",
    )
    return tdir


# --- orchestrated templates ------------------------------------------------------


def test_orchestrated_template_is_accepted(lint, source):
    add_orchestrated_template(source)
    findings, by_rule = lint(source)
    mine = [f for f in findings if "orch-test" in f.path and f.level in ("error", "warning")]
    assert not mine, [f.as_text() for f in mine]


def test_null_source_without_shell_local_is_not_a_template(lint, source):
    tdir = add_orchestrated_template(source)
    edit(tdir / "orch-test.pkr.hcl", 'provisioner "shell-local"', 'provisioner "shell"')
    _, by_rule = lint(source)
    assert any("orch-test" in f.path for f in by_rule.get("T007", []))


def test_orchestration_must_receive_ludus_variables(lint, source):
    env = ORCHESTRATION_ENV.replace('"PROXMOX_STORAGE_POOL=${var.proxmox_storage_pool}",', '"PROXMOX_STORAGE_POOL=local-zfs",')
    add_orchestrated_template(source, env=env)
    _, by_rule = lint(source)
    assert any("proxmox_storage_pool" in f.message and f.level == "warning" for f in by_rule.get("T020", []))


def test_orchestration_path_root_references_are_checked(lint, source):
    add_orchestrated_template(source, inline='bash \\"${path.root}/scripts/missing.sh\\"')
    _, by_rule = lint(source)
    assert any("scripts/missing.sh" in f.message for f in by_rule.get("T012", []))


def test_orchestration_must_not_override_collections_path(lint, source):
    env = ORCHESTRATION_ENV.replace('"ANSIBLE_HOME=${var.ansible_home}",', '"ANSIBLE_HOME=${var.ansible_home}",\n      "ANSIBLE_COLLECTIONS_PATH=${path.root}/collections",')
    add_orchestrated_template(source, env=env)
    _, by_rule = lint(source)
    assert any("ANSIBLE_COLLECTIONS_PATH" in f.message for f in by_rule.get("T017", []))


def test_macos_template_must_not_declare_os(lint, source):
    add_orchestrated_template(source, name="ludusplusplus-macos-test-template", with_os=True)
    _, by_rule = lint(source)
    assert any("macOS" in f.message and f.level == "error" for f in by_rule.get("T010", []))


def test_macos_template_without_os_is_clean(lint, source):
    add_orchestrated_template(source, name="ludusplusplus-macos-test-template", with_os=False)
    findings, _ = lint(source)
    assert not [f for f in findings if "orch-test" in f.path and f.rule == "T010"]


def test_orchestrated_template_without_os_is_a_warning(lint, source):
    add_orchestrated_template(source, with_os=False)
    _, by_rule = lint(source)
    assert any("orch-test" in f.path and f.level == "warning" for f in by_rule.get("T010", []))


# --- requirements files -----------------------------------------------------------


def test_requirements_from_outside_the_template_is_an_error(lint, source):
    (source / DEBIAN.parent / "requirements.yml").write_text("collections:\n  - name: ../../ansible/collections/get_sybers.templates\n    type: dir\n", encoding="utf-8")
    _, by_rule = lint(source)
    assert any("get_sybers.templates" in f.message for f in by_rule.get("T021", []))


def test_galaxy_file_from_outside_the_template_is_an_error(lint, source):
    (source / DEBIAN.parent / "deps.yml").write_text("roles:\n  - src: ../shared/role\n    name: shared\n", encoding="utf-8")
    edit(source / DEBIAN, 'playbook_file      = "ansible/customize.yml"', 'playbook_file      = "ansible/customize.yml"\n    galaxy_file        = "deps.yml"')
    _, by_rule = lint(source)
    assert any("../shared/role" in f.message for f in by_rule.get("T021", []))


# --- ansible dependencies -------------------------------------------------------------


def test_collection_installed_by_ludus_is_fine(lint, source):
    edit(source / DEBIAN.parent / "ansible/customize.yml", "  tasks:\n", "  tasks:\n    - name: use a Ludus-installed collection\n      community.general.ufw:\n        state: enabled\n")
    findings, _ = lint(source)
    assert not [f for f in findings if f.rule == "T018" and str(DEBIAN) in f.path]


def test_collection_nobody_installs_is_a_warning_unless_documented(lint, source):
    edit(source / DEBIAN.parent / "ansible/customize.yml", "  tasks:\n", "  tasks:\n    - name: use an extra collection\n      community.mysql.mysql_db:\n        name: x\n")
    _, by_rule = lint(source)
    assert any("community.mysql" in f.message and f.level == "warning" for f in by_rule.get("T018", []))
    (source / DEBIAN.parent / "README.md").write_text("Needs `ludus ansible collection add community.mysql` first.\n", encoding="utf-8")
    _, by_rule = lint(source)
    assert all(f.level == "info" for f in by_rule.get("T018", []) if "community.mysql" in f.message)


def test_collection_shipped_by_source_is_informational(lint, source):
    edit(source / DEBIAN.parent / "ansible/customize.yml", "  tasks:\n", "  tasks:\n    - name: use the shipped collection\n      ansible.builtin.import_role:\n        name: get_sybers.templates.windows_ngen\n")
    _, by_rule = lint(source)
    assert any("get_sybers.templates" in f.message and f.level == "info" for f in by_rule.get("T018", []))


def test_galaxy_role_nobody_installs_is_a_warning(lint, source):
    edit(source / DEBIAN.parent / "ansible/customize.yml", "  become: true\n", "  become: true\n  roles:\n    - someone.some_role\n")
    _, by_rule = lint(source)
    assert any("someone.some_role" in f.message and f.level == "warning" for f in by_rule.get("T018", []))


# --- deprecated builder attributes -------------------------------------------------------


def test_deprecated_iso_attributes_are_a_warning(lint, source):
    text = (source / DEBIAN).read_text(encoding="utf-8")
    start = text.index("  boot_iso {")
    end = text.index("\n  }\n", start) + len("\n  }\n")
    text = text[:start] + '  iso_url          = "${var.iso_url}"\n  iso_checksum     = "${var.iso_checksum}"\n  iso_storage_pool = "${var.iso_storage_pool}"\n  unmount_iso      = true\n' + text[end:]
    (source / DEBIAN).write_text(text, encoding="utf-8")
    findings, by_rule = lint(source)
    assert any("iso_url" in f.message for f in by_rule.get("T019", []))
    assert not [f for f in findings if f.level == "error"], [f.as_text() for f in findings if f.level == "error"]


# --- icons ----------------------------------------------------------------------------


def test_placeholder_icon_is_a_warning(lint, source):
    Image = pytest.importorskip("PIL.Image")
    Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(source / DEBIAN.parent / "icon.png")
    _, by_rule = lint(source)
    assert any("placeholder" in f.message and f.level == "warning" for f in by_rule.get("T006", []))
