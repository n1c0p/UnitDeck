# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 Nicola Palmieri (n1c0p)
#
# RPM spec for the staging tree built by packaging/stage.sh; invoked by packaging/build-rpm.sh
# with _version and _stage defined. The bundle is self-contained, so automatic dependency
# scanning is off and the system libraries it needs are listed by soname.

%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none

Name:           unitdeck
Version:        %{_version}
Release:        1
Summary:        Desktop application to manage systemd services
License:        GPL-3.0-or-later
URL:            https://github.com/n1c0p/UnitDeck
BuildArch:      x86_64
AutoReqProv:    no

Requires:       python3
Requires:       polkit
Requires:       systemd
Requires:       libxcb-cursor.so.0()(64bit)
Requires:       libEGL.so.1()(64bit)
Requires:       libGL.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       libxkbcommon-x11.so.0()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libfontconfig.so.1()(64bit)
Requires:       libfreetype.so.6()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libgmodule-2.0.so.0()(64bit)
Requires:       libgthread-2.0.so.0()(64bit)
Requires:       libgssapi_krb5.so.2()(64bit)
Requires:       libssl.so.3()(64bit)
Requires:       libcrypto.so.3()(64bit)
Requires:       libz.so.1()(64bit)
Requires:       liblzma.so.5()(64bit)
Requires:       libzstd.so.1()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libffi.so.8()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libX11-xcb.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxcb-icccm.so.4()(64bit)
Requires:       libxcb-image.so.0()(64bit)
Requires:       libxcb-keysyms.so.1()(64bit)
Requires:       libxcb-randr.so.0()(64bit)
Requires:       libxcb-render.so.0()(64bit)
Requires:       libxcb-render-util.so.0()(64bit)
Requires:       libxcb-shape.so.0()(64bit)
Requires:       libxcb-shm.so.0()(64bit)
Requires:       libxcb-sync.so.1()(64bit)
Requires:       libxcb-xfixes.so.0()(64bit)
Requires:       libxcb-xkb.so.1()(64bit)
Requires:       libxcb-util.so.1()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Requires:       libwayland-cursor.so.0()(64bit)
Requires:       libwayland-egl.so.1()(64bit)
Recommends:     gtk3
Recommends:     xdg-utils

%description
UnitDeck manages systemd system and user services from a graphical
interface: start, stop, restart, enable, mask, edit with drop-ins, create
from templates and read the journal, with live updates over D-Bus.

The interface runs as a normal user: privileged actions are authorized
through polkit, and system unit files are written by a small helper
launched with pkexec.

%install
mkdir -p %{buildroot}
cp -a %{_stage}/. %{buildroot}/

%post
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi

%postun
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi

%files
/opt/unitdeck
/usr/bin/unitdeck
/usr/libexec/unitdeck/unitdeck-helper
/usr/share/applications/eu.nicop.unitdeck.desktop
/usr/share/icons/hicolor/scalable/apps/eu.nicop.unitdeck.svg
/usr/share/polkit-1/actions/eu.nicop.unitdeck.policy
%doc /usr/share/doc/unitdeck/copyright
/usr/share/man/man1/unitdeck.1.gz
