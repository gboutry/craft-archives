# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2023 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import http
import subprocess
import urllib.error
from unittest.mock import Mock, call, patch

import pytest
from craft_archives.repo import apt_uca, errors, package_repository


@patch("subprocess.run")
def test_install_uca_keyring_already_installed(subprocess):
    assert apt_uca.install_uca_keyring() is False
    assert subprocess.mock_calls == [
        call(
            ["dpkg", "--status", package_repository.UCA_KEYRING_PACKAGE],
            check=True,
            capture_output=True,
        )
    ]


@patch(
    "subprocess.run",
    side_effect=[
        subprocess.CalledProcessError(
            1,
            cmd="dpkg --status ubuntu-cloud-keyring",
            stderr=b"dpkg-query: package 'ubuntu-cloud-keyring' is not installed and no information is available",
        ),
        None,
    ],
)
def test_install_uca_keyring_not_installed(subprocess):
    assert apt_uca.install_uca_keyring() is True
    assert subprocess.call_count == 2
    assert subprocess.called_with(
        ["apt", "install", "--yes", package_repository.UCA_KEYRING_PACKAGE], check=True
    )


@patch(
    "subprocess.run",
    side_effect=subprocess.CalledProcessError(
        1,
        cmd="dpkg --status ubuntu-cloud-keyring",
        stderr=b"unknown error",
    ),
)
def test_install_uca_keyring_unknown_error(subprocess_patched):
    with pytest.raises(subprocess.CalledProcessError):
        apt_uca.install_uca_keyring()
    assert subprocess_patched.call_count == 1


@patch("urllib.request.urlopen", return_value=Mock(status=http.HTTPStatus.OK))
def test_check_release_compatibility(urllib):
    assert apt_uca.check_release_compatibility("jammy", "antelope") is None


@patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("", http.HTTPStatus.NOT_FOUND, "NOT FOUND", {}, None))  # type: ignore
def test_check_release_compatibility_invalid(urllib):
    with pytest.raises(
        errors.AptUCAInstallError,
        match="Failed to install UCA 'invalid-cloud/updates': not a valid release for 'jammy'",
    ):
        apt_uca.check_release_compatibility("jammy", "invalid-cloud")


@patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("", http.HTTPStatus.BAD_GATEWAY, "BAD GATEWAY", {}, None))  # type: ignore
def test_check_release_compatibility_bad_gateway(urllib):
    with pytest.raises(
        errors.AptUCAInstallError,
        match="Failed to install UCA 'antelope/updates': unexpected status code 502: 'BAD GATEWAY' while fetching release",
    ):
        apt_uca.check_release_compatibility("jammy", "antelope")
